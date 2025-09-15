# File: README.md
# Purpose: Quickstart guide for the uv-based Windows setup for WorldGen.
# Connection: Documents how to install CUDA-enabled PyTorch, sync dependencies with uv, and install the
# upstream WorldGen repository in editable mode without its Linux-only deps.

# WorldGen on WSL2 via conda (upstream exact)

This project contains automation and docs to install the upstream [WorldGen](https://github.com/ZiYang-xie/WorldGen) inside WSL2 (Ubuntu-22.04) using conda — exactly as their README describes. This path is the most compatible (Linux wheels for Triton/xformers, etc.).

Important notes:

- We install `torch` and `torchvision` from the official CUDA 12.8 wheel index first.
- We then run `uv sync` to install the rest of the dependencies from `pyproject.toml`.
- We install the upstream `WorldGen` repo in editable mode with `--no-deps` so that uv continues to fully control dependencies.
- The upstream `nunchaku` wheel is Linux-only; we omit it on Windows.

## Quickstart

1) Install once (inside WSL)

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv && bash ./setup-wsl.sh"
```

This creates a conda env `worldgen`, installs CUDA PyTorch, Gradio, imageio-ffmpeg, and all deps for the upstream `WorldGen`.

2) Launch the Web UI (from Windows PowerShell)

```powershell
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate worldgen && python "/mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv/app/web_ui.py" --port 8080'
```

Open http://localhost:7860

3) Generate a scene

- Set Viewer URL: `http://localhost:8080` (default)
- Enter a Text Prompt, or upload an Image (image takes priority; prompt becomes optional guidance)
- Optional: Return Mesh (view as mesh), Save Scene (export assets), Output Dir (e.g., `output`)
- Optional: GPU ID (use 0 if `nvidia-smi` shows a single GPU)
- Click Generate

4) Outputs and naming

- With Save Scene ON, exports are written under a folder auto-named from `image_stem__prompt` (or just `prompt`):
  - `<base>.ply` (original splat)
  - `<base>_xyzrgb.ply` (XYZ + uint8 RGB, Blender-friendly)
  - `<base>.glb` (mesh with vertex colors)
  - `images/` frames and `<base>.mp4` when you run Save Novel Views

The Output Dir textbox can be relative (saved under this repo) or absolute.

## Usage Details

### Image vs Prompt

- If an image is provided, image-to-scene runs and the prompt is optional guidance.
- If no image is provided, text-to-scene runs with the prompt only.

### GPU selection

- In the Web UI set GPU ID (e.g., `0`). The launcher pins `CUDA_VISIBLE_DEVICES` so the selected GPU is used.
- Verify with:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc 'nvidia-smi --query-gpu=index,name,memory.total --format=csv'
```

### Camera Path and Novel Views

- In the Viser side panel:
  - Camera Path: set Interpolation Steps, click Generate Camera Path.
  - Render Settings: set Render FoV/Height/Width.
  - Click Save Novel Views to render frames to `images/` and a video `<base>.mp4`.
- Note: This renders new viewpoints of the existing scene; it does not generate new geometry.

### Viewer clipping range

- Clipping planes are extended to avoid early cut-offs and re-applied during path generation and rendering.

### Blender import tips

- Point cloud: import `<base>_xyzrgb.ply` (guarantees visible colors). In Shader Editor, use Color Attribute (often `Col`) to drive Principled Base Color. For solid look, instance tiny spheres via Geometry Nodes.
- Mesh: import `<base>.glb`. Vertex colors are imported as a color attribute; wire it to Base Color if not auto-wired.

## Troubleshooting

- No colors in Blender:
  - Use `<base>_xyzrgb.ply` (uint8 RGB). In Shader, select the correct Color Attribute name.

- MP4 writer warning about macro_block_size:
  - Use a render height divisible by 16 (e.g., 1088 instead of 1080), or we can change the writer settings if needed.

- Progress not visible during Save Novel Views:
  - Logs now print progress lines every 10 frames; keep Auto-refresh logs enabled in the Web UI.

- Outputs not appearing in Windows repo:
  - The Web UI resolves relative Output Dir to the repo on Windows automatically and shows the resolved path in logs.

## Direct demo.py commands (optional)

Inside WSL, after `conda activate worldgen` and `cd external/WorldGen`:

```bash
# Text-only
python demo.py -p "A beautiful landscape with a river and mountains"

# Image-to-scene (prompt optional)
python demo.py -i "/mnt/c/path/to/your/image.jpg" -p "Optional guidance"

