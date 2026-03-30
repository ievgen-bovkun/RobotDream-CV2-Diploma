from __future__ import annotations

from collections.abc import Iterator


def should_process_frame(frame_index: int, frame_sampling_interval: int) -> bool:
    if frame_sampling_interval < 1:
        raise ValueError("frame_sampling_interval must be at least 1")
    return frame_index % frame_sampling_interval == 0


def iter_sampled_frame_indices(frame_count: int, frame_sampling_interval: int) -> Iterator[int]:
    if frame_count < 0:
        raise ValueError("frame_count cannot be negative")
    if frame_sampling_interval < 1:
        raise ValueError("frame_sampling_interval must be at least 1")

    for frame_index in range(0, frame_count, frame_sampling_interval):
        yield frame_index
