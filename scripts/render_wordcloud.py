"""Core Wordcloud Contraction & Convergence Renderer (4.0s).
Tags start spread outward and smoothly converge inward with 2.5D background camera push.
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
from .team_colors import get_team_colors

def render_wordcloud_transition(
    photo_path: str,
    keywords: list[str],
    out_mp4: str,
    out_jpg: str = None,
    out_gif: str = None,
    team_key: str = "OKC",
    duration: float = 4.0,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))
    tc = get_team_colors(team_key)

    font_heavy = get_font_path(prefer_heavy=True)

    # Prepare background with dark vignette
    im_raw = Image.open(photo_path).convert("RGB")
    scale = max(W / im_raw.width, H / im_raw.height)
    nw, nh = int(round(im_raw.width * scale)), int(round(im_raw.height * scale))
    im_scaled = im_raw.resize((nw, nh), Image.Resampling.LANCZOS)
    crop_x = int(np.clip((nw - W) * 0.5, 0, max(0, nw - W)))
    crop_y = int(np.clip((nh - H) * 0.20, 0, max(0, nh - H)))
    base_img = im_scaled.crop((crop_x, crop_y, crop_x + W, crop_y + H))
    base_np = np.asarray(base_img, dtype=np.float32)

    # Radial dark vignette
    ys, xs = np.indices((H, W), dtype=np.float32)
    dist = np.sqrt(((xs - W / 2) / (W / 2)) ** 2 + ((ys - H / 2) / (H / 2)) ** 2)
    dark_vignette = np.clip((dist - 0.35) / 0.65, 0.0, 1.0) * 0.70
    base_np = base_np * (1.0 - dark_vignette[:, :, None])

    # Preset layout positions for up to 6 keywords
    target_positions = [
        (int(W * 0.30), int(H * 0.35), 70, (255, 255, 255)),
        (int(W * 0.70), int(H * 0.32), 65, tc["accent"]),
        (int(W * 0.25), int(H * 0.65), 58, tc["accent"]),
        (int(W * 0.75), int(H * 0.68), 64, (255, 255, 255)),
        (int(W * 0.50), int(H * 0.80), 55, (255, 255, 255)),
    ]

    sprites = []
    for idx, kw in enumerate(keywords[:len(target_positions)]):
        tx, ty, fsize, color = target_positions[idx]
        font = ImageFont.truetype(font_heavy, fsize)
        tw = int(font.getlength(kw))
        pad = 24
        sp = Image.new("RGBA", (tw + pad * 2, fsize + pad * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(sp)
        d.text((pad + 2, pad + 4), kw, font=font, fill=(0, 0, 0, 220), stroke_width=2, stroke_fill=(0, 0, 0, 220))
        d.text((pad, pad), kw, font=font, fill=color + (255,))
        # Vector from center to outer start
        dx = tx - W // 2
        dy = ty - H // 2
        start_x = tx + dx * 0.8
        start_y = ty + dy * 0.8
        sprites.append((sp, (start_x, start_y), (tx, ty)))

    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_slam_sfx(tmp_wav, duration, hit_t=0.45)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", tmp_wav,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        push_p = t / duration
        zoom = 1.0 + 0.04 * push_p
        cx, cy = W * 0.50, H * 0.50
        M = np.float32([
            [zoom, 0, cx * (1.0 - zoom)],
            [0, zoom, cy * (1.0 - zoom)],
        ])
        frame = cv2.warpAffine(base_np, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

        # Keyword convergence animation (0.0s..0.5s)
        u = min(1.0, t / 0.50)
        p = ease_out_back(u, overshoot=1.12)
        for sp, (sx, sy), (tx, ty) in sprites:
            cur_x = int(sx + (tx - sx) * p)
            cur_y = int(sy + (ty - sy) * p)
            frame = alpha_composite_sprite(frame, sp, center_x=cur_x, center_y=cur_y, opacity=min(1.0, u * 2))

        out_u8 = np.clip(frame, 0, 255).astype(np.uint8)
        if out_jpg and f_idx == int(2.0 * FPS):
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
