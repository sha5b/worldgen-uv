# File: app/main.py
# Purpose: Minimal entry point to verify the uv-based Windows environment for WorldGen.
# Connection: Used to check CUDA PyTorch, import of WorldGen, and demonstrate a stub prompt call.

import argparse
import sys


def check_environment() -> int:
    try:
        import torch  # noqa: F401
        from torch import cuda
        print(f"torch: {torch.__version__}")
        print(f"CUDA available: {cuda.is_available()}")
        if cuda.is_available():
            try:
                print(f"CUDA device count: {cuda.device_count()}")
                print(f"Current device: {cuda.current_device()}")
                print(f"Device name: {cuda.get_device_name(cuda.current_device())}")
            except Exception as e:  # pragma: no cover
                print(f"Warning: failed to query CUDA device info: {e}")
        else:
            print("Warning: CUDA is not available. Make sure you installed torch with CUDA 12.8 wheels.")
    except Exception as e:
        print(f"Failed to import torch or query CUDA: {e}")
        return 1

    # Try importing worldgen
    try:
        import worldgen  # type: ignore
        print(f"worldgen imported: version={getattr(worldgen, '__version__', 'unknown')}")
    except Exception as e:
        print(f"Failed to import worldgen: {e}")
        return 2

    return 0


def run_prompt(prompt: str) -> int:
    try:
        # The actual API surface may change upstream; attempt a minimal flow.
        from worldgen import WorldGen  # type: ignore
    except Exception as e:
        print("Could not import WorldGen from worldgen. Make sure the package installed correctly.")
        print(f"Import error: {e}")
        return 3

    try:
        print(f"Generating scene for prompt: {prompt}")
        wg = WorldGen()
        # The upstream README shows: worldgen.generate_world("<TEXT>")
        result = wg.generate_world(prompt)
        print("Generation finished.")
        if result is not None:
            print(f"Result: {type(result)}")
        return 0
    except Exception as e:
        print("WorldGen generation failed. Check dependencies, GPU availability, and upstream API.")
        print(f"Error: {e}")
        return 4


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="WorldGen uv Windows verifier")
    parser.add_argument("--check", action="store_true", help="Only check environment and imports")
    parser.add_argument("--prompt", type=str, default="", help="Text prompt to generate a scene")
    args = parser.parse_args(argv)

    if args.check:
        return check_environment()

    if args.prompt:
        return run_prompt(args.prompt)

    print("No action specified. Use --check or --prompt \"...\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
