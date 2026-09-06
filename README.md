# Apply Macro

광운대학교 수강신청 프로그램에서 왼쪽 Alt와 숫자키로 지정한 위치를 클릭하고, 인증번호와 만석 경고 팝업을 자동으로 처리하는 Windows용 도구입니다.

## 일반 사용자: EXE 실행

1. [최신 Release](https://github.com/LunaGunwoo/Apply-Macro/releases/latest)에서 `ApplyMacro-windows-x64-vX.Y.Z.zip`을 다운로드합니다.
2. ZIP 파일의 압축을 해제합니다.
3. 압축을 푼 폴더의 `ApplyMacro.exe`를 더블클릭합니다.
4. 수강신청 프로그램을 실행하면 Apply Macro가 `MDmain.exe`를 자동으로 찾아 연결합니다. 두 프로그램의 실행 순서는 상관없습니다.

Python, uv, VSCode를 별도로 설치할 필요가 없습니다.

### 화면 상태

- 노란색 `연결 대기 중`: 수강신청 프로그램을 찾는 중입니다.
- 초록색 `연결됨`: 팝업 자동 처리를 사용할 수 있습니다.
- 빨간색 `연결 끊김 — 재연결 중`: 연결이 끊겨 다시 찾는 중입니다.
- `인증번호 자동 입력`과 `만석 경고 자동 닫기`는 각각 체크박스로 켜고 끌 수 있으며 기본값은 모두 켜짐입니다.
- 최근 연결 변화, 팝업 처리 결과, 오류는 오른쪽 `최근 처리 내역`에서 확인할 수 있습니다.

## 마우스 위치 단축키

1. `설정 모드 켜짐` 상태에서 `왼쪽 Alt + 상단 숫자키 0~9`를 누르면 현재 마우스 위치가 해당 숫자에 저장됩니다.
2. `끄기` 버튼을 눌러 설정 모드를 끕니다.
3. `왼쪽 Alt + 상단 숫자키`를 누르면 저장한 위치가 클릭됩니다.
4. `1~9 클릭 후 0번 위치 클릭`을 체크하면 `1`~`9` 위치를 클릭한 다음 `0` 위치도 이어서 클릭합니다.

일반 숫자키, `Shift + 숫자키`, 오른쪽 Alt, 숫자패드는 마우스 단축키로 사용되지 않습니다.

프로그램을 종료하려면 Apply Macro 창의 닫기 버튼을 누르세요.

## Windows 보안 경고 및 PC방 사용

현재 Release는 코드 서명되지 않았기 때문에 Windows에서 `Windows의 PC 보호` 경고가 표시될 수 있습니다. 공개 Release는 GitHub에서 받은 ZIP과 EXE를 최신 Microsoft Defender로 검사한 뒤 게시합니다.

- 이 GitHub 저장소에서 직접 받은 파일인지 확인하세요.
- Release에 함께 첨부된 `.sha256` 파일과 다운로드한 ZIP의 SHA-256 값이 일치하는지 확인하세요.
- 개인 PC에서 출처와 해시를 확인했다면 경고 창의 `추가 정보`에서 실행할 수 있습니다.
- `위협 발견` 알림이 뜨거나 ZIP 또는 EXE가 격리되면 Defender를 끄거나 검사 예외를 추가하지 말고 해당 Release를 사용하지 마세요.
- PC방이나 관리되는 PC에서 실행 선택지가 없거나 백신이 파일을 차단하면 해당 PC의 정책을 우회하지 마세요. 관리자 정책과 보안 프로그램에 따라 실행이 불가능할 수 있습니다.

PowerShell에서 ZIP 파일의 해시를 확인하는 예시는 다음과 같습니다.

```powershell
Get-FileHash -Algorithm SHA256 .\ApplyMacro-windows-x64-v0.2.1.zip
```

## 개발 환경

개발에는 [uv](https://docs.astral.sh/uv/getting-started/installation/)를 사용합니다.

```powershell
uv sync --group dev
uv run main.py
```

`popup_hacker.py`는 GUI에서 사용하는 내부 모듈이므로 별도 터미널에서 실행하지 않습니다.

### 테스트와 로컬 빌드

```powershell
uv run pytest
uv run pyinstaller --noconfirm --clean ApplyMacro.spec
```

빌드된 단일 실행 파일은 `dist\ApplyMacro.exe`에 생성됩니다.

### GitHub Release 만들기

`pyproject.toml`의 버전과 같은 `vX.Y.Z` 태그를 푸시하면 GitHub Actions가 Python 3.14.2로 Windows x64 실행 파일을 빌드합니다. ZIP, ZIP SHA-256, EXE SHA-256은 Actions artifact와 Draft Release에 첨부되며 자동으로 공개되지 않습니다.

```powershell
git tag v0.2.1
git push origin v0.2.1
```

Actions에서 받은 ZIP을 실제로 다운로드해 최신 Microsoft Defender로 ZIP과 압축 해제 폴더를 검사하고, EXE 실행까지 확인하세요. 검증을 통과한 경우에만 Draft를 공개합니다.

```powershell
gh release edit v0.2.1 --draft=false --latest
```

단일 EXE가 Defender에 탐지되면 해당 Draft를 공개하지 않고 PyInstaller `onedir` 방식의 portable 폴더 ZIP으로 다시 빌드하고 같은 검증을 반복합니다.
