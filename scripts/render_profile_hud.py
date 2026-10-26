"""Aesthetic Player Profile HUD & Magazine Layout Renderer (12.0s, Two-Stage Dynamic Switch).
Stage 1 (0.0s..6.0s): Identity Dossier & Personal Bio
Stage 2 (6.0s..12.0s): Physical Metrics & Court Positions with Audio Transition
"""

import math
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

def render_profile_hud(
    p1_path: str,
    p2_path: str,
    player_data: dict,
    out_mp4: str,
    out_jpg_part1: str = None,
    out_jpg_part2: str = None,
    out_gif: str = None,
    team_key: str = "OKC",
    duration: float = 12.0,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))
    SWITCH_T = 6.0
    tc = get_team_colors(team_key)

    font_path = get_font_path(prefer_heavy=False)

    def load_frame(photo_path, crop_focus=(0.60, 0.20)):
        im = Image.open(photo_path).convert("RGB")
        scale = max(W / im.width, H / im.height)
        nw, nh = int(round(im.width * scale)), int(round(im.height * scale))
        im_s = im.resize((nw, nh), Image.Resampling.LANCZOS)
        cx = int(np.clip((nw - W) * crop_focus[0], 0, max(0, nw - W)))
        cy = int(np.clip((nh - H) * crop_focus[1], 0, max(0, nh - H)))
        base = im_s.crop((cx, cy, cx + W, cy + H))
        return np.asarray(base, dtype=np.float32)

    bg1_np = load_frame(p1_path, (0.60, 0.20))
    bg2_np = load_frame(p2_path, (0.65, 0.25))

    # Build Stage 1 Sprite (Identity Bio)
    def make_stage1_sprite():
        sp = Image.new("RGBA", (850, 600), (0, 0, 0, 0))
        d = ImageDraw.Draw(sp)
        f_header = ImageFont.truetype(font_path, 48)
        f_label = ImageFont.truetype(font_path, 28)
        f_val = ImageFont.truetype(font_path, 34)

        d.text((21, 23), "PLAYER DOSSIER", font=f_header, fill=(0, 0, 0, 200), stroke_width=1, stroke_fill=(0, 0, 0, 200))
        d.text((20, 20), "PLAYER DOSSIER", font=f_header, fill=tc["accent"] + (255,))
        d.rounded_rectangle([20, 80, 280, 85], radius=2, fill=tc["primary"] + (255,))

        items = [
            ("姓名 / NAME", player_data.get("name_cn", "杰伦·威廉姆斯") + f" ({player_data.get('name_en', 'Jalen Williams')})"),
            ("生日 / BIRTH", player_data.get("birth", "2001年4月14日")),
            ("国籍 / ORIGIN", player_data.get("origin", "美国科罗拉多州丹佛市")),
            ("大学 / COLLEGE", player_data.get("college", "圣塔克拉拉大学 (Santa Clara)")),
            ("选秀 / DRAFT", player_data.get("draft", "2022年首轮第12顺位 (OKC)")),
        ]
        cy = 115
        for lbl, val in items:
            d.text((21, cy + 2), lbl, font=f_label, fill=(0, 0, 0, 180))
            d.text((20, cy), lbl, font=f_label, fill=(180, 195, 210, 220))
            d.text((21, cy + 32), val, font=f_val, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))
            d.text((20, cy + 30), val, font=f_val, fill=(255, 255, 255, 255))
            cy += 85
        return sp

    # Build Stage 2 Sprite (Metrics & Court Positions)
    def make_stage2_sprite():
        sp = Image.new("RGBA", (850, 600), (0, 0, 0, 0))
        d = ImageDraw.Draw(sp)
        f_header = ImageFont.truetype(font_path, 48)
        f_label = ImageFont.truetype(font_path, 28)
        f_val = ImageFont.truetype(font_path, 34)

        d.text((21, 23), "PHYSICAL & POSITIONS", font=f_header, fill=(0, 0, 0, 200), stroke_width=1, stroke_fill=(0, 0, 0, 200))
        d.text((20, 20), "PHYSICAL & POSITIONS", font=f_header, fill=tc["accent"] + (255,))
        d.rounded_rectangle([20, 80, 360, 85], radius=2, fill=tc["secondary"] + (255,))

        items = [
            ("身高 / HEIGHT", player_data.get("height", "1.96 m（6英尺5英寸）")),
            ("体重 / WEIGHT", player_data.get("weight", "96 KG（211磅）")),
            ("臂展 / WINGSPAN", player_data.get("wingspan", "2.19 m（7尺2寸 · 超长臂展）")),
            ("司职 / POSITIONS", player_data.get("positions", "得分后卫 / 小前锋 / 大前锋")),
        ]
        cy = 115
        for lbl, val in items:
            d.text((21, cy + 2), lbl, font=f_label, fill=(0, 0, 0, 180))
            d.text((20, cy), lbl, font=f_label, fill=(180, 195, 210, 220))
            d.text((21, cy + 32), val, font=f_val, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))
            d.text((20, cy + 30), val, font=f_val, fill=(255, 255, 255, 255))
            cy += 95
        return sp

    sp1 = make_stage1_sprite()
    sp2 = make_stage2_sprite()

    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_slam_sfx(tmp_wav, duration, hit_t=SWITCH_T + 0.1)

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
        if t < SWITCH_T:
            curr_bg = bg1_np
            curr_sp = sp1
            p_time = t / SWITCH_T
            zoom = 1.0 + 0.03 * p_time
            u_in = min(1.0, t / 0.40)
            p_in = ease_out_back(u_in, overshoot=1.1)
            sp_x = int(-80 + (120 - (-80)) * p_in)
            sp_alpha = min(1.0, u_in * 2)
        else:
            curr_bg = bg2_np
            curr_sp = sp2
            p_time = (t - SWITCH_T) / (duration - SWITCH_T)
            zoom = 1.0 + 0.03 * p_time
            u_in = min(1.0, (t - SWITCH_T) / 0.40)
            p_in = ease_out_back(u_in, overshoot=1.1)
            sp_x = int(-80 + (120 - (-80)) * p_in)
            sp_alpha = min(1.0, u_in * 2)

        cx, cy = W * 0.65, H * 0.50
        M = np.float32([
            [zoom, 0, cx * (1.0 - zoom)],
            [0, zoom, cy * (1.0 - zoom)],
        ])
        frame = cv2.warpAffine(curr_bg, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

        # Left dark vignette for text readability
        xs = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :, None]
        left_grad = np.clip((0.68 - xs) / 0.68, 0.0, 1.0) * 0.65
        frame = frame * (1.0 - left_grad)

        frame = alpha_composite_sprite(frame, curr_sp, center_x=sp_x + curr_sp.width // 2, center_y=int(H * 0.48), opacity=sp_alpha)

        out_u8 = np.clip(frame, 0, 255).astype(np.uint8)
        if out_jpg_part1 and f_idx == int(3.0 * FPS):
            Image.fromarray(out_u8).save(out_jpg_part1, quality=95)
        if out_jpg_part2 and f_idx == int(9.0 * FPS):
            Image.fromarray(out_u8).save(out_jpg_part2, quality=95)

        proc.stdin.write(out_u8.tobytes())

    proc.stdin.close()
    proc.wait()
    if os.path.exists(tmp_wav):
        os.remove(tmp_wav)

    if out_gif:
        subprocess.run([
            "ffmpeg", "-y", "-i", out_mp4,
            "-vf", "fps=18,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
            out_gif,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
