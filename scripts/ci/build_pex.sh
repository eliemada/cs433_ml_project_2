#!/usr/bin/env bash
# ==============================================================================
# Build PEX executables for API and Worker packages
# Uses uv for fast dependency resolution and pex for bundling
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PACKAGE="${1:-}"

# Auto-detect platform if not specified
if [[ -z "${2:-}" ]]; then
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        # Apple Silicon - default to linux/arm64 for Docker deployment
        PLATFORM="aarch64-manylinux2014"
    elif [[ "$ARCH" == "aarch64" ]]; then
        PLATFORM="aarch64-manylinux2014"
    elif [[ "$ARCH" == "x86_64" ]]; then
        PLATFORM="x86_64-manylinux2014"
    else
        echo -e "${RED}Unknown architecture: $ARCH${NC}"
        echo "Please specify platform manually"
        exit 1
    fi
else
    PLATFORM="${2}"
fi

BUILD_DIR="build/${PACKAGE}"
DIST_DIR="dist"

usage() {
    echo "Usage: $0 <package> [platform]"
    echo ""
    echo "Arguments:"
    echo "  package   - Package to build (api or worker)"
    echo "  platform  - Target platform (default: current platform)"
    echo ""
    echo "Examples:"
    echo "  $0 api                           # Build for current platform"
    echo "  $0 worker x86_64-manylinux2014   # Build for linux/amd64"
    echo "  $0 api aarch64-manylinux2014     # Build for linux/arm64"
    exit 1
}

if [[ -z "$PACKAGE" ]] || [[ "$PACKAGE" != "api" && "$PACKAGE" != "worker" ]]; then
    usage
fi

echo -e "${GREEN}Building PEX for ${PACKAGE} (platform: ${PLATFORM})${NC}"

# Clean build directory
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"
mkdir -p "${DIST_DIR}"

# Step 1: Lock workspace dependencies
echo -e "${YELLOW}[1/5] Locking workspace dependencies...${NC}"
uv pip compile pyproject.toml \
    --quiet \
    --python-platform="${PLATFORM}" \
    --format pylock.toml \
    -o "${BUILD_DIR}/pylock.toml"

# Step 2: Build wheels for all workspace packages
echo -e "${YELLOW}[2/5] Building wheels...${NC}"
uv build --wheel --out-dir "${BUILD_DIR}/wheels" packages/shared
uv build --wheel --out-dir "${BUILD_DIR}/wheels" "packages/${PACKAGE}"

# Step 3: Create venv and install all dependencies
echo -e "${YELLOW}[3/5] Installing dependencies into venv...${NC}"
uv venv --clear "${BUILD_DIR}/install.venv"
uv pip install \
    --quiet \
    --python "${BUILD_DIR}/install.venv" \
    --python-platform="${PLATFORM}" \
    --no-index \
    --find-links "${BUILD_DIR}/wheels" \
    "rag_pipeline" "${PACKAGE}"

# Step 4: Generate requirements.txt for pex
echo -e "${YELLOW}[4/5] Generating requirements.txt...${NC}"
uv pip list \
    --python "${BUILD_DIR}/install.venv" \
    --format freeze \
    --quiet \
    > "${BUILD_DIR}/requirements.all.txt"

# Step 5: Build the pex executable
echo -e "${YELLOW}[5/5] Building PEX executable...${NC}"

if [[ "$PACKAGE" == "api" ]]; then
    # API: FastAPI server executable
    uvx pex \
        --include-tools \
        --project="${BUILD_DIR}/wheels/api-0.1.0-py3-none-any.whl" \
        --requirements="${BUILD_DIR}/requirements.all.txt" \
        --venv-repository "${BUILD_DIR}/install.venv/" \
        --exe uvicorn \
        --script uvicorn \
        -o "${DIST_DIR}/${PACKAGE}.pex"

    echo -e "${GREEN}✓ Built ${DIST_DIR}/${PACKAGE}.pex${NC}"
    echo -e "  Run with: ${DIST_DIR}/${PACKAGE}.pex api.main:app --host 0.0.0.0 --port 8000"

elif [[ "$PACKAGE" == "worker" ]]; then
    # Worker: Distributed PDF processing executable (console script mode)
    uvx pex \
        --include-tools \
        --project="${BUILD_DIR}/wheels/worker-0.1.0-py3-none-any.whl" \
        --requirements="${BUILD_DIR}/requirements.all.txt" \
        --venv-repository "${BUILD_DIR}/install.venv/" \
        --python-shebang '/usr/bin/env python3' \
        -o "${DIST_DIR}/${PACKAGE}.pex"

    echo -e "${GREEN}✓ Built ${DIST_DIR}/${PACKAGE}.pex${NC}"
    echo -e "  Run with: ${DIST_DIR}/${PACKAGE}.pex -m worker.distributed_worker"
fi

# Show size
SIZE=$(du -h "${DIST_DIR}/${PACKAGE}.pex" | cut -f1)
echo -e "${GREEN}PEX size: ${SIZE}${NC}"
