import os
import subprocess
from typing import List, Dict
from PyQt6.QtCore import QStandardPaths

def get_resource_path(relative_path: str) -> str:
    """Получает абсолютный путь к ресурсу в папке resources."""
    base_path = os.path.abspath(".")  # Корень проекта
    return os.path.join(base_path, "resources", relative_path)

def get_default_output_folder() -> str:
    """
    Возвращает папку 'Видео/AutomatedContentCreator_Output' или 
    'Документы/AutomatedContentCreator_Output', если папка Видео не найдена.
    """
    videos = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.MoviesLocation)
    if videos:
        default_folder = os.path.join(videos[0], "AutomatedContentCreator_Output")
    else:
        docs = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.DocumentsLocation)
        default_folder = os.path.join(docs[0], "AutomatedContentCreator_Output")

    os.makedirs(default_folder, exist_ok=True)
    return default_folder

def extract_audio(video_path: str, audio_path: str):
    """
    Шаг 1. Извлечение аудиодорожки из видео.
    Извлекает моно WAV с частотой 16000 Гц из видео-файла.
    """
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",                # перезаписать, если файл уже есть
        "-i", video_path,    # входной файл
        "-ac", "1",          # моно
        "-ar", "16000",      # частота 16 кГц
        "-vn",               # без видео
        audio_path           # выходной WAV
    ]
    subprocess.run(cmd, check=True)

def segments_to_srt(segments: List[Dict], srt_path: str):
    """
    Шаг 2. Конвертация списка сегментов (Whisper) в файл .srt.
    Каждый сегмент — словарь с полями 'start', 'end', 'text'.
    """
    def format_timestamp(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    os.makedirs(os.path.dirname(srt_path), exist_ok=True)
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            start_ts = format_timestamp(seg["start"])
            end_ts   = format_timestamp(seg["end"])
            text     = seg["text"].strip()
            f.write(f"{i}\n{start_ts} --> {end_ts}\n{text}\n\n")

if __name__ == "__main__":
    # Быстрая проверка
    sample_video = "example.mp4"
    sample_wav   = "example.wav"
    sample_srt   = "example.srt"
    print("Вывод папки по умолчанию:", get_default_output_folder())
    # extract_audio(sample_video, sample_wav)
    # segments = [{"start":0.0,"end":1.2,"text":"Привет"}]
    # segments_to_srt(segments, sample_srt)
