import sys
from pywinauto import Application

parent_process_name = "MDmain.exe"
warning_popup_title = "수강신청"
output_file = "popup_inspect_result.txt"


def dump_children(win, f, depth=0):
    """자식 컨트롤을 재귀적으로 탐색하여 기록"""
    indent = "  " * depth
    for child in win.children():
        f.write(f"{indent}Class: {child.friendly_class_name()}\n")
        f.write(f"{indent}Text: {repr(child.window_text())}\n")
        try:
            f.write(f"{indent}AutoID: {child.automation_id()}\n")
        except Exception:
            f.write(f"{indent}AutoID: (unavailable)\n")
        f.write(f"{indent}Handle: {child.handle}\n")
        f.write(f"{indent}Rect: {child.rectangle()}\n")
        f.write("\n")
        dump_children(child, f, depth + 1)


def inspect_popup():
    print(f"'{parent_process_name}' 프로세스에 연결 시도 중...")
    app = Application(backend="win32").connect(path=parent_process_name, timeout=10)
    print("연결 성공!")

    warning_windows = app.windows(title=warning_popup_title)
    print(f"'{warning_popup_title}' 제목의 창 {len(warning_windows)}개 발견")

    if len(warning_windows) < 2:
        print("경고 팝업이 없습니다. (창이 2개 미만)")
        # sys.exit(0)

    with open(output_file, "w", encoding="utf-8") as f:
        for i, win in enumerate(warning_windows):
            f.write(f"===== Window [{i}] =====\n")
            f.write(f"Handle: {win.handle}\n")
            f.write(f"Title: {win.window_text()}\n")
            f.write(f"Class: {win.friendly_class_name()}\n")
            f.write(f"Rectangle: {win.rectangle()}\n")
            f.write(f"\n--- Children (recursive) ---\n")
            dump_children(win, f, depth=1)
            f.write("\n\n")

    print(f"결과를 '{output_file}'에 저장했습니다.")


if __name__ == "__main__":
    inspect_popup()
