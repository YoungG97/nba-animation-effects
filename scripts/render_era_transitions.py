"""Career Era Transitions Renderer.
Enforces strict calibrated timings:
- 0.0s .. 1.5s: ONLY Total time / Era Title appears (exclusive window)
- 1.5s+: Sequential honors appear, each lasting 1.5s ('上一个出现结束，后面一个才出现')
"""

import math
import os
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .engine import (
    make_era_title_sprite,
    make_honor_text_sprite,
    synthesize_multi_hit_sfx,
    alpha_composite_sprite,
    ease_out_back,
)
from .team_colors import get_team_colors

def render_career_era(
    photo_path: str,
    title: str,
    years: str,
    honors: list[tuple[str, str]],
    out_mp4: str,
    out_jpg: str = None,
    out_gif: str = None,
    team_key: str = "OKC",
    mode: str = "stack",  # 'stack' or 'carousel'
):
    W, H = 1920, 1080
    FPS = 60
    TIME_ONLY_DUR = 1.50
    HONOR_DUR = 1.50
    TAIL_HOLD = 0.30
    duration = TIME_ONLY_DUR + len(honors) * HONOR_DUR + TAIL_HOLD
    TOTAL_FRAMES = int(round(FPS * duration))

    tc = get_team_colors(team_key)

    # Prepare background with dark vignette on left for contrast
    im_raw = Image.open(photo_path).convert("RGB")
    scale = max(W / im_raw.width, H / im_raw.height)
    nw, nh = int(round(im_raw.width * scale)), int(round(im_raw.height * scale))
    im_scaled = im_raw.resize((nw, nh), Image.Resampling.LANCZOS)
    crop_x = int(np.clip((nw - W) * 0.65, 0, max(0, nw - W)))
    crop_y = int(np.clip((nh - H) * 0.25, 0, max(0, nh - H)))
    bg_img = im_scaled.crop((crop_x, crop_y, crop_x + W, crop_y + H))
    bg_np = np.asarray(bg_img, dtype=np.float32)

    era_sp, _, _ = make_era_title_sprite(title, years, primary_color=tc["primary"], secondary_color=tc["secondary"], accent_gold=tc["accent"])
    honor_sps = [make_honor_text_sprite(h_title, h_cnt, accent_gold=tc["accent"]) for h_title, h_cnt in honors]

    hit_times = [0.08] + [TIME_ONLY_DUR + idx * HONOR_DUR for idx in range(len(honors))]
    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_multi_hit_sfx(tmp_wav, duration, hit_times)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", tmp_wav,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    base_honor_y = int(H * 0.52)
    honor_spacing = 64
    x_target = 140

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        push_p = t / duration
        bg_scale = 1.0 + 0.05 * push_p

        cx, cy = W * 0.68, H * 0.50
        M_bg = np.float32([
            [bg_scale, 0, cx * (1.0 - bg_scale)],
            [0, bg_scale, cy * (1.0 - bg_scale)],
        ])
        frame = cv2.warpAffine(bg_np, M_bg, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

        # Left dark contrast gradient
        xs = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :, None]
        left_grad = np.clip((0.65 - xs) / 0.65, 0.0, 1.0) * 0.58
        frame = frame * (1.0 - left_grad)

        # 1. Title Entrance: 0.0s .. 0.35s
        u_era = min(1.0, t / 0.35)
        p_era = ease_out_back(u_era, overshoot=1.15)
        x_era = int(round(-150 + (x_target - (-150)) * p_era))
        y_era = int(H * 0.38)
        frame = alpha_composite_sprite(frame, era_sp, center_x=x_era + era_sp.width // 2, center_y=y_era + era_sp.height // 2, opacity=min(1.0, u_era * 2))

        # 2. Sequential Honors (only after t >= 1.50s)
        if mode == "stack":
            for h_idx, (h_sp, _, _) in enumerate(honor_sps):
                st = TIME_ONLY_DUR + h_idx * HONOR_DUR
                if t >= st:
                    u_h = min(1.0, (t - st) / 0.32)
                    p_h = ease_out_back(u_h, overshoot=1.15)
                    x_h = int(round(-140 + (x_target - (-140)) * p_h))
                    y_h = base_honor_y + h_idx * honor_spacing
                    frame = alpha_composite_sprite(frame, h_sp, center_x=x_h + h_sp.width // 2, center_y=y_h + h_sp.height // 2, opacity=min(1.0, u_h * 2))
        elif mode == "carousel":
            for h_idx, (h_sp, _, _) in enumerate(honor_sps):
                st = TIME_ONLY_DUR + h_idx * HONOR_DUR
                et = st + HONOR_DUR
                if st <= t < et + 0.1:
                    dt = t - st
                    if dt < 0.28:
                        u_h = dt / 0.28
                        p_h = ease_out_back(u_h, overshoot=1.15)
                        x_h = int(round(-140 + (x_target - (-140)) * p_h))
                        op = min(1.0, u_h * 2)
                    elif t >= et - 0.20 and h_idx < len(honor_sps) - 1:
                        out_p = (t - (et - 0.20)) / 0.20
                        x_h = x_target
                        op = max(0.0, 1.0 - out_p)
                    else:
                        x_h = x_target
                        op = 1.0
                    y_h = base_honor_y
                    frame = alpha_composite_sprite(frame, h_sp, center_x=x_h + h_sp.width // 2, center_y=y_h + h_sp.height // 2, opacity=op)

        out_u8 = np.clip(frame, 0, 255).astype(np.uint8)

        if out_jpg:
            target_snap = int((duration - 0.15) * FPS) if mode == "stack" else int((TIME_ONLY_DUR + HONOR_DUR * 0.8) * FPS)
            if f_idx == target_snap:
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
