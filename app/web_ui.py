# File: app/web_ui.py
# Purpose: Lightweight browser UI to control WorldGen generation from WSL.
# Connection: Provides controls for text prompt, image-to-scene, and mesh mode, then launches
# the upstream demo (external/WorldGen/demo.py) which serves the 3D viewer via Viser.

import argparse
import os
import shlex
import subprocess
import threading
import time
import json
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import gradio as gr

ROOT = Path(__file__).resolve().parents[1]
WORLDGEN_DIR = ROOT / "external" / "WorldGen"
DEMO_PY = WORLDGEN_DIR / "demo.py"
STATE_PATH = ROOT / ".webui_state.json"
UPLOADS_DIR = ROOT / "uploads"


class Runner:
    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()
        self.logs = ""

    def _read_stream(self, stream, prefix: str = ""):
        for line in iter(stream.readline, b""):
            text = line.decode(errors="ignore")
            with self.lock:
                self.logs += f"{prefix}{text}"
        stream.close()

    def start(self, prompt: str, image_path: Optional[str], return_mesh: bool, viewer_url: str, save_scene: bool, output_dir: str, gpu_id: int) -> Tuple[str, str]:
        if not DEMO_PY.exists():
            return ("", f"demo.py not found at: {DEMO_PY}")

        # Build the command to run demo.py with args
        cmd = ["python", str(DEMO_PY)]
        # Always pass the prompt exactly as typed, even if empty/whitespace
        cmd += ["-p", prompt]
        if image_path:
            cmd += ["-i", image_path]
        if return_mesh:
            cmd += ["--return_mesh"]
        if save_scene:
            cmd += ["--save_scene"]
        # Resolve output dir: if relative, make it under project ROOT to ensure files land in the Windows repo tree
        out_dir_abs = None
        if output_dir:
            p = Path(output_dir)
            if not p.is_absolute():
                p = ROOT / p
            # Derive a run name from prompt / image so outputs are grouped meaningfully
            def sanitize(name: str) -> str:
                name = name.strip().lower()
                # Replace non-word characters with underscore
                name = re.sub(r"[^a-z0-9\-_\.]+", "_", name)
                # Collapse repeats
                name = re.sub(r"_+", "_", name).strip("._-")
                return name[:80] if name else "run"

            run_name_parts = []
            if image_path:
                run_name_parts.append(Path(image_path).stem)
            if prompt and prompt.strip():
                run_name_parts.append(prompt.strip())
            if not run_name_parts:
                run_name_parts.append(datetime.now().strftime("%Y%m%d-%H%M%S"))
            run_name = sanitize("__".join(run_name_parts))
            p = p / run_name
            out_dir_abs = str(p)
            cmd += ["-o", out_dir_abs]

        # Determine port from viewer_url (default 8080)
        try:
            parsed = urlparse(viewer_url)
            port = parsed.port or 8080
        except Exception:
            port = 8080
        if port != 8080:
            cmd += ["--port", str(port)]

        env = os.environ.copy()
        # Pin to selected GPU by remapping it to CUDA device 0 inside the subprocess
        env["CUDA_VISIBLE_DEVICES"] = str(int(gpu_id))
        # Silence HF tokenizers fork warning
        env["TOKENIZERS_PARALLELISM"] = "false"
        # Ensure we run in project root so relative paths resolve
        cwd = str(WORLDGEN_DIR)

        # Kill previous process if running (ours), and any stray demo.py to avoid stale servers
        self.stop()
        try:
            subprocess.run(["bash", "-lc", "pkill -f 'python .*demo.py'"], cwd=cwd)
        except Exception:
            pass
        with self.lock:
            if image_path:
                self.logs = (
                    "[web-ui] Starting WorldGen (mode=i2s)\n"
                    f"[web-ui] CUDA_VISIBLE_DEVICES={gpu_id}\n"
                    + (f"[web-ui] output_dir: {out_dir_abs}\n" if out_dir_abs else "") +
                    f"[web-ui] image: {image_path}\n"
                    f"[web-ui] prompt (optional): {prompt}\n"
                )
            else:
                self.logs = (
                    "[web-ui] Starting WorldGen (mode=t2s)\n"
                    f"[web-ui] CUDA_VISIBLE_DEVICES={gpu_id}\n"
                    + (f"[web-ui] output_dir: {out_dir_abs}\n" if out_dir_abs else "") +
                    f"[web-ui] prompt: {prompt}\n"
                )

        self.proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        # Start background reader
        threading.Thread(target=self._read_stream, args=(self.proc.stdout, ""), daemon=True).start()

        url = viewer_url if viewer_url else f"http://localhost:{port}"
        return (url, "Started generation. Viewer should be available when ready.")

    def stop(self) -> str:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            finally:
                self.proc = None
                return "Stopped previously running demo."
        self.proc = None
        return "No running demo to stop."

    def get_logs(self) -> str:
        with self.lock:
            return self.logs[-8000:]


