from __future__ import annotations

from app.pipeline.video_io import iter_sampled_frame_indices, should_process_frame


def test_iter_sampled_frame_indices_respects_interval() -> None:
    indices = list(iter_sampled_frame_indices(frame_count=10, frame_sampling_interval=3))

    assert indices == [0, 3, 6, 9]


def test_should_process_frame_matches_interval_logic() -> None:
    assert should_process_frame(frame_index=12, frame_sampling_interval=3) is True
    assert should_process_frame(frame_index=13, frame_sampling_interval=3) is False
