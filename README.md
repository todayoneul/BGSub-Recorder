# Video Recorder with Background Subtraction

OpenCV를 사용해 웹캠 영상을 실시간으로 확인하고, 밝기/대비를 조절하며, 원본 및 배경제거 영상을 저장하는 프로젝트입니다.

## 주요 기능

- 실시간 카메라 미리보기
- 밝기/대비 조절
- 원본 영상 녹화 (`output.avi`)
- 배경 프레임 저장 (`background.png`)
- 배경 차영상 기반 객체 분리 이미지 저장 (`output_face.png`)
- 배경이 설정된 상태에서 전경만 저장한 영상 생성 (`output_no_background.avi`)

## 실행 환경

- Python 3.13.11
- OpenCV (`cv2`)

설치:

    pip install opencv-python

실행:

    python __main__.py

## 키 조작

- `Left` / `Right`: 대비 감소 / 증가
- `Up` / `Down`: 밝기 증가 / 감소
- `Space`: 녹화 시작 / 중지
- `R`: 밝기/대비 초기화
- `B` 또는 `1`: 현재 프레임을 배경으로 저장 (`background.png`)
- `F` 또는 `2`: 현재 프레임에서 배경을 제거한 객체 이미지 저장 (`output_face.png`)
- `ESC`: 프로그램 종료

## 출력 파일

- `output.avi`: 밝기/대비 조절이 반영된 원본 녹화본
- `output_no_background.avi`: 배경이 제거된 전경 객체 녹화본
- `background.png`: 저장된 기준 배경 이미지
- `output_face.png`: 추출된 전경 객체 스냅샷

## 동작 원리

`extract_foreground` 함수는 다음 절차로 전경을 추출합니다.

1. **가우시안 블러(Gaussian Blur)** 를 통한 사전 노이즈 제거
2. 현재 프레임과 배경 프레임의 **절대 차(Absolute Difference)** 계산
3. 그레이스케일 변환
4. **Otsu 이진화 알고리즘**을 통한 최적 임계값 자동 설정
5. **미디언 블러(Median Blur)** 로 잔노이즈 제거
6. **모폴로지(CLOSE, OPEN)** 연산으로 정밀한 마스크 생성 및 구멍 메우기
7. 가장 큰 외곽선을 전경 객체로 선택
8. 마스크를 적용해 전경만 추출

## 사용 팁

- 배경은 가능한 한 사람이 없는 상태에서 저장하세요.
- 카메라와 배경이 고정되어 있을수록 분리 품질이 좋아집니다.
- 조명이 크게 변하면 오검출이 늘어날 수 있으니, 필요하면 배경을 다시 저장하세요.
- `output_no_background.avi`는 배경이 저장된 이후부터 의미 있는 결과가 기록됩니다.
