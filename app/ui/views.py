from __future__ import annotations

import base64
import hashlib
import html
import json
from dataclasses import asdict
from typing import Any

import streamlit as st
from streamlit.components.v1 import html as html_component

from app.domain.config import ProcessingConfig
from app.domain.models import VideoMetadata
from app.pipeline.orchestrator import FramePreview
from app.ui.controls import UiActions
from app.ui.state import (
    get_current_video,
    get_uploader_key,
    request_full_reset,
    request_video_pause,
    request_video_playback,
    toggle_guidance_armed,
)


PLAYER_HEIGHT_PX = 420
RUNTIME_SIDE_PANEL_HEIGHT_PX = 560
PIPELINE_PREVIEW_MAX_CARDS = 24


def render_runtime_styles() -> None:
    st.markdown(
        f"""
        <style>
        [data-testid="stFileUploaderDropzone"] {{
            min-height: {PLAYER_HEIGHT_PX}px;
            border: 2px dashed rgba(59, 130, 246, 0.45);
            border-radius: 1rem;
            background:
                radial-gradient(circle at top left, rgba(96, 165, 250, 0.18), transparent 45%),
                linear-gradient(135deg, rgba(15, 23, 42, 0.02), rgba(59, 130, 246, 0.04));
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.25rem;
        }}
        [data-testid="stFileUploaderDropzone"] section {{
            padding: 0;
        }}
        [data-testid="stFileUploaderDropzoneInstructions"] > div {{
            text-align: center;
            gap: 0.5rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.title("Drone Detection, Approval, Tracking, and Guidance Demo")
    st.caption(
        "Operator runtime layout for the diploma MVP: video, detection log, processing controls, and preview details arranged for step-by-step validation."
    )


def _format_file_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "n/a"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024**2):.2f} MB"


def build_detection_log_entries(
    uploaded_video_name: str | None,
    uploaded_video_size: int | None,
    preview_frames: list[FramePreview],
    auto_replay: bool,
    is_processing_preview: bool = False,
    processing_cursor_frame: int | None = None,
    processing_total_frames: int | None = None,
    effective_interval: int | None = None,
) -> list[tuple[str, str]]:
    if uploaded_video_name is None:
        runtime_status = "Awaiting uploaded video"
        video_label = "No video loaded yet"
    elif is_processing_preview:
        runtime_status = "Preprocessing uploaded video"
        video_label = f"{uploaded_video_name} ({_format_file_size(uploaded_video_size)})"
    elif preview_frames:
        runtime_status = "Preview processed and ready for review"
        video_label = f"{uploaded_video_name} ({_format_file_size(uploaded_video_size)})"
    else:
        runtime_status = "Video loaded and ready to process"
        video_label = f"{uploaded_video_name} ({_format_file_size(uploaded_video_size)})"

    entries = [
        ("Runtime Status", runtime_status),
        ("Loaded Video", video_label),
        ("Auto Replay", "Enabled" if auto_replay else "Disabled"),
    ]

    if uploaded_video_name is not None and effective_interval:
        entries.append(("Detection Interval", f"every {effective_interval} frames"))

    if (
        uploaded_video_name is not None
        and processing_total_frames is not None
        and processing_total_frames > 0
        and (is_processing_preview or processing_cursor_frame)
    ):
        safe_cursor = min(max(int(processing_cursor_frame or 0), 0), processing_total_frames)
        entries.append(
            (
                "Processing Progress",
                f"{safe_cursor}/{processing_total_frames} frames ({(safe_cursor / processing_total_frames) * 100:.0f}%)",
            )
        )

    if preview_frames:
        latest_preview = preview_frames[-1]
        latest_status = latest_preview.tracking.tracking_status if latest_preview.tracking is not None else "waiting"
        entries.extend(
            [
                ("Processed Frames", str(len(preview_frames))),
                ("Latest Frame", str(latest_preview.frame_index)),
                ("Latest Detections", str(len(latest_preview.detections))),
                ("Tracking State", latest_status),
            ]
        )

    return entries


def build_runtime_overlay_payload(preview_frames: list[FramePreview]) -> list[dict[str, Any]]:
    overlay_payload: list[dict[str, Any]] = []

    for preview in preview_frames:
        bbox = None
        confidence: float | None = None
        source = "none"

        if preview.tracking is not None and preview.tracking.bbox is not None:
            bbox = preview.tracking.bbox
            confidence = preview.tracking.confidence
            source = "tracking"
        elif preview.detections:
            best_detection = max(preview.detections, key=lambda detection: detection.confidence)
            bbox = best_detection.bbox
            confidence = best_detection.confidence
            source = "detection"

        if bbox is None:
            continue

        overlay_payload.append(
            {
                "timestamp_seconds": preview.timestamp_seconds,
                "frame_index": preview.frame_index,
                "target_label": (
                    preview.guidance.target_profile_label
                    if preview.guidance is not None and preview.guidance.target_profile_label is not None
                    else "Shahed-136"
                ),
                "x_min": bbox.x_min,
                "y_min": bbox.y_min,
                "x_max": bbox.x_max,
                "y_max": bbox.y_max,
                "confidence": confidence,
                "source": source,
                "tracking_status": preview.tracking.tracking_status if preview.tracking is not None else None,
                "guidance": (
                    {
                        "frame_center_x": preview.guidance.frame_center.x,
                        "frame_center_y": preview.guidance.frame_center.y,
                        "aim_point_x": preview.guidance.aim_point.x,
                        "aim_point_y": preview.guidance.aim_point.y,
                        "target_center_x": preview.guidance.target_center.x,
                        "target_center_y": preview.guidance.target_center.y,
                        "target_profile_label": preview.guidance.target_profile_label,
                        "estimated_range_m": preview.guidance.estimated_range_m,
                        "range_estimation_method": preview.guidance.range_estimation_method,
                        "dx_pixels": preview.guidance.dx_pixels,
                        "dy_pixels": preview.guidance.dy_pixels,
                        "yaw_offset_deg": preview.guidance.yaw_offset_deg_approx,
                        "pitch_offset_deg": preview.guidance.pitch_offset_deg_approx,
                    }
                    if preview.guidance is not None
                    else None
                ),
                "guidance_command": (
                    {
                        "yaw_command_norm": preview.guidance_command.yaw_command_norm,
                        "pitch_command_norm": preview.guidance_command.pitch_command_norm,
                        "yaw_direction": preview.guidance_command.yaw_direction,
                        "pitch_direction": preview.guidance_command.pitch_direction,
                        "magnitude_norm": preview.guidance_command.magnitude_norm,
                        "is_centered": preview.guidance_command.is_centered,
                        "range_gain": preview.guidance_command.range_gain,
                        "auto_engagement_triggered": preview.guidance_command.auto_engagement_triggered,
                        "engagement_distance_threshold_m": preview.guidance_command.engagement_distance_threshold_m,
                    }
                    if preview.guidance_command is not None
                    else None
                ),
            }
        )

    return overlay_payload


def select_pipeline_preview_frames(preview_frames: list[FramePreview]) -> tuple[list[FramePreview], str]:
    informative_previews = [
        preview
        for preview in preview_frames
        if (preview.tracking is not None and preview.tracking.bbox is not None) or preview.detections
    ]
    source_previews = informative_previews or preview_frames
    visible_previews = list(reversed(source_previews[-PIPELINE_PREVIEW_MAX_CARDS:]))
    label = "latest informative frames" if informative_previews else "latest processed frames"
    return visible_previews, label


def build_processing_summary_entries(preview_frames: list[FramePreview]) -> list[tuple[str, str]]:
    if not preview_frames:
        return []

    detection_frames = [preview.frame_index for preview in preview_frames if preview.detections]
    tracking_frames = [
        preview.frame_index
        for preview in preview_frames
        if preview.tracking is not None and preview.tracking.bbox is not None
    ]

    entries = [
        ("Detection Frames", str(len(detection_frames))),
        ("Tracking Frames", str(len(tracking_frames))),
    ]
    if detection_frames:
        entries.append(("First Detection", str(detection_frames[0])))
        entries.append(("Last Detection", str(detection_frames[-1])))
    if tracking_frames:
        entries.append(("First Tracking", str(tracking_frames[0])))
        entries.append(("Last Tracking", str(tracking_frames[-1])))
    return entries


def _preview_frame_html(preview: FramePreview, is_latest: bool) -> str:
    tracking_status = preview.tracking.tracking_status if preview.tracking is not None else "waiting"
    summary_bits = [
        f"t={preview.timestamp_seconds:.2f}s",
        f"frame={preview.frame_index}",
        f"detections={len(preview.detections)}",
        f"tracking={tracking_status}",
    ]
    if preview.guidance is not None:
        summary_bits.append(
            f"yaw={preview.guidance.yaw_offset_deg_approx:.2f}deg pitch={preview.guidance.pitch_offset_deg_approx:.2f}deg"
        )

    events_html = "".join(
        f"<li><strong>{html.escape(event.stage)}</strong>: {html.escape(event.message)}</li>"
        for event in preview.events
    ) or "<li>No events recorded.</li>"

    if preview.overlay_lines:
        overlay_html = "".join(
            f"<li><code>{html.escape(line)}</code></li>"
            for line in preview.overlay_lines
        )
    else:
        overlay_html = "<li>No overlay text.</li>"

    badge = (
        "<span style='display:inline-block;padding:0.18rem 0.55rem;border-radius:999px;background:#2563eb;color:#fff;font-size:0.72rem;font-weight:700;'>LATEST</span>"
        if is_latest
        else ""
    )

    return f"""
    <article class="pipeline-card" data-timestamp="{preview.timestamp_seconds:.6f}" style="padding:0.9rem 1rem;border-radius:0.9rem;border:1px solid rgba(148,163,184,0.22);background:{'#eff6ff' if is_latest else '#ffffff'};">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:0.75rem;margin-bottom:0.55rem;">
        <strong style="font-size:0.98rem;">Frame {preview.frame_index}</strong>
        {badge}
      </div>
      <div style="font-size:0.82rem;color:#334155;margin-bottom:0.65rem;">{html.escape(' | '.join(summary_bits))}</div>
      <div style="font-size:0.84rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;">Events</div>
      <ul style="margin:0 0 0.75rem 1rem;padding:0;color:#0f172a;font-size:0.83rem;">{events_html}</ul>
      <div style="font-size:0.84rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;">Overlay</div>
      <ul style="margin:0 0 0 1rem;padding:0;color:#0f172a;font-size:0.8rem;">{overlay_html}</ul>
    </article>
    """


def render_pipeline_preview_panel(
    preview_frames: list[FramePreview],
    player_storage_key: str | None,
    is_processing_preview: bool,
) -> None:
    st.markdown("#### Pipeline Preview")

    if not preview_frames:
        if is_processing_preview:
            st.info("Building preview frames from the uploaded video. The preview cards will appear here after this pass finishes.")
            return
        st.info("Pipeline preview will appear here and auto-follow the latest processed state.")
        return

    visible_previews, preview_label = select_pipeline_preview_frames(preview_frames)
    latest_frame_index = preview_frames[-1].frame_index
    cards_html = "".join(
        _preview_frame_html(preview, is_latest=preview.frame_index == latest_frame_index)
        for preview in visible_previews
    )
    preview_sync_key = (
        f"operator-runtime-video::{hashlib.sha1(player_storage_key.encode('utf-8')).hexdigest()}"
        if player_storage_key is not None
        else None
    )

    preview_html = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;gap:0.75rem;margin:0 0 0.55rem 0;">
      <div style="font-size:0.78rem;color:#475569;">
        Showing {preview_label}: {min(len(visible_previews), PIPELINE_PREVIEW_MAX_CARDS)}
      </div>
      <div style="font-size:0.78rem;color:#475569;">
        Newest first
      </div>
    </div>
    <div id="pipeline-preview-scrollbox" style="height:{RUNTIME_SIDE_PANEL_HEIGHT_PX - 56}px;overflow-y:auto;padding-right:0.35rem;">
      <div style="display:flex;flex-direction:column;gap:0.8rem;">
        {cards_html}
      </div>
    </div>
    <script>
      const rootWindow = (() => {{
        try {{
          return window.parent || window;
        }} catch (error) {{
          return window;
        }}
      }})();
      const runtimeStateBucketKey = "__operatorRuntimeSync";
      const previewBox = document.getElementById("pipeline-preview-scrollbox");
      const previewCards = Array.from(previewBox?.querySelectorAll(".pipeline-card") ?? []);
      const syncStorageKey = {json.dumps(preview_sync_key)};
      const currentTimeKey = syncStorageKey;

      const getRuntimeState = () => {{
        const bucket = rootWindow[runtimeStateBucketKey] ?? {{}};
        return currentTimeKey ? (bucket[currentTimeKey] ?? {{}}) : {{}};
      }};

      const updatePreviewState = () => {{
        if (!previewCards.length) {{
          return;
        }}

        const runtimeState = getRuntimeState();
        let currentTime = currentTimeKey ? Number(runtimeState.currentTime ?? "0") : Number.MAX_SAFE_INTEGER;
        if (Number.isNaN(currentTime)) {{
          currentTime = 0;
        }}

        let activeCard = previewCards[0];
        for (const card of previewCards) {{
          const timestamp = Number(card.dataset.timestamp ?? "0");
          if (!Number.isNaN(timestamp) && timestamp <= currentTime + 0.05) {{
            activeCard = card;
          }}
        }}

        for (const card of previewCards) {{
          const isActive = card === activeCard;
          card.style.background = isActive ? "#dbeafe" : "#ffffff";
          card.style.borderColor = isActive ? "rgba(37, 99, 235, 0.45)" : "rgba(148,163,184,0.22)";
        }}
      }};

      updatePreviewState();
      window.setInterval(updatePreviewState, 300);
    </script>
    """
    html_component(preview_html, height=RUNTIME_SIDE_PANEL_HEIGHT_PX)


def render_runtime_counters_panel(
    *,
    player_storage_key: str | None,
    metadata: VideoMetadata | None,
    preview_ready: bool,
) -> None:
    if player_storage_key is None or metadata is None or metadata.fps <= 0:
        st.caption("Video frame and pipeline frame counters will appear here during runtime.")
        return

    sync_storage_key = f"operator-runtime-video::{hashlib.sha1(player_storage_key.encode('utf-8')).hexdigest()}"
    counters_html = f"""
    <div style="padding:0.85rem 0.95rem;border-radius:0.9rem;border:1px solid rgba(148,163,184,0.22);background:#f8fafc;">
      <div style="font-size:0.85rem;font-weight:700;color:#0f172a;margin-bottom:0.55rem;">Runtime Counters</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.65rem;">
        <div style="padding:0.65rem 0.75rem;border-radius:0.75rem;background:#ffffff;border:1px solid rgba(148,163,184,0.18);">
          <div style="font-size:0.78rem;color:#475569;margin-bottom:0.2rem;">Video Frame</div>
          <div id="video-frame-counter" style="font-size:1.1rem;font-weight:800;color:#0f172a;">0</div>
        </div>
        <div style="padding:0.65rem 0.75rem;border-radius:0.75rem;background:#ffffff;border:1px solid rgba(148,163,184,0.18);">
          <div style="font-size:0.78rem;color:#475569;margin-bottom:0.2rem;">Pipeline Frame</div>
          <div id="pipeline-frame-counter" style="font-size:1.1rem;font-weight:800;color:#0f172a;">0</div>
        </div>
      </div>
    </div>
    <script>
      const rootWindow = (() => {{
        try {{
          return window.parent || window;
        }} catch (error) {{
          return window;
        }}
      }})();
      const runtimeStateBucketKey = "__operatorRuntimeSync";
      const syncStorageKey = {json.dumps(sync_storage_key)};
      const fps = {json.dumps(metadata.fps)};
      const previewReady = {json.dumps(preview_ready)};
      const videoCounter = document.getElementById("video-frame-counter");
      const pipelineCounter = document.getElementById("pipeline-frame-counter");

      const updateCounters = () => {{
        const bucket = rootWindow[runtimeStateBucketKey] ?? {{}};
        const runtimeState = bucket[syncStorageKey] ?? {{}};
        const rawTime = Number(runtimeState.currentTime ?? "0");
        const currentTime = Number.isNaN(rawTime) ? 0 : rawTime;
        const currentFrame = Math.max(0, Math.floor(currentTime * fps));
        if (videoCounter) {{
          videoCounter.textContent = String(currentFrame);
        }}
        if (pipelineCounter) {{
          pipelineCounter.textContent = previewReady ? String(currentFrame) : "0";
        }}
      }};

      updateCounters();
      window.setInterval(updateCounters, 200);
    </script>
    """
    html_component(counters_html, height=118)


def render_operator_runtime_block(
    preview_frames: list[FramePreview],
    metadata: VideoMetadata | None,
    is_processing_preview: bool,
    processing_cursor_frame: int | None,
    processing_total_frames: int | None,
    effective_interval: int | None,
) -> tuple[Any | None, UiActions]:
    current_video = get_current_video()

    with st.container(border=True):
        st.subheader("Operator Runtime Block")
        video_col, preview_col, log_col = st.columns([2, 1, 1], gap="large")

        with video_col:
            pending_upload = None
            start_processing = False
            tactical_pause = False
            reset_state = False
            toggle_guidance = False
            player_storage_key: str | None = None

            if current_video is None:
                pending_upload = st.file_uploader(
                    "Upload prerecorded drone video",
                    type=["mp4", "mov", "avi"],
                    key=get_uploader_key(),
                    help="Load a prerecorded clip into the operator runtime area.",
                    label_visibility="collapsed",
                )
                st.caption("Upload a prerecorded video to initialize the runtime player.")
                action_col, pause_col, guidance_col, reset_col = st.columns(4)
                start_processing = action_col.button(
                    "Processing..." if is_processing_preview else "Start Tracking",
                    type="primary",
                    use_container_width=True,
                    disabled=True,
                    on_click=request_video_playback,
                )
                tactical_pause = pause_col.button(
                    "Tactical Pause",
                    use_container_width=True,
                    disabled=True,
                    on_click=request_video_pause,
                )
                toggle_guidance = guidance_col.button(
                    "Arm Guidance",
                    use_container_width=True,
                    disabled=True,
                    on_click=toggle_guidance_armed,
                )
                reset_state = reset_col.button(
                    "Reset State",
                    use_container_width=True,
                    on_click=request_full_reset,
                )
            else:
                player_storage_key = (
                    f"{current_video['name']}:{current_video['size']}:{st.session_state.uploader_nonce}:{st.session_state.player_session_nonce}"
                )
                st.caption("Play and pause from the built-in video controls.")
                if is_processing_preview:
                    st.info("Processing uploaded video. Tracking playback will unlock when preprocessing completes.")
                render_custom_video_player(
                    video_bytes=current_video["bytes"],
                    mime_type=current_video["type"],
                    auto_replay=bool(st.session_state.auto_replay),
                    play_request_nonce=int(st.session_state.play_request_nonce),
                    pause_request_nonce=int(st.session_state.pause_request_nonce),
                    guidance_armed=bool(st.session_state.get("guidance_armed", False)),
                    guidance_arm_nonce=int(st.session_state.get("guidance_arm_nonce", 0)),
                    player_storage_key=player_storage_key,
                    preview_frames=preview_frames,
                )
                autoplay_col = st.columns([1, 5])[0]
                autoplay_col.toggle(
                    "Auto Replay",
                    key="auto_replay",
                    help="Replay automatically when the uploaded video reaches the end.",
                )
                action_col, pause_col, guidance_col, reset_col = st.columns(4)
                preview_ready = bool(preview_frames) and not is_processing_preview
                start_processing = action_col.button(
                    "Processing..." if is_processing_preview else "Start Tracking",
                    type="primary",
                    use_container_width=True,
                    disabled=not preview_ready,
                    on_click=request_video_playback,
                )
                tactical_pause = pause_col.button(
                    "Tactical Pause",
                    use_container_width=True,
                    disabled=is_processing_preview,
                    on_click=request_video_pause,
                )
                toggle_guidance = guidance_col.button(
                    "Disarm Guidance" if bool(st.session_state.get("guidance_armed", False)) else "Arm Guidance",
                    use_container_width=True,
                    disabled=not preview_ready,
                    type="secondary",
                    on_click=toggle_guidance_armed,
                )
                reset_state = reset_col.button(
                    "Reset State",
                    use_container_width=True,
                    disabled=is_processing_preview,
                    on_click=request_full_reset,
                )

        with preview_col:
            with st.container(border=True, height=RUNTIME_SIDE_PANEL_HEIGHT_PX):
                render_pipeline_preview_panel(
                    preview_frames,
                    player_storage_key=player_storage_key,
                    is_processing_preview=is_processing_preview,
                )

        with log_col:
            with st.container(border=True, height=RUNTIME_SIDE_PANEL_HEIGHT_PX):
                st.markdown("#### Detection Log")
                render_runtime_counters_panel(
                    player_storage_key=player_storage_key,
                    metadata=metadata,
                    preview_ready=bool(preview_frames),
                )
                st.divider()
                detection_log_entries = build_detection_log_entries(
                    uploaded_video_name=current_video["name"] if current_video is not None else None,
                    uploaded_video_size=current_video["size"] if current_video is not None else None,
                    preview_frames=preview_frames,
                    auto_replay=bool(st.session_state.auto_replay),
                    is_processing_preview=is_processing_preview,
                    processing_cursor_frame=processing_cursor_frame,
                    processing_total_frames=processing_total_frames,
                    effective_interval=effective_interval,
                )
                for label, value in detection_log_entries:
                    st.markdown(f"**{label}:** {value}")
                st.markdown(
                    f"**Guidance:** {'Armed' if bool(st.session_state.get('guidance_armed', False)) else 'Standby'}"
                )
                for label, value in build_processing_summary_entries(preview_frames):
                    st.markdown(f"**{label}:** {value}")

                if preview_frames:
                    latest_preview = preview_frames[-1]
                    st.divider()
                    st.markdown("**Latest Processing Events**")
                    for event in latest_preview.events[-3:]:
                        st.write(f"- [{event.stage}] {event.message}")
                elif is_processing_preview:
                    st.info("Preprocessing is running. Results will appear here when ready.")
                else:
                    st.info("Upload a video to start preprocessing automatically.")

    return pending_upload, UiActions(
        start_processing=start_processing,
        reset_state=reset_state,
        tactical_pause=tactical_pause,
        toggle_guidance=toggle_guidance,
    )


def render_other_details(config: ProcessingConfig, metadata: VideoMetadata) -> None:
    with st.expander("Other Details", expanded=False):
        st.markdown("#### Current Scope")
        st.write(
            {
                "milestone": "Milestone 2",
                "status": "Runtime UI, uploaded-video workflow, and first detector benchmark are in progress",
                "next_steps": [
                    "Benchmark daytime and thermal profiles separately",
                    "Tune detector refresh and tracking handoff for close-up shots",
                    "Promote the best detector backend into the next video milestone",
                ],
            }
        )

        st.markdown("#### Placeholder Metadata")
        st.write(asdict(metadata))

        st.markdown("#### Active Config")
        st.write(config.to_dict())

        st.info(
            "The runtime now uses a real detector path with a lightweight tracking bridge between refresh frames. Close-up scaling and thermal tuning are still backlog items."
        )


def build_custom_video_player_html(
    video_bytes: bytes,
    mime_type: str,
    auto_replay: bool,
    play_request_nonce: int,
    pause_request_nonce: int,
    guidance_armed: bool,
    guidance_arm_nonce: int,
    player_storage_key: str,
    preview_frames: list[FramePreview],
) -> None:
    encoded_video = base64.b64encode(video_bytes).decode("utf-8")
    sanitized_storage_key = hashlib.sha1(player_storage_key.encode("utf-8")).hexdigest()
    video_source = f"data:{mime_type};base64,{encoded_video}"
    overlay_payload = build_runtime_overlay_payload(preview_frames)
    return f"""
    <div style="display:flex;flex-direction:column;gap:0.7rem;">
      <div style="position:relative;border-radius: 1rem; overflow: hidden; background: #020617; border: 1px solid rgba(148, 163, 184, 0.28);">
        <video
          id="operator-runtime-video"
          controls
          muted
          playsinline
          style="display:block;width:100%;height:{PLAYER_HEIGHT_PX}px;background:#020617;object-fit:contain;"
        >
          <source src="{html.escape(video_source)}" type="{html.escape(mime_type)}">
        </video>
        <div id="operator-runtime-overlay-layer" style="position:absolute;inset:0;pointer-events:none;"></div>
      </div>
      <div id="guidance-emulator-panel" style="padding:0.8rem 0.95rem;border-radius:0.95rem;background:#0f172a;border:1px solid rgba(148,163,184,0.24);color:#e2e8f0;">
        <div style="font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;color:#93c5fd;margin-bottom:0.45rem;">Guidance Emulator</div>
        <div id="guidance-emulator-content" style="font-size:0.88rem;color:#cbd5e1;">Standby. Arm guidance to visualize correction signals.</div>
      </div>
    </div>
    <script>
      const rootWindow = (() => {{
        try {{
          return window.parent || window;
        }} catch (error) {{
          return window;
        }}
      }})();
      const runtimeStateBucketKey = "__operatorRuntimeSync";
      const video = document.getElementById("operator-runtime-video");
      const storageKey = {json.dumps(f"operator-runtime-video::{sanitized_storage_key}")};
      const autoReplay = {json.dumps(auto_replay)};
      const playRequestNonce = {json.dumps(play_request_nonce)};
      const pauseRequestNonce = {json.dumps(pause_request_nonce)};
      const guidanceArmed = {json.dumps(guidance_armed)};
      const guidanceArmNonce = {json.dumps(guidance_arm_nonce)};
      const overlayFrames = {json.dumps(overlay_payload)};
      const overlayLayer = document.getElementById("operator-runtime-overlay-layer");
      const guidancePanel = document.getElementById("guidance-emulator-content");

      const ensureRuntimeState = () => {{
        if (!rootWindow[runtimeStateBucketKey]) {{
          rootWindow[runtimeStateBucketKey] = {{}};
        }}
        if (!rootWindow[runtimeStateBucketKey][storageKey]) {{
          rootWindow[runtimeStateBucketKey][storageKey] = {{
            currentTime: 0,
            lastPlayRequest: 0,
            lastPauseRequest: 0,
            lastGuidanceArmNonce: 0,
            guidancePulseUntil: 0,
            playing: false,
          }};
        }}
        return rootWindow[runtimeStateBucketKey][storageKey];
      }};

      const updateRuntimeState = (patch) => {{
        const currentState = ensureRuntimeState();
        Object.assign(currentState, patch);
        return currentState;
      }};

      const restoreState = () => {{
        const savedState = ensureRuntimeState();
        const parsedTime = Number(savedState.currentTime ?? 0);
        if (!Number.isNaN(parsedTime) && parsedTime > 0) {{
          const maxTime = Number(video.duration || parsedTime);
          video.currentTime = Math.min(parsedTime, Math.max(0, maxTime - 0.05));
        }}
        video.muted = true;
        video.playbackRate = 1.0;
        video.loop = autoReplay;
      }};

      const tryPlay = () => {{
        video.muted = true;
        video.playbackRate = 1.0;
        const playPromise = video.play();
        if (playPromise && typeof playPromise.catch === "function") {{
          playPromise.catch(() => null);
        }}
      }};

      const retryPlayIfRequested = () => {{
        const currentState = ensureRuntimeState();
        if (currentState.playing && video.paused) {{
          tryPlay();
          window.setTimeout(tryPlay, 180);
        }}
      }};

      const applyPlayRequest = () => {{
        const currentState = ensureRuntimeState();
        const lastPlayRequest = Number(currentState.lastPlayRequest ?? "0");
        if (playRequestNonce > lastPlayRequest) {{
          video.currentTime = 0;
          updateRuntimeState({{
            lastPlayRequest: playRequestNonce,
            playing: true,
            currentTime: 0,
          }});
          tryPlay();
          window.setTimeout(tryPlay, 140);
          window.setTimeout(tryPlay, 320);
        }}
      }};

      const applyPauseRequest = () => {{
        const currentState = ensureRuntimeState();
        const lastPauseRequest = Number(currentState.lastPauseRequest ?? "0");
        if (pauseRequestNonce > lastPauseRequest) {{
          updateRuntimeState({{
            lastPauseRequest: pauseRequestNonce,
            playing: false,
            currentTime: Number(video.currentTime ?? 0),
          }});
          video.pause();
        }}
      }};

      const applyGuidanceState = () => {{
        const currentState = ensureRuntimeState();
        const lastGuidanceArmNonce = Number(currentState.lastGuidanceArmNonce ?? "0");
        if (guidanceArmNonce > lastGuidanceArmNonce) {{
          updateRuntimeState({{
            lastGuidanceArmNonce: guidanceArmNonce,
            guidancePulseUntil: Date.now() + 1400,
          }});
        }}
      }};

      const renderSignedBar = (value, activeColor) => {{
        const normalized = Math.max(-1, Math.min(1, Number(value) || 0));
        const widthPercent = Math.abs(normalized) * 50;
        const align = normalized >= 0 ? "right" : "left";
        const fillStyle = align === "right"
          ? `left:50%;width:${{widthPercent}}%;`
          : `left:${{50 - widthPercent}}%;width:${{widthPercent}}%;`;
        return `
          <div style="position:relative;height:8px;border-radius:999px;background:rgba(148,163,184,0.18);overflow:hidden;">
            <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,0.38);"></div>
            <div style="position:absolute;top:0;bottom:0;${{fillStyle}}background:${{activeColor}};border-radius:999px;"></div>
          </div>
        `;
      }};

        const updateGuidancePanel = (activeOverlay) => {{
        if (!guidancePanel) {{
          return;
        }}
        if (!guidanceArmed) {{
          guidancePanel.innerHTML = "Standby. Arm guidance to visualize correction signals.";
          return;
        }}
        if (!activeOverlay || !activeOverlay.guidance || !activeOverlay.guidance_command) {{
          guidancePanel.innerHTML = "Guidance armed. Waiting for a tracked target with correction data.";
          return;
        }}

        const command = activeOverlay.guidance_command;
        const autoNeutralized = Boolean(command.auto_engagement_triggered);
        const yawPercent = Math.round(Math.abs(Number(command.yaw_command_norm || 0)) * 100);
        const pitchPercent = Math.round(Math.abs(Number(command.pitch_command_norm || 0)) * 100);
        const statusLabel = autoNeutralized
          ? "Neutralized"
          : (command.is_centered ? "Centered" : "Correcting");
        const estimatedRange = activeOverlay.guidance.estimated_range_m;
        const rangeLine = estimatedRange === null || estimatedRange === undefined
          ? "Range: n/a"
          : `Range: ~${{Number(estimatedRange).toFixed(0)}} m (${{activeOverlay.guidance.range_estimation_method || "bbox"}})`;
        const targetLine = activeOverlay.guidance.target_profile_label
          ? `Target: ${{activeOverlay.guidance.target_profile_label}}`
          : "Target: Unknown";
        const engagementLine = autoNeutralized
          ? `Auto engagement: neutralized at ≤${{Number(command.engagement_distance_threshold_m || 2).toFixed(0)}} m`
          : "Auto engagement: standby";

        guidancePanel.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;gap:0.75rem;margin-bottom:0.65rem;">
            <div style="font-weight:700;color:#f8fafc;">${{statusLabel}}</div>
            <div style="padding:0.2rem 0.55rem;border-radius:999px;background:${{autoNeutralized ? "rgba(34,197,94,0.28)" : "rgba(34,197,94,0.18)"}};color:#86efac;font-size:0.78rem;font-weight:700;">
              Frame ${{activeOverlay.frame_index}}
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem 1rem;">
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:0.2rem;">
                <span>Yaw</span>
                <strong>${{command.yaw_direction}} ${{yawPercent}}%</strong>
              </div>
              ${{renderSignedBar(command.yaw_command_norm, "rgba(34,197,94,0.95)")}}
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:0.2rem;">
                <span>Pitch</span>
                <strong>${{command.pitch_direction}} ${{pitchPercent}}%</strong>
              </div>
              ${{renderSignedBar(command.pitch_command_norm, "rgba(56,189,248,0.95)")}}
            </div>
          </div>
          <div style="margin-top:0.65rem;font-size:0.82rem;color:#cbd5e1;">
            ${{targetLine}}<br/>
            ${{rangeLine}}<br/>
            Offset: dx=${{Number(activeOverlay.guidance.dx_pixels).toFixed(0)}} px, dy=${{Number(activeOverlay.guidance.dy_pixels).toFixed(0)}} px
            <br/>
            Angles: yaw=${{Number(activeOverlay.guidance.yaw_offset_deg).toFixed(1)}}°, pitch=${{Number(activeOverlay.guidance.pitch_offset_deg).toFixed(1)}}°
            <br/>
            Range gain: x${{Number(command.range_gain || 1).toFixed(2)}}
            <br/>
            ${{engagementLine}}
          </div>
        `;
      }};

      const updateOverlay = () => {{
        if (!overlayLayer) {{
          return;
        }}

        if (!overlayFrames.length) {{
          overlayLayer.innerHTML = "";
          updateGuidancePanel(null);
          return;
        }}

        const runtimeState = ensureRuntimeState();
        const rawTime = Number(runtimeState.currentTime ?? video.currentTime ?? 0);
        const currentTime = Number.isNaN(rawTime) ? 0 : rawTime;

        let activeOverlay = null;
        for (const overlayFrame of overlayFrames) {{
          if (Number(overlayFrame.timestamp_seconds) <= currentTime + 0.05) {{
            activeOverlay = overlayFrame;
          }}
        }}

        if (!activeOverlay) {{
          overlayLayer.innerHTML = "";
          updateGuidancePanel(null);
          return;
        }}

        const intrinsicWidth = Number(video.videoWidth ?? 0);
        const intrinsicHeight = Number(video.videoHeight ?? 0);
        const renderedWidth = Number(video.clientWidth ?? 0);
        const renderedHeight = Number(video.clientHeight ?? 0);
        if (!intrinsicWidth || !intrinsicHeight || !renderedWidth || !renderedHeight) {{
          overlayLayer.innerHTML = "";
          updateGuidancePanel(activeOverlay);
          return;
        }}

        const scale = Math.min(renderedWidth / intrinsicWidth, renderedHeight / intrinsicHeight);
        const displayWidth = intrinsicWidth * scale;
        const displayHeight = intrinsicHeight * scale;
        const offsetX = (renderedWidth - displayWidth) / 2;
        const offsetY = (renderedHeight - displayHeight) / 2;

        const boxLeft = offsetX + Number(activeOverlay.x_min) * scale;
        const boxTop = offsetY + Number(activeOverlay.y_min) * scale;
        const boxWidth = Math.max(2, (Number(activeOverlay.x_max) - Number(activeOverlay.x_min)) * scale);
        const boxHeight = Math.max(2, (Number(activeOverlay.y_max) - Number(activeOverlay.y_min)) * scale);
        const confidence = activeOverlay.confidence;
        const overlayRuntimeState = ensureRuntimeState();
        const pulseActive = guidanceArmed && Date.now() < Number(overlayRuntimeState.guidancePulseUntil ?? 0);
        const isGuidanceFrame = guidanceArmed && activeOverlay.guidance && activeOverlay.guidance_command;
        const isNeutralizedFrame = Boolean(activeOverlay.guidance_command && activeOverlay.guidance_command.auto_engagement_triggered);
        const isTrackingFrame = activeOverlay.source === "tracking";
        const overlayColor = isNeutralizedFrame
          ? "rgba(34,197,94,0.98)"
          : (isGuidanceFrame
              ? "rgba(56, 189, 248, 0.98)"
              : (isTrackingFrame ? "rgba(34,197,94,0.95)" : "rgba(245,158,11,0.95)"));
        const stateLabel = isNeutralizedFrame ? "neutralized" : (isGuidanceFrame ? "guidance" : (isTrackingFrame ? "tracking" : "detection"));
        const targetLabel = activeOverlay.target_label ? ` • ${{activeOverlay.target_label}}` : "";
        const label = confidence === null || confidence === undefined
          ? `Frame ${{activeOverlay.frame_index}} • ${{stateLabel}}${{targetLabel}}`
          : `Frame ${{activeOverlay.frame_index}} • ${{stateLabel}}${{targetLabel}} • ${{(Number(confidence) * 100).toFixed(0)}}%`;
        const rangeLabel = activeOverlay.guidance && activeOverlay.guidance.estimated_range_m !== null && activeOverlay.guidance.estimated_range_m !== undefined
          ? ` • ~${{Number(activeOverlay.guidance.estimated_range_m).toFixed(0)}}m`
          : "";

        let guidanceMarkup = "";
        if (isGuidanceFrame) {{
          const aimX = offsetX + Number(activeOverlay.guidance.aim_point_x ?? activeOverlay.guidance.frame_center_x) * scale;
          const aimY = offsetY + Number(activeOverlay.guidance.aim_point_y ?? activeOverlay.guidance.frame_center_y) * scale;
          const targetX = offsetX + Number(activeOverlay.guidance.target_center_x) * scale;
          const targetY = offsetY + Number(activeOverlay.guidance.target_center_y) * scale;
          guidanceMarkup = `
            <svg style="position:absolute;inset:0;width:100%;height:100%;overflow:visible;" viewBox="0 0 ${{renderedWidth}} ${{renderedHeight}}" preserveAspectRatio="none">
              <line x1="${{aimX}}" y1="${{aimY}}" x2="${{targetX}}" y2="${{targetY}}" stroke="rgba(56,189,248,0.92)" stroke-width="2.5" stroke-linecap="round" />
              <circle cx="${{aimX}}" cy="${{aimY}}" r="6" fill="rgba(15,23,42,0.9)" stroke="rgba(56,189,248,0.98)" stroke-width="2" />
              <circle cx="${{targetX}}" cy="${{targetY}}" r="5" fill="rgba(56,189,248,0.98)" />
            </svg>
          `;
        }}

        const neutralizedMarkup = isNeutralizedFrame ? `
          <div style="position:absolute;inset:0;background:rgba(34,197,94,0.22);display:flex;align-items:center;justify-content:center;">
            <div style="padding:12px 18px;border-radius:999px;background:rgba(21,128,61,0.82);color:#ecfdf5;font-size:20px;font-weight:800;letter-spacing:0.05em;text-transform:uppercase;box-shadow:0 10px 30px rgba(21,128,61,0.35);">
              Neutralized
            </div>
          </div>
        ` : "";

        overlayLayer.innerHTML = `
          ${{guidanceMarkup}}
          ${{neutralizedMarkup}}
          <div style="position:absolute;left:${{boxLeft}}px;top:${{boxTop}}px;width:${{boxWidth}}px;height:${{boxHeight}}px;border:2px solid ${{overlayColor}};border-radius:8px;box-shadow:0 0 0 1px rgba(15,23,42,0.2) inset, 0 0 18px ${{overlayColor}};opacity:${{pulseActive ? "0.82" : "1"}};"></div>
          <div style="position:absolute;left:${{boxLeft}}px;top:${{Math.max(8, boxTop - 28)}}px;padding:4px 8px;border-radius:999px;background:rgba(15,23,42,0.82);color:#f8fafc;font-size:12px;font-weight:700;line-height:1;">${{label}}${{rangeLabel}}</div>
        `;
        updateGuidancePanel(activeOverlay);
      }};

      video.addEventListener("loadedmetadata", () => {{
        restoreState();
        updateRuntimeState({{
          currentTime: Number(video.currentTime ?? 0),
          duration: Number(video.duration ?? 0),
        }});
        applyPlayRequest();
        applyPauseRequest();
        applyGuidanceState();
        retryPlayIfRequested();
        updateOverlay();
      }});
      video.addEventListener("canplay", () => {{
        applyPlayRequest();
        applyPauseRequest();
        applyGuidanceState();
        retryPlayIfRequested();
      }});
      video.addEventListener("play", () => {{
        updateRuntimeState({{ playing: true }});
      }});
      video.addEventListener("pause", () => {{
        updateRuntimeState({{
          playing: false,
          currentTime: Number(video.currentTime ?? 0),
        }});
      }});
      video.addEventListener("timeupdate", () => {{
        updateRuntimeState({{
          currentTime: Number(video.currentTime ?? 0),
          playing: !video.paused,
        }});
        updateOverlay();
      }});
      video.addEventListener("ended", () => {{
        if (!autoReplay) {{
          updateRuntimeState({{
            currentTime: Number(video.duration ?? video.currentTime ?? 0),
            playing: false,
          }});
        }} else {{
          updateRuntimeState({{ currentTime: 0, playing: true }});
        }}
        updateOverlay();
      }});
      window.addEventListener("resize", updateOverlay);
      ensureRuntimeState();
      restoreState();
      applyPlayRequest();
      applyPauseRequest();
      applyGuidanceState();
      retryPlayIfRequested();
      updateOverlay();
      window.setInterval(updateOverlay, 180);
    </script>
    """


def render_custom_video_player(
    video_bytes: bytes,
    mime_type: str,
    auto_replay: bool,
    play_request_nonce: int,
    pause_request_nonce: int,
    guidance_armed: bool,
    guidance_arm_nonce: int,
    player_storage_key: str,
    preview_frames: list[FramePreview],
) -> None:
    player_html = build_custom_video_player_html(
        video_bytes=video_bytes,
        mime_type=mime_type,
        auto_replay=auto_replay,
        play_request_nonce=play_request_nonce,
        pause_request_nonce=pause_request_nonce,
        guidance_armed=guidance_armed,
        guidance_arm_nonce=guidance_arm_nonce,
        player_storage_key=player_storage_key,
        preview_frames=preview_frames,
    )
    html_component(player_html, height=PLAYER_HEIGHT_PX + 12)


def render_preview_results(preview_frames: list[FramePreview]) -> None:
    if preview_frames:
        st.caption("Pipeline preview is now embedded in the Operator Runtime Block.")
