"""60fps Career Flashback Carousel Video Renderer.
Hardware-accelerated Ken Burns photo montage with camera shutter flash,
gradient scrim, and broadcast 2-stage typography overlays.
"""

import os
import sys
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def render_flashback_carousel(
    items: list[tuple[str, str, str]],
    output_mp4: str,
    fps: int = 60,
    dur_per_item: float = 1.800,
    font_path: str = "/System/Library/Fonts/Hiragino Sans GB.ttc",
    font_size: int = 44,
    text_color: tuple[int, int, int] = (245, 197, 24), # Golden Yellow #F5C518
    width: int = 1920,
    height: int = 1080,
    bitrate: str = "14M",
) -> float:
    """Render a broadcast-grade 60fps Flashback Carousel video.

    Args:
        items: List of (image_path, date_heading, description_multiline).
        output_mp4: Path to export MP4.
        fps: Target frame rate (default 60fps).
        dur_per_item: Seconds per milestone photo (default 1.800s).
        font_path: Path to Truetype font.
        font_size: Point size for text.
        text_color: RGB tuple for font color.
        width: Video width (default 1920).
        height: Video height (default 1080).
        bitrate: Target video bitrate (default 14M).

    Returns:
        total_duration: Exact duration in seconds.
    """
    if os.path.exists(output_mp4):
        try:
            os.remove(output_mp4)
        except Exception:
            pass
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)

    W, H = width, height
    frames_per_item = int(round(fps * dur_per_item))
    total_items = len(items)
    total_duration = round(total_items * dur_per_item, 3)

    try:
        font = ImageFont.truetype(font_path, font_size, index=2)
    except Exception:
        font = ImageFont.load_default()

    # Pre-generate gradient scrim
    scrim = np.zeros((H, W, 4), dtype=np.uint8)
    for y in range(int(H * 0.48), H):
        for x in range(0, int(W * 0.70)):
            vy = max(0.0, (y - H * 0.48) / (H * 0.52))
            vx = max(0.0, 1.0 - (x / (W * 0.70)))
            val = (vy * vx) ** 0.8
            alpha = int(125 * val)
            scrim[y, x] = [0, 0, 0, alpha]
    scrim_img = Image.fromarray(scrim, "RGBA")

    # Select hardware encoder if available
    vcodec = "h264_videotoolbox" if sys.platform == "darwin" else "libx264"
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", vcodec,
        "-b:v", bitrate,
        "-pix_fmt", "yuv420p",
        output_mp4
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    x_start = 280
    y_start = 710
    line_h = int(round(font_size * 1.27))

    for item_idx, (img_path, line1_text, text) in enumerate(items, 1):
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Missing milestone image: {img_path}")

        lines_rest = [l.strip() for l in text.split("\n") if l.strip()]

        raw_img = Image.open(img_path).convert("RGB")
        target_aspect = W / H
        cur_aspect = raw_img.width / raw_img.height

        if cur_aspect > target_aspect:
            nh = H
            nw = int(round(H * cur_aspect))
        else:
            nw = W
            nh = int(round(W / cur_aspect))

        scaled_base = raw_img.resize((nw, nh), Image.Resampling.LANCZOS)
        cl = (nw - W) // 2
        ct = (nh - H) // 2
        base_frame = scaled_base.crop((cl, ct, cl + W, ct + H))

        for frame_idx in range(frames_per_item):
            t = frame_idx / float(fps)

            # 1. Ken Burns push-in zoom (1.000 to 1.035)
            zoom = 1.0 + 0.035 * (t / dur_per_item)
            cw = int(W / zoom)
            ch = int(H / zoom)
            zl = (W - cw) // 2
            zt = (H - ch) // 2
            zoomed = base_frame.crop((zl, zt, zl + cw, zt + ch)).resize((W, H), Image.Resampling.BILINEAR)

            # 2. Camera shutter brightness pop (t < 0.06s)
            if t < 0.06:
                flash_factor = 1.0 + 0.16 * (1.0 - t / 0.06)
                arr = np.array(zoomed, dtype=np.float32)
                arr = np.clip(arr * flash_factor, 0, 255).astype(np.uint8)
                zoomed = Image.fromarray(arr, "RGB")

            # 3. Composite gradient scrim
            frame_rgba = zoomed.convert("RGBA")
            frame_rgba.alpha_composite(scrim_img)

            # 4. Animated Typography Overlay
            txt_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw = ImageDraw.Draw(txt_layer)

            # Stage 1: Date line enters at t = 0.20s
            p1 = min(1.0, max(0.0, (t - 0.20) / 0.18))
            if p1 > 0.0:
                ease1 = 1.0 - (1.0 - p1) ** 3
                alpha1 = int(255 * ease1)
                off_y1 = int(15 * (1.0 - ease1))
                y1 = y_start + off_y1
                draw.text(
                    (x_start, y1),
                    line1_text,
                    font=font,
                    fill=(text_color[0], text_color[1], text_color[2], alpha1),
                    stroke_fill=(0, 0, 0, alpha1),
                    stroke_width=4
                )

            # Stage 2: Details lines enter at t = 0.45s
            p2 = min(1.0, max(0.0, (t - 0.45) / 0.20))
            if p2 > 0.0:
                ease2 = 1.0 - (1.0 - p2) ** 3
                alpha2 = int(255 * ease2)
                off_y2 = int(18 * (1.0 - ease2))
                for idx_l, line_str in enumerate(lines_rest, 1):
                    yl = y_start + idx_l * line_h + off_y2
                    draw.text(
                        (x_start, yl),
                        line_str,
                        font=font,
                        fill=(text_color[0], text_color[1], text_color[2], alpha2),
                        stroke_fill=(0, 0, 0, alpha2),
                        stroke_width=4
                    )

            frame_rgba.alpha_composite(txt_layer)
            rgb_frame = frame_rgba.convert("RGB")
            proc.stdin.write(rgb_frame.tobytes())

    proc.stdin.close()
    stderr_output = proc.stderr.read().decode("utf-8")
    proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg render error: {stderr_output}")

    return total_duration
