# automated_content_creator/modules/clip_exporter_worker.py

import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal, QDateTime
import re

try:
    from sanitize_filename import sanitize as original_sanitize
except ImportError:
    print("ПРЕДУПРЕЖДЕНИЕ: Библиотека 'sanitize-filename' не найдена. Используется базовый внутренний санитайзер.")
    original_sanitize = None


def fallback_sanitize(filename_str: str, max_len: int = 60) -> str:  # Увеличил немного max_len по умолчанию
    if not isinstance(filename_str, str):
        filename_str = str(filename_str)
    temp_desc = re.sub(r'[<>:"/\\|?*]', '_', filename_str)
    temp_desc = re.sub(r'[\x00-\x1f\x7f]', '', temp_desc)
    temp_desc = re.sub(r'[\s\.\(\)]+', '_', temp_desc)
    temp_desc = re.sub(r'_+', '_', temp_desc)
    temp_desc = temp_desc.strip('_')
    if not temp_desc:
        return "sanitized_empty_name"
    name_part, ext_part = os.path.splitext(temp_desc)
    if len(ext_part) > 10:
        name_part = temp_desc
        ext_part = ""
    available_len_for_name = max_len - len(ext_part)
    if available_len_for_name < 0:
        return temp_desc[:max_len]
    name_part = name_part[:available_len_for_name]
    return name_part + ext_part


