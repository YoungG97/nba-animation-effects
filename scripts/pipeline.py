"""Master Orchestrator Pipeline for NBA Player Video Maker.
Parses player JSON configuration and generates the complete broadcast package (1080P 60fps).
"""

import argparse
import json
import os
import shutil
import subprocess

from .render_intro import render_opening_intro
from .render_wordcloud import render_wordcloud_transition
from .render_major_chapter import render_major_chapter_card
from .render_profile_hud import render_profile_hud
from .render_era_transitions import render_career_era
from .render_career_marquee import render_single_career_card, concat_career_marquee
from .render_keyword_posters import render_single_keyword_card
from .team_colors import get_team_colors

def run_pipeline(config_path: str, output_dir: str = None, delivery_dir: str = None):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    player_name = cfg.get("player_name", "NBA Player")
    team_key = cfg.get("team_key", "OKC")
    tc = get_team_colors(team_key)

    out_root = output_dir or os.path.join(os.getcwd(), f"output_{team_key}_{player_name}")
    deliv_root = delivery_dir or os.path.expanduser(f"~/Downloads/{player_name}_剪辑成品素材包")

    os.makedirs(out_root, exist_ok=True)
    os.makedirs(deliv_root, exist_ok=True)

    print("=" * 70)
    print(f"NBA PLAYER VIDEO MAKER: {player_name} ({tc['name_zh']} / {tc['name']})")
    print(f"Output Directory:   {out_root}")
    print(f"Delivery Packaging: {deliv_root}")
    print("=" * 70)

    # 1. Opening Intro (10s)
    print("\n>>> [1/8] Rendering Opening Hero Intro (10.0s)...")
    intro_mp4 = f"{out_root}/01_intro_10s.mp4"
    intro_jpg = f"{out_root}/01_intro_10s.jpg"
    intro_gif = f"{out_root}/01_intro_10s.gif"
    render_opening_intro(cfg["photos"]["intro_hero"], player_name, intro_mp4, intro_jpg, intro_gif, team_key=team_key)

    # 2. Wordcloud (4s)
    print("\n>>> [2/8] Rendering Core Wordcloud Contraction (4.0s)...")
    wc_mp4 = f"{out_root}/02_wordcloud_4s.mp4"
    wc_jpg = f"{out_root}/02_wordcloud_4s.jpg"
    wc_gif = f"{out_root}/02_wordcloud_4s.gif"
    render_wordcloud_transition(cfg["photos"]["wordcloud_bg"], cfg["keywords"], wc_mp4, wc_jpg, wc_gif, team_key=team_key)

    # 3. Major Chapter 1 (2.5s)
    print("\n>>> [3/8] Rendering Major Chapter 1: 基本信息 (2.5s)...")
    ch1_mp4 = f"{out_root}/03_major_01_basic_info_2.5s.mp4"
    render_major_chapter_card(cfg["photos"]["major_ch1_bg"], "基本信息", ch1_mp4, font_size=180)

    # 4. Profile HUD (12s)
    print("\n>>> [4/8] Rendering Aesthetic Profile HUD (12.0s)...")
    prof_mp4 = f"{out_root}/04_profile_hud_12s.mp4"
    prof_jpg1 = f"{out_root}/04_profile_hud_part1.jpg"
    prof_jpg2 = f"{out_root}/04_profile_hud_part2.jpg"
    prof_gif = f"{out_root}/04_profile_hud.gif"
    render_profile_hud(cfg["photos"]["profile_hero1"], cfg["photos"]["profile_hero2"], cfg["profile"], prof_mp4, prof_jpg1, prof_jpg2, prof_gif, team_key=team_key)

    # 5. Major Chapter 2 (2.5s)
    print("\n>>> [5/8] Rendering Major Chapter 2: 职业生涯经历及成就 (2.5s)...")
    ch2_mp4 = f"{out_root}/05_major_02_career_2.5s.mp4"
    render_major_chapter_card(cfg["photos"]["major_ch2_bg"], "职业生涯经历及成就", ch2_mp4, font_size=150)

    # 6. Career Eras
    print("\n>>> [6/8] Rendering Career Era Transitions (Calibrated Timing)...")
    era_clips = []
    for e_idx, era in enumerate(cfg.get("eras", [])):
        era_title = era["title"]
        era_years = era["years"]
        era_honors = [tuple(h) for h in era["honors"]]
        era_mp4 = f"{out_root}/06_era_{e_idx+1:02d}.mp4"
        era_jpg = f"{out_root}/06_era_{e_idx+1:02d}.jpg"
        era_gif = f"{out_root}/06_era_{e_idx+1:02d}.gif"
        render_career_era(era["photo"], era_title, era_years, era_honors, era_mp4, era_jpg, era_gif, team_key=team_key, mode="stack")
        era_clips.append(era_mp4)

    # 7. Career 20 Milestone Cards & Marquee (32s)
    print("\n>>> [7/8] Rendering Career Milestone Cards & Marquee Slideshow...")
    card_clips = []
    for c_idx, card in enumerate(cfg.get("career_cards", [])):
        c_mp4 = f"{out_root}/card_{c_idx+1:02d}.mp4"
        c_jpg = f"{out_root}/card_{c_idx+1:02d}.jpg"
        render_single_career_card(card["photo"], card["lines"], c_mp4, c_jpg, team_key=team_key)
        card_clips.append(c_mp4)

    marquee_mp4 = f"{out_root}/08_career_marquee_32s.mp4"
    marquee_jpg = f"{out_root}/08_career_marquee_32s.jpg"
    marquee_gif = f"{out_root}/08_career_marquee_32s.gif"
    concat_career_marquee(card_clips, marquee_mp4, marquee_gif, marquee_jpg)

    # 8. Keyword Chapter Poster Cards (8s)
    print("\n>>> [8/8] Rendering 4 Keyword Chapter Poster Cards (8.0s)...")
    kw_clips = []
    for k_idx, kw_card in enumerate(cfg.get("keyword_chapters", [])):
        k_mp4 = f"{out_root}/kw_poster_{k_idx+1:02d}.mp4"
        k_jpg = f"{out_root}/kw_poster_{k_idx+1:02d}.jpg"
        k_gif = f"{out_root}/kw_poster_{k_idx+1:02d}.gif"
        render_single_keyword_card(
            chapter_idx=k_idx + 1,
            title_cn=kw_card["title_cn"],
            title_en=kw_card["title_en"],
            body_text=kw_card["body_text"],
            photo_path=kw_card["photo"],
            player_label=f"{cfg.get('name_en_short', player_name)} · #{cfg.get('jersey_number', '0')}",
            out_mp4=k_mp4,
            out_jpg=k_jpg,
            out_gif=k_gif,
            team_key=team_key,
        )
        kw_clips.append(k_mp4)

    kw_all_mp4 = f"{out_root}/09_keywords_all_8s.mp4"
    concat_career_marquee(kw_clips, kw_all_mp4)

    # Concat Full Master Video
    print("\n>>> Assembling Full Master Video...")
    all_ordered = [intro_mp4, wc_mp4, ch1_mp4, prof_mp4, ch2_mp4] + era_clips + [marquee_mp4, kw_all_mp4]
    norm_ts = []
    for p in all_ordered:
        ts_p = p.replace(".mp4", "_norm.ts")
        subprocess.run([
            "ffmpeg", "-y", "-i", p,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "17", "-r", "60", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            ts_p,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        norm_ts.append(ts_p)

    txt_concat = f"{out_root}/master_concat.txt"
    with open(txt_concat, "w") as f:
        for p in norm_ts:
            f.write(f"file '{p}'\n")

    master_mp4 = f"{out_root}/00_master_full.mp4"
    master_jpg = f"{out_root}/00_master_full.jpg"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", txt_concat, "-c", "copy", master_mp4], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["ffmpeg", "-y", "-ss", "00:00:05.5", "-i", master_mp4, "-vframes", "1", "-q:v", "2", master_jpg], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(txt_concat)
    for p in norm_ts:
        if os.path.exists(p): os.remove(p)

    # Package to delivery directories
    d_timeline = os.path.join(deliv_root, "10_【直接拖入剪辑器】按时间线顺序单轨片段")
    d_master = os.path.join(deliv_root, "00_【参考母片】全片无缝合体完整视频")
    os.makedirs(d_timeline, exist_ok=True)
    os.makedirs(d_master, exist_ok=True)

    shutil.copy2(master_mp4, os.path.join(d_master, f"01_【全片合体】{player_name}_完整全片_1080P60.mp4"))
    shutil.copy2(master_jpg, os.path.join(d_master, f"01_【全片合体】{player_name}_封面预览图.jpg"))

    # Direct timeline copy
    timeline_copies = [
        (intro_mp4, "01_开头人物入场_每天认识一位NBA球员_10秒.mp4"),
        (wc_mp4, "02_核心词云过渡_4秒.mp4"),
        (ch1_mp4, "03_大章节过渡一_基本信息_2.5秒.mp4"),
        (prof_mp4, "04_详细基本信息杂志排版_12秒.mp4"),
        (ch2_mp4, "05_大章节过渡二_职业生涯经历及成就_2.5秒.mp4"),
    ]
    for idx, e_p in enumerate(era_clips):
        timeline_copies.append((e_p, f"06_职业生涯时期_{idx+1:02d}.mp4"))
    timeline_copies.append((marquee_mp4, "08_职业生涯全套连续跑马灯_32秒.mp4"))
    timeline_copies.append((kw_all_mp4, "09_关键词小章节全套合体连播_8秒.mp4"))

    for src_p, dst_fn in timeline_copies:
        if os.path.exists(src_p):
            shutil.copy2(src_p, os.path.join(d_timeline, dst_fn))

    print("\n" + "=" * 70)
    print("ALL MODULES SUCCESSFULLY GENERATED & PACKAGED!")
    print(f"Master Video: {os.path.join(d_master, f'01_【全片合体】{player_name}_完整全片_1080P60.mp4')}")
    print(f"Timeline Folder: {d_timeline}")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="NBA Player Video Maker Master Pipeline")
    parser.add_argument("--config", "-c", required=True, help="Path to player JSON config")
    parser.add_argument("--output", "-o", default=None, help="Directory to save raw generated files")
    parser.add_argument("--delivery", "-d", default=None, help="Directory for final NLE timeline delivery packaging")
    args = parser.parse_args()

    run_pipeline(args.config, args.output, args.delivery)

if __name__ == "__main__":
    main()
