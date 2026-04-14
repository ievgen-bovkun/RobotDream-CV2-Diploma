from __future__ import annotations

from typing import Any

import streamlit as st

from app.domain.models import VideoMetadata
from app.pipeline.video_io import cleanup_persisted_video, persist_video_bytes


def _default_state() -> dict[str, object]:
    return {
        "pending_full_reset": False,
        "is_processing_preview": False,
        "preview_frames": [],
        "auto_replay": False,
        "play_request_nonce": 0,
        "pause_request_nonce": 0,
        "player_session_nonce": 0,
        "uploader_nonce": 0,
        "guidance_armed": False,
        "guidance_arm_nonce": 0,
        "current_video_name": None,
        "current_video_type": None,
        "current_video_size": None,
        "current_video_bytes": None,
        "current_video_path": None,
        "current_video_metadata": None,
        "processing_config_dict": None,
        "processing_cursor_frame": 0,
        "processing_effective_interval": 0,
        "processing_chunk_size": 0,
        "processing_target": None,
        "processing_missed_detection_refreshes": 0,
        "processing_playback_started": False,
    }


def initialize_session_state() -> None:
    for key, value in _default_state().items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state() -> None:
    next_uploader_nonce = int(st.session_state.get("uploader_nonce", 0)) + 1
    cleanup_persisted_video(st.session_state.get("current_video_path"))
    for key, value in _default_state().items():
        st.session_state[key] = value
    st.session_state.uploader_nonce = next_uploader_nonce


def request_full_reset() -> None:
    st.session_state.pending_full_reset = True


def get_uploader_key(prefix: str = "runtime_upload") -> str:
    uploader_nonce = int(st.session_state.get("uploader_nonce", 0))
    return f"{prefix}_{uploader_nonce}"


def get_current_video() -> dict[str, Any] | None:
    video_bytes = st.session_state.get("current_video_bytes")
    if video_bytes is None:
        return None
    return {
        "name": st.session_state.get("current_video_name"),
        "type": st.session_state.get("current_video_type"),
        "size": st.session_state.get("current_video_size"),
        "bytes": video_bytes,
        "path": st.session_state.get("current_video_path"),
    }


def get_current_video_metadata() -> VideoMetadata | None:
    metadata = st.session_state.get("current_video_metadata")
    if isinstance(metadata, VideoMetadata):
        return metadata
    return None


def store_uploaded_video(
    *,
    name: str,
    mime_type: str,
    size: int,
    video_bytes: bytes,
    metadata: VideoMetadata,
) -> None:
    cleanup_persisted_video(st.session_state.get("current_video_path"))
    persisted_video_path = persist_video_bytes(
        video_bytes=video_bytes,
        filename=name,
        mime_type=mime_type,
    )
    st.session_state.current_video_name = name
    st.session_state.current_video_type = mime_type
    st.session_state.current_video_size = size
    st.session_state.current_video_bytes = video_bytes
    st.session_state.current_video_path = persisted_video_path
    st.session_state.current_video_metadata = metadata
    st.session_state.preview_frames = []
    st.session_state.auto_replay = False
    st.session_state.play_request_nonce = 0
    st.session_state.pause_request_nonce = 0
    st.session_state.player_session_nonce = 0
    st.session_state.guidance_armed = False
    st.session_state.guidance_arm_nonce = 0
    st.session_state.is_processing_preview = False
    st.session_state.processing_config_dict = None
    st.session_state.processing_cursor_frame = 0
    st.session_state.processing_effective_interval = 0
    st.session_state.processing_chunk_size = 0
    st.session_state.processing_target = None
    st.session_state.processing_missed_detection_refreshes = 0
    st.session_state.processing_playback_started = False


def clear_current_video() -> None:
    cleanup_persisted_video(st.session_state.get("current_video_path"))
    st.session_state.current_video_name = None
    st.session_state.current_video_type = None
    st.session_state.current_video_size = None
    st.session_state.current_video_bytes = None
    st.session_state.current_video_path = None
    st.session_state.current_video_metadata = None
    st.session_state.preview_frames = []
    st.session_state.auto_replay = False
    st.session_state.play_request_nonce = 0
    st.session_state.pause_request_nonce = 0
    st.session_state.player_session_nonce = 0
    st.session_state.guidance_armed = False
    st.session_state.guidance_arm_nonce = 0
    st.session_state.is_processing_preview = False
    st.session_state.processing_config_dict = None
    st.session_state.processing_cursor_frame = 0
    st.session_state.processing_effective_interval = 0
    st.session_state.processing_chunk_size = 0
    st.session_state.processing_target = None
    st.session_state.processing_missed_detection_refreshes = 0
    st.session_state.processing_playback_started = False
    st.session_state.uploader_nonce = int(st.session_state.get("uploader_nonce", 0)) + 1


def request_video_playback() -> None:
    st.session_state.play_request_nonce = int(st.session_state.get("play_request_nonce", 0)) + 1


def request_video_pause() -> None:
    st.session_state.pause_request_nonce = int(st.session_state.get("pause_request_nonce", 0)) + 1


def toggle_guidance_armed() -> None:
    next_state = not bool(st.session_state.get("guidance_armed", False))
    st.session_state.guidance_armed = next_state
    st.session_state.guidance_arm_nonce = int(st.session_state.get("guidance_arm_nonce", 0)) + 1


def begin_preview_processing() -> None:
    st.session_state.is_processing_preview = True
    st.session_state.player_session_nonce = int(st.session_state.get("player_session_nonce", 0)) + 1


def finish_preview_processing() -> None:
    st.session_state.is_processing_preview = False
