"""Opening Hero Intro Renderer (10.0s, '每天认识一位NBA球员' + Hero Cutout + 5.0s Name Slam).
Matches the benchmark visual aesthetic (golden aura glow, title behind head, 5s name slam).
"""

import os
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from .engine import (
    get_font_path,
    synthesize_slam_sfx,
    alpha_composite_sprite,
    ease_out_back,
)
from .team_colors import get_team_colors

SWIFT_SEGMENT = os.path.join(os.path.dirname(__file__), "segment_person.swift")

def get_person_mask(photo_path: str, target_w: int = 1920, target_h: int = 1080) -> np.ndarray:
    cache_png = photo_path + ".mask_cache.png"
    if not os.path.exists(cache_png) and os.path.exists(SWIFT_SEGMENT):
        try:
            subprocess.run(["swift", SWIFT_SEGMENT, photo_path, cache_png], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    if os.path.exists(cache_png):
        m_img = Image.open(cache_png).convert("L")
        m_resized = m_img.resize((target_w, target_h), Image.Resampling.BILINEAR)
        return np.asarray(m_resized, dtype=np.float32) / 255.0
    
    # Fallback soft center mask if Swift is not available
    xs = np.linspace(-1.0, 1.0, target_w, dtype=np.float32)[None, :]
    ys = np.linspace(-1.0, 1.0, target_h, dtype=np.float32)[:, None]
    dist = np.sqrt((xs * 1.2) ** 2 + (ys * 0.9) ** 2)
    return np.clip(1.0 - (dist - 0.2) / 0.5, 0.0, 1.0)

def build_player_with_golden_aura(img_pil: Image.Image, alpha_mask: np.ndarray) -> Image.Image:
    img_np = np.asarray(img_pil.convert("RGB"), dtype=np.float32)
    mask_u8 = (alpha_mask * 255.0).astype(np.uint8)
    k_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))
    dilated = cv2.dilate(mask_u8, k_dilate, iterations=1).astype(np.float32) / 255.0

    glow_inner = cv2.GaussianBlur(dilated, (45, 45), 14.0)
    glow_outer = cv2.GaussianBlur(dilated, (95, 95), 32.0)
    glow_alpha = np.clip(glow_inner * 0.78 + glow_outer * 0.55, 0.0, 0.95)

    aura_color = np.array([255.0, 244.0, 152.0], dtype=np.float32)[None, None, :]
    fg_a = alpha_mask[:, :, None]
    ga = glow_alpha[:, :, None]

    out_a = fg_a + ga * (1.0 - fg_a)
    safe_out_a = np.maximum(out_a, 1e-5)
    out_rgb = (img_np * fg_a + aura_color * ga * (1.0 - fg_a)) / safe_out_a

    rgba = np.dstack([
        np.clip(out_rgb, 0, 255).astype(np.uint8),
        np.clip(out_a[:, :, 0] * 255.0, 0, 255).astype(np.uint8),
    ])
    return Image.fromarray(rgba, mode="RGBA")

def render_top_banner_sprite(text: str = "每天认识一位NBA球员", target_w: int = 1920, target_h: int = 1080) -> Image.Image:
    font_heavy = get_font_path(prefer_heavy=True)
    font = ImageFont.truetype(font_heavy, 182)
    tracking = -4

    char_advances = [font.getlength(ch) for ch in text]
    total_w = sum(char_advances) + tracking * (len(text) - 1)
    start_x = int((target_w - total_w) / 2)
    top_y = int(target_h * 0.068)

    shadow_wide = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    shadow_tight = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    fg_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    draw_sw = ImageDraw.Draw(shadow_wide)
    draw_st = ImageDraw.Draw(shadow_tight)
    draw_fg = ImageDraw.Draw(fg_layer)

    cur_x = start_x
    for idx, ch in enumerate(text):
        draw_sw.text((cur_x, top_y + 10), ch, font=font, fill=(0, 0, 0, 235), stroke_width=8, stroke_fill=(0, 0, 0, 235))
        draw_st.text((cur_x + 5, top_y + 8), ch, font=font, fill=(0, 0, 0, 255), stroke_width=4, stroke_fill=(0, 0, 0, 255))
        draw_fg.text((cur_x, top_y), ch, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(255, 255, 255, 255))
        cur_x += char_advances[idx] + tracking

    shadow_wide = shadow_wide.filter(ImageFilter.GaussianBlur(radius=16))
    shadow_tight = shadow_tight.filter(ImageFilter.GaussianBlur(radius=3.0))

    out = Image.alpha_composite(shadow_wide, shadow_tight)
    out = Image.alpha_composite(out, fg_layer)
    return out

def render_name_slam_sprite(text: str, font_size: int = 168) -> Image.Image:
    font_heavy = get_font_path(prefer_heavy=True)
    font = ImageFont.truetype(font_heavy, font_size)
    tracking = -6
    stroke_width = 2

    char_advances = [font.getlength(ch) for ch in text]
    total_w = int(sum(char_advances) + tracking * max(0, len(text) - 1))
    pad_x = 80
    pad_y = 70
    sw = total_w + pad_x * 2
    sh = font_size + pad_y * 2

    shadow_wide = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    shadow_tight = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    fg_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))

    draw_sw = ImageDraw.Draw(shadow_wide)
    draw_st = ImageDraw.Draw(shadow_tight)
    draw_fg = ImageDraw.Draw(fg_layer)

    cur_x = pad_x
    y = pad_y - int(font_size * 0.12)
    for idx, ch in enumerate(text):
        draw_sw.text((cur_x, y + 8), ch, font=font, fill=(0, 0, 0, 240), stroke_width=stroke_width + 6, stroke_fill=(0, 0, 0, 240))
        draw_st.text((cur_x + 4, y + 7), ch, font=font, fill=(0, 0, 0, 255), stroke_width=stroke_width + 2, stroke_fill=(0, 0, 0, 255))
        draw_fg.text((cur_x, y), ch, font=font, fill=(255, 255, 255, 255), stroke_width=stroke_width, stroke_fill=(255, 255, 255, 255))
        cur_x += char_advances[idx] + tracking

    shadow_wide = shadow_wide.filter(ImageFilter.GaussianBlur(radius=18))
    shadow_tight = shadow_tight.filter(ImageFilter.GaussianBlur(radius=3.5))

    out = Image.alpha_composite(shadow_wide, shadow_tight)
    out = Image.alpha_composite(out, fg_layer)
    return out

