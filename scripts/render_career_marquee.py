"""Career Milestone Cards & Marquee Slideshow Renderer.
Uses broadcast typography with 1px contour shadow, subtle zoom, and procedural camera shutter audio.
"""

import os
import subprocess
import cv2
import numpy as np
from PIL import Image

from .engine import (
    make_text_line_sprite,
    synthesize_camera_shutter_sfx,
)
from .team_colors import get_team_colors

def render_single_career_card(
    photo_path: str,
    lines: list[str],
    out_mp4: str,
    out_jpg: str = None,
    crop_focus: tuple[float, float] = (0.5, 0.20),
    team_key: str = "OKC",
    duration: float = 1.6,
):
    W, H = 1920, 1080
    FPS = 60
    TOTAL_FRAMES = int(round(FPS * duration))
    tc = get_team_colors(team_key)

    im_raw = Image.open(photo_path).convert("RGB")
    iw, ih = im_raw.size
    scale = max(W / iw, H / ih)
    nw, nh = int(round(iw * scale)), int(round(ih * scale))
    im_scaled = im_raw.resize((nw, nh), Image.Resampling.LANCZOS)

    fx, fy = crop_focus
    crop_x = int(np.clip((nw - W) * fx, 0, max(0, nw - W)))
    crop_y = int(np.clip((nh - H) * fy, 0, max(0, nh - H)))
    base_img = im_scaled.crop((crop_x, crop_y, crop_x + W, crop_y + H))
    base_np = np.asarray(base_img, dtype=np.float32)

    sprites_info = []
    line_start_times = [0.00, 0.07, 0.14, 0.22]
    wipe_durations = [0.18, 0.18, 0.18, 0.18]
    for idx, text in enumerate(lines):
        fill = tc["accent"] + (255,) if idx == 0 else (255, 255, 255, 255)
        sp, pad = make_text_line_sprite(text, font_size=42, fill_color=fill, stroke_width=0, has_shadow=True)
        sprites_info.append((sp, pad))

    tmp_wav = out_mp4.replace(".mp4", "_sfx.wav")
    synthesize_camera_shutter_sfx(tmp_wav, duration)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", tmp_wav,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    start_x = int(W * 0.065)
    start_y = int(H * 0.60)
    line_spacing = 64

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS
        push_p = t / duration
        zoom = 1.0 + 0.025 * push_p
        cx, cy = W * 0.45, H * 0.40
        M = np.float32([
            [zoom, 0, cx * (1.0 - zoom)],
            [0, zoom, cy * (1.0 - zoom)],
        ])
        frame = cv2.warpAffine(base_np, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

        # Subtle dark gradient at lower-left corner
        ys = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        xs = np.linspace(0, 1, W, dtype=np.float32)[None, :]
        grad = np.clip((ys - 0.48) / 0.52, 0.0, 1.0) * np.clip((0.72 - xs) / 0.72, 0.0, 1.0) * 0.52
        frame = frame * (1.0 - grad[:, :, None])

        frame_pil = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
        for idx, (sp, pad) in enumerate(sprites_info):
            st = line_start_times[idx]
            dur = wipe_durations[idx]
            if t >= st:
                u = min(1.0, (t - st) / dur)
                cur_y = start_y + idx * line_spacing
                if u >= 0.999:
                    frame_pil.paste(sp, (start_x - pad, cur_y - pad), sp)
                else:
                    sp_w, sp_h = sp.size
                    visible_w = int(round(sp_w * u))
                    if visible_w > 0:
                        cropped_sp = sp.crop((0, 0, visible_w, sp_h))
                        frame_pil.paste(cropped_sp, (start_x - pad, cur_y - pad), cropped_sp)

        out_u8 = np.asarray(frame_pil)
        if out_jpg and f_idx == int(0.9 * FPS):
            Image.fromarray(out_u8).save(out_jpg, quality=95)

        proc.stdin.write(out_u8.tobytes())

    proc.stdin.close()
    proc.wait()
    if os.path.exists(tmp_wav):
        os.remove(tmp_wav)


def concat_career_marquee(clip_list: list[str], out_mp4: str, out_gif: str = None, out_jpg: str = None):
    txt_file = out_mp4.replace(".mp4", "_concat.txt")
    with open(txt_file, "w") as f:
        for c in clip_list:
            f.write(f"file '{c}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", txt_file, "-c", "copy", out_mp4], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(txt_file)

    if out_jpg:
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:01.0", "-i", out_mp4, "-vframes", "1", "-q:v", "2", out_jpg], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if out_gif:
        subprocess.run([
            "ffmpeg", "-y", "-t", "5.0", "-i", out_mp4,
            "-vf", "fps=18,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
            out_gif,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
