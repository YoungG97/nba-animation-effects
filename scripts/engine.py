"""NBA Player Video Maker Core Engine.
Includes 2.5D motion, procedural sound synthesis, broadcast typography, and sprite generation.
"""

import math
import os
import subprocess
import wave
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Font discovery
FONT_BOLD = "/Users/young/Library/Fonts/IBMPlexSansSC-Bold.otf"
FONT_HEAVY = "/Users/young/Library/Fonts/AlibabaPuHuiTi-2-115-Black.otf"
FONT_FALLBACK = "/System/Library/Fonts/PingFang.ttc"

def get_font_path(prefer_heavy: bool = False) -> str:
    if prefer_heavy and os.path.exists(FONT_HEAVY):
        return FONT_HEAVY
    if os.path.exists(FONT_BOLD):
        return FONT_BOLD
    if os.path.exists(FONT_HEAVY):
        return FONT_HEAVY
    return FONT_FALLBACK


# ==============================================================================
# 1. MOTION EASING CURVES
# ==============================================================================

def ease_out_back(u: float, overshoot: float = 1.15) -> float:
    c1 = overshoot
    c3 = c1 + 1.0
    return 1.0 + c3 * ((u - 1.0) ** 3) + c1 * ((u - 1.0) ** 2)

def ease_in_out_quad(u: float) -> float:
    if u < 0.5:
        return 2.0 * u * u
    return 1.0 - ((-2.0 * u + 2.0) ** 2) / 2.0


# ==============================================================================
# 2. PROCEDURAL SOUND SYNTHESIZERS (100% Free Local Synthesis via NumPy/WAV)
# ==============================================================================

def synthesize_slam_sfx(wav_path: str, duration: float = 2.5, hit_t: float = 0.28):
    sr = 44100
    n = int(sr * duration)
    t = np.linspace(0.0, duration, n, dtype=np.float32)
    audio = np.zeros(n, dtype=np.float32)

    np.random.seed(42)
    noise = np.random.normal(0, 1, n).astype(np.float32)

    # 1. Whoosh leading up to hit
    t_rise = hit_t - 0.24
    m_rise = ((t >= t_rise) & (t <= hit_t)).astype(np.float32)
    u_rise = np.clip((t - t_rise) / 0.24, 0.0, 1.0)
    audio += 0.28 * noise * (u_rise ** 2.2) * m_rise

    # 2. Low-frequency punch thud
    dt = np.maximum(0.0, t - hit_t)
    m_hit = (t >= hit_t).astype(np.float32)
    freq = 55.0 + 35.0 * np.exp(-dt * 22.0)
    phase = 2.0 * np.pi * np.cumsum(freq) / sr
    audio += 0.65 * np.sin(phase) * np.exp(-dt * 7.5) * m_hit

    # 3. Sub-bass boom
    freq_sub = 36.0 * np.exp(-dt * 4.0)
    phase_sub = 2.0 * np.pi * np.cumsum(freq_sub) / sr
    audio += 0.40 * np.sin(phase_sub) * np.exp(-dt * 3.5) * m_hit

    audio = np.tanh(audio * 1.15) * 0.85
    pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    stereo = np.column_stack([pcm, pcm]).flatten()
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


def synthesize_multi_hit_sfx(wav_path: str, duration: float, hit_times: list[float]):
    sr = 44100
    n = int(sr * duration)
    t = np.linspace(0.0, duration, n, dtype=np.float32)
    audio = np.zeros(n, dtype=np.float32)

    np.random.seed(42)
    noise = np.random.normal(0, 1, n).astype(np.float32)

    for idx, ht in enumerate(hit_times):
        env_whoosh = np.exp(-((t - ht) ** 2) / (2 * (0.045 ** 2)))
        audio += 0.24 * noise * env_whoosh

        dt = np.maximum(0.0, t - ht)
        m = (t >= ht).astype(np.float32)
        base_f = 65.0 if idx == 0 else 85.0
        freq = base_f + 40.0 * np.exp(-dt * 20.0)
        phase = 2.0 * np.pi * np.cumsum(freq) / sr
        audio += 0.40 * np.sin(phase) * np.exp(-dt * 8.0) * m

    audio = np.tanh(audio * 1.1) * 0.82
    pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    stereo = np.column_stack([pcm, pcm]).flatten()
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


def synthesize_camera_shutter_sfx(wav_path: str, duration: float = 1.6):
    sr = 44100
    n = int(sr * duration)
    t = np.linspace(0.0, duration, n, dtype=np.float32)
    audio = np.zeros(n, dtype=np.float32)

    np.random.seed(123)
    noise = np.random.normal(0, 1, n).astype(np.float32)

    # Shutter click 1 (t=0.04)
    dt1 = np.maximum(0.0, t - 0.04)
    m1 = (t >= 0.04).astype(np.float32)
    audio += 0.45 * noise * np.exp(-dt1 * 60.0) * m1

    # Mirror slap (t=0.07)
    dt2 = np.maximum(0.0, t - 0.07)
    m2 = (t >= 0.07).astype(np.float32)
    audio += 0.38 * np.sin(2.0 * np.pi * 120.0 * dt2) * np.exp(-dt2 * 45.0) * m2
    audio += 0.35 * noise * np.exp(-dt2 * 50.0) * m2

    audio = np.tanh(audio * 1.2) * 0.80
    pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    stereo = np.column_stack([pcm, pcm]).flatten()
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


# ==============================================================================
# 3. TYPOGRAPHY & SPRITE GENERATION (With 1px Subtle Contour Shadow)
# ==============================================================================

