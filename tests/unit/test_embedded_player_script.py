from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from app.ui.views import build_custom_video_player_html


def test_embedded_player_script_has_valid_javascript_syntax() -> None:
    player_html = build_custom_video_player_html(
        video_bytes=b"demo-video",
        mime_type="video/mp4",
        auto_replay=False,
        play_request_nonce=1,
        pause_request_nonce=0,
        guidance_armed=False,
        guidance_arm_nonce=0,
        player_storage_key="syntax-check",
        preview_frames=[],
    )

    script_blocks = re.findall(r"<script>(.*?)</script>", player_html, flags=re.DOTALL)
    assert script_blocks, "Expected at least one embedded script block in the runtime player HTML."

    script_source = "\n\n".join(script_blocks)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as temp_file:
        temp_file.write(script_source)
        temp_path = Path(temp_file.name)

    try:
        result = subprocess.run(
            ["node", "--check", str(temp_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    assert result.returncode == 0, result.stderr or result.stdout
