# automated_content_creator/modules/clip_exporter_worker.py

import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal, QDateTime
import re

try:
    from sanitize_filename import sanitize as original_sanitize
except ImportError:
    print("ПРЕДУПРЕЖДЕНИЕ: Библиотека 'sanitize-filename' не найдена...")  # Сокращено для краткости
    original_sanitize = None


class ClipExporterWorker(QObject):
    export_progress = pyqtSignal(int, int, str)
    export_finished_one = pyqtSignal(str, bool, str)  # path, success, original_description
    export_all_finished = pyqtSignal(list, int)
    export_error = pyqtSignal(str)

    def __init__(self, cutting_engine, export_module_instance, parent_logger=None):
        super().__init__()
        # ... (конструктор без изменений) ...
        self.cutting_engine = cutting_engine
        self.export_module = export_module_instance
        self.parent_logger = parent_logger
        self._is_cancelled = False
        self.temp_dir_for_cutting = ""
        self._log_prefix = self.__class__.__name__
        self._log(f"Инициализирован.", level="DEBUG")

    def _log(self, message: str, level: str = "INFO"):
        # ... (логгер без изменений) ...
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        full_message = f"{timestamp} [{self._log_prefix}] [{level}]: {message}"
        if self.parent_logger and hasattr(self.parent_logger, 'log_message'):
            self.parent_logger.log_message(f"({self._log_prefix}) {message}", level=level)
        else:
            print(full_message)

    def cancel_export(self):
        # ... (без изменений) ...
        self._log("Получен запрос на отмену экспорта.", level="WARN")
        self._is_cancelled = True
        if self.cutting_engine and hasattr(self.cutting_engine, 'cancel_current_operation'):
            self.cutting_engine.cancel_current_operation()

    def set_temp_dir(self, path: str):
        # ... (без изменений) ...
        self._log(f"set_temp_dir: Попытка установить временную папку: '{path}'", level="DEBUG")
        try:
            self.temp_dir_for_cutting = os.path.normpath(path)
            os.makedirs(self.temp_dir_for_cutting, exist_ok=True)
            self._log(
                f"set_temp_dir: Временная папка для нарезки успешно установлена и создана: '{self.temp_dir_for_cutting}'",
                level="INFO")
        except Exception as e:
            error_msg = f"set_temp_dir: КРИТИЧЕСКАЯ ОШИБКА создания временной папки '{path}': {e}. Trace: {traceback.format_exc()}"
            self._log(error_msg, level="CRITICAL")
            self.temp_dir_for_cutting = ""
            self.export_error.emit(f"Не удалось создать временную папку: {e}")

    def process_export_list(self, original_video_path: str, highlights_to_export: list,
                            output_folder: str, export_preset_name: str = "Original"):
        # ... (начало метода без изменений до цикла) ...
        self._log(f"process_export_list: Начало обработки списка для экспорта. Клипов: {len(highlights_to_export)}.",
                  level="INFO")
        # ... (проверки и нормализация путей) ...
        if self._is_cancelled:  # Добавлена проверка перед циклом
            self._log("process_export_list: Экспорт был отменен до начала цикла обработки.", level="WARN")
            self.export_all_finished.emit([], 0)
            return

        if not self.temp_dir_for_cutting or not os.path.isdir(self.temp_dir_for_cutting):
            error_msg = f"КРИТИЧЕСКАЯ ОШИБКА: Временная папка для нарезки ('{self.temp_dir_for_cutting}') не установлена или не является директорией. Экспорт прерван."
            self._log(error_msg, level="CRITICAL")
            self.export_error.emit(error_msg)
            self.export_all_finished.emit([], 0)
            return

        total_clips = len(highlights_to_export)
        exported_clips_info_list = []
        successful_exports_count = 0

        norm_original_video_path = os.path.normpath(original_video_path)
        norm_output_folder = os.path.normpath(output_folder)
        self._log(f"  Нормализованные пути: видео='{norm_original_video_path}', вывод='{norm_output_folder}'",
                  level="DEBUG")

        for i, hl_data in enumerate(highlights_to_export):
            if self._is_cancelled:
                self._log("Экспорт отменен", level="INFO")
                self.export_all_finished.emit([], 0)
                return
            current_clip_number = i + 1
            original_description = hl_data.get('description', f'highlight_{current_clip_number}')
            self._log(f"--- Начало обработки клипа #{current_clip_number}/{total_clips}: '{original_description}' ---",
                      level="INFO")

            if self._is_cancelled:
                self._log(f"Экспорт прерван пользователем на клипе #{current_clip_number} ('{original_description}').",
                          level="WARN")
                break

            self.export_progress.emit(current_clip_number, total_clips, original_description)

            start_sec = hl_data.get('start_time')
            end_sec = hl_data.get('end_time')

            if start_sec is None or end_sec is None or end_sec <= start_sec:
                self._log(
                    f"  Пропуск хайлайта '{original_description}': некорректное время (start: {start_sec}, end: {end_sec}).",
                    level="WARN")
                self.export_finished_one("", False, original_description)
                continue

            self._log(f"  Время для нарезки: {start_sec:.3f}с - {end_sec:.3f}с.", level="DEBUG")

            self._log(
                f"    Перед sanitize: original_description='{original_description}' (Тип: {type(original_description)})",
                level="DEBUG")
            sanitized_desc_part = ""
            try:
                temp_desc = str(original_description)
                temp_desc = re.sub(r'[<>:"/\\|?*]', '_', temp_desc)
                temp_desc = re.sub(r'[\s\.\(\)]+', '_', temp_desc)
                temp_desc = re.sub(r'_+', '_', temp_desc)
                temp_desc = temp_desc.strip('_')
                if len(temp_desc) > 50:
                    name_part, ext_part = os.path.splitext(temp_desc)
                    if len(ext_part) > 10:
                        name_part = temp_desc
                        ext_part = ""
                    available_len_for_name = 50 - len(ext_part)
                    if available_len_for_name < 0: available_len_for_name = 0
                    name_part = name_part[:available_len_for_name]
                    sanitized_desc_part = name_part + ext_part
                else:
                    sanitized_desc_part = temp_desc
                self._log(
                    f"    ВРЕМЕННЫЙ sanitize: sanitized_desc_part='{sanitized_desc_part}' (Длина: {len(sanitized_desc_part)})",
                    level="INFO")
            except Exception as e_sanitize:
                self._log(f"    КРИТИЧЕСКАЯ ОШИБКА во время (тестового) sanitize: {e_sanitize}", level="CRITICAL")
                self._log(f"    Traceback sanitize: {traceback.format_exc()}", level="DEBUG")
                sanitized_desc_part = "sanitize_error"
            self._log(f"    После блока sanitize: sanitized_desc_part='{sanitized_desc_part}'", level="DEBUG")

            clip_num_str = str(current_clip_number).zfill(3)
            self._log(f"    clip_num_str='{clip_num_str}'", level="DEBUG")
            preset_str = str(export_preset_name).lower().replace('(', '').replace(')', '').replace(':', '').replace(' ',
                                                                                                                    '_')
            self._log(f"    preset_str='{preset_str}'", level="DEBUG")
            base_filename_parts = ["clip", clip_num_str, sanitized_desc_part, preset_str]
            self._log(f"    base_filename_parts={base_filename_parts}", level="DEBUG")
            filtered_parts = [part for part in base_filename_parts if part]
            self._log(f"    filtered_parts={filtered_parts}", level="DEBUG")
            base_filename = "_".join(filtered_parts)
            self._log(f"  Сгенерировано базовое имя файла: '{base_filename}'", level="INFO")

            temp_cut_clip_filename = f"{base_filename}_tempcut.mp4"
            temp_cut_clip_path = os.path.normpath(os.path.join(self.temp_dir_for_cutting, temp_cut_clip_filename))
            self._log(f"  Путь для временного файла нарезки: '{temp_cut_clip_path}'", level="INFO")

            success_cut = False
            self._log(f"  Попытка нарезки (cutting_engine.cut_clip)...", level="DEBUG")
            try:
                success_cut = self.cutting_engine.cut_clip(
                    norm_original_video_path, start_sec, end_sec, temp_cut_clip_path
                )
            except Exception as e_cut_eng:
                self._log(
                    f"  КРИТИЧЕСКАЯ ОШИБКА при вызове cutting_engine.cut_clip для '{original_description}': {e_cut_eng}",
                    level="CRITICAL")
                self._log(f"    Traceback: {traceback.format_exc()}", level="DEBUG")
                success_cut = False

            if self._is_cancelled:
                self._log(f"Экспорт прерван после попытки нарезки клипа '{original_description}'.", level="WARN")
                if os.path.exists(temp_cut_clip_path):
                    try:
                        os.remove(temp_cut_clip_path)
                    except OSError as e_rem_cancel:
                        self._log(
                            f"  Не удалось удалить временный файл '{temp_cut_clip_path}' после отмены: {e_rem_cancel}",
                            level="WARN")
                break

            if success_cut:
                self._log(f"  Клип '{original_description}' УСПЕШНО НАРЕЗАН: '{temp_cut_clip_path}'", level="INFO")
                if not os.path.exists(temp_cut_clip_path) or os.path.getsize(temp_cut_clip_path) == 0:
                    self._log(
                        f"  ВНИМАНИЕ: Нарезка считалась успешной, но файл '{temp_cut_clip_path}' не существует или пуст!",
                        level="ERROR")
                    self.export_finished_one("", False, original_description)
                    continue

                final_export_filename_ext = f"{base_filename}.mp4"
                self._log(
                    f"    Подготовка к финальному экспорту с пресетом '{export_preset_name}'. Имя файла: '{final_export_filename_ext}'",
                    level="DEBUG")

                exported_final_path = None
                try:
                    exported_final_path = self.export_module.export_clip(
                        source_clip_path=temp_cut_clip_path,
                        output_folder=norm_output_folder,
                        preset_name=export_preset_name,
                        clip_filename=final_export_filename_ext
                    )
                except Exception as e_export_mod:
                    self._log(
                        f"  КРИТИЧЕСКАЯ ОШИБКА при вызове export_module.export_clip для '{original_description}': {e_export_mod}",
                        level="CRITICAL")
                    self._log(f"    Traceback: {traceback.format_exc()}", level="DEBUG")

                if self._is_cancelled:
                    self._log(f"Экспорт прерван после попытки финального экспорта клипа '{original_description}'.",
                              level="WARN")
                    # ... (удаление файлов при отмене)
                    if os.path.exists(temp_cut_clip_path):
                        try:
                            os.remove(temp_cut_clip_path)
                        except OSError:
                            pass
                    if exported_final_path and os.path.exists(exported_final_path):
                        try:
                            os.remove(exported_final_path)
                        except OSError:
                            pass
                    break

                if exported_final_path:
                    self._log(f"    Клип '{original_description}' УСПЕШНО ЭКСПОРТИРОВАН: '{exported_final_path}'",
                              level="INFO")  # ПОСЛЕДНИЙ ВИДИМЫЙ ЛОГ
                    clip_info_for_plan = {
                        "path": exported_final_path,
                        "description": original_description,
                        "title_suggestion": f"Яркий момент: {original_description}",
                        "source_highlight_info": hl_data.copy()
                    }
                    exported_clips_info_list.append(clip_info_for_plan)
                    successful_exports_count += 1

                    self._log(f"    Перед emit export_finished_one для '{original_description}'",
                              level="DEBUG_DEEP")  # Новый лог
                    try:
                        self.export_finished_one.emit(exported_final_path, True, original_description)
                        self._log(f"    После emit export_finished_one для '{original_description}'",
                                  level="DEBUG_DEEP")  # Новый лог
                    except Exception as e_emit:
                        self._log(f"    КРИТИЧЕСКАЯ ОШИБКА при emit export_finished_one: {e_emit}", level="CRITICAL")
                        self._log(f"    Traceback emit: {traceback.format_exc()}", level="DEBUG")
                        # Продолжаем, но это плохо
                else:
                    self._log(
                        f"    ОШИБКА ФИНАЛЬНОГО ЭКСПОРТА '{original_description}' (preset: '{export_preset_name}').",
                        level="ERROR")
                    self._log(f"    Перед emit export_finished_one (ошибка экспорта) для '{original_description}'",
                              level="DEBUG_DEEP")
                    self.export_finished_one(temp_cut_clip_path, False,
                                             original_description)  # Нарезан, но не экспортирован
                    self._log(f"    После emit export_finished_one (ошибка экспорта) для '{original_description}'",
                              level="DEBUG_DEEP")
            else:  # Ошибка нарезки
                self._log(f"  ОШИБКА НАРЕЗКИ клипа '{original_description}'. Пропуск.", level="ERROR")
                self._log(f"    Перед emit export_finished_one (ошибка нарезки) для '{original_description}'",
                          level="DEBUG_DEEP")
                self.export_finished_one("", False, original_description)
                self._log(f"    После emit export_finished_one (ошибка нарезки) для '{original_description}'",
                          level="DEBUG_DEEP")

            # Удаление временного нарезанного файла
            self._log(f"    Проверка существования временного файла '{temp_cut_clip_path}' для удаления...",
                      level="DEBUG_DEEP")
            temp_file_exists = False
            try:
                temp_file_exists = os.path.exists(temp_cut_clip_path)
                self._log(f"    os.path.exists('{temp_cut_clip_path}') вернул: {temp_file_exists}", level="DEBUG_DEEP")
            except Exception as e_exists:
                self._log(f"    Ошибка при вызове os.path.exists для '{temp_cut_clip_path}': {e_exists}", level="ERROR")
                # Продолжаем, но это странно

            if temp_file_exists:
                self._log(f"    Попытка удаления временного файла '{temp_cut_clip_path}'...", level="DEBUG_DEEP")
                try:
                    os.remove(temp_cut_clip_path)
                    self._log(f"    Временный файл '{os.path.basename(temp_cut_clip_path)}' УДАЛЕН.", level="INFO")
                except OSError as e_rem:
                    self._log(
                        f"    НЕ УДАЛОСЬ удалить временный файл '{os.path.basename(temp_cut_clip_path)}': {e_rem}",
                        level="WARN")
                except Exception as e_rem_generic:
                    self._log(
                        f"    НЕПРЕДВИДЕННАЯ ОШИБКА при удалении временного файла '{os.path.basename(temp_cut_clip_path)}': {e_rem_generic}",
                        level="ERROR")
                    self._log(f"    Traceback удаления: {traceback.format_exc()}", level="DEBUG")

            elif success_cut:  # Если нарезка была успешной, а файла нет - это странно
                self._log(
                    f"   ВНИМАНИЕ: Нарезка клипа '{original_description}' считалась успешной, но временный файл '{temp_cut_clip_path}' НЕ НАЙДЕН для удаления после использования.",
                    level="WARN")

            self._log(f"--- Завершение обработки клипа #{current_clip_number}: '{original_description}' ---",
                      level="INFO")  # Этот лог теперь должен появиться, если проблема не в удалении

        # ... (конец метода, emit export_all_finished) ...
        if self._is_cancelled:
            self._log(
                f"Процесс экспорта был ПРЕРВАН. Успешно экспортировано до отмены: {successful_exports_count} из {total_clips} клипов.",
                level="WARN")
        else:
            self._log(
                f"Процесс экспорта ЗАВЕРШЕН. Успешно экспортировано: {successful_exports_count} из {total_clips} клипов.",
                level="INFO")

        self._log(
            f"Перед emit export_all_finished. Список: {len(exported_clips_info_list)} элементов, Успешно: {successful_exports_count}",
            level="DEBUG_DEEP")
        self.export_all_finished.emit(exported_clips_info_list, successful_exports_count)
        self._log(f"После emit export_all_finished. Завершение работы воркера.", level="DEBUG_DEEP")