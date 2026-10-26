"""Opening Hero Intro Renderer (10.0s, '每天认识一位NBA球员' + Hero Cutout + 5.0s Name Slam).
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

def render_opening_intro(
    photo_path: str,
    player_name: str,
    out_mp4: str,
    out_jpg: str = None,
    out_gif: str = None,
    team_key: str = "OKC",
    duration: float = 10.0,
    name_hit_t: float = 5.0,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))
    tc = get_team_colors(team_key)

    font_heavy = get_font_path(prefer_heavy=True)

    # 1. '每天认识一位NBA球员' Sprite
    f_series = ImageFont.truetype(font_heavy, 155)
    series_title = "每天认识一位NBA球员"
    stw = int(f_series.getlength(series_title))
    series_sp = Image.new("RGBA", (stw + 60, 220), (0, 0, 0, 0))
    ds = ImageDraw.Draw(series_sp)
    ds.text((32, 34), series_title, font=f_series, fill=(0, 0, 0, 220), stroke_width=4, stroke_fill=(0, 0, 0, 220))
    ds.text((30, 30), series_title, font=f_series, fill=(255, 255, 255, 255))

    # 2. Player Name Sprite
    f_name = ImageFont.truetype(font_heavy, 120)
    ntw = int(f_name.getlength(player_name))
    name_sp = Image.new("RGBA", (ntw + 60, 180), (0, 0, 0, 0))
    dn = ImageDraw.Draw(name_sp)
    dn.text((32, 34), player_name, font=f_name, fill=(0, 0, 0, 220), stroke_width=3, stroke_fill=(0, 0, 0, 220))
    dn.text((30, 30), player_name, font=f_name, fill=tc["accent"] + (255,))

    # Load Background
    im_raw = Image.open(photo_path).convert("RGB")
    scale = max(W / im_raw.width, H / im_raw.height)
    nw, nh = int(round(im_raw.width * scale)), int(round(im_raw.height * scale))
    im_scaled = im_raw.resize((nw, nh), Image.Resampling.LANCZOS)
    crop_x = int(np.clip((nw - W) * 0.5, 0, max(0, nw - W)))
    crop_y = int(np.clip((nh - H) * 0.20, 0, max(0, nh - H)))
    base_img = im_scaled.crop((crop_x, crop_y, crop_x + W, crop_y + H))
    base_np = np.asarray(base_img, dtype=np.float32)

    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_slam_sfx(tmp_wav, duration, hit_t=name_hit_t)

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
        cx, cy = W * 0.50, H * 0.45
        M = np.float32([
            [zoom, 0, cx * (1.0 - zoom)],
            [0, zoom, cy * (1.0 - zoom)],
        ])
        frame = cv2.warpAffine(base_np, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

        # Entrance: '每天认识一位NBA球员'
        u_s = min(1.0, t / 0.40)
        p_s = ease_out_back(u_s, overshoot=1.15)
        frame = alpha_composite_sprite(frame, series_sp, center_x=W // 2, center_y=int(H * 0.24 * p_s), opacity=min(1.0, u_s * 2))

        # Entrance: Player Name at name_hit_t (5.0s)
        if t >= name_hit_t:
            u_n = min(1.0, (t - name_hit_t) / 0.30)
            p_n = ease_out_back(u_n, overshoot=1.2)
            frame = alpha_composite_sprite(frame, name_sp, center_x=W // 2, center_y=int(H * 0.82 * p_n), opacity=min(1.0, u_n * 2))

        out_u8 = np.clip(frame, 0, 255).astype(np.uint8)
        if out_jpg and f_idx == int((name_hit_t + 1.0) * FPS):
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
