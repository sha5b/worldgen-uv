#!/usr/bin/env bash
# File: worldgen-uv/setup-wsl.sh
# Purpose: Linux-side provisioning for WorldGen inside WSL2 (Ubuntu 22.04) using CONDA exactly like upstream.
# Connection: This script is invoked by provision-worldgen-wsl.ps1 and mirrors the upstream README:
# - conda create -n worldgen python=3.11
# - conda activate worldgen
# - pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu128
# - pip install . (from the WorldGen repo)

set -euo pipefail

echo "[WSL] Updating apt and ensuring base tooling..."
sudo apt-get update -y
# Tools needed: curl/git for setup, plus build-essential, cmake, and ninja for building PyTorch3D
sudo apt-get install -y curl git build-essential cmake ninja-build

# Install Miniconda (user local) if conda is not available
if ! command -v conda >/dev/null 2>&1; then
  echo "[WSL] Installing Miniconda..."
  MINICONDA_SH="$HOME/miniconda.sh"
  curl -L "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" -o "$MINICONDA_SH"
  if [[ -d "$HOME/miniconda3" ]]; then
    echo "[WSL] Existing Miniconda detected at $HOME/miniconda3 — updating in-place (-u)..."
    bash "$MINICONDA_SH" -b -u -p "$HOME/miniconda3"
  else
    bash "$MINICONDA_SH" -b -p "$HOME/miniconda3"
  fi
  rm -f "$MINICONDA_SH"
  # Initialize conda for bash
  "$HOME/miniconda3/bin/conda" init bash
  # Load conda in this shell
  source "$HOME/.bashrc" || true
fi

# Ensure conda is available now
if ! command -v conda >/dev/null 2>&1; then
  export PATH="$HOME/miniconda3/bin:$PATH"
fi

echo "[WSL] conda: $(conda --version)"

# Configure conda to use conda-forge ONLY (no implicit defaults) to avoid Anaconda TOS prompts
echo "[WSL] Configuring conda to use conda-forge only (strict priority, no defaults)..."
conda config --set always_yes true
conda config --set auto_activate_base false
# Remove existing channel definitions
conda config --remove-key channels || true
conda config --remove-key default_channels || true
# Add conda-forge explicitly for both channels and default_channels
conda config --add channels conda-forge
conda config --add default_channels https://conda.anaconda.org/conda-forge
conda config --set channel_priority strict

# Load optional .env file from project root to supply secrets like Hugging Face token
if [[ -f .env ]]; then
  echo "[WSL] Loading .env from project root..."
  # shellcheck disable=SC2046
  export $(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env | xargs -0 -I {} bash -lc 'echo {}' 2>/dev/null || true)
fi

# Create env exactly as upstream recommends (override if it already exists)
if conda env list | grep -q "^worldgen\s"; then
  echo "[WSL] Removing existing conda env 'worldgen' for a clean setup..."
  conda remove -y -n worldgen --all || true
fi
echo "[WSL] Creating conda env 'worldgen' (python=3.11)..."
conda create -y -n worldgen python=3.11

echo "[WSL] Installing CUDA 12.8 PyTorch/torchvision in 'worldgen' via pip..."
conda run -n worldgen python -m pip install --upgrade pip
conda run -n worldgen pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision

# Web control panel dependency
echo "[WSL] Installing Gradio for the web control panel..."
conda run -n worldgen pip install gradio

# Video export dependency for imageio MP4 writer used by demo.py
echo "[WSL] Installing imageio-ffmpeg and ffmpeg for MP4 writing..."
conda run -n worldgen pip install imageio-ffmpeg
sudo apt-get update -y && sudo apt-get install -y ffmpeg || true

# Ensure Hugging Face CLI is available for authentication
echo "[WSL] Installing huggingface_hub with CLI..."
conda run -n worldgen pip install -U "huggingface_hub[cli]"

# If a Hugging Face token is provided via .env, log in non-interactively
HF_TOKEN_VALUE="${HUGGINGFACE_TOKEN:-${HF_TOKEN:-}}"
if [[ -n "${HF_TOKEN_VALUE}" ]]; then
  echo "[WSL] Logging in to Hugging Face via token from .env (hf auth login)..."
  # Configure git credential helper to avoid interactive git prompts with the Hub
  conda run -n worldgen git config --global credential.helper store || true
  conda run -n worldgen hf auth login --token "${HF_TOKEN_VALUE}" --add-to-git-credential || true
else
  echo "[WSL] No HUGGINGFACE_TOKEN/HF_TOKEN found in .env; you can login later via 'huggingface-cli login' inside the env."
fi

# Clone the upstream WorldGen repo and install it (pip install .)
mkdir -p external
if [[ ! -d external/WorldGen/.git ]]; then
  echo "[WSL] Cloning WorldGen..."
  git clone https://github.com/ZiYang-xie/WorldGen.git external/WorldGen
fi

echo "[WSL] Installing WorldGen (pip install .) into 'worldgen' env..."
conda run -n worldgen pip install -e external/WorldGen

# Install PyTorch3D (required by WorldGen deps but not installed automatically on some setups)
echo "[WSL] Installing PyTorch3D (this may take a while; building from source)..."
conda run -n worldgen pip install "git+https://github.com/facebookresearch/pytorch3d.git" || true

# Verify environment using our small checker under the same env
echo "[WSL] Verifying environment..."
conda run -n worldgen python ./app/main.py --check || true

echo "[WSL] Setup complete. To use the environment inside WSL, run:"
echo "       conda activate worldgen"
echo "       python ./app/main.py --prompt 'a cozy wooden cabin interior at sunset'"
