"""Keyword Chapter Posters Renderer (Figure 2 Editorial Poster Aesthetic).
Generates movie/sports poster cards with chapter badge pill, centered bold title, and cinematic photo grading.
Matches benchmark media_1793033375396_edc63561.png (MotorCade).
"""

import os
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from .engine import (
    get_font_path,
    synthesize_camera_shutter_sfx,
    alpha_composite_sprite,
    ease_out_back,
)
from .team_colors import get_team_colors

def apply_cinematic_grading(img: Image.Image, target_w: int = 1920, target_h: int = 1080) -> Image.Image:
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    elif src_ratio < target_ratio:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 3
        img = img.crop((0, top, src_w, top + new_h))

    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.15)

    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    px = overlay.load()
    for y in range(target_h):
        ny = y / target_h
        grad_alpha = int(210 * ((ny - 0.38) / 0.62) ** 1.3) if ny > 0.38 else 0
        top_alpha = int(95 * ((1.0 - ny / 0.22) ** 2)) if ny < 0.22 else 0
        for x in range(target_w):
            nx = x / target_w
            dx = (nx - 0.50) * 1.15
            dy = (ny - 0.45) * 1.10
            dist_sq = dx * dx + dy * dy
            vig_alpha = min(180, int(150 * (dist_sq ** 1.25)))
            combined = 255 - int((255 - grad_alpha) * (255 - vig_alpha) * (255 - top_alpha) / (255 * 255))
            px[x, y] = (0, 0, 0, min(255, combined))

    return Image.alpha_composite(img.convert("RGBA"), overlay)

def draw_chapter_badge(chapter_idx: int, player_label: str, team_key: str = "GSW", top_y: int = 420, center_x: int = 960) -> Image.Image:
    lay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(lay)
    font_bold = get_font_path(prefer_heavy=False)
    sub_font = ImageFont.truetype(font_bold, 24)
    left_label = f"CHAPTER 0{chapter_idx}"
    right_label = player_label
    tc = get_team_colors(team_key)

    def measure_spaced(s: str, spacing: int = 4) -> float:
        return sum(sub_font.getlength(c) for c in s) + spacing * max(0, len(s) - 1)

    w_left = measure_spaced(left_label, 4)
    w_right = measure_spaced(right_label, 4)
    gap = 26
    pill_pad_x = 14
    pill_pad_y = 5
    total_w = (w_left + pill_pad_x * 2) + gap + w_right
    start_x = int(center_x - total_w / 2)

    pill_rect = [
        start_x,
        top_y - pill_pad_y,
        int(start_x + w_left + pill_pad_x * 2),
        top_y + 28 + pill_pad_y,
    ]
    draw.rounded_rectangle(pill_rect, radius=5, fill=tc["primary"] + (235,))

    cx = start_x + pill_pad_x
    for c in left_label:
        draw.text((cx, top_y), c, font=sub_font, fill=(255, 255, 255, 255))
        cx += sub_font.getlength(c) + 4

    cx = start_x + (w_left + pill_pad_x * 2) + gap
    for c in right_label:
        draw.text((cx + 1, top_y + 1), c, font=sub_font, fill=(0, 0, 0, 160))
        draw.text((cx, top_y), c, font=sub_font, fill=(215, 225, 235, 230))
        cx += sub_font.getlength(c) + 4

    return lay

def render_poster_title_sprite(title: str, font_size: int = 140) -> Image.Image:
    font_heavy = get_font_path(prefer_heavy=True)
    font = ImageFont.truetype(font_heavy, font_size)
    tracking = -5
    stroke_width = 2

    char_advances = [font.getlength(ch) for ch in title]
    total_w = int(sum(char_advances) + tracking * max(0, len(title) - 1))
    pad_x = 60
    pad_y = 50
    sw = total_w + pad_x * 2
    sh = font_size + pad_y * 2

    shadow_wide = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    shadow_tight = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    fg_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))

    draw_sw = ImageDraw.Draw(shadow_wide)
    draw_st = ImageDraw.Draw(shadow_tight)
    draw_fg = ImageDraw.Draw(fg_layer)

    cur_x = pad_x
    y = pad_y - int(font_size * 0.10)
    for idx, ch in enumerate(title):
        draw_sw.text((cur_x, y + 8), ch, font=font, fill=(0, 0, 0, 240), stroke_width=stroke_width + 6, stroke_fill=(0, 0, 0, 240))
        draw_st.text((cur_x + 4, y + 7), ch, font=font, fill=(0, 0, 0, 255), stroke_width=stroke_width + 2, stroke_fill=(0, 0, 0, 255))
        draw_fg.text((cur_x, y), ch, font=font, fill=(255, 255, 255, 255), stroke_width=stroke_width, stroke_fill=(255, 255, 255, 255))
        cur_x += char_advances[idx] + tracking

    shadow_wide = shadow_wide.filter(ImageFilter.GaussianBlur(radius=18))
    shadow_tight = shadow_tight.filter(ImageFilter.GaussianBlur(radius=3.5))

    out = Image.alpha_composite(shadow_wide, shadow_tight)
    out = Image.alpha_composite(out, fg_layer)
    return out

def render_single_keyword_card(
    chapter_idx: int,
    title_cn: str,
    title_en: str,
    body_text: str,
    photo_path: str,
    player_label: str,
    out_mp4: str,
    out_jpg: str = None,
    out_gif: str = None,
    team_key: str = "GSW",
    duration: float = 2.0,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))

    base_graded = apply_cinematic_grading(Image.open(photo_path), W, H)
    badge_layer = draw_chapter_badge(chapter_idx=chapter_idx, player_label=player_label, team_key=team_key, top_y=420, center_x=W // 2)
    title_sprite = render_poster_title_sprite(title_cn, font_size=140)

    if out_jpg:
        comp = Image.alpha_composite(base_graded, badge_layer)
        comp_np = np.asarray(comp.convert("RGB"), dtype=np.float32)
        comp_np = alpha_composite_sprite(comp_np, title_sprite, center_x=W // 2, center_y=540, opacity=1.0)
        Image.fromarray(np.clip(comp_np, 0, 255).astype(np.uint8)).save(out_jpg, quality=95)

    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_camera_shutter_sfx(tmp_wav, duration=duration)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", tmp_wav,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    comp = Image.alpha_composite(base_graded, badge_layer)
    base_with_badge_np = np.asarray(comp.convert("RGB"), dtype=np.float32)

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        push = 1.00 + 0.03 * (t / duration)
        M = np.float32([
            [push, 0, (W * 0.5) * (1.0 - push)],
            [0, push, (H * 0.5) * (1.0 - push)],
        ])
        frame = cv2.warpAffine(base_with_badge_np, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

        u = min(1.0, t / 0.30)
        p = ease_out_back(u, overshoot=1.20)
        cur_y = int(540 * (0.94 + 0.06 * p))
        frame = alpha_composite_sprite(frame, title_sprite, center_x=W // 2, center_y=cur_y, opacity=min(1.0, u * 2))

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
