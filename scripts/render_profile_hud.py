"""Aesthetic Player Profile HUD & Magazine Layout Renderer (12.0s, Fig 3 White Gradient Aesthetic).
Stage 1 (0.0s..6.0s): Identity Dossier & Personal Bio (Top Highlighted)
Stage 2 (6.0s..12.0s): Physical Metrics & Court Positions (Bottom Highlighted) with Audio Transition
Matches the benchmark visual aesthetic (media_1793033422026_c72fc6bb.png).
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

def build_white_gradient_mask(w: int = 1920, h: int = 1080, solid_ratio: float = 0.28, fade_end_ratio: float = 0.62) -> np.ndarray:
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32)
    alpha_1d = np.zeros(w, dtype=np.float32)
    for i, xr in enumerate(xs):
        if xr <= solid_ratio:
            alpha_1d[i] = 1.0
        elif xr >= fade_end_ratio:
            alpha_1d[i] = 0.0
        else:
            u = (xr - solid_ratio) / (fade_end_ratio - solid_ratio)
            alpha_1d[i] = 0.5 * (1.0 + math.cos(math.pi * (u ** 0.88)))
    return np.broadcast_to(alpha_1d[None, :, None], (h, w, 1)).copy()

def build_fig3_profile_layers(player_data: dict, team_key: str = "GSW", w: int = 1920, h: int = 1080):
    font_bold = get_font_path(prefer_heavy=False)
    font_heavy = get_font_path(prefer_heavy=True)
    tc = get_team_colors(team_key)

    font_label = ImageFont.truetype(font_bold, 48)
    font_val = ImageFont.truetype(font_heavy, 50)
    font_en = ImageFont.truetype(font_bold, 44)
    font_sub = ImageFont.truetype(font_bold, 40)
    font_tag = ImageFont.truetype(font_heavy, 24)
    font_wm = ImageFont.truetype(font_heavy, 95)

    name_cn = player_data.get("name_cn", "雅克塞尔·伦德博格")
    name_en = player_data.get("name_en", "Yaxel Lendeborg")
    birth = player_data.get("birth", "2002年9月30日")
    origin = player_data.get("origin", "波多黎各 / 美国")
    origin_sub = player_data.get("origin_sub", "(出生于波多黎各，美国新泽西州长大)")
    height = player_data.get("height", "2.06 m（6英尺9英寸）")
    weight = player_data.get("weight", "109 KG（240磅）")
    positions = player_data.get("positions", "大前锋 / 小前锋")
    jersey = player_data.get("jersey_number", "1")

    def make_state(active_part: int) -> Image.Image:
        lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)

        # 1. Subtle oversized watermark
        wm_text = f"#{jersey} {tc['name'].upper()}"
        d.text((120, 62), wm_text, font=font_wm, fill=(230, 235, 245, 130))

        # 2. Top pill badge [PLAYER PROFILE · 球员档案]
        d.rounded_rectangle([126, 112, 535, 154], radius=8, fill=tc["primary"] + (255,))
        d.rounded_rectangle([126, 112, 140, 154], radius=2, fill=tc["secondary"] + (255,))
        d.text((156, 117), "PLAYER PROFILE · 球员档案", font=font_tag, fill=(255, 255, 255, 255))

        # 3. Left vertical indicator bar track
        d.rounded_rectangle([94, 195, 104, 855], radius=5, fill=(210, 215, 225, 220))
        if active_part == 1:
            d.rounded_rectangle([92, 195, 106, 565], radius=6, fill=tc["primary"] + (255,))
            d.rounded_rectangle([92, 195, 106, 245], radius=6, fill=tc["secondary"] + (255,))
        else:
            d.rounded_rectangle([92, 595, 106, 855], radius=6, fill=tc["secondary"] + (255,))
            d.rounded_rectangle([92, 650, 106, 855], radius=6, fill=tc["primary"] + (255,))

        # 4. Upper Block (Identity)
        upper_alpha = 255 if active_part == 1 else 185
        d.text((128, 195), "姓名：", font=font_label, fill=(60, 68, 82, upper_alpha), stroke_width=3, stroke_fill=(255, 255, 255, upper_alpha))
        lw = font_label.getlength("姓名：")
        d.text((128 + lw, 194), name_cn, font=font_val, fill=(15, 20, 32, upper_alpha), stroke_width=4, stroke_fill=(255, 255, 255, upper_alpha))

        d.text((274, 268), name_en, font=font_en, fill=tc["primary"] + (upper_alpha,), stroke_width=3, stroke_fill=(255, 255, 255, upper_alpha))

        for lbl, val, y in [
            ("生日：", birth, 348),
            ("国籍：", origin, 430),
        ]:
            d.text((128, y), lbl, font=font_label, fill=(60, 68, 82, upper_alpha), stroke_width=3, stroke_fill=(255, 255, 255, upper_alpha))
            lw = font_label.getlength(lbl)
            d.text((128 + lw, y - 1), val, font=font_val, fill=(15, 20, 32, upper_alpha), stroke_width=4, stroke_fill=(255, 255, 255, upper_alpha))

        d.text((148, 506), origin_sub, font=font_sub, fill=(75, 85, 102, upper_alpha), stroke_width=3, stroke_fill=(255, 255, 255, upper_alpha))

        # Horizontal divider line
        d.line([(128, 576), (680, 576)], fill=(200, 208, 220, 220), width=2)

        # 5. Lower Block (Physical & Position)
        lower_alpha = 215 if active_part == 1 else 255
        lower_items = [
            ("身高：", height, 602),
            ("体重：", weight, 688),
            ("球场上司职：", positions, 774),
        ]
        for lbl, val, y in lower_items:
            if active_part == 2:
                lw = font_label.getlength(lbl)
                vw = font_val.getlength(val)
                bx0 = int(128 + lw - 10)
                bx1 = int(128 + lw + vw + 18)
                d.rounded_rectangle([bx0, y + 4, bx1, y + 60], radius=10, fill=tc["primary"] + (28,))

            d.text((128, y), lbl, font=font_label, fill=(60, 68, 82, lower_alpha), stroke_width=3, stroke_fill=(255, 255, 255, lower_alpha))
            lw = font_label.getlength(lbl)
            val_color = tc["secondary"] + (255,) if active_part == 2 else (15, 20, 32, lower_alpha)
            d.text((128 + lw, y - 1), val, font=font_val, fill=val_color, stroke_width=4, stroke_fill=(255, 255, 255, lower_alpha))

        return lay

    return make_state(1), make_state(2)

def prepare_right_photo(photo_path: str, focus_x: float = 0.65, target_w: int = 1920, target_h: int = 1080) -> np.ndarray:
    im = Image.open(photo_path).convert("RGB")
    scale = max(target_w / im.width, target_h / im.height)
    nw, nh = int(round(im.width * scale)), int(round(im.height * scale))
    im_s = im.resize((nw, nh), Image.Resampling.LANCZOS)
    cx = int(np.clip((nw - target_w) * focus_x, 0, max(0, nw - target_w)))
    cy = int(np.clip((nh - target_h) * 0.15, 0, max(0, nh - target_h)))
    base = im_s.crop((cx, cy, cx + target_w, cy + target_h))
    return np.asarray(base, dtype=np.float32)

def render_profile_hud(
    p1_path: str,
    p2_path: str,
    player_data: dict,
    out_mp4: str,
    out_jpg_part1: str = None,
    out_jpg_part2: str = None,
    out_gif: str = None,
    team_key: str = "GSW",
    duration: float = 12.0,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))
    SWITCH_T = 6.0

    white_mask = build_white_gradient_mask(W, H, solid_ratio=0.28, fade_end_ratio=0.62)
    pure_white = np.ones((H, W, 3), dtype=np.float32) * 255.0

    photo1_np = prepare_right_photo(p1_path, focus_x=0.55)
    photo2_np = prepare_right_photo(p2_path, focus_x=0.68)

    bg1_blended = pure_white * white_mask + photo1_np * (1.0 - white_mask)
    bg2_blended = pure_white * white_mask + photo2_np * (1.0 - white_mask)

    hud_part1, hud_part2 = build_fig3_profile_layers(player_data, team_key=team_key, w=W, h=H)

    if out_jpg_part1:
        comp1 = Image.alpha_composite(Image.fromarray(np.clip(bg1_blended, 0, 255).astype(np.uint8)).convert("RGBA"), hud_part1)
        comp1.convert("RGB").save(out_jpg_part1, quality=95)

    if out_jpg_part2:
        comp2 = Image.alpha_composite(Image.fromarray(np.clip(bg2_blended, 0, 255).astype(np.uint8)).convert("RGBA"), hud_part2)
        comp2.convert("RGB").save(out_jpg_part2, quality=95)

    # Transition audio at 6.0s
    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    sr = 44100
    n = int(sr * duration)
    t_aud = np.linspace(0.0, duration, n, dtype=np.float32)
    audio = np.zeros(n, dtype=np.float32)
    np.random.seed(42)
    noise = np.random.normal(0, 1, n).astype(np.float32)

    dt = np.maximum(0.0, t_aud - SWITCH_T)
    m = ((t_aud >= SWITCH_T - 0.20) & (t_aud <= SWITCH_T + 0.40)).astype(np.float32)
    audio += 0.25 * noise * np.exp(-abs(t_aud - SWITCH_T) * 12.0) * m
    audio += 0.35 * np.sin(2.0 * np.pi * 90.0 * dt) * np.exp(-dt * 8.0) * (t_aud >= SWITCH_T).astype(np.float32)

    import wave
    pcm = np.int16(np.clip(np.tanh(audio) * 0.75, -1.0, 1.0) * 32767)
    stereo = np.column_stack([pcm, pcm]).flatten()
    with wave.open(tmp_wav, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", tmp_wav,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    hud1_arr = np.asarray(hud_part1, dtype=np.float32)
    hud2_arr = np.asarray(hud_part2, dtype=np.float32)

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        if t < SWITCH_T:
            push = 1.00 + 0.02 * (t / SWITCH_T)
            M = np.float32([[push, 0, (W * 0.7) * (1.0 - push)], [0, push, (H * 0.5) * (1.0 - push)]])
            frame_bg = cv2.warpAffine(bg1_blended, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
            hud_rgb = hud1_arr[:, :, :3]
            hud_a = hud1_arr[:, :, 3:4] / 255.0
            frame = hud_rgb * hud_a + frame_bg * (1.0 - hud_a)
        elif t < SWITCH_T + 0.40:
            u = (t - SWITCH_T) / 0.40
            frame_bg = bg1_blended * (1.0 - u) + bg2_blended * u
            hud_curr = hud1_arr * (1.0 - u) + hud2_arr * u
            hud_rgb = hud_curr[:, :, :3]
            hud_a = hud_curr[:, :, 3:4] / 255.0
            frame = hud_rgb * hud_a + frame_bg * (1.0 - hud_a)
        else:
            t_rem = t - SWITCH_T
            push = 1.00 + 0.02 * (t_rem / (duration - SWITCH_T))
            M = np.float32([[push, 0, (W * 0.7) * (1.0 - push)], [0, push, (H * 0.5) * (1.0 - push)]])
            frame_bg = cv2.warpAffine(bg2_blended, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
            hud_rgb = hud2_arr[:, :, :3]
            hud_a = hud2_arr[:, :, 3:4] / 255.0
            frame = hud_rgb * hud_a + frame_bg * (1.0 - hud_a)

        out_u8 = np.clip(frame, 0, 255).astype(np.uint8)
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
