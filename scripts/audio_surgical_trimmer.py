"""Audio Surgical Trimmer & Breath Gap Calibration Engine.
High-precision acoustic processor that trims leading/trailing dead air,
removes internal mid-sentence silences (>0.12s), and calibrates breath pacing
for broadcast sports documentaries.
"""

import os
import wave
import json
import numpy as np

def trim_interval_energy(mono: np.ndarray, sr: int, t0: float, t1: float, thresh: float = 30.0, margin: float = 0.018, win_ms: float = 5.0) -> tuple[float, float]:
    """Trim leading and trailing silence from an interval using RMS energy threshold."""
    win = int(round((win_ms / 1000.0) * sr))
    s0, s1 = int(round(t0 * sr)), int(round(t1 * sr))
    clip = mono[s0:s1]
    if len(clip) < win * 2:
        return t0, t1

    v0 = 0
    for i in range(0, len(clip) - win, win):
        if np.mean(clip[i:i + win]) > thresh:
            v0 = i
            break

    v1 = len(clip)
    for i in range(len(clip), win, -win):
        if np.mean(clip[i - win:i]) > thresh:
            v1 = i
            break

    new_t0 = max(t0, t0 + (v0 / sr) - margin)
    new_t1 = min(t1, t0 + (v1 / sr) + margin)
    return round(new_t0, 3), round(new_t1, 3)

def slice_and_calibrate_audio(
    src_wav: str,
    speech_items: list[tuple[list[tuple[float, float]], str, float]],
    out_wav: str,
    out_json: str,
    auto_energy_trim: bool = True,
    fade_ms: float = 4.0,
    internal_subgap_ms: float = 15.0,
    thresh_ratio: float = 2.8,
) -> tuple[float, list[dict]]:
    """Assemble cleaned voiceover audio with calibrated tight breath gaps and export metadata.

    Args:
        src_wav: Path to source high-resolution WAV (44.1kHz or 48kHz stereo).
        speech_items: List of (intervals_list, subtitle_text, gap_after_seconds).
        out_wav: Output cleaned WAV path.
        out_json: Output segment metadata JSON path.
        auto_energy_trim: Whether to auto-trim silent edges on each sub-interval.
        fade_ms: Milliseconds for edge anti-click micro-fade.
        internal_subgap_ms: Milliseconds of micro-gap between sub-intervals within the same sentence.
        thresh_ratio: Multiplier above noise floor for voice detection threshold.

    Returns:
        total_duration: Total audio timeline duration in seconds.
        segments_meta: List of segment timing dictionaries.
    """
    with wave.open(src_wav, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        data = wf.readframes(wf.getnframes())
        audio = np.frombuffer(data, dtype=np.int16).reshape(-1, ch)

    mono = np.abs(audio[:, 0].astype(np.float32))
    noise_floor = np.mean(mono[: int(sr * 0.5)])
    thresh = max(15.0, noise_floor * thresh_ratio)

    fade_len = int(round((fade_ms / 1000.0) * sr))
    fade_in = np.linspace(0, 1, fade_len)[:, None]
    fade_out = np.linspace(1, 0, fade_len)[:, None]

    def get_clean_clip(t0, t1):
        s0 = int(round(t0 * sr))
        s1 = int(round(t1 * sr))
        clip = audio[s0:s1].copy()
        if len(clip) > fade_len * 2:
            clip[:fade_len] = (clip[:fade_len] * fade_in).astype(np.int16)
            clip[-fade_len:] = (clip[-fade_len] * fade_out).astype(np.int16)
        return clip

    internal_gap_samples = int(round((internal_subgap_ms / 1000.0) * sr))

    out_clips = []
    segments_meta = []
    cur_time = 0.0

    for idx, (intervals, text, gap_after) in enumerate(speech_items):
        if auto_energy_trim:
            trimmed_intervals = [trim_interval_energy(mono, sr, t0, t1, thresh=thresh) for t0, t1 in intervals]
        else:
            trimmed_intervals = intervals

        sub_clips = []
        for sub_idx, (t0, t1) in enumerate(trimmed_intervals):
            clip = get_clean_clip(t0, t1)
            sub_clips.append(clip)
            if sub_idx < len(trimmed_intervals) - 1 and internal_gap_samples > 0:
                sub_clips.append(np.zeros((internal_gap_samples, ch), dtype=np.int16))

        full_clip = np.concatenate(sub_clips, axis=0) if len(sub_clips) > 1 else sub_clips[0]
        dur = round(len(full_clip) / sr, 3)
        start_time = round(cur_time, 3)
        end_time = round(start_time + dur, 3)

        segments_meta.append({
            "id": idx,
            "intervals": trimmed_intervals,
            "start": start_time,
            "end": end_time,
            "dur": dur,
            "text": text,
            "gap_after": gap_after,
        })

        out_clips.append(full_clip)
        gap_samples = int(round(gap_after * sr))
        if gap_samples > 0:
            out_clips.append(np.zeros((gap_samples, ch), dtype=np.int16))
        cur_time = end_time + gap_after

    full_audio = np.concatenate(out_clips, axis=0)

    os.makedirs(os.path.dirname(os.path.abspath(out_wav)), exist_ok=True)
    with wave.open(out_wav, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(full_audio.tobytes())

    os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(segments_meta, f, ensure_ascii=False, indent=2)

    total_dur = round(len(full_audio) / sr, 3)
    return total_dur, segments_meta
