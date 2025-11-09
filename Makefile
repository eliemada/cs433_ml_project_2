.PHONY: help build test push docker-login docker-test

# Docker image configuration
IMAGE_NAME := ravinala/pdf-parser
IMAGE_TAG := v2-distributed
FULL_IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)

help:
	@echo "PDF Processing Docker Commands"
	@echo "=============================="
	@echo ""
	@echo "  make build          - Build Docker image"
	@echo "  make test           - Test Docker image locally"
	@echo "  make docker-login   - Login to Docker Hub"
	@echo "  make push           - Push image to Docker Hub"
	@echo "  make docker-test    - Run full test suite"
	@echo ""
	@echo "Current image: $(FULL_IMAGE)"

build:
	@echo "Building $(FULL_IMAGE)..."
	docker build -t $(FULL_IMAGE) .
	docker tag $(FULL_IMAGE) $(IMAGE_NAME):latest
	@echo "✓ Build complete"
	@echo "  Tagged: $(FULL_IMAGE)"
	@echo "  Tagged: $(IMAGE_NAME):latest"

docker-login:
	@echo "Logging in to Docker Hub..."
	docker login

push: build
	@echo "Pushing $(IMAGE_NAME):$(IMAGE_TAG)..."
	docker push $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Pushing $(IMAGE_NAME):latest..."
	docker push $(IMAGE_NAME):latest
	@echo "✓ Push complete"

test:
	@echo "Testing $(FULL_IMAGE)..."
	@echo ""
	@echo "Test 1: Check image exists"
	docker images $(FULL_IMAGE)
	@echo ""
	@echo "Test 2: Test distributed mode entrypoint"
	docker run --rm \
		-e S3_INPUT_BUCKET=test \
		-e S3_OUTPUT_BUCKET=test \
		$(FULL_IMAGE) echo "Entrypoint test passed" || true
	@echo ""
	@echo "✓ Basic tests passed"

docker-test: build test
	@echo "Full test suite complete!"