def make_text_line_sprite(
    text: str,
    font_size: int = 42,
    fill_color=(255, 196, 18, 255),
    stroke_width: int = 0,
    has_shadow: bool = True,
    font_path: str = None,
) -> tuple[Image.Image, int]:
    """Clean broadcast-grade text line sprite with IBM Plex Sans SC Bold, subtle crisp 1px contour shadow."""
    fp = font_path or get_font_path(prefer_heavy=False)
    font = ImageFont.truetype(fp, font_size)
    total_w = int(font.getlength(text))
    pad = 30
    sw = total_w + pad * 2
    sh = int(font_size * 1.5) + pad * 2

    base = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    cx, cy = pad, pad
    if has_shadow:
        # Subtle crisp shadow with 1px contour stroke and (1, 3) offset
        d.text((cx + 1, cy + 3), text, font=font, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))

    # Foreground text (crisp fill, no stroke expansion so strokes remain razor sharp)
    d.text((cx, cy), text, font=font, fill=fill_color)
    return base, pad


def make_era_title_sprite(
    title: str,
    years: str,
    primary_color: tuple[int, int, int] = (0, 125, 195),
    secondary_color: tuple[int, int, int] = (239, 59, 36),
    accent_gold: tuple[int, int, int] = (255, 212, 92),
) -> tuple[Image.Image, int, int]:
    """Era header with dual-color team underline and 1px contour shadow."""
    font_path = get_font_path(prefer_heavy=False)
    font_title = ImageFont.truetype(font_path, 54)
    font_years = ImageFont.truetype(font_path, 36)

    tw = font_title.getlength(title)
    yw = font_years.getlength(years)
    gap = 18
    total_w = int(tw + gap + yw)
    pad = 24
    sw = total_w + pad * 2
    sh = 130

    base = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    dl = ImageDraw.Draw(base)

    # 1px contour shadow
    dl.text((pad + 1, pad + 3), title, font=font_title, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))
    dl.text((pad + tw + gap + 1, pad + 14 + 3), years, font=font_years, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))

    # Foreground text
    dl.text((pad, pad), title, font=font_title, fill=(255, 255, 255, 255))
    dl.text((pad + tw + gap, pad + 14), years, font=font_years, fill=accent_gold + (255,))

    # Dual-color team underline
    bar_y = pad + 72
    bar_h = 8
    dl.rounded_rectangle([pad, bar_y, pad + int(tw), bar_y + bar_h], radius=3, fill=primary_color + (255,))
    dl.rounded_rectangle([pad + int(tw) + 8, bar_y, pad + total_w, bar_y + bar_h], radius=3, fill=secondary_color + (255,))

    return base, pad, pad


def make_honor_text_sprite(
    title: str,
    count_str: str = "X1",
    font_size: int = 36,
    accent_gold: tuple[int, int, int] = (255, 212, 92),
) -> tuple[Image.Image, int, int]:
    """Sequential honor sprite with golden star, clean white title, and golden count."""
    font_path = get_font_path(prefer_heavy=False)
    font = ImageFont.truetype(font_path, font_size)
    font_star = ImageFont.truetype(font_path, int(font_size * 0.95))
    font_count = ImageFont.truetype(font_path, int(font_size * 0.95))

    star_str = "★ "
    w_star = font_star.getlength(star_str)
    w_title = font.getlength(title)
    w_count = font_count.getlength(" " + count_str)

    total_w = int(w_star + w_title + w_count)
    pad = 20
    sw = total_w + pad * 2
    sh = int(font_size * 1.5) + pad * 2

    base = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)

    cx = pad
    cy = pad
    # 1px contour shadow
    d.text((cx + 1, cy + 3), star_str, font=font_star, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))
    d.text((cx + w_star + 1, cy + 3), title, font=font, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))
    d.text((cx + w_star + w_title + 1, cy + 3), " " + count_str, font=font_count, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))

    # Foreground
    d.text((cx, cy), star_str, font=font_star, fill=accent_gold + (255,))
    d.text((cx + w_star, cy), title, font=font, fill=(255, 255, 255, 255))
    d.text((cx + w_star + w_title, cy), " " + count_str, font=font_count, fill=accent_gold + (255,))

    return base, pad, pad


# ==============================================================================
# 4. COMPOSITING & IMAGE UTILITIES
# ==============================================================================

def alpha_composite_sprite(
    frame_rgb: np.ndarray,
    sprite_rgba: Image.Image,
    center_x: int,
    center_y: int,
    opacity: float = 1.0,
) -> np.ndarray:
    """Overlays an RGBA PIL sprite onto a float32 RGB numpy frame (0..255)."""
    H, W, _ = frame_rgb.shape
    sw, sh = sprite_rgba.size
    x0 = int(round(center_x - sw / 2.0))
    y0 = int(round(center_y - sh / 2.0))
    x1 = x0 + sw
    y1 = y0 + sh

    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(W, x1), min(H, y1)
    if fx0 >= fx1 or fy0 >= fy1:
        return frame_rgb

    sx0 = fx0 - x0
    sy0 = fy0 - y0
    sx1 = sx0 + (fx1 - fx0)
    sy1 = sy0 + (fy1 - fy0)

    sp_np = np.asarray(sprite_rgba, dtype=np.float32)
    sp_crop = sp_np[sy0:sy1, sx0:sx1]
    sp_rgb = sp_crop[:, :, :3]
    sp_a = (sp_crop[:, :, 3:4] / 255.0) * float(np.clip(opacity, 0.0, 1.0))

    out = frame_rgb.copy()
    out[fy0:fy1, fx0:fx1] = out[fy0:fy1, fx0:fx1] * (1.0 - sp_a) + sp_rgb * sp_a
    return out
