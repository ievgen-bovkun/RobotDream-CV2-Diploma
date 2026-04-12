from __future__ import annotations

from app.ui.state import _default_state


def test_default_state_includes_runtime_playback_defaults() -> None:
    default_state = _default_state()

    assert default_state["pending_full_reset"] is False
    assert default_state["is_processing_preview"] is False
    assert default_state["preview_frames"] == []
    assert default_state["playback_speed"] == 1.0
    assert default_state["auto_replay"] is False
    assert default_state["play_request_nonce"] == 0
    assert default_state["pause_request_nonce"] == 0
    assert default_state["player_session_nonce"] == 0
    assert default_state["uploader_nonce"] == 0
    assert default_state["current_video_name"] is None
    assert default_state["current_video_type"] is None
    assert default_state["current_video_size"] is None
    assert default_state["current_video_bytes"] is None
    assert default_state["current_video_path"] is None
    assert default_state["current_video_metadata"] is None
    assert default_state["processing_config_dict"] is None
    assert default_state["processing_cursor_frame"] == 0
    assert default_state["processing_effective_interval"] == 0
    assert default_state["processing_chunk_size"] == 0
    assert default_state["processing_target"] is None
    assert default_state["processing_missed_detection_refreshes"] == 0
    assert default_state["processing_playback_started"] is False
