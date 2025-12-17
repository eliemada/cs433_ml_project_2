"""
Dolphin model wrapper for document understanding.
"""

from typing import List, Union

import torch
from PIL import Image
from transformers import AutoProcessor, VisionEncoderDecoderModel

from rag_pipeline.pdf_parsing.config import DolphinModelConfig
from rag_pipeline.pdf_parsing.core.exceptions import ModelLoadError
from rag_pipeline.pdf_parsing.core.interfaces import ModelWrapper


class DolphinModel(ModelWrapper):
    """
    Wrapper for ByteDance Dolphin vision-language model.

    Handles model loading, device management, and inference.
    """

    def __init__(self, config: DolphinModelConfig):
        """
        Initialize Dolphin model wrapper.

        Args:
            config: Model configuration
        """
        self.config = config
        self.processor = None
        self.model = None
        self.tokenizer = None
        self.device = None
        self._loaded = False

    def load(self) -> None:
        """Load model into memory."""
        if self._loaded:
            print("Model already loaded")
            return

        try:
            model_path = str(self.config.model_path)

            # Load processor and model
            print(f"Loading Dolphin model from {model_path}...")
            self.processor = AutoProcessor.from_pretrained(model_path, use_fast=True)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_path)
            self.model.eval()

            # Set device
            if self.config.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = self.config.device

            self.model.to(self.device)

            # Set precision
            if self.device == "cuda" and self.config.use_fp16:
                self.model = self.model.half()
                print("Using FP16 precision on CUDA")
            else:
                self.model = self.model.float()
                print("Using FP32 precision")

            # Set tokenizer
            self.tokenizer = self.processor.tokenizer

            self._loaded = True
            print(f"Model loaded successfully on {self.device}")

        except Exception as e:
            raise ModelLoadError(f"Failed to load Dolphin model: {str(e)}")

    def unload(self) -> None:
        """Unload model from memory."""
        if not self._loaded:
            return

        try:
            del self.model
            del self.processor
            del self.tokenizer

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._loaded = False
            print("Model unloaded successfully")

        except Exception as e:
            print(f"Error unloading model: {str(e)}")

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded

    def infer(self, prompt: str, image: Image.Image) -> str:
        """
        Single inference.

        Args:
            prompt: Text prompt for the model
            image: Input image

        Returns:
            Model output text
        """
        if not self._loaded:
            self.load()

        results = self.infer_batch([prompt], [image])
        return results[0]

    def infer_batch(self, prompts: List[str], images: List[Image.Image]) -> List[str]:
        """
        Batch inference.

        Args:
            prompts: List of text prompts
            images: List of input images

        Returns:
            List of model output texts
        """
        if not self._loaded:
            self.load()

        try:
            # Ensure prompts and images are lists
            if not isinstance(images, list):
                images = [images]
            if not isinstance(prompts, list):
                prompts = [prompts]

            # If single prompt for multiple images, replicate it
            if len(prompts) == 1 and len(images) > 1:
                prompts = prompts * len(images)

            # Prepare images
            batch_inputs = self.processor(images, return_tensors="pt", padding=True)

            # Set dtype based on device and config
            if self.device == "cuda" and self.config.use_fp16:
                batch_pixel_values = batch_inputs.pixel_values.half().to(self.device)
            else:
                batch_pixel_values = batch_inputs.pixel_values.float().to(self.device)

            # Prepare prompts
            formatted_prompts = [f"<s>{p} <Answer/>" for p in prompts]
            batch_prompt_inputs = self.tokenizer(
                formatted_prompts, add_special_tokens=False, return_tensors="pt"
            )

            batch_prompt_ids = batch_prompt_inputs.input_ids.to(self.device)
            batch_attention_mask = batch_prompt_inputs.attention_mask.to(self.device)

            # Generate text
            with torch.no_grad():
                outputs = self.model.generate(
                    pixel_values=batch_pixel_values,
                    decoder_input_ids=batch_prompt_ids,
                    decoder_attention_mask=batch_attention_mask,
                    min_length=1,
                    max_length=4096,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=True,
                    bad_words_ids=[[self.tokenizer.unk_token_id]],
                    return_dict_in_generate=True,
                    do_sample=False,
                    num_beams=1,
                )

            # Decode outputs
            sequences = self.tokenizer.batch_decode(outputs.sequences, skip_special_tokens=False)

            # Clean prompt text from output
            results = []
            for i, sequence in enumerate(sequences):
                cleaned = (
                    sequence.replace(formatted_prompts[i], "")
                    .replace("<pad>", "")
                    .replace("</s>", "")
                    .strip()
                )
                results.append(cleaned)

            return results

        except Exception as e:
            raise Exception(f"Inference error: {str(e)}")

    def chat(self, prompt: Union[str, List[str]], image: Union[Image.Image, List[Image.Image]]) -> Union[str, List[str]]:
        """
        Convenience method compatible with Dolphin demo_page.py interface.

        Args:
            prompt: Text prompt or list of prompts
            image: PIL Image or list of images

        Returns:
            Generated text or list of texts
        """
        is_batch = isinstance(image, list)

        if not is_batch:
            return self.infer(prompt, image)
        else:
            prompts = prompt if isinstance(prompt, list) else [prompt] * len(image)
            return self.infer_batch(prompts, image)