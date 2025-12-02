"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InputComposerProps {
    onSend: (message: string) => void;
    isTyping?: boolean;
    dict: any;
}

export function InputComposer({ onSend, isTyping, dict }: InputComposerProps) {
    const [input, setInput] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || isTyping) return;
        onSend(input);
        setInput('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
        }
    }, [input]);

    return (
        <div className="w-full max-w-3xl mx-auto">
            {/* Starter Chips (only show if empty input and no history - simplified logic for now just show if empty) */}
            {input === '' && (
                <div className="flex flex-wrap gap-2 mb-4 justify-center">
                    {dict.starters.map((prompt: string, idx: number) => (
                        <button
                            key={idx}
                            onClick={() => setInput(prompt)}
                            className="text-xs bg-secondary/50 hover:bg-secondary text-secondary-foreground px-3 py-1.5 rounded-full transition-colors border border-transparent hover:border-border"
                        >
                            {prompt}
                        </button>
                    ))}
                </div>
            )}

            <form onSubmit={handleSubmit} className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-purple-500/20 rounded-2xl blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />

                <div className="relative bg-card border border-border shadow-sm rounded-2xl overflow-hidden focus-within:ring-1 focus-within:ring-primary/50 transition-all">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={dict.placeholder}
                        className="w-full max-h-[200px] min-h-[60px] p-4 pr-14 bg-transparent resize-none outline-none text-foreground placeholder:text-muted-foreground/70"
                        rows={1}
                    />

                    <button
                        type="submit"
                        disabled={!input.trim() || isTyping}
                        className={cn(
                            "absolute right-2 bottom-2 p-2 rounded-xl transition-all duration-200",
                            input.trim() && !isTyping
                                ? "bg-primary text-primary-foreground hover:opacity-90 shadow-md"
                                : "bg-muted text-muted-foreground cursor-not-allowed"
                        )}
                    >
                        {isTyping ? (
                            <Sparkles className="w-5 h-5 animate-pulse" />
                        ) : (
                            <Send className="w-5 h-5" />
                        )}
                    </button>
                </div>
            </form>

            <div className="text-center mt-3">
                <p className="text-[10px] text-muted-foreground">
                    {dict.disclaimer}
                </p>
            </div>
        </div>
    );
}
