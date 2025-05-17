# automated_content_creator/modules/cutting_engine.py

import subprocess  # Для вызова FFmpeg
import os
import platform  # Для разных команд в будущем, если понадобится


class CuttingEngine:
    def __init__(self, parent_logger=None):
        self.parent_logger = parent_logger
        self.ffmpeg_path = "ffmpeg"
        self._current_process = None  # Для возможности отмены

    def _log(self, message, level="INFO"):  # Добавил level
        if self.parent_logger and hasattr(self.parent_logger, 'log_message'):
            self.parent_logger.log_message(f"CuttingEngine: {message}", level=level)
        else:
            print(f"CuttingEngine [{level}] (no logger): {message}")

    def set_ffmpeg_path(self, path: str):
        resolved_path = path if path else "ffmpeg"
        self._log(f"Установлен путь к FFmpeg: '{resolved_path}'")
        self.ffmpeg_path = resolved_path

    def cancel_current_operation(self):  # Метод для попытки отмены
        if self._current_process and self._current_process.poll() is None:  # Если процесс существует и выполняется
            self._log("Попытка отменить текущую операцию FFmpeg...", level="WARN")
            try:
                self._current_process.terminate()  # Посылаем SIGTERM
                # Можно добавить ожидание с тайм-аутом и self._current_process.kill() если terminate не сработал
                self._log("Команда terminate отправлена процессу FFmpeg.", level="WARN")
            except Exception as e:
                self._log(f"Ошибка при попытке отменить процесс FFmpeg: {e}", level="ERROR")
        else:
            self._log("Нет активной операции FFmpeg для отмены.", level="DEBUG")

    def cut_clip(self, input_video_path: str, start_time_sec: float, end_time_sec: float, output_path: str) -> bool:
        norm_input_video_path = os.path.normpath(input_video_path)
        norm_output_path = os.path.normpath(output_path)

        self._log(
            f"Попытка вырезать клип из '{os.path.basename(norm_input_video_path)}' "
            f"с {start_time_sec:.3f}с по {end_time_sec:.3f}с в '{os.path.basename(norm_output_path)}'"
        )
        self._log(f"  FFmpeg используется: '{self.ffmpeg_path}'")

        duration = end_time_sec - start_time_sec
        if duration <= 0:
            self._log(f"Ошибка: Длительность клипа должна быть положительной ({duration:.3f}с). Пропуск.", level="WARN")
            return False

        if not os.path.exists(norm_input_video_path):
            self._log(f"Ошибка: Входной видеофайл не найден: {norm_input_video_path}", level="ERROR")
            return False

        output_dir = os.path.dirname(norm_output_path)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                self._log(f"  Создана выходная директория: {output_dir}", level="DEBUG")
            except OSError as e_mkdir:
                self._log(f"  Ошибка создания выходной директории {output_dir}: {e_mkdir}", level="ERROR")
                return False

        command = [
            self.ffmpeg_path,
            '-hide_banner',
            '-loglevel', 'error',  # Оставляем error для чистого вывода, stderr будем анализировать
            '-y',  # Перезаписывать выходной файл без запроса
            '-ss', str(start_time_sec),  # Указываем время начала (лучше перед -i для быстрого поиска)
            '-i', norm_input_video_path,
            '-to', str(end_time_sec),  # Указываем время окончания (относительно начала файла)
            # '-t', str(duration), # Альтернатива: указать длительность вырезаемого фрагмента
            '-c:v', 'libx264',  # Кодек видео
            '-preset', 'medium',  # Пресет качества/скорости для x264
            '-crf', '23',  # Constant Rate Factor (качество, меньше = лучше и больше размер)
            '-c:a', 'aac',  # Кодек аудио
            '-b:a', '160k',  # Битрейт аудио
            # ИСПРАВЛЕНИЕ: Замена 'make_nonnegative' на '1' или 'auto'. '1' обычно работает.
            # Эта опция полезна, если исходное видео имеет неправильные временные метки.
            # Для MP4 muxer, значение должно быть одним из флагов, а не строкой 'make_nonnegative'.
            # Либо можно использовать '-output_ts_offset' или другие методы коррекции TS.
            # Попробуем '-avoid_negative_ts', '1'
            # '-avoid_negative_ts', '1', # Для избежания отрицательных временных меток
            # Либо можно попробовать '-flags', '+ бит_для_коррекции_ts'
            # По документации FFmpeg: avoid_negative_ts type:flags
            # Available values for flags:
            # ‘disabled’ 0
            # ‘auto’ -1 default
            # ‘make_zero’ 1 Shift timestamps so that the first one is 0.
            # ‘make_nonnegative’ 2 Shift timestamps so that the first one is not negative. This is useful when clipping parts of a stream.
            # Попробуем '2' (make_nonnegative) как числовой флаг
            '-avoid_negative_ts', '2',
            '-movflags', '+faststart',  # Для оптимизации MP4 для стриминга
            norm_output_path
        ]

        self._log(f"  Сформирована команда FFmpeg: {' '.join(command)}", level="DEBUG")

        self._current_process = None
        try:
            self._log("  Запуск процесса FFmpeg...", level="DEBUG")
            # Используем subprocess.run для более простого управления и получения вывода
            # Для скрытия окна консоли на Windows:
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            self._current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,  # Захватываем stdout
                stderr=subprocess.PIPE,  # Захватываем stderr
                universal_newlines=True,  # Декодировать байты в строки
                startupinfo=startupinfo
            )
            self._log(
                f"  Процесс FFmpeg запущен (PID: {self._current_process.pid if self._current_process else 'N/A'}). Ожидание завершения...",
                level="DEBUG")

            stdout, stderr = self._current_process.communicate(timeout=120)  # Таймаут 2 минуты
            return_code = self._current_process.returncode
            self._current_process = None  # Сбрасываем после завершения

            self._log(f"  Процесс FFmpeg завершен с кодом: {return_code}", level="INFO")

            if return_code == 0:
                if not os.path.exists(norm_output_path) or os.path.getsize(norm_output_path) == 0:
                    self._log(
                        f"  ВНИМАНИЕ: FFmpeg вернул 0, но выходной файл '{norm_output_path}' не существует или пуст!",
                        level="ERROR")
                    if stderr: self._log(f"    FFmpeg STDERR (при успехе, но пустом файле): {stderr.strip()}",
                                         level="WARN")
                    return False
                self._log(f"  Клип успешно нарезан и сохранен: {os.path.basename(norm_output_path)}")
                return True
            else:
                self._log(f"  ОШИБКА FFmpeg при нарезке клипа (код возврата: {return_code}):", level="ERROR")
                if stdout: self._log(f"    FFmpeg STDOUT: {stdout.strip()}",
                                     level="WARN")  # Может содержать полезную информацию
                if stderr: self._log(f"    FFmpeg STDERR: {stderr.strip()}", level="ERROR")  # Основные ошибки здесь

                if os.path.exists(norm_output_path):  # Попытка удалить частично созданный файл
                    try:
                        os.remove(norm_output_path)
                        self._log(f"    Частично созданный файл {os.path.basename(norm_output_path)} удален.",
                                  level="DEBUG")
                    except OSError as e_rem:
                        self._log(
                            f"    Не удалось удалить частично созданный файл {os.path.basename(norm_output_path)}: {e_rem}",
                            level="WARN")
                return False
        except FileNotFoundError:
            self._log(
                f"КРИТИЧЕСКАЯ ОШИБКА: FFmpeg не найден по пути '{self.ffmpeg_path}'. Убедитесь, что FFmpeg установлен и указан в PATH или в настройках приложения.",
                level="CRITICAL")
            return False
        except subprocess.TimeoutExpired:
            self._log(
                "  ОШИБКА FFmpeg: Время ожидания операции истекло (120 секунд). Процесс будет принудительно завершен.",
                level="ERROR")
            if self._current_process:
                self._current_process.kill()
                stdout, stderr = self._current_process.communicate()
                self._log(f"    FFmpeg STDOUT (после kill): {stdout.strip() if stdout else ''}", level="WARN")
                self._log(f"    FFmpeg STDERR (после kill): {stderr.strip() if stderr else ''}", level="ERROR")
            self._current_process = None
            return False
        except Exception as e:
            self._log(f"  НЕПРЕДВИДЕННАЯ ОШИБКА при вызове FFmpeg: {type(e).__name__} - {e}", level="CRITICAL")
            import traceback
            self._log(f"    Traceback: {traceback.format_exc()}", level="DEBUG")
            if self._current_process:  # Если ошибка произошла после запуска, но до communicate
                try:
                    self._current_process.kill()
                except:
                    pass  # Игнорируем ошибки при kill
            self._current_process = None
            return False
        finally:
            self._current_process = None  # Убедимся, что сброшен