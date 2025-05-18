# automated_content_creator/modules/export_module.py

import os
import shutil  # Для простого "экспорта" путем копирования, если не требуется перекодирование
import subprocess  # Для реального перекодирования FFmpeg


class ExportModule:
    def __init__(self, parent_logger=None):
        self.parent_logger = parent_logger
        self.presets = {
            "Original MP4": {
                "description": "Исходный формат нарезанного клипа (MP4). Копирование без перекодирования.",
                "ffmpeg_params": [],
                "recode": False,
                "extension": ".mp4"  # Явно указываем расширение
            },
            "Reels (9:16, MP4)": {
                "description": "Instagram Reels, TikTok, YouTube Shorts (вертикальный MP4).",
                "target_resolution": "1080x1920",
                "aspect_ratio": "9:16",
                "video_codec": "libx264", "audio_codec": "aac", "audio_bitrate": "160k", "crf": "22",
                "ffmpeg_params_template": [  # Используем шаблон, т.к. input/output будут добавлены
                    "-vf",
                    "scale='min(1080,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease,pad=1080:1920:(1080-iw*min(1080/iw,1920/ih))/2:(1920-ih*min(1080/iw,1920/ih))/2,setsar=1",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                    "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart"
                ],
                "recode": True,
                "extension": ".mp4"
            },
            "YouTube Shorts (16:9, MP4)": {
                "description": "YouTube Shorts (горизонтальный MP4, до 60 сек).",
                "target_resolution": "1920x1080",
                "aspect_ratio": "16:9",
                "video_codec": "libx264", "audio_codec": "aac", "audio_bitrate": "160k", "crf": "22",
                "ffmpeg_params_template": [
                    "-vf", "scale=1920:1080,setsar=1",  # Простое масштабирование
                    "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                    "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart"
                ],
                "recode": True,
                "extension": ".mp4"
            },
            # Можно добавить другие пресеты, например, для GIF
            "Animated GIF (Low Quality)": {
                "description": "Анимированный GIF, низкое качество, малый размер.",
                "target_resolution": "480x-1",  # Ширина 480, высота авто
                "fps": 10,
                "ffmpeg_params_template": [
                    "-vf", "fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                ],
                "recode": True,
                "extension": ".gif"
            }
        }

    def _log(self, message, level="INFO"):  # Добавил level по умолчанию
        if self.parent_logger and hasattr(self.parent_logger, 'log_message'):
            # Предполагается, что parent_logger это MainWindow, у которого есть log_message
            self.parent_logger.log_message(f"(ExportModule) {message}", level=level)
        else:
            print(f"ExportModule [{level}] (no logger): {message}")

    def export_clip(self, source_clip_path: str, output_folder: str,
                    preset_name: str = "Original MP4", clip_filename: str = "exported_clip.mp4") -> str | None:
        """
        Экспортирует клип согласно выбранному пресету.
        """
        if not os.path.exists(source_clip_path):
            self._log(f"Ошибка: Исходный нарезанный клип не найден: {source_clip_path}", level="ERROR")
            return None

        if preset_name not in self.presets:
            self._log(f"Предупреждение: Неизвестный пресет '{preset_name}'. Используется 'Original MP4'.", level="WARN")
            preset_name = "Original MP4"

        preset_config = self.presets[preset_name]
        # Имя файла теперь должно приходить с правильным расширением от ClipExporterWorker
        final_output_path = os.path.join(output_folder, clip_filename)
        os.makedirs(output_folder, exist_ok=True)

        self._log(f"Подготовка к экспорту клипа '{os.path.basename(source_clip_path)}' "
                  f"с пресетом '{preset_name}' в '{final_output_path}'", level="INFO")

        try:
            if not preset_config.get("recode", False):
                self._log(f"  Пресет '{preset_name}' не требует перекодирования. Копирование файла...", level="DEBUG")
                shutil.copy2(source_clip_path, final_output_path)
                self._log(f"  Клип успешно скопирован (экспортирован): {final_output_path}", level="INFO")
                return final_output_path
            else:
                self._log(f"  Пресет '{preset_name}' требует перекодирования.", level="INFO")

                ffmpeg_exe = "ffmpeg"  # По умолчанию
                if self.parent_logger and hasattr(self.parent_logger,
                                                  'cutting_engine') and self.parent_logger.cutting_engine:
                    ffmpeg_exe = self.parent_logger.cutting_engine.ffmpeg_path

                base_command = [
                    ffmpeg_exe,
                    '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', source_clip_path
                ]

                preset_ffmpeg_params = preset_config.get("ffmpeg_params_template", [])

                # Обработка плейсхолдеров в параметрах FFmpeg (для GIF)
                formatted_params = []
                for param in preset_ffmpeg_params:
                    if isinstance(param, str):
                        param = param.replace("{fps}", str(preset_config.get("fps", 10)))
                        param = param.replace("{width}",
                                              str(preset_config.get("target_resolution", "480x-1").split('x')[0]))
                    formatted_params.append(param)

                full_command = base_command + formatted_params + [final_output_path]

                self._log(f"    Команда FFmpeg: {' '.join(full_command)}", level="DEBUG")

                process = subprocess.Popen(
                    full_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                stdout, stderr = process.communicate(timeout=180)  # Таймаут 3 минуты для перекодирования

                if process.returncode == 0:
                    if not os.path.exists(final_output_path) or os.path.getsize(final_output_path) == 0:
                        self._log(
                            f"  ВНИМАНИЕ: FFmpeg (recode) вернул 0, но файл '{final_output_path}' не найден или пуст. STDERR: {stderr.strip()}",
                            level="ERROR")
                        return None
                    self._log(f"  Клип успешно перекодирован и сохранен: {final_output_path}", level="INFO")
                    return final_output_path
                else:
                    self._log(f"  ОШИБКА FFmpeg при перекодировании (код {process.returncode}): {stderr.strip()}",
                              level="ERROR")
                    if os.path.exists(final_output_path):
                        try:
                            os.remove(final_output_path)
                        except OSError:
                            pass
                    return None

        except subprocess.TimeoutExpired:
            self._log(f"  ОШИБКА: Время ожидания FFmpeg для перекодирования истекло (пресет '{preset_name}').",
                      level="ERROR")
            if process: process.kill()
            if os.path.exists(final_output_path):
                try:
                    os.remove(final_output_path)
                except OSError:
                    pass
            return None
        except Exception as e:
            self._log(
                f"КРИТИЧЕСКАЯ ОШИБКА при экспорте (перекодировании) клипа '{os.path.basename(source_clip_path)}': {type(e).__name__} - {e}",
                level="CRITICAL")
            import traceback
            self._log(f"Traceback: {traceback.format_exc()}", level="DEBUG")
            if os.path.exists(final_output_path) and source_clip_path != final_output_path:
                try:
                    if not os.path.samefile(source_clip_path, final_output_path):
                        os.remove(final_output_path)
                except Exception:
                    pass
            return None

    def get_available_presets(self):
        """Возвращает список имен доступных пресетов."""
        return list(self.presets.keys())

    def get_preset_config(self, preset_name):
        """Возвращает конфигурацию для указанного пресета."""
        return self.presets.get(preset_name)

    def get_preset_extension(self, preset_name: str) -> str:
        """Возвращает расширение файла для данного пресета."""
        config = self.get_preset_config(preset_name)
        if config and "extension" in config:
            return config["extension"]
        self._log(f"Предупреждение: Расширение не найдено для пресета '{preset_name}'. Возврат '.mp4'.", level="WARN")
        return ".mp4"  # Расширение по умолчанию

