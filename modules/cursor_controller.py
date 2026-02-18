import pyautogui

from utils.math_utils import clamp


class CursorController:
    def __init__(
        self,
        sensitivity_x: float,
        sensitivity_y: float,
        invert_x: bool = False,
        invert_y: bool = False,
        max_cursor_step_px: int = 50,
        pen_active_margin_x: float = 0.15,
        pen_active_margin_y: float = 0.18,
    ):
        pyautogui.FAILSAFE = False
        self.screen_width, self.screen_height = pyautogui.size()
        self.sensitivity_x = sensitivity_x
        self.sensitivity_y = sensitivity_y
        self.invert_x = invert_x
        self.invert_y = invert_y
        self.max_cursor_step_px = max_cursor_step_px
        self.pen_active_margin_x = pen_active_margin_x
        self.pen_active_margin_y = pen_active_margin_y

    def map_pen_to_screen(self, pen_x: float, pen_y: float):
        active_min_x = self.pen_active_margin_x
        active_max_x = 1.0 - self.pen_active_margin_x
        active_min_y = self.pen_active_margin_y
        active_max_y = 1.0 - self.pen_active_margin_y

        if active_max_x <= active_min_x:
            active_min_x, active_max_x = 0.0, 1.0
        if active_max_y <= active_min_y:
            active_min_y, active_max_y = 0.0, 1.0

        nx = clamp((pen_x - active_min_x) / (active_max_x - active_min_x), 0.0, 1.0)
        ny = clamp((pen_y - active_min_y) / (active_max_y - active_min_y), 0.0, 1.0)

        if self.invert_x:
            nx = 1.0 - nx
        if self.invert_y:
            ny = 1.0 - ny

        nx = clamp(0.5 + (nx - 0.5) * self.sensitivity_x, 0.0, 1.0)
        ny = clamp(0.5 + (ny - 0.5) * self.sensitivity_y, 0.0, 1.0)

        screen_x = int(nx * self.screen_width)
        screen_y = int(ny * self.screen_height)
        return screen_x, screen_y

    def move_cursor(self, x: int, y: int) -> None:
        cx, cy = pyautogui.position()
        dx = int(clamp(x - cx, -self.max_cursor_step_px, self.max_cursor_step_px))
        dy = int(clamp(y - cy, -self.max_cursor_step_px, self.max_cursor_step_px))
        pyautogui.moveTo(cx + dx, cy + dy, _pause=False)

    def left_click(self) -> None:
        pyautogui.click(_pause=False)

    def right_click(self) -> None:
        pyautogui.click(button="right", _pause=False)

    def double_click(self) -> None:
        pyautogui.doubleClick(_pause=False)

    def drag_down(self) -> None:
        pyautogui.mouseDown(button="left", _pause=False)

    def drag_up(self) -> None:
        pyautogui.mouseUp(button="left", _pause=False)

    def scroll(self, amount: int) -> None:
        pyautogui.scroll(amount, _pause=False)

    def zoom(self, amount: int) -> None:
        if amount == 0:
            return
        pyautogui.keyDown("ctrl", _pause=False)
        pyautogui.scroll(amount, _pause=False)
        pyautogui.keyUp("ctrl", _pause=False)

    def minimize_window(self) -> None:
        pyautogui.hotkey("win", "down", _pause=False)
        pyautogui.hotkey("win", "down", _pause=False)

    def maximize_window(self) -> None:
        pyautogui.hotkey("win", "up", _pause=False)

    def close_window(self) -> None:
        pyautogui.hotkey("alt", "f4", _pause=False)

    def show_all_windows(self) -> None:
        """Show task view / all open windows (Win+Tab on Windows)."""
        pyautogui.hotkey("win", "tab", _pause=False)
