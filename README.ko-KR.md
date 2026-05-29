<p align="center">
  <img src="https://github.com/user-attachments/assets/d4f48f71-d76e-4ffe-9fb1-0b075d79bf05" alt="forza-painter FH6 logo" width="720">
</p>

<h1 align="center">forza-painter FH6</h1>

<p align="center">
  <strong>이미지를 Forza Horizon 6 비닐 그룹 레이어로 변환하고 가져오는 도구입니다.</strong>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">中文</a> ·
  <a href="README.ja-JP.md">日本語</a> ·
  <a href="README.ko-KR.md">한국어</a>
</p>

<p align="center">
  <a href="README.md">README</a> ·
  <a href="FAQ.md">FAQ</a> ·
  <a href="ACKNOWLEDGEMENTS.md">Acknowledgements</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="LICENSE">License</a>
</p>

<p align="center">
  <code>v1.6.6</code> · <code>Windows</code> · <code>Forza Horizon 6</code> · <code>GPU/OpenCL</code> · <code>One-file EXE</code>
</p>

PNG/JPG/BMP 이미지를 Forza Horizon 6 비닐 그룹 레이어로 변환합니다. 앱에서 생성, 미리보기, 가져오기를 한 번에 처리하며 일반 사용자는 Python, `.venv`, 배치 파일, 메모리 주소 입력이 필요 없습니다.

> **EXE 다운로드:** [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases)에서 `forza-painter-fh6-v1.6.6.exe`를 내려받아 바로 실행하세요.

> **결과가 흐릿하면:** 먼저 **Random samples** 값을 높이세요. **200000** 이상부터 품질 차이가 크게 보이는 경우가 많습니다.

> **가져오기는 시간이 걸릴 수 있습니다:** 여러 FH6 템플릿 위치 찾기 방식을 시도하며 최대 5분 정도 걸릴 수 있습니다. FH6를 Vinyl Group Editor에 그대로 두고 메뉴를 바꾸지 마세요.

| 기능 | 설명 |
| --- | --- |
| JSON 생성 | 내장 GPU/OpenCL 생성기로 이미지를 geometry JSON으로 변환합니다. |
| 이미지 미리보기 | 생성 전에 전처리 필터(luma, 양방향, 포스터라이즈, 셀 셰이딩 등)를 비교합니다. |
| 텍스트 비닐 | GB2312 문자 라이브러리와 시스템 글꼴로 CJK 입력, 또는 참조 이미지 추적. |
| Final JSON 가져오기 | 생성된 geometry JSON을 FH6로 가져옵니다. |
| 수작업 JSON 가져오기 | FH6 타입코드/수작업 JSON을 가져옵니다. |
| 게임 JSON 내보내기 | 열린 FH6 비닐 그룹을 수작업 JSON으로 내보냅니다. |
| 안전한 쓰기 | 쓰기 전에 편집 가능한 레이어 테이블을 자동으로 찾고 검증합니다. |
| 업데이트 확인 | 시작 시 새 버전을 확인하고 변경 내역을 표시합니다. |

## 빠른 시작

1. [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases)에서 `forza-painter-fh6-v1.6.6.exe`를 다운로드합니다.
2. EXE를 쓰기 가능한 일반 폴더에 둡니다. 예: `Desktop\forza-painter-fh6`.
3. EXE를 더블 클릭합니다. **가져오기 또는 내보내기** 시 동의를 요청하고 필요하면 UAC(관리자) 프롬프트가 표시됩니다.
4. FH6에서 `Create Vinyl Group` / `Vinyl Group Editor`를 열고 sphere 템플릿을 불러온 뒤 `Ungroup`합니다.
5. 앱 **Create**에서 JSON을 생성하고 **Import → Import Final JSON**에서 **정확한 템플릿 레이어 수**를 입력한 뒤 가져옵니다. 헤더 **Help**에서 튜토리얼과 안전 가이드를 열 수 있습니다.

개발 목적이 아니라면 GitHub의 자동 `Source code` ZIP을 받을 필요가 없습니다. 일반 사용자는 `.exe`만 사용하세요.

## 미리보기

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/app-import-preview.png" alt="App import page"><br>
      <strong>App import page</strong>
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-template-ready.png" alt="FH6 template ready"><br>
      <strong>Template ready in FH6</strong>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-import-result.png" alt="FH6 import result"><br>
      <strong>Imported result</strong>
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-car-applied.png" alt="FH6 car applied result"><br>
      <strong>Applied to car</strong>
    </td>
  </tr>
</table>

## 품질 프리셋 (요약)

| 프리셋 | 레이어 | 무작위 샘플 | 비고 |
| --- | ---: | ---: | --- |
| 0. Tailored (실험) | 이미지별 | 이미지별 | 선택 사항. Image Preview 분석 후 생성. **Normal(4)이 기본값.** |
| 1. Eco (실험) | 1500 | 90000 | 낮은 GPU 부하 |
| 4. Normal | 1800 | 120000 | 권장 기본값 |
| 7. Maximum Power | 2900 | 1000000 | 최고 품질, 가장 느림 |

전체 프리셋 표, 작업 흐름, 문제 해결, 안전 FAQ: **[FAQ.md](FAQ.md)** (영어)

## 추가 문서

| 문서 | 내용 |
| --- | --- |
| [FAQ.md](FAQ.md) | 작업 흐름, 규칙, 문제 해결 (영어) |
| [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) | 감사 및 상류 프로젝트 |
| [CHANGELOG.md](CHANGELOG.md) | 버전 기록 (앱 내 업데이트도 참조) |
| [SECURITY.md](SECURITY.md) | 보안 정책 |
| [docs/SAFETY.ko.md](docs/SAFETY.ko.md) | 안전 가이드 (한국어) |
| [docs/TEXT_VINYL.md](docs/TEXT_VINYL.md) | 텍스트 비닐 참고 |
