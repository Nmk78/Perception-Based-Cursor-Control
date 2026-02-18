from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Camera selection and capture size.
    camera_index: int = 0
    frame_width: int = 1280
    frame_height: int = 720

    # MediaPipe hand tracking quality.
    hand_min_detection_confidence: float = 0.6
    hand_min_tracking_confidence: float = 0.5
    max_hands: int = 2

    # Which hand controls the cursor: "Right", "Left", or "Either".
    pointer_hand: str = "Right"

    # If True, gesture actions use the other hand (two-hand mode).
    require_two_hands_for_gestures: bool = True
    # Gesture-hand open palm = rest (ignored). Pointer-hand open palm = pause.
    allow_pointer_scroll: bool = True
    pointer_scroll_requires_gesture_rest: bool = True

    # Draw the hand joint geometry (skeleton) on the camera preview.
    draw_hand_landmarks: bool = True
    draw_hand_handedness: bool = True

    # Cursor mapping and speed tuning.
    cursor_sensitivity_x: float = 1.05
    cursor_sensitivity_y: float = 1.0
    invert_x: bool = False
    invert_y: bool = False
    max_cursor_step_px: int = 35
    pen_active_margin_x: float = 0.15
    pen_active_margin_y: float = 0.18

    # Extra smoothing for stability (more = smoother, but adds lag).
    smoothing_alpha: float = 0.12
    moving_average_window: int = 8

    # Gesture thresholds and timing.
    pinch_threshold: float = 0.055
    # Distance between index and middle tips to count as a "V" shape (zoom in).
    v_shape_threshold: float = 0.07
    gesture_hold_seconds: float = 0.35
    click_cooldown_seconds: float = 0.55
    right_click_cooldown_seconds: float = 0.65
    double_click_cooldown_seconds: float = 0.7
    window_action_cooldown_seconds: float = 1.0
    gesture_switch_cooldown_seconds: float = 0.3

    # Scroll/zoom response (higher = faster).
    scroll_gain: float = 65.0
    zoom_gain: float = 45.0

    # Show an on-screen gesture demo for the first N seconds (press H to toggle).
    gesture_demo_seconds: float = 10.0


CFG = Config()
