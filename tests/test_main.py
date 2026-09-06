from __future__ import annotations

import queue

import keyboard
import main
from main import (
    ENROLLMENT_KEY,
    FUNCTION_KEY_SCAN_CODES,
    KEY_QUEUE_POLL_MS,
    ApplyMacroApp,
)
from popup_hacker import EventKind


class FakePopupMonitor:
    input_in_progress = False


class FakeWindow:
    def __init__(self) -> None:
        self.after_calls: list[tuple[int, object]] = []

    def after(self, delay: int, callback) -> None:
        self.after_calls.append((delay, callback))


class FakeBooleanVar:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value


class FakeKeyboardEvent:
    def __init__(self, event_type: str) -> None:
        self.event_type = event_type


def make_app() -> ApplyMacroApp:
    app = ApplyMacroApp.__new__(ApplyMacroApp)
    app.keyboard_hooks = []
    app.pressed_function_keys = set()
    app.key_events = queue.Queue()
    app.monitor_events = queue.Queue()
    app.is_closing = False
    app.popup_monitor = FakePopupMonitor()
    return app


def test_registers_independent_function_key_hooks(monkeypatch) -> None:
    app = make_app()
    registrations: list[tuple[int, object, bool]] = []

    def fake_hook_key(scan_code, callback, *, suppress):
        registrations.append((scan_code, callback, suppress))
        return lambda: None

    monkeypatch.setattr(main.keyboard, "hook_key", fake_hook_key)

    app._register_mouse_hotkeys()

    assert [item[0] for item in registrations] == list(
        FUNCTION_KEY_SCAN_CODES.values()
    )
    assert all(item[2] for item in registrations)
    assert len(app.keyboard_hooks) == 11


def test_overlapping_function_keys_are_both_queued() -> None:
    app = make_app()
    key_down = FakeKeyboardEvent(keyboard.KEY_DOWN)

    assert app._handle_function_key_event(1, key_down) is False
    assert app._handle_function_key_event(ENROLLMENT_KEY, key_down) is False

    assert app.key_events.get_nowait() == 1
    assert app.key_events.get_nowait() == ENROLLMENT_KEY


def test_key_repeat_is_ignored_until_key_up() -> None:
    app = make_app()
    key_down = FakeKeyboardEvent(keyboard.KEY_DOWN)
    key_up = FakeKeyboardEvent(keyboard.KEY_UP)

    app._handle_function_key_event(3, key_down)
    app._handle_function_key_event(3, key_down)
    app._handle_function_key_event(3, key_up)
    app._handle_function_key_event(3, key_down)

    assert [app.key_events.get_nowait(), app.key_events.get_nowait()] == [3, 3]
    assert app.key_events.empty()


def test_shortcut_is_queued_while_popup_input_is_busy() -> None:
    app = make_app()
    app.popup_monitor.input_in_progress = True

    app._queue_shortcut(4)
    assert app.key_events.get_nowait() == 4

    app.is_closing = True
    app._queue_shortcut(5)
    assert app.key_events.empty()


def test_queue_processing_waits_for_popup_input() -> None:
    app = make_app()
    app.window = FakeWindow()
    handled: list[int] = []
    app._handle_shortcut = handled.append
    app.key_events.put(6)

    app.popup_monitor.input_in_progress = True
    app._drain_queues()
    assert handled == []
    assert app.key_events.qsize() == 1

    app.popup_monitor.input_in_progress = False
    app._drain_queues()
    assert handled == [6]
    assert app.key_events.empty()
    assert all(call[0] == KEY_QUEUE_POLL_MS for call in app.window.after_calls)


def test_partial_hook_registration_failure_cleans_up(monkeypatch) -> None:
    app = make_app()
    removed: list[int] = []
    logs: list[tuple[str, EventKind]] = []
    hook_calls = 0

    def fake_hook_key(*args, **kwargs):
        nonlocal hook_calls
        hook_calls += 1
        if hook_calls == 3:
            raise RuntimeError("registration failed")
        registered = hook_calls
        return lambda: removed.append(registered)

    monkeypatch.setattr(main.keyboard, "hook_key", fake_hook_key)
    app._append_log = lambda message, kind: logs.append((message, kind))

    app._register_mouse_hotkeys()

    assert removed == [1, 2]
    assert app.keyboard_hooks == []
    assert logs == [("전역 단축키 등록 오류: registration failed", EventKind.ERROR)]


def test_unregister_hooks_continues_after_cleanup_error() -> None:
    app = make_app()
    removed: list[str] = []

    def remove_first() -> None:
        removed.append("first")

    def remove_second() -> None:
        removed.append("second")
        raise RuntimeError("cleanup failed")

    def remove_third() -> None:
        removed.append("third")

    app.keyboard_hooks = [remove_first, remove_second, remove_third]
    app.pressed_function_keys = {1, 2}

    app._unregister_mouse_hotkeys()

    assert removed == ["first", "second", "third"]
    assert app.keyboard_hooks == []
    assert app.pressed_function_keys == set()


def test_course_click_can_be_followed_by_enrollment_click(monkeypatch) -> None:
    app = make_app()
    app.is_set_mode = False
    app.positions = {
        2: main.Point(120, 240),
        ENROLLMENT_KEY: main.Point(500, 600),
    }
    app.is_click_enrollment_after = FakeBooleanVar(True)
    clicks: list[tuple[int, int]] = []
    logs: list[tuple[str, EventKind]] = []
    monkeypatch.setattr(
        main.pyautogui,
        "click",
        lambda *, x, y: clicks.append((x, y)),
    )
    app._append_log = lambda message, kind: logs.append((message, kind))

    app._handle_shortcut(2)

    assert clicks == [(120, 240), (500, 600)]
    assert logs == [
        ("F2 과목 클릭 후 F11 수강신청 클릭 완료", EventKind.ACTION)
    ]


def test_f11_direct_click_does_not_click_twice(monkeypatch) -> None:
    app = make_app()
    app.is_set_mode = False
    app.positions = {ENROLLMENT_KEY: main.Point(500, 600)}
    app.is_click_enrollment_after = FakeBooleanVar(True)
    clicks: list[tuple[int, int]] = []
    monkeypatch.setattr(
        main.pyautogui,
        "click",
        lambda *, x, y: clicks.append((x, y)),
    )

    app._handle_shortcut(ENROLLMENT_KEY)

    assert clicks == [(500, 600)]
