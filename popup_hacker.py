from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import win32api
from pywinauto import Application, Desktop, findwindows


class EventKind(StrEnum):
    CONNECTION = "connection"
    ACTION = "action"
    ERROR = "error"


class ConnectionState(StrEnum):
    WAITING = "waiting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


@dataclass(frozen=True, slots=True)
class MonitorEvent:
    kind: EventKind
    message: str
    timestamp: datetime
    connection_state: ConnectionState | None = None


class PopupMonitor:
    """Monitor the enrollment application without touching Tk widgets."""

    def __init__(
        self,
        event_sink: Callable[[MonitorEvent], None],
        *,
        process_name: str = "MDmain.exe",
        auth_popup_title: str = "대학 수강신청(과부하방지)",
        warning_popup_title: str = "수강신청",
        search_interval: float = 0.05,
        connection_check_interval: float = 0.25,
        reconnect_interval: float = 1.0,
        connect_timeout: float = 0.25,
        error_log_interval: float = 5.0,
    ) -> None:
        self._event_sink = event_sink
        self.process_name = process_name
        self.auth_popup_title = auth_popup_title
        self.warning_popup_title = warning_popup_title
        self.search_interval = search_interval
        self.connection_check_interval = connection_check_interval
        self.reconnect_interval = reconnect_interval
        self.connect_timeout = connect_timeout
        self.error_log_interval = error_log_interval

        self._auth_enabled = threading.Event()
        self._warning_enabled = threading.Event()
        self._auth_enabled.set()
        self._warning_enabled.set()

        self._stop_event = threading.Event()
        self._input_in_progress = threading.Event()
        self._thread: threading.Thread | None = None
        self._application: Application | None = None
        self._connection_state: ConnectionState | None = None
        self._last_error_at: dict[str, float] = {}

    @property
    def input_in_progress(self) -> bool:
        """Whether authentication digits are currently being injected."""
        return self._input_in_progress.is_set()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="popup-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def set_auth_enabled(self, enabled: bool) -> None:
        self._set_feature(self._auth_enabled, enabled)

    def set_warning_enabled(self, enabled: bool) -> None:
        self._set_feature(self._warning_enabled, enabled)

    @staticmethod
    def _set_feature(feature_event: threading.Event, enabled: bool) -> None:
        if enabled:
            feature_event.set()
        else:
            feature_event.clear()

    def _emit(
        self,
        kind: EventKind,
        message: str,
        connection_state: ConnectionState | None = None,
    ) -> None:
        self._event_sink(
            MonitorEvent(
                kind=kind,
                message=message,
                timestamp=datetime.now().astimezone(),
                connection_state=connection_state,
            )
        )

    def _emit_error(self, key: str, message: str) -> None:
        now = time.monotonic()
        last_emitted = self._last_error_at.get(key, float("-inf"))
        if now - last_emitted < self.error_log_interval:
            return
        self._last_error_at[key] = now
        self._emit(EventKind.ERROR, message)

    def _set_connection_state(
        self,
        state: ConnectionState,
        message: str,
    ) -> None:
        if state == self._connection_state:
            return
        self._connection_state = state
        self._emit(EventKind.CONNECTION, message, state)

    def _run(self) -> None:
        self._set_connection_state(
            ConnectionState.WAITING,
            f"{self.process_name} 연결 대기 중",
        )
        next_reconnect_at = 0.0
        next_connection_check_at = 0.0

        while not self._stop_event.is_set():
            now = time.monotonic()

            if self._application is None:
                if now >= next_reconnect_at:
                    self._try_connect()
                    next_reconnect_at = now + self.reconnect_interval
                    next_connection_check_at = now + self.connection_check_interval
                self._stop_event.wait(self.search_interval)
                continue

            if now >= next_connection_check_at:
                next_connection_check_at = now + self.connection_check_interval
                if not self._is_process_running():
                    self._application = None
                    self._set_connection_state(
                        ConnectionState.DISCONNECTED,
                        f"{self.process_name} 연결 끊김 — 재연결 중",
                    )
                    next_reconnect_at = now
                    continue

            if self._auth_enabled.is_set():
                self._handle_auth_popup()
            if self._warning_enabled.is_set():
                self._handle_warning_popups()

            self._stop_event.wait(self.search_interval)

    def _try_connect(self) -> None:
        try:
            application = Application(backend="win32").connect(
                path=self.process_name,
                timeout=self.connect_timeout,
            )
        except Exception:  # noqa: BLE001 - pywinauto raises backend-specific errors
            return

        self._application = application
        process_id = getattr(application, "process", None)
        process_suffix = f" (PID {process_id})" if process_id is not None else ""
        self._set_connection_state(
            ConnectionState.CONNECTED,
            f"{self.process_name} 연결됨{process_suffix}",
        )

    def _is_process_running(self) -> bool:
        if self._application is None:
            return False
        try:
            return bool(self._application.is_process_running())
        except Exception:  # noqa: BLE001 - a dead process can invalidate any wrapper call
            return False

    @contextmanager
    def _preserve_cursor_position(self) -> Iterator[None]:
        original_position = win32api.GetCursorPos()
        try:
            yield
        finally:
            try:
                win32api.SetCursorPos(original_position)
            except Exception as exc:  # noqa: BLE001 - cursor restoration is best effort
                self._emit_error(
                    "cursor-restore-error",
                    f"마우스 위치 복원 오류: {exc}",
                )

    def _handle_auth_popup(self) -> None:
        try:
            auth_windows = findwindows.find_windows(title=self.auth_popup_title)
            if not auth_windows:
                return

            self._input_in_progress.set()
            try:
                with self._preserve_cursor_position():
                    popup_window = Desktop(backend="win32").window(
                        handle=auth_windows[0]
                    )
                    popup_window.set_focus()
                    auth_label = popup_window.child_window(auto_id="Label")
                    match = re.search(r"\[(\d+)\]", auth_label.window_text())

                    if match is None:
                        self._emit_error(
                            "auth-code-missing",
                            "인증번호 팝업에서 숫자를 찾지 못했습니다.",
                        )
                        return

                    auth_code = match.group(1)
                    edit_box = popup_window.child_window(auto_id="TextBox")
                    ok_button = popup_window.child_window(
                        title="OK",
                        auto_id="OKButton",
                    )

                    edit_box.type_keys(auth_code, with_spaces=False)
                    ok_button.click()
                    self._stop_event.wait(0.05)
            finally:
                self._input_in_progress.clear()

            self._emit(EventKind.ACTION, f"인증번호 [{auth_code}] 입력 완료")
        except Exception as exc:  # noqa: BLE001 - keep monitoring after malformed popups
            self._emit_error(
                "auth-popup-error",
                f"인증번호 팝업 처리 오류: {exc}",
            )

    def _handle_warning_popups(self) -> None:
        try:
            dialog_handles = findwindows.find_windows(
                title=self.warning_popup_title,
                class_name="#32770",
            )
            for handle in dialog_handles:
                win = Desktop(backend="win32").window(handle=handle)
                try:
                    static = win.child_window(
                        class_name="Static",
                        title="이 과목은 만석입니다",
                    )
                    if not static.exists():
                        continue

                    ok_button = win.child_window(class_name="Button", title="OK")
                    ok_button.click()
                    self._emit(EventKind.ACTION, "만석 경고 팝업 닫기 완료")
                    self._stop_event.wait(0.05)
                    return
                except Exception:  # noqa: BLE001, S112 - inspect the next matching dialog
                    continue
        except Exception as exc:  # noqa: BLE001 - keep monitoring after backend failures
            self._emit_error(
                "warning-popup-error",
                f"만석 경고 팝업 처리 오류: {exc}",
            )
