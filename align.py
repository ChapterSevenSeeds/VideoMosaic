import cv2
import imagehash
from PIL import Image, ImageEnhance

reference = Image.open("align_ref.jpg")
ref_hash = imagehash.average_hash(reference)

source = cv2.VideoCapture(r"What\Season 1\Arthur - S01E01-E02 - Arthur's Eyes + Francine's Bad Hair Day WEBDL-480p.mp4")

frame_num = 1
max_intro_frames = 500
lowest_difference = 100
lowest_diff_frame = None
lowest_diff_frame_num = 1
for _ in range(max_intro_frames):
    success, image = source.read()
    if not success:
        break

    frame = Image.fromarray(image)
    frame_hash = imagehash.average_hash(frame)
    diff = ref_hash - frame_hash
    if diff < lowest_difference:
        lowest_diff_frame = image
        lowest_difference = diff
        lowest_diff_frame_num = frame_num
    frame_num += 1

source = cv2.VideoCapture(r"What\Season 1\Arthur - S01E01-E02 - Arthur's Eyes + Francine's Bad Hair Day WEBDL-480p.mp4")

frame_num = 1
last_black_frame_num = 1
last_black_frame = None
for _ in range(lowest_diff_frame_num):
    success, image = source.read()
    if not success:
        break

    
    frame = Image.fromarray(image)
    enhancer = ImageEnhance.Brightness(frame)

    darkened = enhancer.enhance(0.1)
    colors = darkened.getcolors()
    if colors and len(colors) < 120:
        last_black_frame_num = frame_num
        last_black_frame = image

    frame_num += 1

print(last_black_frame_num)
cv2.imshow("", last_black_frame)
cv2.waitKey(0)