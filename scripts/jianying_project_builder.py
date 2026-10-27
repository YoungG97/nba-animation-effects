"""Automated 12-Track JianYing Pro Draft Project Builder.
Generates fully packaged sports documentary projects with voiceover, BGM ducking,
SFX triggers, typography animations, chapter cards, stacked honors tiers, and video clips,
and registers them into JianYing Pro's home screen.
"""

import os
import sys
import json
import time
import shutil

skill_root = "/Users/young/.gemini/config/skills/jianying-editor"
if os.path.exists(os.path.join(skill_root, "scripts")):
    sys.path.insert(0, os.path.join(skill_root, "scripts"))

try:
    from jy_wrapper import JyProject, draft
except ImportError:
    JyProject = None
    draft = None

def build_nba_jianying_project(
    project_name: str,
    voice_audio_path: str,
    segments_path: str,
    bgm_music_path: str,
    sfx_paths: dict[str, str],
    poster_titles: list[tuple[str, float, float]],
    honors_tiers: list[tuple[str, float, float]],
    timeline_materials: list[tuple[str, str, float, float, float, any]],
    cover_image_path: str = None,
    drafts_root: str = "/Users/young/Movies/JianyingPro/User Data/Projects/young/JianyingPro Drafts",
    global_meta_path: str = "/Users/young/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/root_meta_info.json",
    bgm_volume: float = 0.18,
    whoosh_volume: float = 0.85,
    click_volume: float = 0.90,
    shutter_volume: float = 0.85,
) -> str:
    """Build and register a broadcast-grade 12-track JianYing Pro documentary project.

    Args:
        project_name: Name of the draft (e.g., '雅克塞尔·伦德博格_人物志').
        voice_audio_path: Path to cleaned WAV voiceover.
        segments_path: Path to segments metadata JSON.
        bgm_music_path: Path to BGM audio file.
        sfx_paths: Dict with keys 'whoosh', 'click', 'shutter'.
        poster_titles: List of (title_text, start_sec, dur_sec).
        honors_tiers: List of (honor_text, start_sec, transform_y).
        timeline_materials: List of (media_type, media_path, start_sec, dur_sec, source_start_sec, intro_animation).
        cover_image_path: Path to cover image JPG.
        drafts_root: JianYing drafts directory.
        global_meta_path: JianYing global root_meta_info.json path.

    Returns:
        draft_dir: Absolute path to the created JianYing draft directory.
    """
    if JyProject is None or draft is None:
        raise ImportError("jy_wrapper is required. Ensure jianying-editor skill is installed.")

    with open(segments_path, "r", encoding="utf-8") as f:
        raw_segments = json.load(f)

    total_dur = round(raw_segments[-1]["end"] + raw_segments[-1]["gap_after"], 3)
    timeline_dur_us = int(round(total_dur * 1e6))

    project = JyProject(project_name, drafts_root=drafts_root, overwrite=True)

    # 1. Voiceover Track
    project.add_media_safe(voice_audio_path, start_time="0s", track_name="Voiceover_Audio")

    # 2. BGM Music Track with Ducking & Fade
    bgm_seg = project.add_media_safe(bgm_music_path, start_time="0s", duration=f"{total_dur:.3f}s", track_name="BGM_Music")
    if bgm_seg:
        bgm_seg.volume = bgm_volume
        bgm_seg.add_fade("0s", "3s")

    # 3. SFX Whoosh Track
    sfx_whoosh = sfx_paths.get("whoosh")
    if sfx_whoosh and os.path.exists(sfx_whoosh):
        for _, p_start, _ in poster_titles:
            w_seg = project.add_media_safe(sfx_whoosh, start_time=f"{p_start:.3f}s", duration="1.0s", track_name="SFX_Whoosh")
            if w_seg:
                w_seg.volume = whoosh_volume

    # 4. SFX Staircase Click Track
    sfx_click = sfx_paths.get("click")
    if sfx_click and os.path.exists(sfx_click):
        for _, h_start, _ in honors_tiers:
            c_seg = project.add_media_safe(sfx_click, start_time=f"{h_start:.3f}s", duration="0.3s", track_name="SFX_Staircase_Click")
            if c_seg:
                c_seg.volume = click_volume

    # 5. SFX Flashback Shutter Track
    sfx_shutter = sfx_paths.get("shutter")
    if sfx_shutter and os.path.exists(sfx_shutter):
        for mtype, mpath, t_start, t_dur, _, _ in timeline_materials:
            if "flashback" in mpath.lower() or "carousel" in mpath.lower():
                num_photos = int(round(t_dur / 1.800))
                for p_i in range(num_photos):
                    st = t_start + p_i * 1.800
                    sh_seg = project.add_media_safe(sfx_shutter, start_time=f"{st:.3f}s", duration="0.5s", track_name="SFX_Flashback_Shutter")
                    if sh_seg:
                        sh_seg.volume = shutter_volume

    # 6. Subtitles Track
    for seg in raw_segments:
        s_start = seg["start"]
        s_dur = seg["dur"]
        text = seg["text"]
        project.add_text_simple(text, start_time=f"{s_start:.3f}s", duration=f"{s_dur:.3f}s")

    # 7. Keyword Poster Titles Track
    poster_style = draft.TextStyle(color=(1.0, 1.0, 1.0), size=12.0, bold=True, align=1)
    poster_border = draft.TextBorder(color=(0.0, 0.0, 0.0), width=0.15)
    poster_clip = draft.ClipSettings(transform_y=0.0)
    poster_track_name = "Keyword_Poster_Title"
    project.script.add_track(draft.TrackType.text, poster_track_name)
    for title_text, p_start, p_dur in poster_titles:
        p_seg = draft.TextSegment(
            title_text,
            draft.trange(int(round(p_start * 1e6)), int(round(p_dur * 1e6))),
            style=poster_style,
            border=poster_border,
            clip_settings=poster_clip,
        )
        p_seg.add_animation(draft.TextIntro.向上滑动, duration="0.35s")
        project.script.add_segment(p_seg, poster_track_name)

    # 8. Stacked Honors Tiers Tracks
    honor_style = draft.TextStyle(color=(1.0, 0.85, 0.0), size=9.5, bold=True, align=1)
    honor_border = draft.TextBorder(color=(0.0, 0.0, 0.0), width=0.12)
    for i, (htext, hstart, hy) in enumerate(honors_tiers, 1):
        track_name = f"Honor_Tier_{i}"
        project.script.add_track(draft.TrackType.text, track_name)
        # End tier at flashback start
        h_end = timeline_materials[-5][2] if len(timeline_materials) >= 5 else total_dur
        for m in timeline_materials:
            if "flashback" in m[1].lower():
                h_end = m[2]
                break
        dur = max(0.5, h_end - hstart)
        h_clip = draft.ClipSettings(transform_y=hy)
        seg = draft.TextSegment(
            htext,
            draft.trange(int(round(hstart * 1e6)), int(round(dur * 1e6))),
            style=honor_style,
            border=honor_border,
            clip_settings=h_clip,
        )
        seg.add_animation(draft.TextIntro.向上滑动, duration="0.30s")
        project.script.add_segment(seg, track_name)

    # 9. Main Video Track
    for mtype, mpath, t_start, t_dur, src_start, anim_type in timeline_materials:
        if not os.path.exists(mpath):
            continue
        dur_str = f"{t_dur:.3f}s"
        start_str = f"{t_start:.3f}s"
        src_str = f"{src_start:.3f}s" if mtype == "video" else "0s"
        seg = project.add_media_safe(
            mpath,
            start_time=start_str,
            duration=dur_str,
            track_name="Main_Video",
            source_start=src_str,
        )
        if seg:
            if hasattr(seg, "volume"):
                seg.volume = 0.0
            if anim_type:
                seg.add_animation(anim_type, duration="0.5s")

    project.save()

    # Post-process draft meta files for instant JianYing recognition
    draft_dir = os.path.join(drafts_root, project_name)
    info_path = os.path.join(draft_dir, "draft_info.json")
    content_path = os.path.join(draft_dir, "draft_content.json")
    content_bak = os.path.join(draft_dir, "draft_content.json.bak")
    if os.path.exists(info_path):
        shutil.copyfile(info_path, content_path)
        shutil.copyfile(info_path, content_bak)

    meta_path = os.path.join(draft_dir, "draft_meta_info.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["draft_name"] = project_name
        meta["draft_fold_path"] = draft_dir
        meta["draft_timeline_dur"] = timeline_dur_us
        meta["tm_draft_modified"] = int(time.time() * 1000000)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    if cover_image_path and os.path.exists(cover_image_path):
        shutil.copyfile(cover_image_path, os.path.join(draft_dir, "draft_cover.jpg"))

    if os.path.exists(global_meta_path):
        try:
            with open(global_meta_path, "r", encoding="utf-8") as f:
                rm = json.load(f)
            drafts = rm.get("all_draft_store", [])
            found = False
            for d in drafts:
                if d.get("draft_name") == project_name:
                    d["draft_timeline_dur"] = timeline_dur_us
                    d["tm_draft_modified"] = int(time.time() * 1000000)
                    found = True
            if not found:
                new_draft_entry = {
                    "draft_id": f"nba_draft_{int(time.time())}",
                    "draft_name": project_name,
                    "draft_fold_path": draft_dir,
                    "draft_timeline_dur": timeline_dur_us,
                    "tm_draft_create": int(time.time() * 1000000),
                    "tm_draft_modified": int(time.time() * 1000000),
                    "draft_cover": os.path.join(draft_dir, "draft_cover.jpg"),
                    "draft_root_path": drafts_root,
                }
                drafts.insert(0, new_draft_entry)
            with open(global_meta_path, "w", encoding="utf-8") as f:
                json.dump(rm, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return draft_dir
