from whisper import load_model
import pytesseract
from PIL import Image
import os
import moviepy.editor as mp

def transcribe_audio(audio_path: str) -> str:
    """使用 Whisper 模型将语音转写为文本"""
    model = load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]

def ocr_image(image_path: str) -> str:
    """使用 Tesseract OCR 识别图像中的文字"""
    image = Image.open(image_path)
    return pytesseract.image_to_string(image, lang="chi_sim")

def extract_text_from_video(video_path: str) -> str:
    """从视频提取音频并转写文字"""
    audio_path = "temp.wav"
    mp.VideoFileClip(video_path).audio.write_audiofile(audio_path)
    return transcribe_audio(audio_path)

def read_text_file(file_path: str) -> str:
    """读取 txt/md 文件内容"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""
