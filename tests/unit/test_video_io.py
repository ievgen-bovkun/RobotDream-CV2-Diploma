from __future__ import annotations

from app.pipeline.video_io import (
    iter_sampled_frame_indices,
    should_process_frame,
    suggest_runtime_chunk_size,
    suggest_runtime_detection_interval,
)


def test_iter_sampled_frame_indices_respects_interval() -> None:
    indices = list(iter_sampled_frame_indices(frame_count=10, frame_sampling_interval=3))

    assert indices == [0, 3, 6, 9]


def test_should_process_frame_matches_interval_logic() -> None:
    assert should_process_frame(frame_index=12, frame_sampling_interval=3) is True
    assert should_process_frame(frame_index=13, frame_sampling_interval=3) is False


def test_suggest_runtime_detection_interval_scales_for_higher_fps() -> None:
    assert suggest_runtime_detection_interval(source_fps=30.0, requested_interval=3) == 3
    assert suggest_runtime_detection_interval(source_fps=60.0, requested_interval=3) == 6


def test_suggest_runtime_chunk_size_tracks_effective_interval() -> None:
    assert suggest_runtime_chunk_size(detection_interval=3) == 12
    assert suggest_runtime_chunk_size(detection_interval=6) == 24