# Mesh mode
python demo.py -p "A beautiful landscape with a river and mountains" --return_mesh
```

Use `-o <abs_or_rel_output_dir>` and `--save_scene` to write exports.

## Prerequisites

- Python 3.11 (uv will also manage a virtual environment)
- NVIDIA driver with CUDA 12.8 capability installed (see `nvidia-smi` output)
- Windows 10/11 64-bit

Install `uv` if you don't have it:

```powershell
pip install uv
```

### Web control panel (Gradio)

A lightweight control panel to start WorldGen runs from your browser, with fields for prompt, image upload, mesh toggle, and viewer port. It proxies to the upstream `demo.py` and streams logs.

Launch it from PowerShell:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate worldgen && python "/mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv/app/web_ui.py" --port 8080'
```

Open the Gradio panel at:
- http://localhost:7860

Controls:
- Text Prompt
- Image upload (optional)
- Return Mesh (toggle)
- Viewer Port (defaults to 8080)
- Generate / Stop and a Logs panel

## Setup on Windows (PowerShell)

Run the following commands from this project directory `worldgen-uv/`:

```powershell
# 1) Create and activate a virtual environment managed by uv
uv venv
. .\.venv\Scripts\Activate.ps1

# 2) Install CUDA 12.8 builds of torch and torchvision first
uv pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision

# 3) Install remaining dependencies from pyproject.toml
uv sync

# 4) Install WorldGen in editable mode without pulling its deps (we manage them via uv)
uv pip install --no-deps -e git+https://github.com/ZiYang-xie/WorldGen.git#egg=worldgen

# 5) Verify the environment
uv run python .\app\main.py --check
```

If you plan to use the demo or training features that require additional assets/models, follow the upstream repo instructions.

## Optional (Linux-only extra)

If you later use Linux and want `nunchaku`, you can install the `linux` extra group or install the wheel directly. We've provided an optional group in `pyproject.toml` for documentation, but it is not installed by default and is marked non-win32.

## Running a basic generation

Once everything is installed, you can try using WorldGen programmatically. The `app/main.py` includes a stub demonstrating where you'd call the API. The real API surface may evolve upstream, so consult the upstream README for up-to-date usage.

```powershell
uv run python .\app\main.py --prompt "a cozy wooden cabin interior at sunset"
```

This should invoke WorldGen and print placeholders or perform minimal API calls if available.

## WSL2 automated setup (recommended for full Linux compatibility)

If you prefer a Linux environment (recommended for packages like Triton/xformers), use WSL2 with Ubuntu 22.04. This repo includes automation scripts:

- `worldgen-uv/provision-worldgen-wsl.ps1` (PowerShell, Windows host)
- `worldgen-uv/setup-wsl.sh` (Bash, runs inside WSL)

Steps (PowerShell):

```powershell
# From the project folder: worldgen-uv/
# Optionally allow this session to run the provisioning script
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Provision WSL and run Linux-side setup inside Ubuntu-22.04
./provision-worldgen-wsl.ps1
```

What this does:

 - Ensures WSL and the `Ubuntu-22.04` distro are installed.
 - Maps this project path into WSL (`/mnt/c/...`).
 - Runs `setup-wsl.sh`, which follows the upstream WorldGen instructions using conda:
   - Installs/updates Miniconda in-place (uses `-u` if already present) and configures conda-forge only (avoids Anaconda TOS).
   - Recreates the `worldgen` conda env with Python 3.11 (removes any existing env first).
   - Installs CUDA 12.8 `torch` and `torchvision` via the PyTorch index.
   - Installs build tools (`build-essential`, `cmake`, `ninja-build`) for PyTorch3D.
   - Clones WorldGen and runs `pip install -e external/WorldGen` (same as `pip install .`).
   - Installs PyTorch3D from source if needed.
   - Verifies the environment with our checker script.

After provisioning, open a WSL shell (Ubuntu-22.04), cd to this folder under `/mnt/c/.../worldgen-uv`, and run:

```bash
conda activate worldgen
python ./app/main.py --check
python ./app/main.py --prompt "a cozy wooden cabin interior at sunset"
```

This approach mirrors upstream Linux expectations closely and avoids Windows-only wheel limitations.

bash "$HOME/miniconda.sh" -b -p "$HOME/miniconda3"
source "$HOME/.bashrc"

# 2) Configure conda-forge channels (optional but recommended)
conda config --set always_yes true
conda config --set auto_activate_base false
conda config --remove-key channels || true
conda config --add channels conda-forge
conda config --set channel_priority strict