def render_opening_intro(
    photo_path: str,
    player_name: str,
    out_mp4: str,
    out_jpg: str = None,
    out_gif: str = None,
    bg_arena_path: str = None,
    team_key: str = "GSW",
    duration: float = 10.0,
    name_hit_t: float = 5.0,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))

    # Background
    bg_src = bg_arena_path if bg_arena_path and os.path.exists(bg_arena_path) else photo_path
    arena_raw = Image.open(bg_src).convert("RGB")
    scale = max(W / arena_raw.width, H / arena_raw.height)
    nw, nh = int(round(arena_raw.width * scale)), int(round(arena_raw.height * scale))
    arena_scaled = arena_raw.resize((nw, nh), Image.Resampling.LANCZOS)
    cx = (nw - W) // 2
    cy = (nh - H) // 2
    bg_base = arena_scaled.crop((cx, cy, cx + W, cy + H))
    bg_blurred = bg_base.filter(ImageFilter.GaussianBlur(radius=18))

    bg_rgba = bg_blurred.convert("RGBA")
    top_dim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = top_dim.load()
    for y in range(H):
        ny = y / H
        a = int(120 * max(0.0, 1.0 - ny / 0.40))
        for x in range(W):
            px[x, y] = (0, 0, 0, a)
    bg_darkened = Image.alpha_composite(bg_rgba, top_dim)

    # Cutout & Aura
    cutout_raw = Image.open(photo_path).convert("RGB")
    sc = max(W / cutout_raw.width, H / cutout_raw.height)
    cnw, cnh = int(round(cutout_raw.width * sc)), int(round(cutout_raw.height * sc))
    cutout_scaled = cutout_raw.resize((cnw, cnh), Image.Resampling.LANCZOS)
    ccx = (cnw - W) // 2
    ccy = int((cnh - H) * 0.15)
    player_crop = cutout_scaled.crop((ccx, ccy, ccx + W, ccy + H))

    alpha_mask = get_person_mask(photo_path, W, H)
    player_aura_pil = build_player_with_golden_aura(player_crop, alpha_mask)

    banner_pil = render_top_banner_sprite("每天认识一位NBA球员", W, H)
    name_sprite = render_name_slam_sprite(player_name, font_size=168)
    name_center_x = int(W * 0.50)
    name_center_y = int(H * 0.72)

    # Preview Image
    if out_jpg:
        comp = Image.alpha_composite(bg_darkened, banner_pil)
        comp = Image.alpha_composite(comp, player_aura_pil)
        comp_np = np.asarray(comp.convert("RGB"), dtype=np.float32)
        comp_np = alpha_composite_sprite(comp_np, name_sprite, center_x=name_center_x, center_y=name_center_y, opacity=1.0)
        Image.fromarray(np.clip(comp_np, 0, 255).astype(np.uint8)).save(out_jpg, quality=95)

    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_slam_sfx(tmp_wav, duration, hit_t=name_hit_t)

    bg_np = np.asarray(bg_darkened.convert("RGB"), dtype=np.float32)
    player_aura_np = np.asarray(player_aura_pil, dtype=np.float32)
    player_rgb = player_aura_np[:, :, :3]
    player_a = player_aura_np[:, :, 3:4] / 255.0

    banner_np = np.asarray(banner_pil, dtype=np.float32)
    banner_rgb = banner_np[:, :, :3]
    banner_a = banner_np[:, :, 3:4] / 255.0

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
        push = 1.00 + 0.05 * (t / duration)
        M_bg = np.float32([
            [push, 0, (W * 0.5) * (1.0 - push)],
            [0, push, (H * 0.5) * (1.0 - push)],
        ])
        frame_bg = cv2.warpAffine(bg_np, M_bg, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        frame_with_banner = banner_rgb * banner_a + frame_bg * (1.0 - banner_a)

        player_push = 1.00 + 0.04 * (t / duration)
        M_pl = np.float32([
            [player_push, 0, (W * 0.5) * (1.0 - player_push)],
            [0, player_push, (H * 0.45) * (1.0 - player_push)],
        ])
        warped_player_rgb = cv2.warpAffine(player_rgb, M_pl, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        warped_player_a = cv2.warpAffine(player_a, M_pl, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[:, :, None]

        frame_comp = warped_player_rgb * warped_player_a + frame_with_banner * (1.0 - warped_player_a)

        if t >= name_hit_t:
            u_n = min(1.0, (t - name_hit_t) / 0.32)
            p_n = ease_out_back(u_n, overshoot=1.22)
            cur_cy = int(name_center_y * (0.92 + 0.08 * p_n))
            cur_op = min(1.0, u_n * 2.0)
            frame_comp = alpha_composite_sprite(frame_comp, name_sprite, center_x=name_center_x, center_y=cur_cy, opacity=cur_op)

        out_u8 = np.clip(frame_comp, 0, 255).astype(np.uint8)
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
