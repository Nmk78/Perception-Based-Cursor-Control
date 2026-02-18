import cv2

try:
    import mediapipe as mp
except Exception as exc:
    raise RuntimeError("MediaPipe is not installed correctly.") from exc


def _get_hands_module():
    if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
        return mp.solutions.hands
    raise RuntimeError(
        "This project requires MediaPipe Solutions API (mp.solutions.hands). "
        "Install a compatible version: pip install mediapipe==0.10.14"
    )


class HandTracker:
    def __init__(self, min_detection_confidence: float, min_tracking_confidence: float, max_hands: int = 1):
        self._mp_hands = _get_hands_module()
        self._mp_drawing = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            model_complexity=0,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)
        if not result.multi_hand_landmarks:
            return []

        hands = []
        for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            handedness = None
            if result.multi_handedness and idx < len(result.multi_handedness):
                handedness = result.multi_handedness[idx].classification[0].label
            hands.append((hand_landmarks, handedness))
        return hands

    def draw(self, frame_bgr, hand_landmarks, handedness: str = None, draw_label: bool = False) -> None:
        self._mp_drawing.draw_landmarks(
            frame_bgr,
            hand_landmarks,
            self._mp_hands.HAND_CONNECTIONS,
            self._mp_styles.get_default_hand_landmarks_style(),
            self._mp_styles.get_default_hand_connections_style(),
        )

        if draw_label and handedness:
            h, w = frame_bgr.shape[:2]
            wrist = hand_landmarks.landmark[0]
            x = int(wrist.x * w) - 10
            y = int(wrist.y * h) - 10
            cv2.putText(frame_bgr, handedness, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def close(self) -> None:
        self._hands.close()
