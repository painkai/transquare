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
