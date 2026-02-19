# Touchless Cursor

A **hand-gesture-controlled mouse** for Windows: use your webcam to move the cursor, scroll, click, and control windows—no physical mouse or touchpad required.

---

## Table of Contents

- [Features](#features)
- [Theory & How It Works](#theory--how-it-works)
- [Gesture Reference](#gesture-reference)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Setup & Run](#setup--run)
- [Dependencies](#dependencies)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Notes](#notes)

---

## Features

- **Pointer hand**: Index finger moves the cursor; two fingers scroll; open palm pauses tracking.
- **Gesture hand**: Pinch = left click, two fingers = right click, thumbs up = double click, fist hold = drag.
- **Zoom**: Three fingers spread = zoom in, three fingers pinch = zoom out (Ctrl+scroll).
- **Window control**: Spider gesture = close, thumbs down = minimize, ring+pinky up = maximize, two-hand “show all” = task view.
- **Smooth cursor**: Exponential smoothing + moving average for stable, low-jitter movement.
- **Configurable**: All thresholds, sensitivity, and behavior are tuned in `config.py`.

---

## Theory & How It Works

### 1. Hand tracking (MediaPipe)

The pipeline uses **MediaPipe Hands** (`mediapipe.solutions.hands`) to detect and track hands in the camera feed.

- **Input**: RGB frames from the webcam (optionally flipped for mirror view).
- **Output**: For each hand, a set of **21 3D landmarks** in normalized image coordinates `[0, 1]`, plus a **handedness** label (Left/Right).
- **Landmarks**: Wrist (0), thumb CMC/IP/tip (1–4), index PIP/tip (5–8), middle (9–12), ring (13–16), pinky (17–20). Tips and PIP/MCP joints are used for finger state and gesture logic.
- **Parameters**: `min_detection_confidence` and `min_tracking_confidence` control detection vs. tracking trade-off; `max_num_hands` is set to 2 for two-hand mode.

**Reference**: [MediaPipe Hands](https://google.github.io/mediapipe/solutions/hands.html) — real-time hand landmark estimation.

---

### 2. Hand roles (pointer vs. gesture)

- **Pointer hand**: Drives cursor position. Configurable as left, right, or first-detected (`config.pointer_hand`).
- **Gesture hand**: The *other* hand is used for clicks, scroll, zoom, and window actions. If only one hand is visible and `require_two_hands_for_gestures` is false, the same hand can act as both pointer and gesture source.

---

### 3. Cursor mapping

- The **index fingertip** of the pointer hand gives a 2D point `(pen_x, pen_y)` in normalized coordinates.
- **Active region**: Margins (`pen_active_margin_x`, `pen_active_margin_y`) define a rectangle; the point is linearly mapped from this rectangle to `[0, 1] × [0, 1]`, then clamped.
- **Sensitivity**: A gain around the center: `0.5 + (n - 0.5) * sensitivity` stretches movement for finer control.
- **Inversion**: Optional `invert_x` / `invert_y` flip the axis.
- **Output**: Normalized coords are multiplied by screen size to get pixel coordinates. Movement is applied with a **per-frame step limit** (`max_cursor_step_px`) to avoid huge jumps.

---

### 4. Smoothing

Cursor position is smoothed in two stages (see `modules/smoothing.py` and `utils/filters.py`):

1. **Exponential moving average (EMA)**  
   `out = alpha * new + (1 - alpha) * prev`  
   Low `alpha` = smoother but more lag; `config.smoothing_alpha` controls this.

2. **Moving average (MA)**  
   A sliding window of the last `moving_average_window` points is averaged. Reduces jitter further.

The smoother is **reset** when the pointer is not active (e.g. scrolling, zooming, or paused) so the cursor doesn’t “slide” from the last position when you resume pointing.

---

### 5. Gesture recognition

Gestures are derived from landmark geometry and timing:

| Concept | Implementation |
|--------|----------------|
| **Finger extended** | Tip’s *y* (image space) above PIP *y* (e.g. “finger up” in frame). |
| **Pinch** | Euclidean distance (thumb tip, index tip) &lt; `pinch_threshold`. |
| **Two fingers** | Index and middle extended; ring and pinky not. |
| **Three fingers** | Index, middle, ring extended; pinky not. |
| **Open palm** | At least four fingers extended. |
| **Thumbs up/down** | Thumb tip above/below thumb MCP; other fingers curled. |
| **Spider** | Index and pinky extended (tip–wrist &gt; PIP–wrist ratio); middle and ring curled. |
| **Ring + pinky up** | Same ratio-based logic for maximize. |
| **Show-all-windows** | Four fingers extended, thumb down, fingers spread (both hands). |

**Stability**: A gesture must be **held** for `gesture_hold_seconds` before triggering an action. Separate **cooldowns** (e.g. `click_cooldown_seconds`, `window_action_cooldown_seconds`) prevent repeated triggers. A short **gesture switch cooldown** avoids accidental action when changing gestures.

**Scroll (pointer hand)**: Two fingers up on the pointer hand; scroll delta from vertical movement of the two-finger centroid, scaled by `scroll_gain`. Can be gated by “gesture hand at rest” (`pointer_scroll_requires_gesture_rest`).

**Zoom (gesture hand)**: Three-finger mode; zoom delta from the change in sum of adjacent finger-tip distances (spread vs. pinch), scaled by `zoom_gain`. Sent as Ctrl+scroll.

---

### 6. System integration

- **Mouse movement, clicks, scroll, drag**: Implemented with **PyAutoGUI** (`moveTo`, `click`, `scroll`, `mouseDown`/`mouseUp`).
- **Window actions**: Keyboard shortcuts (e.g. Alt+F4, Win+Down, Win+Up, Win+Tab) via PyAutoGUI.

---

## Gesture Reference

### Pointer hand (cursor movement)

| Gesture | Action |
|--------|--------|
| **Index tip** | Move cursor |
| **Two fingers** (index + middle) | Scroll (after short hold) |
| **Open palm** | Pause tracking (touchpad-style rest) |

### Gesture hand — mouse

| Gesture | Action |
|--------|--------|
| **Pinch** (thumb + index) | Left click |
| **Two fingers** (index + middle) | Right click |
| **Thumbs up** | Double click |
| **Fist hold** | Drag (hold to drag, release gesture to drop) |

### Gesture hand — zoom

| Gesture | Action |
|--------|--------|
| **Three fingers spread** | Zoom in |
| **Three fingers pinch** | Zoom out |

### Gesture hand — window control

| Gesture | Action |
|--------|--------|
| **Spider** (index + pinky up, middle + ring down) | Close window |
| **Thumbs down** | Minimize window |
| **Ring + pinky up** | Maximize window |
| **Both hands: four fingers spread, thumb down** | Show all windows (task view) |

### Other

| Input | Action |
|-------|--------|
| **ESC** | Exit application |
| **H** | Toggle on-screen gesture help |

---

## Configuration

All behavior is controlled by the **`Config`** dataclass in `config.py`. Key groups:

- **Camera**: `camera_index`, `frame_width`, `frame_height`, `display_scale`
- **MediaPipe**: `hand_min_detection_confidence`, `hand_min_tracking_confidence`, `max_hands`
- **Hand roles**: `pointer_hand` ("Left" / "Right"), `require_two_hands_for_gestures`, `allow_pointer_scroll`, `pointer_scroll_requires_gesture_rest`
- **Display**: `draw_hand_landmarks`, `draw_hand_handedness`
- **Cursor**: `cursor_sensitivity_x/y`, `invert_x/y`, `max_cursor_step_px`, `pen_active_margin_x/y`
- **Smoothing**: `smoothing_alpha`, `moving_average_window`
- **Gestures**: `pinch_threshold`, `v_shape_threshold`, `gesture_hold_seconds`, all `*_cooldown_seconds`, `scroll_gain`, `zoom_gain`
- **UI**: `gesture_demo_seconds` (seconds to show help on startup)

Edit `config.py` and restart the app to apply changes.

---

## Project Structure

```
TouchlessCursor/
├── main.py              # Entry point: camera loop, hand selection, gesture → cursor actions
├── config.py            # Single source of configuration (Config dataclass)
├── requirements.txt     # Python dependencies
├── modules/
│   ├── camera.py        # Webcam capture (OpenCV), frame flip
│   ├── hand_tracker.py  # MediaPipe Hands wrapper (landmarks + handedness)
│   ├── gesture_controller.py  # Gesture detection and action flags (pinch, scroll, zoom, etc.)
│   ├── cursor_controller.py  # Pen→screen mapping, move/click/scroll/drag/zoom/window hotkeys
│   └── smoothing.py     # CursorSmoother: EMA + moving average
└── utils/
    ├── math_utils.py    # clamp, distance_2d, lerp, normalized_ratio
    └── filters.py       # ExponentialPointFilter, MovingAveragePointFilter
```

**Data flow**: Camera → HandTracker (landmarks) → hand selection (pointer vs. gesture) → GestureController (pen point, scroll, zoom, click/drag/window flags) → CursorSmoother → CursorController (PyAutoGUI).

---

## Setup & Run

**Requirements**: Python 3.8+, Windows (for PyAutoGUI and window hotkeys), webcam.

1. **Clone or download** the project and open a terminal in its root.

2. **Create and activate a virtual environment** (recommended):

   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. **Run the application**:

   ```powershell
   python main.py
   ```

5. A window titled **"Touchless Cursor (Pen + Gestures)"** shows the camera feed with overlay. Use the gestures above; press **H** to toggle the help panel, **ESC** to quit.

---

## Dependencies

| Package | Purpose |
|--------|--------|
| `opencv-python` | Camera capture and display |
| `mediapipe==0.10.14` | Hand landmark detection (Solutions API; version pinned) |
| `protobuf>=4.25.3,<5` | MediaPipe protocol buffers |
| `pyautogui` | Mouse and keyboard control |
| `numpy` | Optional/transitive use |
| `attrs>=19.1.0` | Optional/transitive use |

**Note**: This project relies on MediaPipe’s **Solutions API** (`mp.solutions.hands`). Use `mediapipe==0.10.14` for compatibility; other versions may change or remove this API.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **H** | Toggle on-screen gesture help |
| **ESC** | Exit Touchless Cursor |

---

## Notes

- **Performance**: Higher camera resolution and smoothing increase CPU use; lower resolution or higher `smoothing_alpha` can improve responsiveness.
- **Lighting**: Reliable hand tracking works best with even lighting and a clear view of the hand.
- **Safety**: PyAutoGUI’s failsafe is disabled in this app so cursor movement is not interrupted by moving the mouse to a corner. Use ESC to exit.