runner = Runner()
AUTO_REFRESH_ENABLED = True


def launch_ui(default_port: int = 8080):
    # Load persisted state (prompt/image/viewer_url)
    persisted = {}
    try:
        if STATE_PATH.exists():
            persisted = json.loads(STATE_PATH.read_text())
    except Exception:
        persisted = {}
    persisted_prompt = persisted.get("prompt", "a cozy wooden cabin interior at sunset")
    persisted_image = persisted.get("image_path")
    persisted_viewer_url = persisted.get("viewer_url", f"http://localhost:{default_port}")
    persisted_gpu = int(persisted.get("gpu_id", 0))

    with gr.Blocks(
        title="WorldGen Controller",
        css="""
        :root { --gap: 12px; --pad: 12px; --radius: 10px; }
        .gradio-container { padding: var(--pad); }
        .gr-row { gap: var(--gap) !important; }
        .gr-column { gap: var(--gap) !important; }

        .card { padding: var(--pad); border: 1px solid #2a2a2a; border-radius: var(--radius); background: #0f0f0f; }
        .card h3, .card label { margin-top: 0; }

        #img_preview img, #img_preview canvas {
            width: 100% !important;
            height: 220px !important; /* ~25% typical display height */
            object-fit: contain !important;
            border-radius: 8px;
            border: 1px solid #333;
            background: #111;
        }

        /* Full-width viewer gets the same card look but spans 100% */
        #viewer_card { padding: 0; border: 1px solid #2a2a2a; border-radius: var(--radius); overflow: hidden; }
        #viewer_card iframe { display: block; width: 100%; height: 720px; border: none; }
        """
    ) as demo:
        gr.Markdown(
            """
            # WorldGen Controller
            Use this panel to launch WorldGen in your browser (Viser).
            - Enter a text prompt, optionally upload an image for image-to-scene.
            - Toggle mesh mode to request mesh outputs (requires modified Viser).
            - Click Generate to start; open the viewer URL once ready.
            """
        )

        # Controls (left) + Logs (right) in the same row
        with gr.Row():
            with gr.Column(scale=2, elem_classes=["card"]):
                prompt = gr.Textbox(label="Text Prompt", value=persisted_prompt, lines=2)
                # Single image component serves as uploader + live preview
                image = gr.Image(
                    label="Input Image (optional)",
                    value=(persisted_image if (persisted_image and os.path.exists(persisted_image)) else None),
                    type="filepath",
                    elem_id="img_preview",
                )
                with gr.Row():
                    return_mesh = gr.Checkbox(label="Return Mesh", value=False)
                    save_scene = gr.Checkbox(label="Save Scene (export)", value=False)
                with gr.Row():
                    generate_btn = gr.Button("Generate", variant="primary")
                    stop_btn = gr.Button("Stop")
                with gr.Row():
                    viewer_url = gr.Textbox(label="Viewer URL", value=persisted_viewer_url)
                    output_dir = gr.Textbox(label="Output Dir", value="output")
                    gpu_id = gr.Number(label="GPU ID", value=persisted_gpu, precision=0)
            with gr.Column(scale=1, elem_classes=["card"]):
                auto_refresh = gr.Checkbox(label="Auto-refresh logs", value=True)
                logs = gr.Textbox(label="Logs", value="", lines=20)
                refresh_btn = gr.Button("Refresh Logs")
                remember = gr.Checkbox(label="Remember inputs", value=True)

        # Viewer iframe below, full width (single column)
        viewer_iframe = gr.HTML(value=f'<iframe src="http://localhost:{default_port}" allow="clipboard-read; clipboard-write"></iframe>', elem_id="viewer_card")

        def on_generate(p: str, img, mesh: bool, v_url: str, export: bool, out_dir: str, remember_inputs: bool, gpu_sel: float):
            # gr.Image with type='filepath' returns a string path, or None
            img_path = img if img else None
            # Persist inputs
            if remember_inputs:
                try:
                    data = {
                        "prompt": p,
                        "viewer_url": v_url,
                        "gpu_id": int(gpu_sel),
                    }
                    if img_path and os.path.exists(img_path):
                        UPLOADS_DIR.mkdir(exist_ok=True)
                        dest = UPLOADS_DIR / os.path.basename(img_path)
                        try:
                            shutil.copy2(img_path, dest)
                            data["image_path"] = str(dest)
                        except Exception:
                            data["image_path"] = img_path
                    elif persisted_image and os.path.exists(persisted_image):
                        # Keep previous image if user didn't upload a new one
                        data["image_path"] = persisted_image
                    STATE_PATH.write_text(json.dumps(data))
                except Exception:
                    pass
            url, msg = runner.start(p, img_path, mesh, v_url, export, out_dir, int(gpu_sel))
            iframe_html = f'<iframe src="{url}" allow="clipboard-read; clipboard-write"></iframe>'
            return url, iframe_html, msg

        def on_stop():
            return runner.stop()

        def on_refresh():
            return runner.get_logs()

        def on_tick():
            if AUTO_REFRESH_ENABLED:
                return runner.get_logs()
            return gr.update()

        def on_toggle_auto(val: bool):
            global AUTO_REFRESH_ENABLED
            AUTO_REFRESH_ENABLED = bool(val)
            # No outputs expected

        generate_btn.click(on_generate, inputs=[prompt, image, return_mesh, viewer_url, save_scene, output_dir, remember, gpu_id], outputs=[viewer_url, viewer_iframe, logs])
        stop_btn.click(on_stop, outputs=[logs])
        refresh_btn.click(on_refresh, outputs=[logs])
        auto_refresh.change(on_toggle_auto, inputs=[auto_refresh], outputs=[])

        # Auto-refresh logs every 1s
        try:
            timer = gr.Timer(1.0)
            timer.tick(on_tick, outputs=[logs])
        except Exception:
            # Fallback if Timer is unavailable in this Gradio version
            pass

        # Persist image immediately on change so it survives reloads
        def on_image_change(img, p, v_url):
            try:
                data = {
                    "prompt": p,
                    "viewer_url": v_url,
                }
                if img and os.path.exists(img):
                    UPLOADS_DIR.mkdir(exist_ok=True)
                    dest = UPLOADS_DIR / os.path.basename(img)
                    try:
                        shutil.copy2(img, dest)
                        data["image_path"] = str(dest)
                    except Exception:
                        data["image_path"] = img
                STATE_PATH.write_text(json.dumps(data))
            except Exception:
                pass
            # No outputs expected; return nothing

        image.change(on_image_change, inputs=[image, prompt, viewer_url], outputs=[])

    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WorldGen web controller")
    parser.add_argument("--port", type=int, default=8080, help="Viser viewer port to pass to demo.py")
    args = parser.parse_args()
    launch_ui(default_port=args.port)
