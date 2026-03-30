from __future__ import annotations

import pytest

from app.domain.config import ProcessingConfig


def test_processing_config_defaults_are_valid() -> None:
    config = ProcessingConfig()
    config.validate()


def test_processing_config_rejects_invalid_threshold() -> None:
    config = ProcessingConfig(detection_threshold=1.2)

    with pytest.raises(ValueError):
        config.validate()
