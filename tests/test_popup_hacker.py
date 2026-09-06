from __future__ import annotations

import threading
import time

import popup_hacker
from popup_hacker import ConnectionState, EventKind, MonitorEvent, PopupMonitor


class FakeApplication:
    available = False
    process = 4321

    def __init__(self, backend: str) -> None:
        assert backend == "win32"

    def connect(self, *, path: str, timeout: float) -> FakeApplication:
        assert path == "MDmain.exe"
        assert timeout >= 0
        if not self.available:
            raise RuntimeError("process is not running")
        return self

    def is_process_running(self) -> bool:
        return self.available


def wait_until(predicate, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("condition was not met before timeout")


def make_monitor(events: list[MonitorEvent]) -> PopupMonitor:
    return PopupMonitor(
        events.append,
        search_interval=0.005,
        connection_check_interval=0.01,
        reconnect_interval=0.01,
        connect_timeout=0,
        error_log_interval=0.02,
    )


def test_default_popup_search_interval_is_low_latency() -> None:
    monitor = PopupMonitor(lambda event: None)

    assert monitor.search_interval == 0.01


def test_reconnects_and_reports_connection_transitions(monkeypatch) -> None:
    FakeApplication.available = False
    monkeypatch.setattr(popup_hacker, "Application", FakeApplication)
    events: list[MonitorEvent] = []
    monitor = make_monitor(events)

    monitor.start()
    try:
        wait_until(
            lambda: any(
                event.connection_state == ConnectionState.WAITING for event in events
            )
        )

        FakeApplication.available = True
        wait_until(
            lambda: any(
                event.connection_state == ConnectionState.CONNECTED for event in events
            )
        )
        connected_event = next(
            event
            for event in events
            if event.connection_state == ConnectionState.CONNECTED
        )
        assert "PID 4321" in connected_event.message

        FakeApplication.available = False
        wait_until(
            lambda: any(
                event.connection_state == ConnectionState.DISCONNECTED
                for event in events
            )
        )

        FakeApplication.available = True
        wait_until(
            lambda: sum(
                event.connection_state == ConnectionState.CONNECTED
                for event in events
            )
            == 2
        )
    finally:
        monitor.stop()
        FakeApplication.available = False


def test_feature_switches_are_independent(monkeypatch) -> None:
    FakeApplication.available = True
    monkeypatch.setattr(popup_hacker, "Application", FakeApplication)
    events: list[MonitorEvent] = []
    monitor = make_monitor(events)
    auth_called = threading.Event()
    warning_called = threading.Event()

    monkeypatch.setattr(monitor, "_handle_auth_popup", auth_called.set)
    monkeypatch.setattr(monitor, "_handle_warning_popups", warning_called.set)

    monitor.set_auth_enabled(False)
    monitor.start()
    try:
        wait_until(warning_called.is_set)
        assert not auth_called.is_set()

        warning_called.clear()
        monitor.set_warning_enabled(False)
        monitor.set_auth_enabled(True)
        wait_until(auth_called.is_set)
        time.sleep(0.03)
        assert not warning_called.is_set()
    finally:
        monitor.stop()
        FakeApplication.available = False


def test_duplicate_errors_are_throttled() -> None:
    events: list[MonitorEvent] = []
    monitor = make_monitor(events)

    monitor._emit_error("same-error", "첫 오류")
    monitor._emit_error("same-error", "반복 오류")

    assert [(event.kind, event.message) for event in events] == [
        (EventKind.ERROR, "첫 오류")
    ]

    time.sleep(0.03)
    monitor._emit_error("same-error", "다시 표시되는 오류")
    assert events[-1].message == "다시 표시되는 오류"


def test_auth_popup_restores_cursor_position(monkeypatch) -> None:
    cursor_position = [840, 320]
    events: list[MonitorEvent] = []

    class FakeLabel:
        @staticmethod
        def window_text() -> str:
            return "인증번호 [1234]"

    class FakeEditBox:
        @staticmethod
        def set_edit_text(text: str) -> None:
            assert text == "1234"
            cursor_position[:] = [0, 500]

    class FakeButton:
        @staticmethod
        def click() -> None:
            return None

    class FakePopup:
        @staticmethod
        def child_window(*, auto_id: str, title: str | None = None):
            if auto_id == "Label":
                return FakeLabel()
            if auto_id == "TextBox":
                return FakeEditBox()
            assert auto_id == "OKButton"
            assert title == "OK"
            return FakeButton()

    class FakeDesktop:
        def __init__(self, backend: str) -> None:
            assert backend == "win32"

        @staticmethod
        def window(*, handle: int) -> FakePopup:
            assert handle == 99
            return FakePopup()

    monkeypatch.setattr(
        popup_hacker.findwindows,
        "find_windows",
        lambda **kwargs: [99],
    )
    monkeypatch.setattr(popup_hacker, "Desktop", FakeDesktop)
    monkeypatch.setattr(
        popup_hacker.win32api,
        "GetCursorPos",
        lambda: tuple(cursor_position),
    )
    monkeypatch.setattr(
        popup_hacker.win32api,
        "SetCursorPos",
        lambda position: cursor_position.__setitem__(slice(None), position),
    )

    monitor = make_monitor(events)
    monitor._handle_auth_popup()

    assert cursor_position == [840, 320]
    assert not monitor.input_in_progress
    assert events[-1].kind == EventKind.ACTION
    assert events[-1].message == "인증번호 [1234] 입력 완료"
