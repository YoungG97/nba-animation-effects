"""Major Chapter Poster Transitions Renderer (2.5s, 2.5D Push + Heavy Slam Audio).
Renders transitions like 《基本信息》 and 《职业生涯经历及成就》.
"""

import os
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .engine import (
    get_font_path,
    synthesize_slam_sfx,
    alpha_composite_sprite,
    ease_out_back,
)

def render_major_chapter_card(
    photo_path: str,
    title: str,
    out_mp4: str,
    out_jpg: str = None,
    out_gif: str = None,
    duration: float = 2.5,
    font_size: int = 150,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))

    font_heavy = get_font_path(prefer_heavy=True)
    font = ImageFont.truetype(font_heavy, font_size)

    tw = int(font.getlength(title))
    pad = 30
    sw = tw + pad * 2
    sh = int(font_size * 1.4) + pad * 2

    title_sp = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(title_sp)
    cx, cy = pad, pad
    # Double drop shadow
    d.text((cx + 2, cy + 6), title, font=font, fill=(0, 0, 0, 220), stroke_width=3, stroke_fill=(0, 0, 0, 220))
    d.text((cx, cy), title, font=font, fill=(255, 255, 255, 255))

    im_raw = Image.open(photo_path).convert("RGB")
    scale = max(W / im_raw.width, H / im_raw.height)
    nw, nh = int(round(im_raw.width * scale)), int(round(im_raw.height * scale))
    im_scaled = im_raw.resize((nw, nh), Image.Resampling.LANCZOS)
    crop_x = int(np.clip((nw - W) * 0.5, 0, max(0, nw - W)))
    crop_y = int(np.clip((nh - H) * 0.20, 0, max(0, nh - H)))
    base_img = im_scaled.crop((crop_x, crop_y, crop_x + W, crop_y + H))
    base_np = np.asarray(base_img, dtype=np.float32)

    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_slam_sfx(tmp_wav, duration, hit_t=0.28)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", tmp_wav,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    y_coords = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
    black_gradient = np.clip((y_coords - 0.44) / 0.56, 0.0, 1.0) ** 1.35 * 0.90

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        push_p = t / duration
        zoom = 1.0 + 0.04 * push_p
        cx, cy = W * 0.50, H * 0.45
        M = np.float32([
            [zoom, 0, cx * (1.0 - zoom)],
            [0, zoom, cy * (1.0 - zoom)],
        ])
        frame = cv2.warpAffine(base_np, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        frame = frame * (1.0 - black_gradient)

        u = min(1.0, t / 0.32)
        p = ease_out_back(u, overshoot=1.2)
        y_pos = int(H * 0.82 * p)

        frame = alpha_composite_sprite(frame, title_sp, center_x=W // 2, center_y=y_pos, opacity=min(1.0, u * 2))

        out_u8 = np.clip(frame, 0, 255).astype(np.uint8)
        if out_jpg and f_idx == int(0.9 * FPS):
            Image.fromarray(out_u8).save(out_jpg, quality=95)

        proc.stdin.write(out_u8.tobytes())

    proc.stdin.close()
    proc.wait()
    if os.path.exists(tmp_wav):
        os.remove(tmp_wav)

    if out_gif:
        subprocess.run([
            "ffmpeg", "-y", "-i", out_mp4,
            "-vf", "fps=20,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
            out_gif,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
