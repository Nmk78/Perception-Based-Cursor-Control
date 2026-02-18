import time

import cv2

from config import CFG
from modules.camera import CameraStream
from modules.cursor_controller import CursorController
from modules.gesture_controller import GestureController
from modules.hand_tracker import HandTracker
from modules.smoothing import CursorSmoother


def draw_status(frame, fps: float, tracking: bool, gesture: str, dragging: bool, paused: bool):
    if not tracking:
        status_text = "Hand Lost"
        status_color = (0, 0, 255)
    elif paused:
        status_text = "Paused (Touchpad Enabled)"
        status_color = (0, 220, 255)
    else:
        status_text = "Pen Active"
        status_color = (0, 200, 0)

    cv2.rectangle(frame, (10, 10), (470, 130), (20, 20, 20), -1)
    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2)
    cv2.putText(frame, f"Status: {status_text}", (20, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
    cv2.putText(frame, f"Gesture: {gesture}", (20, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
    cv2.putText(frame, f"Drag: {'ON' if dragging else 'OFF'}", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def draw_gesture_demo(frame):
    lines = [
        "--- Gesture Summary ---",
        "",
        "Pointer hand",
        "  Index tip -> Move cursor",
        "  Two fingers -> Scroll",
        "  Open palm -> Pause tracking",
        "",
        "Gesture hand (mouse)",
        "  Pinch -> Left click",
        "  Two fingers -> Right click",
        "  Thumbs up -> Double click",
        "  Fist hold -> Drag",
        "",
        "Gesture hand (zoom)",
        "  Three fingers spread -> Zoom in",
        "  Three fingers pinch -> Zoom out",
        "",
        "Window control (gesture hand)",
        "  Spider -> Close window",
        "  Thumbs down -> Minimize",
        "  Ring + pinky up -> Maximize",
        "  Both hands: four fingers spread, thumb down -> Show all windows",
        "",
        "Press H to toggle this help",
    ]
    x, y = 20, 150
    width = 460
    height = 20 * len(lines) + 20
    cv2.rectangle(frame, (x - 10, y - 20), (x + width, y - 20 + height), (15, 15, 15), -1)
    for idx, line in enumerate(lines):
        if not line:
            continue
        if line.startswith("---") or line.startswith("Pointer") or line.startswith("Gesture") or line.startswith("Window"):
            color = (0, 220, 255)
        else:
            color = (220, 220, 220)
        cv2.putText(
            frame,
            line,
            (x, y + idx * 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
        )


def select_hands(hands, pointer_preference: str):
    """Returns (pointer_hand, gesture_hand, gesture_handedness)."""
    if not hands:
        return None, None, None

    pref = (pointer_preference or "").strip().lower()
    pointer_idx = None
    if pref in {"left", "right"}:
        for idx, (_, handedness) in enumerate(hands):
            if handedness and handedness.lower() == pref:
                pointer_idx = idx
                break

    if pointer_idx is None:
        pointer_idx = 0

    pointer = hands[pointer_idx]
    gesture = None
    gesture_handedness = None
    if len(hands) > 1:
        for idx, hand in enumerate(hands):
            if idx != pointer_idx:
                gesture = hand
                gesture_handedness = hand[1]  # handedness label
                break

    return pointer, gesture, gesture_handedness


def main():
    camera = CameraStream(CFG.camera_index, CFG.frame_width, CFG.frame_height)
    hand_tracker = HandTracker(
        CFG.hand_min_detection_confidence,
        CFG.hand_min_tracking_confidence,
        max_hands=CFG.max_hands,
    )

    cursor = CursorController(
        CFG.cursor_sensitivity_x,
        CFG.cursor_sensitivity_y,
        invert_x=CFG.invert_x,
        invert_y=CFG.invert_y,
        max_cursor_step_px=CFG.max_cursor_step_px,
        pen_active_margin_x=CFG.pen_active_margin_x,
        pen_active_margin_y=CFG.pen_active_margin_y,
    )
    smoother = CursorSmoother(alpha=CFG.smoothing_alpha, window_size=CFG.moving_average_window)
    gestures = GestureController(
        pinch_threshold=CFG.pinch_threshold,
        v_shape_threshold=CFG.v_shape_threshold,
        hold_seconds=CFG.gesture_hold_seconds,
        click_cooldown_seconds=CFG.click_cooldown_seconds,
        right_click_cooldown_seconds=CFG.right_click_cooldown_seconds,
        double_click_cooldown_seconds=CFG.double_click_cooldown_seconds,
        window_action_cooldown_seconds=CFG.window_action_cooldown_seconds,
        scroll_gain=CFG.scroll_gain,
        zoom_gain=CFG.zoom_gain,
        gesture_switch_cooldown_seconds=CFG.gesture_switch_cooldown_seconds,
    )

    prev_time = time.time()
    demo_until = prev_time + max(0.0, CFG.gesture_demo_seconds)
    demo_pinned = False

    try:
        while True:
            frame = camera.read()
            if frame is None:
                continue

            hands = hand_tracker.process(frame)
            pointer_hand, gesture_hand, gesture_handedness = select_hands(hands, CFG.pointer_hand)
            pointer_landmarks = pointer_hand[0] if pointer_hand else None
            gesture_landmarks = gesture_hand[0] if gesture_hand else None

            if CFG.draw_hand_landmarks:
                for hand_landmarks, handedness in hands:
                    label = handedness if CFG.draw_hand_handedness else None
                    hand_tracker.draw(frame, hand_landmarks, label, draw_label=CFG.draw_hand_handedness)

            gesture_result = gestures.detect(
                pointer_landmarks,
                gesture_landmarks,
                gesture_handedness=gesture_handedness,
                allow_single_hand=not CFG.require_two_hands_for_gestures,
                allow_pointer_scroll=CFG.allow_pointer_scroll,
                pointer_scroll_requires_gesture_rest=CFG.pointer_scroll_requires_gesture_rest,
            )

            tracking = bool(hands)
            paused = gesture_result["paused"]

            if gesture_result["pen_active"] and not paused:
                pen_x, pen_y = gesture_result["pen_point"]
                target = cursor.map_pen_to_screen(pen_x, pen_y)
                smoothed = smoother.update(target)
                cursor.move_cursor(int(smoothed[0]), int(smoothed[1]))
            else:
                smoother.reset()

            if gesture_result["click"]:
                cursor.left_click()
            if gesture_result["right_click"]:
                cursor.right_click()
            if gesture_result["double_click"]:
                cursor.double_click()
            if gesture_result["minimize_window"]:
                cursor.minimize_window()
            if gesture_result["maximize_window"]:
                cursor.maximize_window()
            if gesture_result["close_window"]:
                cursor.close_window()
            if gesture_result["show_all_windows"]:
                cursor.show_all_windows()
            if gesture_result["drag_down"]:
                cursor.drag_down()
            if gesture_result["drag_up"]:
                cursor.drag_up()
            if gesture_result["scroll_mode"] and abs(gesture_result["scroll_delta"]) > 0:
                cursor.scroll(gesture_result["scroll_delta"])
            if gesture_result["zoom_mode"] and abs(gesture_result["zoom_delta"]) > 0:
                cursor.zoom(gesture_result["zoom_delta"])

            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            draw_status(
                frame,
                fps=fps,
                tracking=tracking,
                gesture=gesture_result["gesture"],
                dragging=gesture_result["dragging"],
                paused=paused,
            )
            if demo_pinned or time.time() <= demo_until:
                draw_gesture_demo(frame)

            cv2.imshow("Touchless Cursor (Pen + Gestures)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            if key in (ord("h"), ord("H")):
                demo_pinned = not demo_pinned

    finally:
        camera.release()
        hand_tracker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