class ClipExporterWorker(QObject):
    export_progress = pyqtSignal(int, int, str)
    export_finished_one = pyqtSignal(str, bool, str)  # path, success, original_description
    export_all_finished = pyqtSignal(list, int)
    export_error = pyqtSignal(str)

    def __init__(self, cutting_engine, export_module_instance, parent_logger=None):
        super().__init__()
        self.cutting_engine = cutting_engine
        self.export_module = export_module_instance  # Теперь это экземпляр ExportModule
        self.parent_logger = parent_logger
        self._is_cancelled = False
        self.temp_dir_for_cutting = ""
        self._log_prefix = self.__class__.__name__
        self._log(f"Инициализирован.", level="DEBUG")

    def _log(self, message: str, level: str = "INFO"):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        full_message = f"{timestamp} [{self._log_prefix}] [{level}]: {message}"
        if self.parent_logger and hasattr(self.parent_logger, 'log_message'):
            self.parent_logger.log_message(f"({self._log_prefix}) {message}", level=level)
        else:
            print(full_message)

    def cancel_export(self):
        self._log("Получен запрос на отмену экспорта.", level="WARN")
        self._is_cancelled = True
        if self.cutting_engine and hasattr(self.cutting_engine, 'cancel_current_operation'):
            self.cutting_engine.cancel_current_operation()
        # Дополнительно можно попробовать отменить операцию в export_module, если она длительная (например, FFmpeg процесс)
        # if self.export_module and hasattr(self.export_module, 'cancel_current_operation'):
        # self.export_module.cancel_current_operation() # Потребует реализации в ExportModule

    def set_temp_dir(self, path: str):
        self._log(f"set_temp_dir: Попытка установить временную папку: '{path}'", level="DEBUG")
        try:
            self.temp_dir_for_cutting = os.path.normpath(path)
            os.makedirs(self.temp_dir_for_cutting, exist_ok=True)
            self._log(f"set_temp_dir: Временная папка для нарезки успешно установлена: '{self.temp_dir_for_cutting}'",
                      level="INFO")
        except Exception as e:
            error_msg = f"set_temp_dir: КРИТИЧЕСКАЯ ОШИБКА создания временной папки '{path}': {e}. Trace: {traceback.format_exc()}"
            self._log(error_msg, level="CRITICAL")
            self.temp_dir_for_cutting = ""  # Сбрасываем, чтобы предотвратить использование
            self.export_error.emit(f"Не удалось создать временную папку: {e}")

    def process_export_list(self, original_video_path: str, highlights_to_export: list,
                            output_folder: str, export_preset_name: str):  # export_preset_name теперь обязателен
        self._log(
            f"process_export_list: Начало обработки. Клипов: {len(highlights_to_export)}. Пресет: '{export_preset_name}'.",
            level="INFO")

        if not self.cutting_engine:
            # ... (обработка ошибки)
            return
        if not self.export_module:
            # ... (обработка ошибки)
            return
        if not self.temp_dir_for_cutting or not os.path.isdir(self.temp_dir_for_cutting):
            error_msg = f"КРИТИЧЕСКАЯ ОШИБКА: Временная папка для нарезки ('{self.temp_dir_for_cutting}') не установлена или не является директорией. Экспорт прерван."
            self._log(error_msg, level="CRITICAL")
            self.export_error.emit(error_msg)
            self.export_all_finished.emit([], 0)  # Сигнализируем о завершении без успеха
            return

        total_clips = len(highlights_to_export)
        exported_clips_info_list = []
        successful_exports_count = 0

        norm_original_video_path = os.path.normpath(original_video_path)
        norm_output_folder = os.path.normpath(output_folder)

        # Получаем расширение файла из пресета
        target_extension = self.export_module.get_preset_extension(export_preset_name)
        self._log(f"  Целевое расширение для пресета '{export_preset_name}': '{target_extension}'", level="DEBUG")

        for i, hl_data in enumerate(highlights_to_export):
            if self._is_cancelled:
                self._log("Экспорт отменен в цикле обработки клипов.", level="INFO")
                break  # Выходим из цикла for

            current_clip_number = i + 1
            original_description = hl_data.get('description', f'highlight_{current_clip_number}')
            self._log(f"--- Начало обработки клипа #{current_clip_number}/{total_clips}: '{original_description}' ---",
                      level="INFO")
            self.export_progress.emit(current_clip_number, total_clips, original_description)

            start_sec = hl_data.get('start_time')
            end_sec = hl_data.get('end_time')

            if start_sec is None or end_sec is None or end_sec <= start_sec:
                self._log(
                    f"  Пропуск хайлайта '{original_description}': некорректное время (start: {start_sec}, end: {end_sec}).",
                    level="WARN")
                self.export_finished_one.emit("", False, original_description)
                continue

            # Санитайзер имени файла
            sanitized_desc_part = ""
            try:
                desc_str = str(original_description)
                if original_sanitize:
                    base_sanitized = original_sanitize(desc_str)
                    # Обрезка, если sanitize-filename не контролирует длину
                    if len(base_sanitized) > 50:  # Макс. длина для части описания в имени
                        name_part_s, ext_part_s = os.path.splitext(base_sanitized)
                        if len(ext_part_s) > 10: name_part_s = base_sanitized; ext_part_s = ""
                        available_len_s = 50 - len(ext_part_s)
                        if available_len_s < 0: available_len_s = 0
                        name_part_s = name_part_s[:available_len_s]
                        sanitized_desc_part = name_part_s + ext_part_s
                    else:
                        sanitized_desc_part = base_sanitized
                else:
                    sanitized_desc_part = fallback_sanitize(desc_str, max_len=50)
                if not sanitized_desc_part: sanitized_desc_part = f"clip_{current_clip_number}"
                self._log(f"    Sanitized description: '{sanitized_desc_part}'", level="DEBUG")
            except Exception as e_sanitize:
                self._log(f"    ОШИБКА sanitize: {e_sanitize}. Используется заглушка.", level="ERROR")
                sanitized_desc_part = f"sanitize_error_{current_clip_number}"

            clip_num_str = str(current_clip_number).zfill(3)
            preset_str_clean = re.sub(r'[^a-zA-Z0-9_-]', '', str(export_preset_name).lower().replace(' ', '_'))

            base_filename_parts = ["clip", clip_num_str, sanitized_desc_part, preset_str_clean]
            base_filename_no_ext = "_".join(filter(None, base_filename_parts))
            base_filename_no_ext = re.sub(r'_+', '_', base_filename_no_ext).strip('_')
            self._log(f"  Сгенерировано базовое имя (без расширения): '{base_filename_no_ext}'", level="DEBUG")

            # Временный файл всегда MP4, т.к. cutting_engine выдает MP4
            temp_cut_clip_filename = f"{base_filename_no_ext}_tempcut.mp4"
            temp_cut_clip_path = os.path.normpath(os.path.join(self.temp_dir_for_cutting, temp_cut_clip_filename))
            self._log(f"  Путь для временного файла нарезки: '{temp_cut_clip_path}'", level="DEBUG")

            success_cut = False
            try:
                success_cut = self.cutting_engine.cut_clip(
                    norm_original_video_path, start_sec, end_sec, temp_cut_clip_path
                )
            except Exception as e_cut_eng:
                self._log(f"  КРИТИЧЕСКАЯ ОШИБКА cutting_engine.cut_clip: {e_cut_eng}\n{traceback.format_exc()}",
                          level="CRITICAL")
                success_cut = False  # Убедимся, что false

            if self._is_cancelled:  # Проверка отмены ПОСЛЕ вызова cutting_engine.cut_clip
                self._log(f"Экспорт прерван пользователем после попытки нарезки клипа '{original_description}'.",
                          level="WARN")
                if os.path.exists(temp_cut_clip_path):
                    try:
                        os.remove(temp_cut_clip_path)
                    except OSError as e_rem_cancel:  # Исправлено: catch на except, добавлена переменная для ошибки
                        self._log(
                            f"  Не удалось удалить временный файл '{temp_cut_clip_path}' после отмены (после нарезки): {e_rem_cancel}",
                            level="WARN")  # Логируем ошибку удаления
                        pass  # Продолжаем, так как отмена важнее
                break  # Выходим из цикла for

            if success_cut:
                self._log(f"  Клип '{original_description}' УСПЕШНО НАРЕЗАН: '{temp_cut_clip_path}'", level="INFO")
                if not os.path.exists(temp_cut_clip_path) or os.path.getsize(temp_cut_clip_path) == 0:
                    self._log(f"  ВНИМАНИЕ: Нарезка успешна, но файл '{temp_cut_clip_path}' не существует или пуст!",
                              level="ERROR")
                    self.export_finished_one.emit("", False, original_description)
                    continue

                # Формируем имя финального файла с правильным расширением из пресета
                final_export_filename_with_ext = f"{base_filename_no_ext}{target_extension}"

                # Проверка на существование и добавление индекса (опционально, но хорошо бы)
                final_path_candidate = os.path.join(norm_output_folder, final_export_filename_with_ext)
                counter = 1
                actual_final_filename = final_export_filename_with_ext
                while os.path.exists(os.path.join(norm_output_folder, actual_final_filename)):
                    actual_final_filename = f"{base_filename_no_ext}_{counter}{target_extension}"
                    counter += 1
                    if counter > 100:  # Защита
                        self._log(f"  Слишком много файлов с именем {base_filename_no_ext}. Перезапись.", level="WARN")
                        actual_final_filename = f"{base_filename_no_ext}_override{target_extension}"
                        break
                if actual_final_filename != final_export_filename_with_ext:
                    self._log(
                        f"    Файл '{final_export_filename_with_ext}' уже существует. Новое имя: '{actual_final_filename}'",
                        level="INFO")

                self._log(f"    Подготовка к финальному экспорту. Имя файла: '{actual_final_filename}'", level="DEBUG")

                exported_final_path = None
                try:
                    exported_final_path = self.export_module.export_clip(
                        source_clip_path=temp_cut_clip_path,
                        output_folder=norm_output_folder,
                        preset_name=export_preset_name,
                        clip_filename=actual_final_filename  # Передаем имя с расширением
                    )
                except Exception as e_export_mod:
                    self._log(
                        f"  КРИТИЧЕСКАЯ ОШИБКА export_module.export_clip: {e_export_mod}\n{traceback.format_exc()}",
                        level="CRITICAL")

                if self._is_cancelled:
                    self._log(f"Экспорт прерван после попытки финального экспорта клипа '{original_description}'.",
                              level="WARN")
                    if os.path.exists(temp_cut_clip_path):
                        try:
                            os.remove(temp_cut_clip_path)
                        except OSError:  # Исправлено: catch на except
                            # Логируем или обрабатываем ошибку удаления, если нужно, но часто можно просто pass
                            self._log(
                                f"  Не удалось удалить временный файл '{temp_cut_clip_path}' после отмены (финальный экспорт).",
                                level="DEBUG_EXTRA")
                            pass
                    if exported_final_path and os.path.exists(exported_final_path):
                        try:
                            os.remove(exported_final_path)
                        except OSError:  # Исправлено: catch на except
                            self._log(
                                f"  Не удалось удалить экспортированный файл '{exported_final_path}' после отмены.",
                                level="DEBUG_EXTRA")
                            pass
                    break  # Выходим из цикла for

                if exported_final_path:
                    self._log(f"    Клип '{original_description}' УСПЕШНО ЭКСПОРТИРОВАН: '{exported_final_path}'",
                              level="INFO")
                    clip_info_for_plan = {
                        "path": exported_final_path,
                        "description": original_description,
                        "title_suggestion": f"Яркий момент: {original_description}",
                        "source_highlight_info": hl_data.copy()  # Копируем исходные данные хайлайта
                    }
                    exported_clips_info_list.append(clip_info_for_plan)
                    successful_exports_count += 1
                    self.export_finished_one.emit(exported_final_path, True, original_description)
                else:
                    self._log(
                        f"    ОШИБКА ФИНАЛЬНОГО ЭКСПОРТА '{original_description}' (preset: '{export_preset_name}').",
                        level="ERROR")
                    self.export_finished_one(temp_cut_clip_path, False,
                                             original_description)  # Нарезан, но не экспортирован
            else:  # Ошибка нарезки
                self._log(f"  ОШИБКА НАРЕЗКИ клипа '{original_description}'. Пропуск.", level="ERROR")
                self.export_finished_one.emit("", False, original_description)

            # Удаление временного нарезанного файла
            if os.path.exists(temp_cut_clip_path):
                try:
                    os.remove(temp_cut_clip_path)
                    self._log(f"    Временный файл '{os.path.basename(temp_cut_clip_path)}' УДАЛЕН.", level="DEBUG")
                except OSError as e_rem:
                    self._log(
                        f"    НЕ УДАЛОСЬ удалить временный файл '{os.path.basename(temp_cut_clip_path)}': {e_rem}",
                        level="WARN")
            elif success_cut:  # Если нарезка была успешной, а файла нет - это странно
                self._log(
                    f"   ВНИМАНИЕ: Нарезка '{original_description}' успешна, но временный файл '{temp_cut_clip_path}' НЕ НАЙДЕН для удаления.",
                    level="WARN")
            self._log(f"--- Завершение обработки клипа #{current_clip_number}: '{original_description}' ---",
                      level="INFO")

        # После цикла
        if self._is_cancelled:
            self._log(
                f"Процесс экспорта был ПРЕРВАН. Успешно экспортировано до отмены: {successful_exports_count} из {total_clips} клипов.",
                level="WARN")
        else:
            self._log(
                f"Процесс экспорта ЗАВЕРШЕН. Успешно экспортировано: {successful_exports_count} из {total_clips} клипов.",
                level="INFO")

        self.export_all_finished.emit(exported_clips_info_list, successful_exports_count)
        self._log(f"Сигнал export_all_finished отправлен. Завершение работы воркера.", level="DEBUG")

