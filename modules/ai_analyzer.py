# automated_content_creator/modules/ai_analyzer.py

import os
import time

import whisper
from PyQt6.QtCore import QObject, pyqtSignal, QTime
# import cv2 # cv2 импортируется неявно через PySceneDetect, если выбран OpenCV бэкенд

# PySceneDetect
from scenedetect import open_video, SceneManager, FrameTimecode  # Добавил FrameTimecode для format_timecode
from scenedetect.detectors import ContentDetector
from typing import List, Dict


# from scenedetect.video_splitter import split_video_ffmpeg # Не используется сейчас

class AIAnalyzer(QObject):
    analysis_finished = pyqtSignal(list)
    analysis_progress = pyqtSignal(int, str)
    analysis_error = pyqtSignal(str)

    def __init__(self, parent_logger=None, settings=None):
        super().__init__()
        self.parent_logger = parent_logger
        self.settings = settings if settings else {}
        self._video_path = None
        self._is_cancelled = False

        self.pyscene_threshold = self.settings.get('pyscenedetect_threshold', 27.0)
        self.min_scene_duration_sec_pysd = self.settings.get('min_scene_len_sec', 2.0)
        self.final_min_highlight_duration_sec = self.settings.get('final_min_highlight_duration_sec', 3.0)

        self._log(f"AIAnalyzer инициализирован с настройками: threshold={self.pyscene_threshold}, "
                  f"min_scene_detect_duration={self.min_scene_duration_sec_pysd}s, "
                  f"final_min_highlight_duration={self.final_min_highlight_duration_sec}s")

    def _log(self, message: str, important: bool = False):
        if self.parent_logger and hasattr(self.parent_logger, 'log_message'):
            self.parent_logger.log_message(f"AIAnalyzer: {message}")
        else:
            print(f"AIAnalyzer (no logger): {message}")

    def cancel_analysis(self):
        self._log("Получен запрос на отмену анализа.", important=True)
        self._is_cancelled = True

    @staticmethod
    def format_timecode(time_sec: float, fps: float) -> str:  # fps теперь обязателен для FrameTimecode
        # Используем FrameTimecode для преобразования секунд в формат временного кода
        # FrameTimecode требует fps для корректной работы
        if fps is None or fps <= 0:  # Добавим проверку на корректность fps
            q_time = QTime(0, 0, 0, 0).addSecs(int(time_sec))
            milliseconds = int((time_sec - int(time_sec)) * 1000)
            return f"{q_time.toString('HH:mm:ss')}.{milliseconds:03d} (fps error)"
        return FrameTimecode(time_sec, fps).get_timecode()

    def analyze(self, video_path: str):
        self._log(f"Начало анализа видео: {video_path}", important=True)
        self._video_path = video_path
        self._is_cancelled = False
        highlights = []
        video_stream = None

        if not os.path.exists(video_path):
            error_msg = f"Файл видео не найден: {video_path}"
            self._log(error_msg, important=True)
            self.analysis_error.emit(error_msg)
            return

        try:
            self.analysis_progress.emit(0, "Инициализация видео...")
            # Использование with должно гарантировать закрытие, если PySceneDetect > v0.6.1
            # Для более старых версий, PySceneDetect сам управляет закрытием при выходе из области видимости.
            video_stream = open_video(video_path, backend='opencv') # persist_frames=False может помочь с памятью

            fps = video_stream.frame_rate
            if fps is None or fps <= 0:
                # Попытка получить FPS через OpenCV напрямую, если PySceneDetect не смог
                # Это более глубокое вмешательство и может быть не нужно, если open_video всегда дает fps
                self._log("Не удалось получить FPS от PySceneDetect, попытка через OpenCV напрямую (если возможно).",
                          True)
                # Это потребует video_stream.capture (если это объект cv2.VideoCapture)
                # Но video_stream это обертка. Лучше полагаться на PySceneDetect.
                # Если fps некорректен, дальнейший анализ может быть неточным.
                error_msg_fps = f"Некорректное значение FPS ({fps}) от PySceneDetect для видео {video_path}"
                self._log(error_msg_fps, True)
                self.analysis_error.emit(error_msg_fps)
                return

            duration_sec_total = video_stream.duration.get_seconds()
            num_frames_total = video_stream.duration.get_frames()

            self._log(
                f"Видео '{os.path.basename(video_path)}': FPS={fps:.2f}, Длительность={duration_sec_total:.2f}s, Кадров={num_frames_total}")

            if self._is_cancelled:
                self._log("Анализ отменен пользователем перед началом обработки.", True)
                self.analysis_finished.emit([])
                # Удаляем video_stream.release()
                return

            scene_manager = SceneManager()
            min_len_for_detector_frames = int(fps * self.min_scene_duration_sec_pysd)
            if min_len_for_detector_frames < 1:
                min_len_for_detector_frames = 1
            self._log(
                f"PySceneDetect ContentDetector min_scene_len установлен в {min_len_for_detector_frames} кадров (из {self.min_scene_duration_sec_pysd}s при {fps:.2f} FPS).")

            scene_manager.add_detector(
                ContentDetector(threshold=self.pyscene_threshold, min_scene_len=min_len_for_detector_frames))

            self.analysis_progress.emit(5, "Обнаружение сцен (PySceneDetect)...")

            processed_frames_for_progress = 0
            progress_update_interval_frames = max(1, num_frames_total // 20 if num_frames_total > 20 else 5)

            def progress_callback(frame_image, frame_num):
                nonlocal processed_frames_for_progress
                processed_frames_for_progress = frame_num
                if frame_num % progress_update_interval_frames == 0 or frame_num == num_frames_total - 1:
                    percent = 5 + int((frame_num / num_frames_total) * 85) if num_frames_total > 0 else 5
                    self.analysis_progress.emit(percent, f"Обработано кадров: {frame_num + 1}/{num_frames_total}")
                if self._is_cancelled:
                    raise InterruptedError("Анализ отменен пользователем во время detect_scenes.")

            try:
                scene_manager.detect_scenes(video=video_stream, frame_skip=0, show_progress=False,
                                            callback=progress_callback)
            except InterruptedError:
                self._log("Анализ (detect_scenes) прерван из-за отмены.", True)
                self.analysis_finished.emit([])
                # Удаляем video_stream.release()
                return
            except Exception as e_detect:
                self._log(f"Ошибка во время detect_scenes: {type(e_detect).__name__} - {e_detect}", True)
                self.analysis_error.emit(f"Ошибка PySceneDetect: {e_detect}")
                # Удаляем video_stream.release()
                return

            # После detect_scenes объект video_stream может быть уже "потреблен" или его позиция в конце.
            # Если нужно будет снова читать кадры (например, для другого анализа), его нужно будет "перемотать" (reset).
            # Но для простого получения списка сцен это не требуется.
            # video_stream.reset() # Если нужно было бы снова анализировать

            scene_list_pysd = scene_manager.get_scene_list()

            if self._is_cancelled:
                self._log("Анализ отменен после обнаружения сцен.", True)
                self.analysis_finished.emit([])
                # Удаляем video_stream.release()
                return

            self.analysis_progress.emit(95, "Фильтрация и форматирование хайлайтов...")
            self._log(f"PySceneDetect нашел {len(scene_list_pysd)} сцен(ы).")

            if not scene_list_pysd and duration_sec_total > 0:
                self._log("Сцен не найдено PySceneDetect. Если видео не пустое, возможно, порог слишком высок.", True)

            for i, (start_timecode, end_timecode) in enumerate(scene_list_pysd):
                start_sec = start_timecode.get_seconds()
                end_sec = end_timecode.get_seconds()
                duration_scene_sec = end_sec - start_sec

                if duration_scene_sec >= self.final_min_highlight_duration_sec:
                    highlight = {
                        'description': f"Хайлайт #{len(highlights) + 1} (Сцена {i + 1})",
                        'start_time': start_sec,
                        'end_time': end_sec,
                        'start_time_str': start_timecode.get_timecode(),
                        # Используем get_timecode() который уже форматирован
                        'end_time_str': end_timecode.get_timecode(),
                        'duration_sec': duration_scene_sec,
                        'score': round(min(1.0, duration_scene_sec / 60.0), 2)
                    }
                    highlights.append(highlight)
                    self._log(
                        f"  Добавлен хайлайт: {highlight['description']} ({highlight['start_time_str']} - {highlight['end_time_str']})")
                else:
                    self._log(f"  Сцена {i + 1} ({start_timecode.get_timecode()} - {end_timecode.get_timecode()}) "
                              f"длительностью {duration_scene_sec:.2f}с пропущена (меньше {self.final_min_highlight_duration_sec}с).")

                if self._is_cancelled:
                    self._log("Анализ отменен во время фильтрации сцен.", True)
                    self.analysis_finished.emit(highlights)
                    # Удаляем video_stream.release()
                    return

            # Удаляем video_stream.release() отсюда, так как PySceneDetect сам управляет ресурсом
            # или он освободится при выходе из области видимости/сборке мусора.

            self.analysis_progress.emit(100, f"Завершено. Найдено {len(highlights)} хайлайтов.")
            self._log(f"Анализ успешно завершен. Общее количество хайлайтов: {len(highlights)}.", important=True)
            self.analysis_finished.emit(highlights)

        except InterruptedError:
            self._log("Анализ прерван из-за отмены (внешний InterruptedError).", True)
            self.analysis_finished.emit([])
        except Exception as e:
            error_msg = f"Критическая ошибка во время анализа видео: {type(e).__name__} - {str(e)}"
            self._log(error_msg, important=True)
            import traceback
            self._log(f"Traceback: {traceback.format_exc()}")
            self.analysis_error.emit(error_msg)
        finally:
            # Явное удаление video_stream.release() из finally.
            # Если video_stream является менеджером контекста (для PySceneDetect >= v0.6.1),
            # то его лучше использовать через `with open_video(...) as video_stream:`.
            # Но так как мы используем его в коллбэках и он должен жить дольше,
            # полагаемся на автоматическое управление ресурсами PySceneDetect.
            if video_stream is not None:
                # Если есть какой-то явный метод закрытия в API PySceneDetect, его нужно использовать.
                # В текущей версии PySceneDetect (например, 0.6.x), объект VideoStream (например, VideoStreamCv2)
                # должен сам освобождать ресурсы при сборке мусора.
                # Убедимся, что нет ссылок, чтобы сборщик мусора мог сработать:
                del video_stream
                self._log("Ссылка на video_stream удалена.")

class WhisperSubtitleGenerator:
    """
    Генератор субтитров на основе OpenAI Whisper.
    """
    def __init__(self, model_size: str = "base"):
        # Варианты размера: tiny, base, small, medium, large
        self.model = whisper.load_model(model_size)
    def transcribe(self, audio_path: str) -> List[Dict]:
        """
        Транскрибирует аудио-файл и возвращает список сегментов:
        [{'id': 0, 'start': 0.0, 'end': 2.4, 'text': '...'}, ...]
        """
        result = self.model.transcribe(audio_path, word_timestamps=False)
        segments: List[Dict] = []
        for seg in result.get("segments", []):
            segments.append({
                "id": seg.get("id"),
                "start": seg.get("start"),
                "end": seg.get("end"),
                "text": seg.get("text", "").strip()
            })
        return segments