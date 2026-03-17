import cv2 as cv
import numpy as np
import os
import argparse

def get_video_source():
    parser = argparse.ArgumentParser(description="OpenCV Video Recorder")
    parser.add_argument('--source', type=str, help='Video source (camera index or RTSP URL)')
    args, _ = parser.parse_known_args()

    if args.source is not None:
        if args.source.isdigit():
            return int(args.source)
        return args.source
    
    print("비디오 소스를 선택하세요:")
    print("1. 로컬 카메라 (기본값: 0)")
    print("2. IP 카메라 (RTSP 주소 입력)")
    choice = input("선택 (1 또는 2, 기본값 1): ").strip()
    
    if choice == '2':
        rtsp_url = input("RTSP 주소를 입력하세요: ").strip()
        return rtsp_url
    else:
        cam_idx = input("카메라 인덱스를 입력하세요 (기본값 0): ").strip()
        return int(cam_idx) if cam_idx.isdigit() else 0

# 결과물을 저장할 assets 폴더 생성
if not os.path.exists('assets'):
    os.makedirs('assets')

contrast = 1.0
brightness = 0
sensitivity = 1.0  # 기본 민감도 (높을수록 더 많이 감지)

CONTRAST_STEP = 0.05
BRIGHTNESS_STEP = 1
SENSITIVITY_STEP = 0.1

LEFT_KEYS = {2424832, 81}
UP_KEYS = {2490368, 82}
RIGHT_KEYS = {2555904, 83}
DOWN_KEYS = {2621440, 84}
# macOS 방향키 코드
LEFT_KEYS.update({63234})
UP_KEYS.update({63232})
RIGHT_KEYS.update({63235})
DOWN_KEYS.update({63233})


def extract_foreground(background_img, current_img, sens=1.0):
    # 1. 사전 노이즈 제거
    bg_blur = cv.GaussianBlur(background_img, (5, 5), 0)
    cur_blur = cv.GaussianBlur(current_img, (5, 5), 0)

    # 2. RGB 차이 계산
    diff_rgb = cv.absdiff(cur_blur, bg_blur)
    b, g, r = cv.split(diff_rgb)
    gray_diff_rgb = cv.max(cv.max(b, g), r)

    # 3. HSV 채도(Saturation) 차이 계산 (이마 노이즈 보정용)
    bg_hsv = cv.cvtColor(bg_blur, cv.COLOR_BGR2HSV)
    cur_hsv = cv.cvtColor(cur_blur, cv.COLOR_BGR2HSV)
    diff_hsv = cv.absdiff(cur_hsv, bg_hsv)
    _, s_diff, _ = cv.split(diff_hsv)

    # 4. RGB 차이와 채도 차이를 결합
    combined_diff = cv.addWeighted(gray_diff_rgb, 0.7, s_diff, 0.3, 0)
    combined_diff = cv.normalize(combined_diff, None, 0, 255, cv.NORM_MINMAX)

    # 5. 민감도가 반영된 이진화
    otsu_thr, _ = cv.threshold(combined_diff, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    final_thr = max(5, int(otsu_thr / sens)) 
    _, mask = cv.threshold(combined_diff, final_thr, 255, cv.THRESH_BINARY)

    # 6. 정밀 모폴로지 연산
    kernel_small = cv.getStructuringElement(cv.MORPH_ELLIPSE, (3, 3))
    kernel_mid = cv.getStructuringElement(cv.MORPH_ELLIPSE, (7, 7))
    kernel_large = cv.getStructuringElement(cv.MORPH_ELLIPSE, (21, 21))

    mask = cv.medianBlur(mask, 5)
    mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, kernel_large, iterations=2)
    mask = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel_mid, iterations=1)
    mask = cv.dilate(mask, kernel_small, iterations=1)

    # 7. 유효 객체 추출 및 병합
    contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    object_mask = np.zeros_like(mask)
    has_object = False
    frame_area = mask.shape[0] * mask.shape[1]
    min_area = frame_area * 0.0005

    for cnt in contours:
        if cv.contourArea(cnt) > min_area:
            cv.drawContours(object_mask, [cnt], -1, 255, thickness=cv.FILLED)
            has_object = True

    if not has_object:
        return None, None

    foreground = cv.bitwise_and(current_img, current_img, mask=object_mask)
    return foreground, object_mask


# 1. 카메라 영상 얻기
source = get_video_source()
cap = cv.VideoCapture(source)

if not cap.isOpened():
    print("카메라를 열 수 없습니다.")
    exit()

# 비디오 저장을 위한 코덱 및 VideoWriter 설정
fourcc = cv.VideoWriter_fourcc(*'XVID')
width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
fps = 30.0

# 2. 동영상 파일 만들기 준비
out = cv.VideoWriter('assets/output.avi', fourcc, fps, (width, height))
out_no_bg = cv.VideoWriter('assets/output_no_background.avi', fourcc, fps, (width, height))

