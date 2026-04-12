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
from app.ui.state import get_current_video, get_uploader_key


PLAYBACK_SPEED_OPTIONS = [0.25, 0.5, 0.75, 1.0, 1.5]
PLAYER_HEIGHT_PX = 420
RUNTIME_SIDE_PANEL_HEIGHT_PX = 560


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


def format_playback_speed(speed: float) -> str:
    return f"x{speed:g}"


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
    playback_speed: float,
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
        runtime_status = "Processing uploaded video preview"
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
        ("Playback Speed", format_playback_speed(playback_speed)),
        ("Auto Replay", "Enabled" if auto_replay else "Disabled"),
    ]

    if uploaded_video_name is not None and effective_interval:
        entries.append(("Effective Detection Interval", f"every {effective_interval} frames"))

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
                "x_min": bbox.x_min,
                "y_min": bbox.y_min,
                "x_max": bbox.x_max,
                "y_max": bbox.y_max,
                "confidence": confidence,
                "source": source,
            }
        )

    return overlay_payload


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

    cards_html = "".join(
        _preview_frame_html(preview, is_latest=index == len(preview_frames) - 1)
        for index, preview in enumerate(preview_frames)
    )
    preview_sync_key = (
        f"operator-runtime-video::{hashlib.sha1(player_storage_key.encode('utf-8')).hexdigest()}"
        if player_storage_key is not None
        else None
    )

    preview_html = f"""
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
      let lastActiveTimestamp = null;

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

        const activeTimestamp = activeCard?.dataset.timestamp ?? null;
        if (activeCard && previewBox && activeTimestamp !== lastActiveTimestamp) {{
          lastActiveTimestamp = activeTimestamp;
          activeCard.scrollIntoView({{ block: "nearest", behavior: "smooth" }});
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
                action_col, pause_col, reset_col = st.columns(3)
                start_processing = action_col.button(
                    "Processing..." if is_processing_preview else "Start Processing",
                    type="primary",
                    use_container_width=True,
                    disabled=True,
                )
                tactical_pause = pause_col.button(
                    "Tactical Pause",
                    use_container_width=True,
                    disabled=True,
                )
                reset_state = reset_col.button(
                    "Reset State",
                    use_container_width=True,
                )
            else:
                player_storage_key = (
                    f"{current_video['name']}:{current_video['size']}:{st.session_state.uploader_nonce}:{st.session_state.player_session_nonce}"
                )
                st.caption("Play and pause from the built-in video controls.")
                if is_processing_preview:
                    st.info("Building the runtime preview now. When processing finishes, the player will restart from frame 0.")
                render_custom_video_player(
                    video_bytes=current_video["bytes"],
                    mime_type=current_video["type"],
                    playback_speed=float(st.session_state.playback_speed),
                    auto_replay=bool(st.session_state.auto_replay),
                    play_request_nonce=int(st.session_state.play_request_nonce),
                    pause_request_nonce=int(st.session_state.pause_request_nonce),
                    player_storage_key=player_storage_key,
                    preview_frames=preview_frames,
                )
                controls_col, autoplay_col = st.columns([5, 2], gap="small")
                controls_col.segmented_control(
                    "Playback speed",
                    options=PLAYBACK_SPEED_OPTIONS,
                    default=st.session_state.playback_speed,
                    key="playback_speed",
                    format_func=format_playback_speed,
                    width="stretch",
                )
                autoplay_col.toggle(
                    "Auto Replay",
                    key="auto_replay",
                    help="Replay automatically when the uploaded video reaches the end.",
                )
                action_col, pause_col, reset_col = st.columns(3)
                start_processing = action_col.button(
                    "Processing..." if is_processing_preview else "Start Processing",
                    type="primary",
                    use_container_width=True,
                    disabled=is_processing_preview,
                )
                tactical_pause = pause_col.button(
                    "Tactical Pause",
                    use_container_width=True,
                    disabled=is_processing_preview,
                )
                reset_state = reset_col.button(
                    "Reset State",
                    use_container_width=True,
                    disabled=is_processing_preview,
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
                    playback_speed=float(st.session_state.playback_speed),
                    auto_replay=bool(st.session_state.auto_replay),
                    is_processing_preview=is_processing_preview,
                    processing_cursor_frame=processing_cursor_frame,
                    processing_total_frames=processing_total_frames,
                    effective_interval=effective_interval,
                )
                for label, value in detection_log_entries:
                    st.markdown(f"**{label}:** {value}")

                if preview_frames:
                    latest_preview = preview_frames[-1]
                    st.divider()
                    st.markdown("**Latest Runtime Events**")
                    for event in latest_preview.events[-3:]:
                        st.write(f"- [{event.stage}] {event.message}")
                elif is_processing_preview:
                    st.info("Runtime preview is being built. The first review pass will appear here when processing finishes.")
                else:
                    st.info("Processing updates will appear here once runtime preview generation begins.")

    return pending_upload, UiActions(
        start_processing=start_processing,
        reset_state=reset_state,
        tactical_pause=tactical_pause,
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


def render_custom_video_player(
    video_bytes: bytes,
    mime_type: str,
    playback_speed: float,
    auto_replay: bool,
    play_request_nonce: int,
    pause_request_nonce: int,
    player_storage_key: str,
    preview_frames: list[FramePreview],
) -> None:
    encoded_video = base64.b64encode(video_bytes).decode("utf-8")
    sanitized_storage_key = hashlib.sha1(player_storage_key.encode("utf-8")).hexdigest()
    video_source = f"data:{mime_type};base64,{encoded_video}"
    overlay_payload = build_runtime_overlay_payload(preview_frames)
    autoplay_attribute = "autoplay" if play_request_nonce > pause_request_nonce else ""

    player_html = f"""
    <div style="position:relative;border-radius: 1rem; overflow: hidden; background: #020617; border: 1px solid rgba(148, 163, 184, 0.28);">
      <video
        id="operator-runtime-video"
        controls
        muted
        playsinline
        {autoplay_attribute}
        style="display:block;width:100%;height:{PLAYER_HEIGHT_PX}px;background:#020617;object-fit:contain;"
      >
        <source src="{html.escape(video_source)}" type="{html.escape(mime_type)}">
      </video>
      <div id="operator-runtime-overlay-layer" style="position:absolute;inset:0;pointer-events:none;"></div>
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
      const playbackSpeed = {json.dumps(playback_speed)};
      const autoReplay = {json.dumps(auto_replay)};
      const playRequestNonce = {json.dumps(play_request_nonce)};
      const pauseRequestNonce = {json.dumps(pause_request_nonce)};
      const overlayFrames = {json.dumps(overlay_payload)};
      const overlayLayer = document.getElementById("operator-runtime-overlay-layer");

      const ensureRuntimeState = () => {{
        if (!rootWindow[runtimeStateBucketKey]) {{
          rootWindow[runtimeStateBucketKey] = {{}};
        }}
        if (!rootWindow[runtimeStateBucketKey][storageKey]) {{
          rootWindow[runtimeStateBucketKey][storageKey] = {{
            currentTime: 0,
            lastPlayRequest: 0,
            lastPauseRequest: 0,
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
        video.playbackRate = playbackSpeed;
        video.loop = autoReplay;
      }};

      const tryPlay = () => {{
        video.muted = true;
        video.playbackRate = playbackSpeed;
        video.autoplay = true;
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

      const updateOverlay = () => {{
        if (!overlayLayer) {{
          return;
        }}

        if (!overlayFrames.length) {{
          overlayLayer.innerHTML = "";
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
          return;
        }}

        const intrinsicWidth = Number(video.videoWidth ?? 0);
        const intrinsicHeight = Number(video.videoHeight ?? 0);
        const renderedWidth = Number(video.clientWidth ?? 0);
        const renderedHeight = Number(video.clientHeight ?? 0);
        if (!intrinsicWidth || !intrinsicHeight || !renderedWidth || !renderedHeight) {{
          overlayLayer.innerHTML = "";
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
        const label = confidence === null || confidence === undefined
          ? `Frame ${{activeOverlay.frame_index}}`
          : `Frame ${{activeOverlay.frame_index}} • ${{(Number(confidence) * 100).toFixed(0)}}%`;

        overlayLayer.innerHTML = `
          <div style="position:absolute;left:${{boxLeft}}px;top:${{boxTop}}px;width:${{boxWidth}}px;height:${{boxHeight}}px;border:2px solid rgba(34,197,94,0.95);border-radius:8px;box-shadow:0 0 0 1px rgba(15,23,42,0.2) inset, 0 0 18px rgba(34,197,94,0.25);"></div>
          <div style="position:absolute;left:${{boxLeft}}px;top:${{Math.max(8, boxTop - 28)}}px;padding:4px 8px;border-radius:999px;background:rgba(15,23,42,0.82);color:#f8fafc;font-size:12px;font-weight:700;line-height:1;">${{label}}</div>
        `;
      }};

      video.addEventListener("loadedmetadata", () => {{
        restoreState();
        updateRuntimeState({{
          currentTime: Number(video.currentTime ?? 0),
          duration: Number(video.duration ?? 0),
        }});
        applyPlayRequest();
        applyPauseRequest();
        retryPlayIfRequested();
        updateOverlay();
      }});
      video.addEventListener("canplay", () => {{
        applyPlayRequest();
        applyPauseRequest();
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
          updateRuntimeState({{ currentTime: 0, playing: false }});
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
      retryPlayIfRequested();
      updateOverlay();
      window.setInterval(updateOverlay, 180);
    </script>
    """
    html_component(player_html, height=PLAYER_HEIGHT_PX + 12)


def render_preview_results(preview_frames: list[FramePreview]) -> None:
    if preview_frames:
        st.caption("Pipeline preview is now embedded in the Operator Runtime Block.")
