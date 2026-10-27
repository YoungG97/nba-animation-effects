"""Core Wordcloud Contraction & Convergence Renderer (4.0s).
Matches benchmark cade_wordcloud_v2 style:
- Pure black background
- Official NBA transparent headshot PNG (1040x760) placed in center
- Dense 3-tier surrounding keywords converging inward in 0.5s with whoosh + sub-bass lock-in punch at 0.46s, followed by sustained slow inward push.
"""

import math
import os
import subprocess
import wave
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .engine import get_font_path

def prepare_nba_headshot_canvas(
    png_path: str,
    target_w: int = 1920,
    target_h: int = 1080,
) -> Image.Image:
    im = Image.open(png_path).convert("RGBA")
    arr = np.asarray(im)
    ys, xs = np.where(arr[:, :, 3] > 10)
    top_y = int(ys.min())
    bot_y = int(ys.max())
    left_x = int(xs.min())
    right_x = int(xs.max())

    cropped = im.crop((left_x, top_y, right_x + 1, bot_y + 1))
    cw, ch = cropped.size

    desired_h = int(target_h * 0.985)
    scale = desired_h / ch
    desired_w = int(cw * scale)

    resized = cropped.resize((desired_w, desired_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    paste_x = int(target_w * 0.495 - desired_w / 2)
    paste_y = target_h - desired_h
    canvas.paste(resized, (paste_x, paste_y), resized)
    return canvas

def make_word_sprite(text: str, font_size: int, tracking: int = -4, font_path: str = None) -> Image.Image:
    fp = font_path or get_font_path(prefer_heavy=True)
    font = ImageFont.truetype(fp, font_size)
    advs = [font.getlength(c) for c in text]
    total_w = int(sum(advs) + tracking * max(0, len(text) - 1))
    pad = 24
    sw = max(1, total_w + pad * 2)
    sh = max(1, int(font_size * 1.32) + pad * 2)

    sp = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sp)
    cx = pad
    cy = pad - int(font_size * 0.10)
    for i, c in enumerate(text):
        draw.text(
            (cx, cy),
            c,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=max(1, font_size // 75),
            stroke_fill=(255, 255, 255, 255),
        )
        cx += advs[i] + tracking
    return sp

def composite_tinted_sprite(
    frame_rgb: np.ndarray,
    sprite_rgba: Image.Image,
    center_x: float,
    center_y: float,
    scale: float,
    gray_val: float,
    opacity: float,
) -> np.ndarray:
    if opacity <= 0.005:
        return frame_rgb

    sw, sh = sprite_rgba.size
    if abs(scale - 1.0) > 0.003:
        nw = max(1, int(sw * scale))
        nh = max(1, int(sh * scale))
        sp = sprite_rgba.resize((nw, nh), Image.Resampling.BILINEAR)
    else:
        sp = sprite_rgba
        nw, nh = sw, sh

    arr = np.asarray(sp, dtype=np.float32)
    alpha = (arr[:, :, 3:4] / 255.0) * opacity

    x0 = int(round(center_x - nw / 2.0))
    y0 = int(round(center_y - nh / 2.0))
    x1 = x0 + nw
    y1 = y0 + nh

    fh, fw, _ = frame_rgb.shape
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(fw, x1), min(fh, y1)
    if cx0 >= cx1 or cy0 >= cy1:
        return frame_rgb

    sx0, sy0 = cx0 - x0, cy0 - y0
    sx1, sy1 = sx0 + (cx1 - cx0), sy0 + (cy1 - cy0)

    roi = frame_rgb[cy0:cy1, cx0:cx1]
    sp_a = alpha[sy0:sy1, sx0:sx1]
    color = np.full_like(roi, gray_val)

    frame_rgb[cy0:cy1, cx0:cx1] = roi * (1.0 - sp_a) + color * sp_a
    return frame_rgb

def synthesize_wordcloud_sfx(wav_path: str, duration: float = 4.0):
    sr = 44100
    n_samples = int(sr * duration)
    t = np.linspace(0.0, duration, n_samples, dtype=np.float32)
    audio = np.zeros(n_samples, dtype=np.float32)

    np.random.seed(7)
    noise = np.random.normal(0, 1, n_samples).astype(np.float32)

    whoosh_env = np.exp(-((t - 0.26) ** 2) / (2 * 0.11 ** 2))
    audio += 0.16 * noise * whoosh_env

    hit_t = 0.46
    dt = np.maximum(0.0, t - hit_t)
    mask = (t >= hit_t).astype(np.float32)
    freq = 38.0 + 65.0 * np.exp(-dt * 20.0)
    phase = 2.0 * np.pi * np.cumsum(freq) / sr
    sub = np.sin(phase) * np.exp(-dt * 4.5) * mask
    audio += 0.72 * sub

    audio = np.tanh(audio * 1.2) * 0.85
    pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    stereo = np.column_stack([pcm, pcm]).flatten()
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())

def render_wordcloud_transition(
    headshot_png: str,
    keywords: list[str],
    out_mp4: str,
    out_jpg: str = None,
    out_gif: str = None,
    team_key: str = "GSW",
    duration: float = 4.0,
):
    W, H = 1920, 1080
    FPS = 60
    ANIM_END = 0.5
    TOTAL_FRAMES = int(round(FPS * duration))

    player_pil = prepare_nba_headshot_canvas(headshot_png, W, H)
    player_arr = np.asarray(player_pil, dtype=np.float32)

    kw1 = keywords[0] if len(keywords) > 0 else "核心球星"
    kw2 = keywords[1] if len(keywords) > 1 else "攻防一体"
    kw3 = keywords[2] if len(keywords) > 2 else "全能战士"
    kw4 = keywords[3] if len(keywords) > 3 else "传切轴心"
    kw5 = keywords[4] if len(keywords) > 4 else "草根逆袭"

    cloud_specs = [
        # --- TIER 3: Dark-Grey Echoes ---
        (kw1[:4], 42, 0.12, 0.055, 78, 0.02, 3),
        (kw5, 46, 0.32, 0.055, 92, 0.03, 3),
        (kw2, 46, 0.68, 0.055, 92, 0.03, 3),
        (kw3, 42, 0.88, 0.055, 78, 0.04, 3),
        (kw3, 44, 0.09, 0.40, 82, 0.04, 3),
        (kw4[:4], 46, 0.91, 0.37, 85, 0.05, 3),
        (kw1[:4], 42, 0.08, 0.66, 80, 0.05, 3),
        (kw2, 46, 0.90, 0.75, 82, 0.06, 3),
        (kw5, 44, 0.13, 0.93, 75, 0.06, 3),
        (kw4[:4], 46, 0.87, 0.93, 75, 0.07, 3),

        # --- TIER 2: Medium Grey Echoes ---
        (kw5, 52, 0.20, 0.12, 140, 0.05, 2),
        (kw2, 54, 0.77, 0.12, 148, 0.06, 2),
        (kw3, 62, 0.24, 0.40, 138, 0.06, 2),
        (kw2, 64, 0.76, 0.37, 142, 0.07, 2),
        (kw1, 56, 0.22, 0.66, 145, 0.07, 2),
        (kw4, 54, 0.76, 0.75, 148, 0.08, 2),
        (kw5, 50, 0.15, 0.80, 132, 0.08, 2),
        (kw3, 52, 0.81, 0.85, 128, 0.09, 2),

        # --- TIER 1: Main Core Keywords (Huge Pure White 255) ---
        (kw1, 118 if len(kw1) >= 6 else 135, 0.185, 0.255, 255, 0.08, 1),
        (kw2, 148 if len(kw2) <= 4 else 125, 0.805, 0.245, 255, 0.08, 1),
        (kw3, 135 if len(kw3) <= 4 else 115, 0.205, 0.525, 255, 0.09, 1),
        (kw4, 92 if len(kw4) >= 7 else 115, 0.795, 0.50, 255, 0.09, 1),
        (kw5, 76, 0.795, 0.64, 255, 0.10, 1),
        ("乐透乐透新星", 74, 0.205, 0.68, 255, 0.09, 1),
    ]

    prepared = []
    center_screen_x, center_screen_y = W * 0.50, H * 0.48
    font_heavy = get_font_path(prefer_heavy=True)
    for text, fsize, cx_r, cy_r, t_gray, delay_s, tier in cloud_specs:
        sp = make_word_sprite(text, fsize, tracking=-4 if fsize >= 80 else -2, font_path=font_heavy)
        fcx = W * cx_r
        fcy = H * cy_r
        sscale = 1.34 if tier == 1 else 1.25
        anim_dur = max(0.15, ANIM_END - delay_s)
        prepared.append((sp, fcx, fcy, sscale, t_gray, delay_s, anim_dur, tier))

    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_wordcloud_sfx(tmp_wav, duration)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", tmp_wav,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    slow_dur = duration - ANIM_END
    slow_creep = 0.060

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        frame = np.zeros((H, W, 3), dtype=np.float32)

        for sp, fcx, fcy, sscale, t_gray, delay_s, anim_dur, tier in prepared:
            if t >= delay_s:
                A = sscale - 1.0
                if t <= ANIM_END:
                    u = (t - delay_s) / anim_dur
                    s_slope = min(0.18, (slow_creep / slow_dur) / (A / anim_dur))
                    rem = (1.0 - s_slope) * ((1.0 - u) ** 3) + s_slope * (1.0 - u)
                    factor = 1.0 + A * rem
                else:
                    u = 1.0
                    v = (t - ANIM_END) / slow_dur
                    factor = 1.0 - slow_creep * v

                cur_cx = center_screen_x + (fcx - center_screen_x) * factor
                cur_cy = center_screen_y + (fcy - center_screen_y) * factor
                cur_scale = factor

                start_gray = t_gray * 0.48
                cur_gray = start_gray + (t_gray - start_gray) * (u ** 1.5)
                opacity = min(1.0, (t - delay_s) / 0.07)

                frame = composite_tinted_sprite(frame, sp, cur_cx, cur_cy, cur_scale, cur_gray, opacity)

        p_rgb = player_arr[:, :, :3]
        p_a = player_arr[:, :, 3:4] / 255.0
        frame = frame * (1.0 - p_a) + p_rgb * p_a

        out_u8 = np.clip(frame, 0, 255).astype(np.uint8)
        if out_jpg and f_idx == int(0.55 * FPS):
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
