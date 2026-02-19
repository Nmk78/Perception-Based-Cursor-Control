# Touchless Interaction System

Use this as a script for building your presentation. Each section = one or more slides. Tips are at the end.

---

## Slide 1: Title

**Points:**
- **Touchless Cursor**
- Hand-gesture-controlled mouse using a webcam
- [Your name / course / date]

**Tip:** Keep title slide minimal; one clear line under the title is enough.

---

## Slide 2: Problem / Motivation

**Points:**
- Need to control PC without touching mouse or keyboard
- Accessibility: limited mobility, sterile environments, presentations
- Touchless interaction via camera is natural and hygienic

**Tip:** One short problem statement; add one real-world scenario (e.g. “presenting without a clicker”).

---

## Slide 3: Solution Overview

**Points:**
- Use **webcam** to track hands in real time
- **One hand** = move cursor (index finger) and scroll (two fingers)
- **Other hand** = clicks, zoom, drag, window control (minimize, maximize, close)
- No extra hardware — software only on Windows

**Tip:** Use a simple diagram: “Webcam → Hand tracking → Cursor + gestures.”

---

## Slide 4: Main Features

**Points:**
- **Pointer:** Index = move cursor; two fingers = scroll; open palm = pause
- **Clicks:** Pinch = left click; two fingers = right click; thumbs up = double click
- **Drag:** Fist hold = drag, release = drop
- **Zoom:** Three fingers spread = zoom in; pinch = zoom out
- **Windows:** Spider = close; thumbs down = minimize; ring+pinky up = maximize; two-hand gesture = show all windows
- **Smooth cursor** via filtering (less jitter)

**Tip:** Use icons or one-word labels per row; avoid long sentences.

---

## Slide 5: Technology Stack

**Points:**
- **MediaPipe Hands** — hand detection and 21 landmarks per hand
- **OpenCV** — camera capture and display
- **PyAutoGUI** — mouse movement, clicks, scroll, keyboard shortcuts
- **Python 3** — main logic, config, smoothing filters

**Tip:** One bullet per technology; add version only if required (e.g. MediaPipe 0.10.14).

---

## Slide 6: Theory — Hand Tracking (MediaPipe)

**Points:**
- Input: RGB frames from webcam
- Output: **21 3D landmarks** per hand (normalized 0–1), plus Left/Right label
- Landmarks: wrist, thumb (4), index/middle/ring/pinky (4 each) — tips and joints (PIP, MCP)
- Tuning: `min_detection_confidence`, `min_tracking_confidence`, `max_num_hands = 2`

**Tip:** Show the classic “21-point hand skeleton” image from MediaPipe docs for one slide.

---

## Slide 7: Theory — Cursor Mapping

**Points:**
- **Index fingertip** → normalized (x, y)
- **Active region:** margins crop the frame so only the center area maps to screen
- **Sensitivity:** gain around center for finer control; optional X/Y invert
- **Step limit:** max pixels per frame so cursor doesn’t jump
- Formula: margins → normalize → sensitivity → screen width/height → pixel position

**Tip:** One simple diagram: “Hand region → [mapping] → Screen” with one equation if needed.

---

## Slide 8: Theory — Smoothing (Less Jitter)

**Points:**
- **Stage 1 — Exponential moving average (EMA):**  
  `new_pos = α × raw + (1 − α) × previous`  
  Low α = smoother, more lag
- **Stage 2 — Moving average:** average of last N positions
- **Reset** when not pointing (e.g. scroll/zoom/pause) so cursor doesn’t drift

**Tip:** Show “raw vs smoothed” with a small graph or two curves; keep math to one line.

---

## Slide 9: Theory — Gesture Recognition

**Points:**
- **Finger state:** tip above PIP (in image) = finger “up”
- **Pinch:** distance (thumb tip, index tip) < threshold
- **Spider:** index + pinky extended (tip–wrist vs PIP–wrist ratio), middle + ring curled
- **Thumbs up/down:** thumb tip vs MCP; other fingers curled
- **Stability:** gesture must be **held** for ~0.35 s before action
- **Cooldowns:** prevent double clicks / repeated window actions

**Tip:** One slide for “how we detect” (geometry + thresholds), one for “how we stabilize” (hold + cooldown).

---

## Slide 10: System Architecture / Pipeline

**Points:**
- **Camera** → frames
- **Hand tracker** → landmarks + handedness
- **Hand selection** → pointer hand vs gesture hand (by config)
- **Gesture controller** → pen point, scroll, zoom, click/drag/window flags
- **Smoothing** → filtered cursor position
- **Cursor controller** → PyAutoGUI (move, click, scroll, hotkeys)

**Tip:** Use a horizontal flow: Camera → HandTracker → GestureController → Smoother → CursorController. One box per component.

---

## Slide 11: Gesture Cheat Sheet (Optional)

**Points:**
- Table or grid: Gesture | Action (e.g. Pinch → Left click; Two fingers → Right click; Fist hold → Drag)
- Or split: Pointer hand | Gesture hand | Window control

**Tip:** Single slide; use icons or hand photos if available; keep text minimal.

---

## Slide 12: Configuration

**Points:**
- All settings in **one place:** `config.py` (Python dataclass)
- Camera: index, resolution, display scale
- Cursor: sensitivity X/Y, margins, step limit, invert
- Smoothing: α, window size
- Gestures: pinch threshold, hold time, cooldowns, scroll/zoom gain
- Hand roles: which hand is pointer; two-hand vs single-hand mode

**Tip:** Show 3–4 bullet groups; “Change one file, restart app.”

---

## Slide 13: Demo / Screenshot

**Points:**
- Optional: screenshot of the app window (camera + overlay + status)
- Or: “Live demo” slide with 2–3 steps (e.g. move cursor → pinch click → scroll)

**Tip:** If no live demo, one screenshot with short captions (e.g. “Hand landmarks”, “Status: Pen Active”).

---

## Slide 14: Setup & Run

**Points:**
- Python 3.8+, Windows, webcam
- `python -m venv venv` → activate → `pip install -r requirements.txt`
- `python main.py`
- ESC to quit, H for on-screen help

**Tip:** Three steps only; code blocks only if the audience expects it.

---

## Slide 15: Limitations & Future Work

**Points:**
- **Lighting** and **camera position** affect tracking
- **Performance:** resolution and smoothing trade-off (CPU vs smoothness)
- Possible extensions: more gestures, calibration wizard, other OS or input devices

**Tip:** Keep to 3–4 short bullets; “future work” can be one line.

---

## Slide 16: Conclusion / Q&A

**Points:**
- Touchless Cursor = webcam + MediaPipe + gestures → full mouse control
- Theory: landmarks, mapping, smoothing, gesture geometry + hold/cooldown
- Configurable, no extra hardware
- Thank you / Questions?

**Tip:** One recap sentence, then “Questions?” or “Thank you”.

---

## General PowerPoint Tips

1. **One idea per slide** — avoid crowding; use 2–3 bullets per slide.
2. **Consistent style** — same font (e.g. title 24–28 pt, body 18–20 pt), one accent color.
3. **Less text, more visuals** — diagrams for pipeline and mapping; table for gestures.
4. **Theory slides** — one formula or one diagram per slide; explain in speech.
5. **Demo** — if live, have a backup screenshot/video in case the camera fails.
6. **Timing** — aim for ~1–2 minutes per slide; leave 2–3 minutes for Q&A.
7. **Rehearse** — practice transitions (especially “theory” and “demo”).
8. **References** — last slide or footnote: MediaPipe Hands, PyAutoGUI, OpenCV (with links if allowed).
