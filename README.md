# UV 설치 권장

[UV 설치하러 가기](https://docs.astral.sh/uv/getting-started/installation/)

---

# 초보자 가이드

1. **[VSCode 설치](https://code.visualstudio.com/download)**
2. **UV 설치**
   - PowerShell 실행 후 [UV 설치 홈페이지](https://docs.astral.sh/uv/getting-started/installation/)에 있는 명령어를 복사하여 붙여넣으세요.
   - 설치 확인: PowerShell에서 `uv`를 입력했을 때...
     - ❌ **설치 실패**: 빨간색 글씨로 에러가 나온다면 설치되지 않은 상태입니다.
     - ✅ **설치 성공**: 흰색, 파란색 등 사용 방법 설명이 나온다면 설치된 상태입니다.
   - 설치가 완료되면 PowerShell은 닫아도 됩니다.
3. **코드 다운로드**
   - 현재 Github 페이지 상단의 초록색 **Code** 버튼을 클릭한 후 **Download ZIP**을 클릭하세요.
4. **VSCode 실행**
5. **폴더 열기**
   - 다운로드한 ZIP 파일의 압축을 해제합니다.
   - **압축 해제된 폴더 자체**를 VSCode 화면 위로 드래그하여 엽니다.
6. **터미널 실행**
   - VSCode에서  **【 L_Ctrl + L_Shift + ` 】** (숫자 1 왼쪽 키)를 **2번** 눌러 터미널 2개를 엽니다.

7. **프로그램 실행**
   - 화면 하단 TERMINAL 영역 오른쪽 리스트에서 각각의 터미널을 선택해 아래 명령어를 입력합니다.

**터미널 1 (수강신청 프로그램을 켜놓은 상태에서 실행):**

```shell
uv run popup_hacker.py
```

**터미널 2:**

```shell
uv run main.py
```

---

### ⚠️ 주의 및 참고 사항

- **종료 방법:** 실행을 종료하려면 터미널에서 `Ctrl` + `C`를 누르세요.
- **popup_hacker.py:** 광운대 수강신청 창이 활성화된 상태에서 실행하면 팝업창 숫자를 자동으로 입력하고 닫습니다.
- **main.py:** 실행 시 1, 2, 3... 등의 숫자로 마우스 위치를 매핑하여 사용할 수 있습니다.