# 기본 모드는 Preview (녹화 안 함)
recording = False 
background_frame = None

window_name = 'Video Recorder'
cv.namedWindow(window_name)

while True:
    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽어올 수 없습니다.")
        break

    # 거울 모드 적용 (좌우 반전)
    frame = cv.flip(frame, 1)

    adjusted_frame = cv.convertScaleAbs(frame, alpha=contrast, beta=brightness)

    # 화면 표시용 프레임 복사 (녹화본에는 빨간 원이 안 들어가게 하기 위함)
    display_frame = adjusted_frame.copy()

    cv.putText(
        display_frame,
        f'contrast: {contrast:.2f}  brightness: {brightness}  sensitivity: {sensitivity:.1f}',
        (10, 30),
        cv.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )
    cv.putText(
        display_frame,
        'Arrows: contrast/brightness  +/-: sensitivity  R: reset',
        (10, 58),
        cv.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 0),
        1,
    )
    cv.putText(
        display_frame,
        'B/1: background  F/2: save snapshot  Space: rec  ESC: quit',
        (10, 80),
        cv.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 0),
        1,
    )
    cv.putText(
        display_frame,
        f'Background: {"READY" if background_frame is not None else "NOT SET"}',
        (10, 110),
        cv.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 200, 255) if background_frame is not None else (0, 120, 255),
        1,
    )
    cv.putText(
        display_frame,
        'No-bg video: output_no_background.avi (recording + background)',
        (10, 135),
        cv.FONT_HERSHEY_SIMPLEX,
        0.5,
        (180, 255, 180),
        1,
    )

    # Record 모드일 경우: 화면에 빨간색 원 표시 및 프레임 저장
    if recording:
        out.write(adjusted_frame) # 동영상 파일에 조절된 프레임 저장

        if background_frame is not None:
            foreground_for_video, _ = extract_foreground(background_frame, adjusted_frame, sensitivity)
            if foreground_for_video is None:
                foreground_for_video = adjusted_frame.copy()
                foreground_for_video[:, :] = 0
            out_no_bg.write(foreground_for_video)

        # 녹화 중임을 알리는 빨간색 원 표시
        cv.circle(display_frame, (width - 50, 50), 20, (0, 0, 255), -1) 

    # 3. 화면에 현재 카메라 영상 표시
    cv.imshow(window_name, display_frame)

    # 키 입력 대기 (1ms)
    key = cv.waitKeyEx(1)
    key_low = key & 0xFF

    if key in LEFT_KEYS:
        contrast = max(0.2, contrast - CONTRAST_STEP)
    elif key in RIGHT_KEYS:
        contrast = min(3.0, contrast + CONTRAST_STEP)
    elif key in UP_KEYS:
        brightness = min(100, brightness + BRIGHTNESS_STEP)
    elif key in DOWN_KEYS:
        brightness = max(-100, brightness - BRIGHTNESS_STEP)

    # 4. Preview / Record 모드 변환
    if key_low == ord(' '):
        recording = not recording
        if recording:
            print("Record 모드: 녹화 시작")
        else:
            print("Preview 모드: 녹화 중지")
    elif key_low in (ord('r'), ord('R')):
        contrast = 1.0
        brightness = 0
        sensitivity = 1.0
        print("밝기/대비/민감도 값을 초기화했습니다.")
    elif key_low in (ord('+'), ord('=')):
        sensitivity = min(3.0, round(sensitivity + SENSITIVITY_STEP, 2))
        print(f"민감도: {sensitivity:.2f}")
    elif key_low == ord('-'):
        sensitivity = max(0.5, round(sensitivity - SENSITIVITY_STEP, 2))
        print(f"민감도: {sensitivity:.2f}")
    elif key_low in (ord('b'), ord('B'), ord('1')):
        background_frame = adjusted_frame.copy()
        cv.imwrite('assets/background.png', background_frame)
        print("배경을 assets/background.png로 저장했습니다.")
    elif key_low in (ord('f'), ord('F'), ord('2')):
        if background_frame is None:
            print("먼저 B 키로 배경을 저장하세요.")
        else:
            foreground, object_mask = extract_foreground(background_frame, adjusted_frame, sensitivity)
            if foreground is None:
                print("객체를 찾지 못했습니다. 배경을 다시 저장하거나 민감도(+/-)를 조절하세요.")
            else:
                cv.imwrite('assets/output_face.png', foreground)
                print("분리된 객체를 assets/output_face.png로 저장했습니다.")

    # 5. 프로그램 종료
    elif key_low == 27: # ESC 키
        print("프로그램을 종료합니다.")
        break

# 자원 해제
cap.release()
out.release()
out_no_bg.release()
cv.destroyAllWindows()
