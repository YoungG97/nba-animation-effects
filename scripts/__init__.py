"""NBA Animation Effects (NBA 动画效果) package."""

from .audio_surgical_trimmer import slice_and_calibrate_audio, trim_interval_energy
from .render_flashback_carousel import render_flashback_carousel
from .jianying_project_builder import build_nba_jianying_project
from .render_intro import render_hero_intro
from .render_wordcloud import render_wordcloud_transition
from .render_keyword_posters import render_keyword_posters
from .render_major_chapter import render_major_chapter
from .render_profile_hud import render_profile_hud
from .render_era_transitions import render_career_era_calibrated
from .render_career_marquee import render_career_marquee
from .pipeline import run_pipeline
from .team_colors import get_team_colors, ALL_TEAMS

__all__ = [
    "slice_and_calibrate_audio",
    "trim_interval_energy",
    "render_flashback_carousel",
    "build_nba_jianying_project",
    "render_hero_intro",
    "render_wordcloud_transition",
    "render_keyword_posters",
    "render_major_chapter",
    "render_profile_hud",
    "render_career_era_calibrated",
    "render_career_marquee",
    "run_pipeline",
    "get_team_colors",
    "ALL_TEAMS",
]
