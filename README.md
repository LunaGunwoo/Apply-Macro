# UV 설치 권장

[UV 설치하러 가기](https://docs.astral.sh/uv/getting-started/installation/)

---

# 초보자 가이드

1. [vscode 설치](https://code.visualstudio.com/download)
2. powershell 실행 후 [UV 설치](https://docs.astral.sh/uv/getting-started/installation/) 홈페이지에 나와있는 명령어 복붙
   - 그 powershell에서 `uv` 입력했을 때
     - <text style="color:#f14433">빨간 글씨</text>가 나왔다면 설치 되지 않은 상태
     - <text style="color:#61d6d6">민트색</text>, <text style="color:#3a96dd">파란색</text>, <text style="color:#cccccc">흰색</text>으로 적힌 사용방법이 적혀있다면 설치된 상태
   - 이제 powershell은 닫아도 상관없음
3. 현재 Github 페이지에서 상단에
   <button style="background-color: #29903b; color: white; padding: 5px"><> Code ▼</button> 버튼 클릭 후 `Download ZIP` 클릭
4. VSCode 실행
5. 다운로드한 ZIP을 압축해제하고 그 폴더를 **_폴더 채로 VSCode 화면 위까지 드래그_**
6. 이후 VSCode에서 **【 L_Ctrl + L_Shift + ` 】** 를 <text style="color: yellow">2번</text> 눌러 2개의 TERMINAL 열기 (키보드의 1 왼쪽에 있는 문자 참고)
7. 하단에 TERMINAL이 보이는데 (오른쪽에 2개의 TERMINAL이 보임)
   - 그 2개 중 하나의 TERMINAL에는 아래 명령어 복붙 (_수강신청 프로그램을 켜놓은 상태에서 복붙해야함_)

   ```shell
   uv run popup_hacker.py
   ```

   - 또 다른 하나의 TERMINAL에는 아래 명령어 복붙 복붙

   ```shell
   uv run main.py
   ```

---

### 터미널 2개 실행 필요.

실행 종료시키고 싶으면 `ctrl + C` 누르면 종료.

#### 1. `uv run popup_hacker.py`

광운대 수강신청을 켜놓은 후에 터미널에서 실행시켜 놓으면 광운대 수강신청 pop up 창 자동으로 수 입력하고 닫음

#### 2. `uv run main.py`

실행시켜 놓으면 1,2, ... 숫자들로 마우스를 매핑 시켜놓을 수 있음
