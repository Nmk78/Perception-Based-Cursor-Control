import time
from typing import Dict, Optional, Tuple

from utils.math_utils import distance_2d


TIP_IDS = {
    "thumb": 4,
    "index": 8,
    "middle": 12,
    "ring": 16,
    "pinky": 20,
}

PIP_IDS = {
    "index": 6,
    "middle": 10,
    "ring": 14,
    "pinky": 18,
}

MCP_IDS = {
    "thumb": 2,
    "index": 5,
    "middle": 9,
    "ring": 13,
    "pinky": 17,
}


class GestureController:
    def __init__(
        self,
        pinch_threshold: float,
        v_shape_threshold: float,
        hold_seconds: float,
        click_cooldown_seconds: float,
        right_click_cooldown_seconds: float,
        double_click_cooldown_seconds: float,
        window_action_cooldown_seconds: float,
        scroll_gain: float,
        zoom_gain: float,
        gesture_switch_cooldown_seconds: float = 0.3,
    ):
        self.pinch_threshold = pinch_threshold
        self.v_shape_threshold = v_shape_threshold
        self.hold_seconds = hold_seconds
        self.click_cooldown_seconds = click_cooldown_seconds
        self.right_click_cooldown_seconds = right_click_cooldown_seconds
        self.double_click_cooldown_seconds = double_click_cooldown_seconds
        self.window_action_cooldown_seconds = window_action_cooldown_seconds
        self.scroll_gain = scroll_gain
        self.zoom_gain = zoom_gain
        self.gesture_switch_cooldown_seconds = gesture_switch_cooldown_seconds

        self._active_gesture: Optional[str] = None
        self._gesture_started_at: float = 0.0
        self._last_left_click_at: float = 0.0
        self._last_right_click_at: float = 0.0
        self._last_double_click_at: float = 0.0
        self._last_minimize_at: float = 0.0
        self._last_maximize_at: float = 0.0
        self._last_close_at: float = 0.0
        self._last_show_all_windows_at: float = 0.0
        self._last_gesture_action_at: float = 0.0

        self._dragging = False
        self._previous_zoom_dist = None  # 3-finger spread/pinch distance
        self._pointer_scroll_started_at: float = 0.0
        self._pointer_scroll_active: bool = False
        self._previous_pointer_scroll_y = None

    @staticmethod
    def _finger_up(hand_landmarks, tip_idx: int, pip_idx: int) -> bool:
        return hand_landmarks.landmark[tip_idx].y < hand_landmarks.landmark[pip_idx].y

    @staticmethod
    def _point(hand_landmarks, idx: int) -> Tuple[float, float]:
        lm = hand_landmarks.landmark[idx]
        return lm.x, lm.y

    def _finger_states(self, hand_landmarks):
        index_up = self._finger_up(hand_landmarks, TIP_IDS["index"], PIP_IDS["index"])
        middle_up = self._finger_up(hand_landmarks, TIP_IDS["middle"], PIP_IDS["middle"])
        ring_up = self._finger_up(hand_landmarks, TIP_IDS["ring"], PIP_IDS["ring"])
        pinky_up = self._finger_up(hand_landmarks, TIP_IDS["pinky"], PIP_IDS["pinky"])
        return index_up, middle_up, ring_up, pinky_up

    def _is_open_palm(self, hand_landmarks) -> bool:
        if hand_landmarks is None:
            return False
        index_up, middle_up, ring_up, pinky_up = self._finger_states(hand_landmarks)
        return (index_up + middle_up + ring_up + pinky_up) >= 4

    def is_open_palm(self, hand_landmarks) -> bool:
        return self._is_open_palm(hand_landmarks)

    def _is_thumb_down(self, hand_landmarks) -> bool:
        """Thumb extended downward (tip below MCP) with all other fingers curled.
        Requires thumb to be extended (not curled in a fist) so we don't confuse fist with thumbs-down.
        """
        if hand_landmarks is None:
            return False
        thumb_tip = hand_landmarks.landmark[TIP_IDS["thumb"]]
        thumb_mcp = hand_landmarks.landmark[MCP_IDS["thumb"]]
        index_up, middle_up, ring_up, pinky_up = self._finger_states(hand_landmarks)
        all_fingers_curled = not index_up and not middle_up and not ring_up and not pinky_up
        if not all_fingers_curled:
            return False
        # Thumb pointing downward: tip below MCP (higher y = lower in frame)
        thumb_down = thumb_tip.y > thumb_mcp.y
        # Thumb must be extended (not curled): tip reasonably far from MCP so we don't treat fist as thumbs-down
        thumb_extended = distance_2d(
            (thumb_tip.x, thumb_tip.y),
            (thumb_mcp.x, thumb_mcp.y),
        ) > 0.06
        return thumb_down and thumb_extended

    def _is_spider(self, hand_landmarks) -> bool:
        """Spider-Man / spidy gesture: index + pinky up, middle + ring curled.

        Uses distance-based checks (tip-to-wrist vs pip-to-wrist) so detection
        is robust even when the hand is tilted or rotated.
        """
        if hand_landmarks is None:
            return False

        lm = hand_landmarks.landmark
        wrist = (lm[0].x, lm[0].y)

        def _ext_ratio(finger: str) -> float:
            """Return tip-to-wrist / pip-to-wrist.  > 1 ⇒ extended, < 1 ⇒ curled."""
            tip = (lm[TIP_IDS[finger]].x, lm[TIP_IDS[finger]].y)
            pip = (lm[PIP_IDS[finger]].x, lm[PIP_IDS[finger]].y)
            d_tip = distance_2d(tip, wrist)
            d_pip = distance_2d(pip, wrist)
            return d_tip / d_pip if d_pip > 1e-6 else 0.0

        idx_r = _ext_ratio("index")
        mid_r = _ext_ratio("middle")
        rng_r = _ext_ratio("ring")
        pnk_r = _ext_ratio("pinky")

        # Index & pinky should be extended (ratio well above 1)
        # Middle & ring should be curled  (ratio below 1)
        extended_thresh = 1.05   # finger clearly extended
        curled_thresh   = 1.0    # finger clearly curled

        index_ext = idx_r > extended_thresh
        pinky_ext = pnk_r > extended_thresh
        middle_cur = mid_r < curled_thresh
        ring_cur   = rng_r < curled_thresh

        return index_ext and pinky_ext and middle_cur and ring_cur

    def _is_ring_pinky_up(self, hand_landmarks) -> bool:
        """Only ring and pinky extended; index and middle curled. Used for maximize.
        Uses wrist-distance ratios (like spider) so it's robust and doesn't conflict with pinch."""
        if hand_landmarks is None:
            return False
        lm = hand_landmarks.landmark
        wrist = (lm[0].x, lm[0].y)

        def _ext_ratio(finger: str) -> float:
            tip = (lm[TIP_IDS[finger]].x, lm[TIP_IDS[finger]].y)
            pip = (lm[PIP_IDS[finger]].x, lm[PIP_IDS[finger]].y)
            d_tip = distance_2d(tip, wrist)
            d_pip = distance_2d(pip, wrist)
            return d_tip / d_pip if d_pip > 1e-6 else 0.0

        extended_thresh = 1.05
        curled_thresh = 1.0
        index_curled = _ext_ratio("index") < curled_thresh
        middle_curled = _ext_ratio("middle") < curled_thresh
        ring_extended = _ext_ratio("ring") > extended_thresh
        pinky_extended = _ext_ratio("pinky") > extended_thresh
        return index_curled and middle_curled and ring_extended and pinky_extended

    # Minimum spread (index-tip to pinky-tip distance) for show-all-windows — keeps gesture distinct.
    SHOW_WINDOWS_SPREAD_MIN = 0.14

    def _is_show_all_windows_gesture(self, hand_landmarks) -> bool:
        """Clean, distinct gesture for show-all-windows: four fingers up, thumb down, fingers spread.
        Avoids confusion with rest/open palm and works in single-hand mode (does not trigger pause)."""
        if hand_landmarks is None:
            return False
        index_up, middle_up, ring_up, pinky_up = self._finger_states(hand_landmarks)
        if not (index_up and middle_up and ring_up and pinky_up):
            return False
        # Thumb must be down (not relaxed open palm)
        thumb_tip = hand_landmarks.landmark[TIP_IDS["thumb"]]
        thumb_mcp = hand_landmarks.landmark[MCP_IDS["thumb"]]
        thumb_down = thumb_tip.y > thumb_mcp.y
        if not thumb_down:
            return False
        # Fingers must be spread apart (deliberate pose, not accidental)
        idx_pt = self._point(hand_landmarks, TIP_IDS["index"])
        pnk_pt = self._point(hand_landmarks, TIP_IDS["pinky"])
        spread = distance_2d(idx_pt, pnk_pt)
        return spread >= self.SHOW_WINDOWS_SPREAD_MIN

    def _is_thumbs_up(self, hand_landmarks) -> bool:
        """Thumbs up: thumb extended upward, all other fingers curled."""
        if hand_landmarks is None:
            return False
        thumb_tip = hand_landmarks.landmark[TIP_IDS["thumb"]]
        thumb_mcp = hand_landmarks.landmark[MCP_IDS["thumb"]]
        index_up, middle_up, ring_up, pinky_up = self._finger_states(hand_landmarks)
        # Thumb pointing upward: tip above MCP (lower y = higher in frame)
        thumb_up = thumb_tip.y < thumb_mcp.y
        all_fingers_curled = not index_up and not middle_up and not ring_up and not pinky_up
        return thumb_up and all_fingers_curled

    def _update_hold_timer(self, gesture: Optional[str], now: float) -> float:
        if gesture != self._active_gesture:
            self._active_gesture = gesture
            self._gesture_started_at = now
        return now - self._gesture_started_at

    def _global_cooldown_ok(self, now: float) -> bool:
        """Returns True if enough time has passed since the last gesture action."""
        return now - self._last_gesture_action_at >= self.gesture_switch_cooldown_seconds

    def _mark_action(self, now: float) -> None:
        """Record that a gesture action just fired."""
        self._last_gesture_action_at = now

    def detect(
        self,
        pointer_landmarks,
        gesture_landmarks,
        gesture_handedness: Optional[str] = None,
        now: Optional[float] = None,
        allow_single_hand: bool = False,
        allow_pointer_scroll: bool = False,
        pointer_scroll_requires_gesture_rest: bool = True,
    ) -> Dict[str, object]:
        now = now if now is not None else time.time()

        result = {
            "gesture": "none",
            "paused": False,
            "pen_active": False,
            "pen_point": None,
            "click": False,
            "right_click": False,
            "double_click": False,
            "drag_down": False,
            "drag_up": False,
            "scroll_mode": False,
            "scroll_delta": 0,
            "zoom_mode": False,
            "zoom_delta": 0,
            "dragging": self._dragging,
            "gesture_resting": False,
            "minimize_window": False,
            "maximize_window": False,
            "close_window": False,
            "show_all_windows": False,
        }

        if pointer_landmarks is None and gesture_landmarks is None:
            held = self._update_hold_timer(None, now)
            _ = held
            if self._dragging:
                result["drag_up"] = True
                self._dragging = False
            self._previous_zoom_dist = None
            self._pointer_scroll_active = False
            self._previous_pointer_scroll_y = None
            result["dragging"] = self._dragging
            return result

        # Two-hand gesture: both hands in "show all windows" pose (four fingers spread, thumb down)
        both_hands_show_windows = (
            pointer_landmarks is not None
            and gesture_landmarks is not None
            and self._is_show_all_windows_gesture(pointer_landmarks)
            and self._is_show_all_windows_gesture(gesture_landmarks)
        )

        # Don't pause when both hands are doing show-all-windows
        result["paused"] = (
            self._is_open_palm(pointer_landmarks)
            and not both_hands_show_windows
        )
        if result["paused"]:
            if self._dragging:
                result["drag_up"] = True
                self._dragging = False
            result["gesture"] = "paused"
            result["dragging"] = self._dragging
            self._previous_zoom_dist = None
            self._pointer_scroll_active = False
            self._previous_pointer_scroll_y = None
            return result

        if gesture_landmarks is not None and self._is_open_palm(gesture_landmarks) and not both_hands_show_windows:
            result["gesture_resting"] = True

        gesture_source = gesture_landmarks
        if (gesture_source is None or result["gesture_resting"]) and allow_single_hand:
            gesture_source = pointer_landmarks
        if gesture_source is None:
            held = self._update_hold_timer(None, now)
            _ = held
            if self._dragging:
                result["drag_up"] = True
                self._dragging = False
            result["dragging"] = self._dragging
            gesture_source = None

        if gesture_source is not None:
            index_up, middle_up, ring_up, pinky_up = self._finger_states(gesture_source)
            fingers_up_count = index_up + middle_up + ring_up + pinky_up

            thumb = self._point(gesture_source, TIP_IDS["thumb"])
            index = self._point(gesture_source, TIP_IDS["index"])

            pinch_index = distance_2d(thumb, index) < self.pinch_threshold
            thumbs_up = self._is_thumbs_up(gesture_source)
            spider = self._is_spider(gesture_source)
            thumb_down = self._is_thumb_down(gesture_source)
            ring_pinky_up = self._is_ring_pinky_up(gesture_source)

            three_fingers = index_up and middle_up and ring_up and not pinky_up
            two_fingers = index_up and middle_up and not ring_up and not pinky_up

            # Determine the gesture handedness label (normalized)
            g_hand = (gesture_handedness or "").strip().lower()

            # --- Classify raw gesture (single-hand). Show-all-windows is two-hand only. ---
            # Gesture hand is always the non-pointer hand (e.g. left when pointer=Right), so all gestures are same hand.
            raw_gesture = "none"
            if both_hands_show_windows:
                raw_gesture = "two_hands_show_windows"
            elif fingers_up_count <= 1 and not thumb_down and not thumbs_up:
                raw_gesture = "fist"
            elif thumb_down:
                raw_gesture = "thumbs_down"
            elif thumbs_up:
                raw_gesture = "thumbs_up"
            elif spider:
                raw_gesture = "spider"
            elif ring_pinky_up:
                raw_gesture = "ring_pinky_up"
            elif pinch_index and not ring_pinky_up:
                raw_gesture = "pinch"
            elif three_fingers and not pinch_index:
                raw_gesture = "three_fingers"
            elif two_fingers and not pinch_index:
                raw_gesture = "two_fingers"
            elif fingers_up_count >= 4:
                raw_gesture = "open_palm"

            held_for = self._update_hold_timer(raw_gesture, now)
            stable = held_for >= self.hold_seconds

            # --- Map raw gesture to action label ---
            # Two fingers = right click; three fingers = zoom (spread/pinch)
            gesture_label = raw_gesture
            if raw_gesture == "pinch":
                gesture_label = "left_click"
            elif raw_gesture == "two_fingers":
                gesture_label = "right_click"
            elif raw_gesture == "three_fingers":
                gesture_label = "zoom"
            elif raw_gesture == "thumbs_up":
                gesture_label = "double_click"
            elif raw_gesture == "spider":
                gesture_label = "close"
            elif raw_gesture == "thumbs_down":
                gesture_label = "minimize"
            elif raw_gesture == "ring_pinky_up":
                gesture_label = "maximize"
            elif raw_gesture == "two_hands_show_windows":
                gesture_label = "show_all_windows"
            elif raw_gesture == "open_palm":
                gesture_label = "rest"
            result["gesture"] = gesture_label

            # --- Fire actions (with hold + cooldown) ---

            # Left click: pinch
            if raw_gesture == "pinch" and stable and self._global_cooldown_ok(now):
                if now - self._last_left_click_at >= self.click_cooldown_seconds:
                    result["click"] = True
                    self._last_left_click_at = now
                    self._mark_action(now)

            # Right click: two fingers (index + middle)
            if raw_gesture == "two_fingers" and stable and self._global_cooldown_ok(now):
                if now - self._last_right_click_at >= self.right_click_cooldown_seconds:
                    result["right_click"] = True
                    self._last_right_click_at = now
                    self._mark_action(now)

            # Double click: thumbs up
            if raw_gesture == "thumbs_up" and stable and self._global_cooldown_ok(now):
                if now - self._last_double_click_at >= self.double_click_cooldown_seconds:
                    result["double_click"] = True
                    self._last_double_click_at = now
                    self._mark_action(now)

            # Window control (gesture hand only — e.g. left when pointer=Right)
            if raw_gesture == "spider" and stable and self._global_cooldown_ok(now):
                if now - self._last_close_at >= self.window_action_cooldown_seconds:
                    result["close_window"] = True
                    self._last_close_at = now
                    self._mark_action(now)

            if raw_gesture == "thumbs_down" and stable and self._global_cooldown_ok(now):
                if now - self._last_minimize_at >= self.window_action_cooldown_seconds:
                    result["minimize_window"] = True
                    self._last_minimize_at = now
                    self._mark_action(now)

            if raw_gesture == "ring_pinky_up" and stable and self._global_cooldown_ok(now):
                if now - self._last_maximize_at >= self.window_action_cooldown_seconds:
                    result["maximize_window"] = True
                    self._last_maximize_at = now
                    self._mark_action(now)

            # Drag: fist hold
            if raw_gesture == "fist" and stable:
                if not self._dragging:
                    result["drag_down"] = True
                    self._dragging = True

            if self._dragging and raw_gesture != "fist":
                result["drag_up"] = True
                self._dragging = False

            # Zoom: three fingers (index + middle + ring) — spread = zoom in, pinch = zoom out
            if raw_gesture == "three_fingers":
                result["zoom_mode"] = True
                idx_pt = self._point(gesture_source, TIP_IDS["index"])
                mid_pt = self._point(gesture_source, TIP_IDS["middle"])
                rng_pt = self._point(gesture_source, TIP_IDS["ring"])
                # Use sum of adjacent finger distances as spread measure
                tip_dist = distance_2d(idx_pt, mid_pt) + distance_2d(mid_pt, rng_pt)

                if self._previous_zoom_dist is not None:
                    # delta > 0 => spreading => zoom in; delta < 0 => pinch => zoom out
                    delta = tip_dist - self._previous_zoom_dist
                    result["zoom_delta"] = int(delta * self.zoom_gain * 100)

                self._previous_zoom_dist = tip_dist
            else:
                self._previous_zoom_dist = None

            # Show all windows: two-hand gesture only (both hands: four fingers spread, thumb down)
            if raw_gesture == "two_hands_show_windows" and stable and self._global_cooldown_ok(now):
                if now - self._last_show_all_windows_at >= self.window_action_cooldown_seconds:
                    result["show_all_windows"] = True
                    self._last_show_all_windows_at = now
                    self._mark_action(now)

        if allow_pointer_scroll and pointer_landmarks is not None:
            if pointer_scroll_requires_gesture_rest and gesture_landmarks is not None and not result["gesture_resting"]:
                self._pointer_scroll_active = False
                self._previous_pointer_scroll_y = None
            else:
                p_index_up, p_middle_up, p_ring_up, p_pinky_up = self._finger_states(pointer_landmarks)
                pointer_two_fingers = p_index_up and p_middle_up and not p_ring_up and not p_pinky_up
                if pointer_two_fingers:
                    if not self._pointer_scroll_active:
                        self._pointer_scroll_active = True
                        self._pointer_scroll_started_at = now
                    if now - self._pointer_scroll_started_at >= self.hold_seconds:
                        result["scroll_mode"] = True
                        index_y = pointer_landmarks.landmark[TIP_IDS["index"]].y
                        if self._previous_pointer_scroll_y is not None:
                            delta = self._previous_pointer_scroll_y - index_y
                            result["scroll_delta"] = int(delta * self.scroll_gain * 100)
                        self._previous_pointer_scroll_y = index_y
                else:
                    self._pointer_scroll_active = False
                    self._previous_pointer_scroll_y = None

        if (
            pointer_landmarks is not None
            and not result["scroll_mode"]
            and not result["zoom_mode"]
            and not result["paused"]
        ):
            result["pen_active"] = True
            result["pen_point"] = self._point(pointer_landmarks, TIP_IDS["index"])

        result["dragging"] = self._dragging
        return result
