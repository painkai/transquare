# Transquare

Windows용 실시간 화면 번역 오버레이 앱. 게임·문서 화면 위에 올려두면 자동으로 텍스트를 인식해 한국어로 번역해줍니다.

## 주요 기능

**오버레이 창**
- 프레임리스 반투명 창, 항상 최상위 표시
- 상단: 캡처 영역 (드래그로 이동, 테두리 드래그로 크기 조절)
- 하단: 번역 결과 표시 영역
- 우측 버튼: 시작/정지(▶⏹), 다시 번역(↺), 언어 설정(⚙)
- 투명 영역 우측 상단 종료 버튼(✕)

**화면 캡처**
- DirectX 기반 dxcam으로 고속 캡처
- 수동 시작/정지 제어 (시작 전까지 캡처 없음)
- 텍스트 변화가 없으면 재번역 생략 (불필요한 API 호출 방지)

**OCR (텍스트 인식)**
- Windows OCR API (winrt) 사용, 별도 서버 불필요
- 단어 bounding rect 기반으로 텍스트 블록 자동 분리
  - 줄 간격과 폰트 크기 변화로 제목/본문/바이라인 구분
- 지원 언어: 영어, 일본어, 중국어(간·번체), 프랑스어, 독일어, 스페인어, 러시아어, 태국어, 베트남어

**번역**
- Ollama 로컬 LLM 사용 (기본 모델: qwen3.5:9b)
- thinking 모드 비활성화로 빠른 응답
- 소스/타겟 언어 UI에서 선택 가능

**번역 결과 표시**
- 블록별 폰트 크기 자동 조정 (원문 크기 비율 반영)
- 원문이 클수록 bold 적용
- 번역 결과 전체가 하단 영역 안에 들어오도록 크기 자동 맞춤
- 블록 간 구분 여백

## 요구 사항

- Windows 10/11
- Python 3.12 (conda 권장)
- RTX GPU (dxcam DirectX 캡처)
- [Ollama](https://ollama.com) 설치 및 모델 준비

```bash
ollama pull qwen3.5:9b
```

## 설치

```bash
conda create -n transquare python=3.12 -y
conda activate transquare
pip install PyQt6 dxcam numpy Pillow winsdk opencv-python-headless requests
```

## 실행

```bash
conda activate transquare
python overlay.py
```

## 사용 방법

1. 앱 실행 후 번역할 화면 위로 오버레이 창 이동
2. 상단 투명 영역을 번역할 텍스트 위에 맞게 크기 조절
3. ▶ 버튼으로 번역 시작
4. ⚙ 버튼으로 소스/타겟 언어 변경
5. ↺ 버튼으로 현재 화면 강제 재번역

## 트러블슈팅

### `[언어 미지원: en-US]` 메시지가 표시될 때

Windows OCR은 시스템에 설치된 언어팩만 인식합니다. 한국어 Windows에는 영어 OCR팩이 기본 포함되지 않을 수 있습니다.

**해결 방법:**

1. **Windows 설정 → 시간 및 언어 → 언어 및 지역** 열기
2. 필요한 언어(예: English) 추가
3. 해당 언어 클릭 → **언어 옵션** → **광학 문자 인식** 다운로드
4. 앱 재시작

### 실행 시 콘솔 경고

아래 두 경고는 앱 동작에 영향 없는 무해한 메시지입니다.

```
qt.qpa.window: SetProcessDpiAwarenessContext() failed: 액세스가 거부되었습니다.
```
Python 실행 파일이 이미 DPI 인식을 설정해둬서 Qt가 중복 설정을 시도할 때 발생합니다. 수정 불가능한 Windows/Qt 조합 이슈입니다.

```
QFont::setPointSize: Point size <= 0 (-1), must be greater than 0
```
Qt 내부 폰트 초기화 과정의 경고입니다. v1.1.0에서 수정되었습니다.