# 3) Create and activate env
conda create -y -n worldgen python=3.11
conda activate worldgen

# 4) Install CUDA 12.8 wheels for torch/torchvision
pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision

# 5) Clone and install WorldGen exactly as upstream
git clone https://github.com/ZiYang-xie/WorldGen.git
cd WorldGen
pip install .
cd /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv

# 6) Verify
python ./app/main.py --check
python ./app/main.py --prompt "a cozy wooden cabin interior at sunset"
```

## How to run

After provisioning is complete, you can run WorldGen via our minimal script.

### From a WSL (Ubuntu-22.04) shell

```bash
conda activate worldgen
cd /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv
python ./app/main.py --prompt "a cozy wooden cabin interior at sunset"
```

### From Windows PowerShell (one-liner via WSL)

```powershell
# Use absolute path to conda. IMPORTANT: use single quotes so PowerShell does not expand $HOME.
wsl -d Ubuntu-22.04 -- bash -lc '$HOME/miniconda3/bin/conda run -n worldgen python /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv/app/main.py --prompt "a cozy wooden cabin interior at sunset"'
```

Alternative (source conda.sh then activate):

```powershell
# Alternative: source conda.sh then activate. Again, single quotes prevent PowerShell from expanding $HOME.
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate worldgen && python /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv/app/main.py --prompt "a cozy wooden cabin interior at sunset"'
```

Note: If you accidentally use double quotes in PowerShell, `$HOME` gets expanded on Windows (e.g., `C:\Users\sha5b`) and will not be a valid Linux path. Use single quotes as shown.

### Interactive viewer (WorldGen demo with Viser)

Run the official WorldGen demo server to visualize and explore scenes in your browser via Viser.

```powershell
# Start the Viser demo server (opens http://localhost:8080)
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate worldgen && cd /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv/external/WorldGen && python demo.py -p "a cozy wooden cabin interior at sunset"'
```

Open: http://localhost:8080

Variants:

```powershell
# Change the prompt
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate worldgen && cd /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv/external/WorldGen && python demo.py -p "a beautiful landscape with a river and mountains"'

# Image-to-scene
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate worldgen && cd /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv/external/WorldGen && python demo.py -i "/mnt/c/Path/To/your_image.jpg" -p "optional text description"'

# Use a different port if 8080 is busy
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate worldgen && cd /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv/external/WorldGen && python demo.py -p "..." --port 8081'
```

## Troubleshooting and bugfixes

Use this section to fix common issues encountered during setup and the first run.

- __Conda not found from PowerShell one-liner__
  - Use single quotes so `$HOME` is not expanded by PowerShell.
  - Example: `wsl -d Ubuntu-22.04 -- bash -lc '$HOME/miniconda3/bin/conda --version'`

- __Anaconda Terms of Service prompt__
  - The script configures conda-forge as the only channel to avoid TOS prompts. If you still see TOS prompts, run:
  - `conda config --remove-key channels || true`
  - `conda config --remove-key default_channels || true`
  - `conda config --add channels conda-forge`
  - `conda config --add default_channels https://conda.anaconda.org/conda-forge`
  - `conda config --set channel_priority strict`

- __No module named pytorch3d__
  - The setup installs PyTorch3D from source; this requires build tools.
  - Ensure these are installed inside WSL:
  - `sudo apt-get install -y build-essential cmake ninja-build`
  - Then (inside env):
  - `pip install "git+https://github.com/facebookresearch/pytorch3d.git"`

- __g++ missing while building pytorch3d__
  - Install toolchain: `sudo apt-get install -y build-essential`

- __UniK3D KNN compile warning (only for evaluation)__
  - Optional; generation typically works without it. To compile:
  - `source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate worldgen && KNN_DIR="$(python -c "import unik3d, os; print(os.path.join(os.path.dirname(unik3d.__file__), 'ops','knn'))")" && cd "$KNN_DIR" && bash compile.sh`

- __pkg_resources deprecation warning__
  - Benign. To silence: `pip install "setuptools<81"`

- __Re-running clean setup__
  - The script updates Miniconda in-place and recreates the `worldgen` env automatically. Just rerun:
  - `wsl -d Ubuntu-22.04 -- bash -lc 'cd /mnt/c/Users/sha5b/Documents/GitHub/3D-Generator/worldgen-uv && bash ./setup-wsl.sh'`

- __First run is slow / GPU shows low util__
  - Large model downloads and first-time CUDA kernel builds can take time; GPU VRAM may be reserved without much util. Use `watch -n 2 nvidia-smi` and be patient on the first run.

---

