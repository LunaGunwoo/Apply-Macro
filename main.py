from __future__ import annotations

import queue
import tkinter as tk
from collections import deque
from collections.abc import Callable
from datetime import datetime

import keyboard
import pyautogui

from popup_hacker import ConnectionState, EventKind, MonitorEvent, PopupMonitor

Point = pyautogui.Point

# Windows Set 1 scan codes keep the shortcuts tied to the physical F keys.
FUNCTION_KEY_SCAN_CODES = {
    1: 59,
    2: 60,
    3: 61,
    4: 62,
    5: 63,
    6: 64,
    7: 65,
    8: 66,
    9: 67,
    10: 68,
    11: 87,
}
COURSE_KEYS = frozenset(range(1, 11))
ENROLLMENT_KEY = 11
KEY_QUEUE_POLL_MS = 10
MOUSE_ACTION_PAUSE_SECONDS = 0.01

pyautogui.PAUSE = MOUSE_ACTION_PAUSE_SECONDS


class ApplyMacroApp:
    LOG_LIMIT = 100

    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        self.window.title("Apply Macro")
        self.window.geometry("900x680")
        self.window.minsize(900, 680)

        self.default_font = ("Helvetica", 14, "bold")
        self.colors = {True: "skyblue", False: "pink"}
        self.positions: dict[int, Point] = {}
        self.position_labels: dict[int, tk.Label] = {}
        self.is_set_mode = True
        self.is_closing = False
        self.keyboard_hooks: list[Callable[[], None]] = []
        self.pressed_function_keys: set[int] = set()

        self.monitor_events: queue.Queue[MonitorEvent] = queue.Queue()
        self.key_events: queue.Queue[int] = queue.Queue()
        self.log_lines: deque[tuple[str, EventKind]] = deque(maxlen=self.LOG_LIMIT)

        self.is_click_enrollment_after = tk.BooleanVar(value=False)
        self.is_auth_enabled = tk.BooleanVar(value=True)
        self.is_warning_enabled = tk.BooleanVar(value=True)

        self._build_ui()

        self.popup_monitor = PopupMonitor(self.monitor_events.put)
        self.popup_monitor.start()

        self._register_mouse_hotkeys()

        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.after(100, self._update_mouse_position)
        self.window.after(KEY_QUEUE_POLL_MS, self._drain_queues)

    def _build_ui(self) -> None:
        option_frame = tk.Frame(self.window)
        option_frame.pack(side="top", fill="x", padx=10, pady=(10, 5))

        self.mode_label = tk.Label(
            option_frame,
            text="설정 모드 켜짐",
            bg=self.colors[self.is_set_mode],
            font=self.default_font,
        )
        self.mode_label.grid(row=0, column=0, sticky="w")

        self.mode_button = tk.Button(
            option_frame,
            text="끄기",
            font=self.default_font,
            command=self._change_set_mode,
        )
        self.mode_button.grid(row=0, column=1, padx=5)

        self.mouse_label = tk.Label(
            option_frame,
            text="마우스 위치: (0, 0)",
            font=self.default_font,
        )
        self.mouse_label.grid(row=0, column=2, padx=5)

        click_enrollment_checkbox = tk.Checkbutton(
            option_frame,
            text="F1~F10 과목 클릭 후 F11 수강신청 클릭",
            font=self.default_font,
            variable=self.is_click_enrollment_after,
        )
        click_enrollment_checkbox.grid(row=0, column=3, padx=10, sticky="w")

        monitor_frame = tk.LabelFrame(
            self.window,
            text="팝업 자동 처리",
            font=self.default_font,
            padx=10,
            pady=8,
        )
        monitor_frame.pack(fill="x", padx=10, pady=5)

        auth_checkbox = tk.Checkbutton(
            monitor_frame,
            text="인증번호 자동 입력",
            font=self.default_font,
            variable=self.is_auth_enabled,
            command=self._toggle_auth_monitor,
        )
        auth_checkbox.grid(row=0, column=0, padx=(0, 15), sticky="w")

        warning_checkbox = tk.Checkbutton(
            monitor_frame,
            text="만석 경고 자동 닫기",
            font=self.default_font,
            variable=self.is_warning_enabled,
            command=self._toggle_warning_monitor,
        )
        warning_checkbox.grid(row=0, column=1, padx=(0, 15), sticky="w")

        self.connection_label = tk.Label(
            monitor_frame,
            text="MDmain.exe 연결 대기 중",
            bg="#ffd966",
            font=self.default_font,
            padx=8,
            pady=3,
        )
        self.connection_label.grid(row=0, column=2, sticky="w")

        content_frame = tk.Frame(self.window)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)

        position_frame = tk.LabelFrame(
            content_frame,
            text="마우스 위치 (F1~F11)",
            font=self.default_font,
            padx=8,
            pady=6,
        )
        position_frame.pack(side="left", fill="y")

        for key in FUNCTION_KEY_SCAN_CODES:
            position_name = self._position_name(key)
            label = tk.Label(
                position_frame,
                text=f"{position_name}: 할당되지 않음",
                bg=self.colors[False],
                font=self.default_font,
                width=36,
                anchor="w",
            )
            label.pack(anchor="w", pady=2)
            self.position_labels[key] = label

        log_frame = tk.LabelFrame(
            content_frame,
            text="최근 처리 내역",
            font=self.default_font,
            padx=8,
            pady=6,
        )
        log_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_frame,
            state="disabled",
            wrap="word",
            font=("Malgun Gothic", 10),
            yscrollcommand=scrollbar.set,
        )
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_configure("connection", foreground="#1f4e79")
        self.log_text.tag_configure("action", foreground="#38761d")
        self.log_text.tag_configure("error", foreground="#cc0000")

    def _change_set_mode(self) -> None:
        self.is_set_mode = not self.is_set_mode
        self.mode_label.config(
            bg=self.colors[self.is_set_mode],
            text=f"설정 모드 {'켜짐' if self.is_set_mode else '꺼짐'}",
        )
        self.mode_button.config(text="끄기" if self.is_set_mode else "켜기")

    def _toggle_auth_monitor(self) -> None:
        enabled = self.is_auth_enabled.get()
        self.popup_monitor.set_auth_enabled(enabled)
        self._append_log(
            f"인증번호 자동 입력 {'켜짐' if enabled else '꺼짐'}",
            EventKind.ACTION,
        )

    def _toggle_warning_monitor(self) -> None:
        enabled = self.is_warning_enabled.get()
        self.popup_monitor.set_warning_enabled(enabled)
        self._append_log(
            f"만석 경고 자동 닫기 {'켜짐' if enabled else '꺼짐'}",
            EventKind.ACTION,
        )

    def _update_mouse_position(self) -> None:
        if self.is_closing:
            return
        try:
            x, y = pyautogui.position()
            self.mouse_label.config(text=f"마우스 위치: ({x}, {y})")
        except pyautogui.FailSafeException:
            self._append_log("PyAutoGUI 안전장치가 작동했습니다.", EventKind.ERROR)
            self.close()
            return
        self.window.after(100, self._update_mouse_position)

    def _register_mouse_hotkeys(self) -> None:
        try:
            for key, scan_code in FUNCTION_KEY_SCAN_CODES.items():
                remove_hook = keyboard.hook_key(
                    scan_code,
                    lambda event, key=key: self._handle_function_key_event(
                        key, event
                    ),
                    # Reserve F1-F11 while the app is running so their normal
                    # Help/Refresh/Menu actions do not fire as well.
                    suppress=True,
                )
                self.keyboard_hooks.append(remove_hook)
        except Exception as exc:  # noqa: BLE001 - keyboard exposes OS-specific failures
            self._unregister_mouse_hotkeys()
            self._append_log(f"전역 단축키 등록 오류: {exc}", EventKind.ERROR)

    def _unregister_mouse_hotkeys(self) -> None:
        for remove_hook in self.keyboard_hooks:
            try:
                remove_hook()
            except Exception:  # noqa: BLE001, S110 - cleanup must continue
                pass
        self.keyboard_hooks.clear()
        self.pressed_function_keys.clear()

    def _handle_function_key_event(
        self, key: int, event: keyboard.KeyboardEvent
    ) -> bool:
        if event.event_type == keyboard.KEY_UP:
            self.pressed_function_keys.discard(key)
        elif (
            event.event_type == keyboard.KEY_DOWN
            and key not in self.pressed_function_keys
        ):
            self.pressed_function_keys.add(key)
            self._queue_shortcut(key)
        return False

    def _queue_shortcut(self, key: int) -> None:
        if self.is_closing:
            return
        self.key_events.put(key)

    def _drain_queues(self) -> None:
        if self.is_closing:
            return

        if not self.popup_monitor.input_in_progress:
            while True:
                try:
                    key = self.key_events.get_nowait()
                except queue.Empty:
                    break
                self._handle_shortcut(key)

        while True:
            try:
                event = self.monitor_events.get_nowait()
            except queue.Empty:
                break
            self._handle_monitor_event(event)

        self.window.after(KEY_QUEUE_POLL_MS, self._drain_queues)

    @staticmethod
    def _position_name(key: int) -> str:
        if key == ENROLLMENT_KEY:
            return "F11 수강신청"
        return f"F{key} 과목 {key}"

    def _handle_shortcut(self, key: int) -> None:
        position_name = self._position_name(key)
        if self.is_set_mode:
            point = pyautogui.position()
            self.positions[key] = point
            self.position_labels[key].config(
                bg=self.colors[True],
                text=f"{position_name}: ({point.x}, {point.y})로 할당됨",
            )
            return

        if key not in self.positions:
            self._append_log(
                f"클릭 실패: {position_name} 위치가 할당되지 않았습니다.",
                EventKind.ERROR,
            )
            return

        try:
            pyautogui.click(x=self.positions[key].x, y=self.positions[key].y)

            if self.is_click_enrollment_after.get() and key in COURSE_KEYS:
                if ENROLLMENT_KEY not in self.positions:
                    self._append_log(
                        "클릭 실패: F11 수강신청 위치가 할당되지 않았습니다.",
                        EventKind.ERROR,
                    )
                    return
                enrollment_point = self.positions[ENROLLMENT_KEY]
                pyautogui.click(x=enrollment_point.x, y=enrollment_point.y)
                self._append_log(
                    f"F{key} 과목 클릭 후 F11 수강신청 클릭 완료",
                    EventKind.ACTION,
                )
        except pyautogui.PyAutoGUIException as exc:
            self._append_log(f"마우스 클릭 오류: {exc}", EventKind.ERROR)

    def _handle_monitor_event(self, event: MonitorEvent) -> None:
        if event.connection_state is not None:
            color_by_state = {
                ConnectionState.WAITING: "#ffd966",
                ConnectionState.CONNECTED: "#93c47d",
                ConnectionState.DISCONNECTED: "#e06666",
            }
            self.connection_label.config(
                text=event.message,
                bg=color_by_state[event.connection_state],
            )
        self._append_log(event.message, event.kind, event.timestamp)

    def _append_log(
        self,
        message: str,
        kind: EventKind,
        timestamp: datetime | None = None,
    ) -> None:
        occurred_at = timestamp or datetime.now().astimezone()
        line = f"[{occurred_at:%H:%M:%S}] {message}\n"
        self.log_lines.append((line, kind))

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        for log_line, log_kind in self.log_lines:
            self.log_text.insert("end", log_line, log_kind.value)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def close(self) -> None:
        if self.is_closing:
            return
        self.is_closing = True

        self._unregister_mouse_hotkeys()

        self.popup_monitor.stop(timeout=2.0)
        self.window.destroy()

    def run(self) -> None:
        self.window.mainloop()


def main() -> None:
    window = tk.Tk()
    app = ApplyMacroApp(window)
    app.run()


if __name__ == "__main__":
    main()
