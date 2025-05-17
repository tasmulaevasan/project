# automated_content_creator/modules/export_module.py

import os
import shutil # Для простого "экспорта" путем копирования, если не требуется перекодирование

class ExportModule:
    def __init__(self, parent_logger=None): # Изменил parent на parent_logger
        self.parent_logger = parent_logger
        # Предустановки форматов (можно расширить и сделать настраиваемыми из GUI/Settings)
        self.presets = {
            "Original": { # Просто копирует нарезанный клип без изменений
                "description": "Исходный формат нарезанного клипа",
                "ffmpeg_params": [], # Не используется, т.к. это прямой экспорт нарезанного
                "recode": False # Флаг, указывающий на необходимость перекодирования
            },
            "Reels (9:16)": {
                "description": "Instagram Reels, TikTok, YouTube Shorts (вертикальный)",
                "target_resolution": "1080x1920", # Ширина x Высота
                "aspect_ratio": "9:16",
                "video_codec": "libx264", "audio_codec": "aac", "audio_bitrate": "160k", "crf": "22",
                "ffmpeg_params": [ # Примерные параметры для FFmpeg
                    "-vf", "scale='min(1080,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease,pad=1080:1920:(1080-iw*min(1080/iw,1920/ih))/2:(1920-ih*min(1080/iw,1920/ih))/2,setsar=1",
                    # Эта сложная строка пытается масштабировать и добавить черные полосы, сохраняя пропорции.
                    # Для чистого 9:16 без letterbox/pillarbox, если исходник другой, нужно кадрирование (crop)
                    # или более умное масштабирование.
                    # Простой вариант: "-vf", "scale=1080:1920,setsar=1" (может исказить, если AR не совпадает)
                    # Вариант с кропом до 9:16 (центральная часть):
                    # "-vf", "crop=ih*9/16:ih,scale=1080:1920,setsar=1" # Если видео шире 9:16
                    # "-vf", "crop=iw:iw*16/9,scale=1080:1920,setsar=1" # Если видео выше 9:16
                ],
                "recode": True
            },
            "YouTube Shorts (16:9)": { # Для YouTube Shorts также допустим 16:9
                "description": "YouTube Shorts (горизонтальный, до 60 сек)",
                "target_resolution": "1920x1080",
                "aspect_ratio": "16:9",
                "video_codec": "libx264", "audio_codec": "aac", "audio_bitrate": "160k", "crf": "22",
                "ffmpeg_params": ["-vf", "scale=1920:1080,setsar=1"], # Простое масштабирование
                "recode": True
            },
            # Можно добавить другие пресеты: "TikTok (HD)", "VK Clips" и т.д.
        }
        # CuttingEngine не должен быть здесь, он используется ДО экспорта
        # self.cutting_engine = CuttingEngine(parent_logger=parent_logger)

    def _log(self, message):
        if self.parent_logger and hasattr(self.parent_logger, 'log_message'):
            self.parent_logger.log_message(f"ExportModule: {message}")
        else:
            print(f"ExportModule (no logger): {message}")


    def export_clip(self, source_clip_path: str, output_folder: str,
                      preset_name: str = "Original", clip_filename: str = "exported_clip.mp4") -> str | None:
        """
        Экспортирует клип.
        Если preset_name="Original", то source_clip_path (уже нарезанный) просто копируется.
        Для других пресетов (в будущем) будет происходить перекодирование с помощью FFmpeg.

        Args:
            source_clip_path: Путь к УЖЕ НАРЕЗАННОМУ клипу (например, из CuttingEngine).
            output_folder: Папка для сохранения финального клипа.
            preset_name: Имя пресета из self.presets.
            clip_filename: Желаемое имя файла для экспортированного клипа.

        Returns:
            Полный путь к экспортированному файлу или None в случае ошибки.
        """
        if not os.path.exists(source_clip_path):
            self._log(f"Ошибка: Исходный нарезанный клип не найден: {source_clip_path}")
            return None

        if preset_name not in self.presets:
            self._log(f"Предупреждение: Неизвестный пресет '{preset_name}'. Используется 'Original'.")
            preset_name = "Original"

        preset_config = self.presets[preset_name]
        final_output_path = os.path.join(output_folder, clip_filename)
        os.makedirs(output_folder, exist_ok=True) # Убедимся, что папка существует

        self._log(f"Подготовка к экспорту клипа '{os.path.basename(source_clip_path)}' "
                  f"с пресетом '{preset_name}' в '{final_output_path}'")

        try:
            if not preset_config.get("recode", False) or preset_name == "Original":
                # Простое копирование, если не требуется перекодирование или это "Original"
                self._log(f"  Пресет '{preset_name}' не требует перекодирования. Копирование файла...")
                shutil.copy2(source_clip_path, final_output_path)
                self._log(f"  Клип успешно скопирован (экспортирован): {final_output_path}")
                return final_output_path
            else:
                # --- ЗАГЛУШКА ДЛЯ ПЕРЕКОДИРОВАНИЯ ---
                # В реальном приложении здесь был бы вызов FFmpeg с параметрами из preset_config
                self._log(f"  Пресет '{preset_name}' требует перекодирования (ФУНКЦИОНАЛ В РАЗРАБОТКЕ).")
                self._log(f"    Параметры для FFmpeg (пример): {' '.join(preset_config.get('ffmpeg_params', []))}")
                self._log(f"    Целевое разрешение: {preset_config.get('target_resolution', 'N/A')}")

                # Имитируем перекодирование путем копирования (для работоспособности примера)
                # TODO: Заменить на реальный вызов FFmpeg, используя self.parent_logger.cutting_engine.ffmpeg_path
                # и параметры из preset_config.
                # cutting_engine = self.parent_logger.cutting_engine # Доступ к CuttingEngine из MainWindow
                # ffmpeg_exe = cutting_engine.ffmpeg_path
                # command = [ffmpeg_exe, '-i', source_clip_path] + preset_config.get('ffmpeg_params', []) + [final_output_path]
                # ... (запуск subprocess с этой командой) ...
                shutil.copy2(source_clip_path, final_output_path) # Имитация
                self._log(f"  [ИМИТАЦИЯ ПЕРЕКОДИРОВАНИЯ] Клип сохранен как: {final_output_path}")
                # if success_recode:
                #    self._log(f"Клип успешно перекодирован и сохранен: {final_output_path}")
                #    return final_output_path
                # else:
                #    self._log(f"Ошибка при перекодировании клипа '{os.path.basename(source_clip_path)}' для пресета '{preset_name}'.")
                #    return None
                return final_output_path # Возвращаем путь после имитации

        except Exception as e:
            self._log(f"КРИТИЧЕСКАЯ ОШИБКА при экспорте клипа '{os.path.basename(source_clip_path)}': {type(e).__name__} - {e}")
            # Попытка удалить частично созданный файл
            if os.path.exists(final_output_path) and source_clip_path != final_output_path : # Не удалять исходник, если копируем в ту же папку с тем же именем
                try:
                    # Только если это не тот же файл (например, при ошибке копирования)
                    if not os.path.samefile(source_clip_path, final_output_path):
                        os.remove(final_output_path)
                        self._log(f"  Частично экспортированный файл {final_output_path} удален.")
                except Exception as e_rem:
                     self._log(f"  Не удалось удалить частично экспортированный файл {final_output_path}: {e_rem}")
            return None

    def get_available_presets(self):
        """Возвращает список имен доступных пресетов."""
        return list(self.presets.keys())

    def get_preset_config(self, preset_name):
        """Возвращает конфигурацию для указанного пресета."""
        return self.presets.get(preset_name)