from __future__ import annotations

import queue

import main
from main import LEFT_ALT_SCAN_CODE, TOP_ROW_DIGIT_SCAN_CODES, ApplyMacroApp
from popup_hacker import EventKind


class FakePopupMonitor:
    input_in_progress = False


def make_app() -> ApplyMacroApp:
    app = ApplyMacroApp.__new__(ApplyMacroApp)
    app.keyboard_hotkeys = []
    app.key_events = queue.Queue()
    app.is_closing = False
    app.popup_monitor = FakePopupMonitor()
    return app


def test_registers_left_alt_top_row_digit_hotkeys(monkeypatch) -> None:
    app = make_app()
    registrations: list[tuple[tuple[int, int], tuple[str, ...], bool]] = []

    def fake_add_hotkey(hotkey, callback, *, args, suppress):
        assert callback.__self__ is app
        registrations.append((hotkey, args, suppress))
        return f"hotkey-{len(registrations)}"

    monkeypatch.setattr(main.keyboard, "add_hotkey", fake_add_hotkey)

    app._register_mouse_hotkeys()

    assert registrations == [
        ((LEFT_ALT_SCAN_CODE, scan_code), (digit,), True)
        for digit, scan_code in TOP_ROW_DIGIT_SCAN_CODES.items()
    ]
    assert app.keyboard_hotkeys == [f"hotkey-{index}" for index in range(1, 11)]


def test_hotkey_callback_only_queues_while_input_is_available() -> None:
    app = make_app()

    app._queue_digit("1")
    assert app.key_events.get_nowait() == "1"

    app.is_closing = True
    app._queue_digit("2")
    assert app.key_events.empty()

    app.is_closing = False
    app.popup_monitor.input_in_progress = True
    app._queue_digit("3")
    assert app.key_events.empty()


def test_partial_hotkey_registration_failure_cleans_up(monkeypatch) -> None:
    app = make_app()
    removed: list[str] = []
    logs: list[tuple[str, EventKind]] = []
    add_calls = 0

    def fake_add_hotkey(*args, **kwargs):
        nonlocal add_calls
        add_calls += 1
        if add_calls == 3:
            raise RuntimeError("registration failed")
        return f"hotkey-{add_calls}"

    monkeypatch.setattr(main.keyboard, "add_hotkey", fake_add_hotkey)
    monkeypatch.setattr(main.keyboard, "remove_hotkey", removed.append)
    app._append_log = lambda message, kind: logs.append((message, kind))

    app._register_mouse_hotkeys()

    assert removed == ["hotkey-1", "hotkey-2"]
    assert app.keyboard_hotkeys == []
    assert logs == [("전역 단축키 등록 오류: registration failed", EventKind.ERROR)]


def test_unregister_hotkeys_continues_after_cleanup_error(monkeypatch) -> None:
    app = make_app()
    app.keyboard_hotkeys = ["first", "second", "third"]
    removed: list[str] = []

    def fake_remove_hotkey(hotkey: str) -> None:
        removed.append(hotkey)
        if hotkey == "second":
            raise RuntimeError("cleanup failed")

    monkeypatch.setattr(main.keyboard, "remove_hotkey", fake_remove_hotkey)

    app._unregister_mouse_hotkeys()

    assert removed == ["first", "second", "third"]
    assert app.keyboard_hotkeys == []
