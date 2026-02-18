# Touchless Cursor (Eye + Hand Gesture)

## Gesture Summary

### Pointer hand
- **Index tip** → move cursor
- **Two fingers** → scroll
- **Open palm** → pause tracking

### Gesture hand — mouse
- **Pinch** → left click
- **Three fingers up** (index + middle + ring) → right click
- **Thumbs up** → double click
- **Fist hold** → drag

### Gesture hand — zoom
- **Two fingers spread** → zoom in
- **Two fingers pinch** → zoom out

### Window control
- **Left Spider gesture** → close window
- **Right Spider gesture** → maximize window
- **Left Thumbs down** → minimize window



### Other
- `ESC` → emergency stop

## Notes
- Cursor mapping and gesture behavior are tuned in `config.py` (hand selection, smoothing, thresholds).
- A gesture demo overlay appears for the first few seconds on startup (`gesture_demo_seconds`), and can be toggled with `H`.

## Setup (Windows PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run
```powershell
python main.py
```

## Note
This project depends on MediaPipe `solutions` API, so `mediapipe==0.10.14` is pinned.
