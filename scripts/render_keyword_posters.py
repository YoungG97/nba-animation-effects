"""Keyword Chapter Posters Renderer (Figure 2 Editorial Poster Aesthetic).
Generates movie/sports poster cards with chapter badge pill, bold title, English subtitle, and lower-third bio.
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

def render_badge_sprite(chapter_idx: int, player_label: str, team_key: str = "OKC") -> Image.Image:
    font_path = get_font_path(prefer_heavy=False)
    sub_font = ImageFont.truetype(font_path, 24)
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

    total_w = int((w_left + pill_pad_x * 2) + gap + w_right)
    pad = 20
    sprite_w = total_w + pad * 2
    sprite_h = 44 + pad * 2

    sprite = Image.new("RGBA", (sprite_w, sprite_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)

    start_x = pad
    top_y = pad + pill_pad_y

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

    return sprite


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
    team_key: str = "OKC",
    duration: float = 2.0,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))
    tc = get_team_colors(team_key)

    font_heavy = get_font_path(prefer_heavy=True)
    font_bold = get_font_path(prefer_heavy=False)

    im_raw = Image.open(photo_path).convert("RGB")
    scale = max(W / im_raw.width, H / im_raw.height)
    nw, nh = int(round(im_raw.width * scale)), int(round(im_raw.height * scale))
    im_scaled = im_raw.resize((nw, nh), Image.Resampling.LANCZOS)
    crop_x = int(np.clip((nw - W) * 0.5, 0, max(0, nw - W)))
    crop_y = int(np.clip((nh - H) * 0.25, 0, max(0, nh - H)))
    base_img = im_scaled.crop((crop_x, crop_y, crop_x + W, crop_y + H))
    base_np = np.asarray(base_img, dtype=np.float32)

    # Sprites
    badge_sp = render_badge_sprite(chapter_idx, player_label, team_key=team_key)

    # Title Sprite (Bold Chinese typography)
    f_title = ImageFont.truetype(font_heavy, 105)
    f_sub = ImageFont.truetype(font_bold, 28)
    tw = f_title.getlength(title_cn)
    sw = int(max(tw, f_sub.getlength(title_en))) + 60
    sh = 180
    title_sp = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    dt = ImageDraw.Draw(title_sp)
    dt.text((31, 33), title_cn, font=f_title, fill=(0, 0, 0, 220), stroke_width=2, stroke_fill=(0, 0, 0, 220))
    dt.text((30, 30), title_cn, font=f_title, fill=(255, 255, 255, 255))
    dt.text((31, 141), title_en, font=f_sub, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))
    dt.text((30, 140), title_en, font=f_sub, fill=tc["accent"] + (255,))

    # Lower-third description
    f_body = ImageFont.truetype(font_bold, 30)
    bw = int(f_body.getlength(body_text)) + 60
    bh = 70
    body_sp = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    db = ImageDraw.Draw(body_sp)
    db.text((31, 22), body_text, font=f_body, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))
    db.text((30, 20), body_text, font=f_body, fill=(255, 255, 255, 240))

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
    black_gradient = np.clip((y_coords - 0.40) / 0.60, 0.0, 1.0) ** 1.35 * 0.85

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        push_p = t / duration
        zoom = 1.0 + 0.035 * push_p
        cx, cy = W * 0.50, H * 0.45
        M = np.float32([
            [zoom, 0, cx * (1.0 - zoom)],
            [0, zoom, cy * (1.0 - zoom)],
        ])
        frame = cv2.warpAffine(base_np, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        frame = frame * (1.0 - black_gradient)

        # Entrance animations
        u_b = min(1.0, t / 0.25)
        p_b = ease_out_back(u_b, overshoot=1.1)
        frame = alpha_composite_sprite(frame, badge_sp, center_x=int(140 + badge_sp.width // 2), center_y=int(H * 0.52 * p_b), opacity=min(1.0, u_b * 2))

        if t >= 0.10:
            u_t = min(1.0, (t - 0.10) / 0.28)
            p_t = ease_out_back(u_t, overshoot=1.15)
            frame = alpha_composite_sprite(frame, title_sp, center_x=int(140 + title_sp.width // 2), center_y=int(H * 0.65 * p_t), opacity=min(1.0, u_t * 2))

        if t >= 0.22:
            u_d = min(1.0, (t - 0.22) / 0.30)
            p_d = ease_out_back(u_d, overshoot=1.1)
            frame = alpha_composite_sprite(frame, body_sp, center_x=int(140 + body_sp.width // 2), center_y=int(H * 0.80 * p_d), opacity=min(1.0, u_d * 2))

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
