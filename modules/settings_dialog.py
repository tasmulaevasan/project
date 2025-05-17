# automated_content_creator/modules/settings_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QHBoxLayout, QMessageBox, QDialogButtonBox, QFileDialog,
                             QLabel, QGroupBox, QDoubleSpinBox, QSpinBox, QTabWidget, QWidget, QCheckBox) # Добавил QDoubleSpinBox
from PyQt6.QtCore import QSettings, QStandardPaths, Qt
import os
from utils import get_default_output_folder # Используем нашу утилиту

# --- Ключи для QSettings ---
# Пути
CONFIG_FFMPEG_PATH = "paths/ffmpeg_path"
CONFIG_DEFAULT_EXPORT_FOLDER = "paths/default_export_folder"

# Настройки AI Анализатора (PySceneDetect)
CONFIG_AI_PYSCENEDETECT_THRESHOLD = "ai/pyscenedetect_threshold"
CONFIG_AI_MIN_SCENE_DURATION_SEC = "ai/min_scene_len_sec" # Минимальная длина сцены от детектора
CONFIG_AI_FINAL_MIN_HIGHLIGHT_DURATION_SEC = "ai/final_min_highlight_duration_sec" # Финальная мин. длина для хайлайта

# Настройки Контент-плана (Пример)
CONFIG_PLANNER_POSTS_PER_DAY = "planner/posts_per_day"
CONFIG_PLANNER_START_TIME_HOUR = "planner/start_time_hour"


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Настройки приложения")
        self.setMinimumWidth(550) # Немного шире

        # Используем QSettings для сохранения и загрузки настроек
        self.settings = QSettings("AZGROUP", "AutomatedContentCreator")

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        # --- Вкладка "Общие" (Пути) ---
        paths_tab = QWidget()
        paths_layout = QFormLayout(paths_tab)

        # FFmpeg
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_button = QPushButton("Обзор...")
        self.ffmpeg_path_button.clicked.connect(self.browse_ffmpeg_path)
        ffmpeg_layout = QHBoxLayout()
        ffmpeg_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_layout.addWidget(self.ffmpeg_path_button)
        paths_layout.addRow("Путь к FFmpeg:", ffmpeg_layout)

        # Папка экспорта
        self.default_export_folder_edit = QLineEdit()
        self.default_export_folder_button = QPushButton("Обзор...")
        self.default_export_folder_button.clicked.connect(self.browse_default_export_folder)
        export_folder_layout = QHBoxLayout()
        export_folder_layout.addWidget(self.default_export_folder_edit)
        export_folder_layout.addWidget(self.default_export_folder_button)
        paths_layout.addRow("Папка экспорта по умолчанию:", export_folder_layout)
        paths_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow) # Чтобы поля растягивались

        self.tab_widget.addTab(paths_tab, "Пути и Общие")


        # --- Вкладка "AI Анализ" ---
        ai_tab = QWidget()
        ai_main_layout = QVBoxLayout(ai_tab) # Общий layout для вкладки

        # Группа для PySceneDetect
        pyscenedetect_group = QGroupBox("Параметры PySceneDetect (анализ сцен)")
        ai_form_layout = QFormLayout(pyscenedetect_group)

        self.pyscene_threshold_spinbox = QDoubleSpinBox()
        self.pyscene_threshold_spinbox.setRange(1.0, 100.0)
        self.pyscene_threshold_spinbox.setSingleStep(1.0)
        self.pyscene_threshold_spinbox.setDecimals(1)
        self.pyscene_threshold_spinbox.setToolTip(
            "Порог чувствительности для ContentDetector (обычно 25-35).\n"
            "Меньше значение = больше коротких сцен (выше чувствительность)."
        )
        ai_form_layout.addRow("Порог чувствительности детектора:", self.pyscene_threshold_spinbox)

        self.min_scene_duration_spinbox = QDoubleSpinBox()
        self.min_scene_duration_spinbox.setRange(0.1, 60.0) # От 0.1 до 60 секунд
        self.min_scene_duration_spinbox.setSingleStep(0.1)
        self.min_scene_duration_spinbox.setDecimals(1)
        self.min_scene_duration_spinbox.setSuffix(" сек.")
        self.min_scene_duration_spinbox.setToolTip(
            "Минимальная длительность сцены, которую обнаружит PySceneDetect.\n"
            "Сцены короче этого значения будут проигнорированы детектором."
        )
        ai_form_layout.addRow("Мин. длина сцены (детектор):", self.min_scene_duration_spinbox)
        ai_main_layout.addWidget(pyscenedetect_group)

        # Группа для финальной обработки хайлайтов
        highlight_filter_group = QGroupBox("Фильтрация хайлайтов (после анализа)")
        highlight_form_layout = QFormLayout(highlight_filter_group)

        self.final_min_highlight_duration_spinbox = QDoubleSpinBox()
        self.final_min_highlight_duration_spinbox.setRange(0.5, 180.0) # От 0.5 до 3 минут
        self.final_min_highlight_duration_spinbox.setSingleStep(0.5)
        self.final_min_highlight_duration_spinbox.setDecimals(1)
        self.final_min_highlight_duration_spinbox.setSuffix(" сек.")
        self.final_min_highlight_duration_spinbox.setToolTip(
             "Минимальная длительность для итогового хайлайта.\n"
             "Даже если сцена была найдена, она будет отброшена, если короче этого значения."
        )
        highlight_form_layout.addRow("Мин. длина итогового хайлайта:", self.final_min_highlight_duration_spinbox)
        ai_main_layout.addWidget(highlight_filter_group)
        ai_main_layout.addStretch(1) # Растягиваем, чтобы группы были вверху

        self.tab_widget.addTab(ai_tab, "AI Анализ")


        # --- Вкладка "Контент-план" ---
        planner_tab = QWidget()
        planner_layout = QFormLayout(planner_tab)

        self.posts_per_day_spinbox = QSpinBox()
        self.posts_per_day_spinbox.setRange(1, 10)
        self.posts_per_day_spinbox.setToolTip("Сколько постов в среднем планировать на один день.")
        planner_layout.addRow("Постов в день (по умолчанию):", self.posts_per_day_spinbox)

        self.start_time_hour_spinbox = QSpinBox()
        self.start_time_hour_spinbox.setRange(0, 23)
        self.start_time_hour_spinbox.setSuffix(" час(ов)")
        self.start_time_hour_spinbox.setToolTip("Предпочтительное время начала публикаций в дне (час).")
        planner_layout.addRow("Время начала постов (час):", self.start_time_hour_spinbox)
        planner_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)


        self.tab_widget.addTab(planner_tab, "Контент-план")


        # --- Вкладка "Интеграции API" (остается заглушкой) ---
        api_tab = QWidget()
        api_main_layout = QVBoxLayout(api_tab)
        api_info_label = QLabel(
            "Настройки интеграций с API социальных сетей (Instagram, YouTube и др.) "
            "будут доступны в будущих версиях.\n\n"
            "Здесь можно будет вводить ключи API, проходить OAuth2 аутентификацию и т.д."
        )
        api_info_label.setWordWrap(True)
        api_main_layout.addWidget(api_info_label)

        # Пример кнопок для аутентификации (пока неактивны или имитируют)
        ig_group = QGroupBox("Instagram API (Заглушка)")
        ig_layout = QVBoxLayout(ig_group)
        self.ig_auth_button = QPushButton("Аутентификация Instagram")
        self.ig_auth_button.clicked.connect(self.authenticate_instagram_placeholder)
        ig_layout.addWidget(self.ig_auth_button)
        api_main_layout.addWidget(ig_group)

        yt_group = QGroupBox("YouTube Data API (Заглушка)")
        yt_layout = QVBoxLayout(yt_group)
        self.yt_auth_button = QPushButton("Аутентификация YouTube")
        self.yt_auth_button.clicked.connect(self.authenticate_youtube_placeholder)
        yt_layout.addWidget(self.yt_auth_button)
        api_main_layout.addWidget(yt_group)
        api_main_layout.addStretch(1)

        self.tab_widget.addTab(api_tab, "Интеграции API")
        main_layout.addWidget(self.tab_widget)

        # --- Кнопки OK и Cancel ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply # Кнопка "Применить"
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).setText("Применить")
        self.button_box.accepted.connect(self.accept_settings) # OK
        self.button_box.rejected.connect(self.reject) # Cancel
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_settings) # Apply
        main_layout.addWidget(self.button_box)

        self.load_settings() # Загружаем сохраненные настройки при открытии

    def browse_ffmpeg_path(self):
        current_path = self.ffmpeg_path_edit.text()
        # На Windows ищем .exe, на других - просто исполняемый файл
        executable_filter = "Исполняемый файл FFmpeg (ffmpeg.exe)" if os.name == 'nt' else "Исполняемый файл FFmpeg (ffmpeg);;Все файлы (*)"
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите исполняемый файл FFmpeg",
            os.path.dirname(current_path) if current_path and os.path.exists(os.path.dirname(current_path)) else QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ApplicationsLocation),
            executable_filter
        )
        if path:
            self.ffmpeg_path_edit.setText(path)
            if self.parent_window: self.parent_window.log_message(f"Настройки: Выбран путь к FFmpeg: {path}")

    def browse_default_export_folder(self):
        current_path = self.default_export_folder_edit.text()
        path = QFileDialog.getExistingDirectory(
            self, "Выберите папку для экспорта по умолчанию",
            current_path if current_path and os.path.exists(current_path) else get_default_output_folder()
        )
        if path:
            self.default_export_folder_edit.setText(path)
            if self.parent_window: self.parent_window.log_message(f"Настройки: Выбрана папка экспорта: {path}")


    def load_settings(self):
        """Загружает настройки из QSettings в элементы UI."""
        # Пути
        self.ffmpeg_path_edit.setText(self.settings.value(CONFIG_FFMPEG_PATH, "ffmpeg"))
        self.default_export_folder_edit.setText(self.settings.value(CONFIG_DEFAULT_EXPORT_FOLDER, get_default_output_folder()))

        # AI Анализ
        self.pyscene_threshold_spinbox.setValue(float(self.settings.value(CONFIG_AI_PYSCENEDETECT_THRESHOLD, 27.0)))
        self.min_scene_duration_spinbox.setValue(float(self.settings.value(CONFIG_AI_MIN_SCENE_DURATION_SEC, 2.0)))
        self.final_min_highlight_duration_spinbox.setValue(float(self.settings.value(CONFIG_AI_FINAL_MIN_HIGHLIGHT_DURATION_SEC, 3.0)))

        # Контент-план
        self.posts_per_day_spinbox.setValue(int(self.settings.value(CONFIG_PLANNER_POSTS_PER_DAY, 1)))
        self.start_time_hour_spinbox.setValue(int(self.settings.value(CONFIG_PLANNER_START_TIME_HOUR, 10)))


        if self.parent_window: self.parent_window.log_message("Настройки: Загружены сохраненные значения.")

    def save_settings(self):
        """Сохраняет текущие настройки из UI в QSettings."""
        # Пути
        self.settings.setValue(CONFIG_FFMPEG_PATH, self.ffmpeg_path_edit.text())
        self.settings.setValue(CONFIG_DEFAULT_EXPORT_FOLDER, self.default_export_folder_edit.text())

        # AI Анализ
        self.settings.setValue(CONFIG_AI_PYSCENEDETECT_THRESHOLD, self.pyscene_threshold_spinbox.value())
        self.settings.setValue(CONFIG_AI_MIN_SCENE_DURATION_SEC, self.min_scene_duration_spinbox.value())
        self.settings.setValue(CONFIG_AI_FINAL_MIN_HIGHLIGHT_DURATION_SEC, self.final_min_highlight_duration_spinbox.value())

        # Контент-план
        self.settings.setValue(CONFIG_PLANNER_POSTS_PER_DAY, self.posts_per_day_spinbox.value())
        self.settings.setValue(CONFIG_PLANNER_START_TIME_HOUR, self.start_time_hour_spinbox.value())

        # Применяем некоторые настройки немедленно (например, путь к FFmpeg)
        if self.parent_window and hasattr(self.parent_window, 'cutting_engine'):
             self.parent_window.cutting_engine.set_ffmpeg_path(self.ffmpeg_path_edit.text())
             if self.parent_window: self.parent_window.log_message(f"Настройки: Путь к FFmpeg немедленно обновлен на '{self.ffmpeg_path_edit.text()}'.")

        if self.parent_window: self.parent_window.log_message("Настройки: Текущие значения сохранены.")

    def apply_settings(self):
        """Применяет настройки без закрытия диалога."""
        self.save_settings()
        if self.parent_window: self.parent_window.log_message("Настройки: Изменения применены.")
        # Можно добавить QMessageBox.information(self, "Настройки", "Изменения применены.")


    def accept_settings(self):
        """Применяет настройки и закрывает диалог."""
        self.save_settings()
        self.accept() # Закрывает диалог с QDialog.DialogCode.Accepted

    def get_current_settings(self):
        """
        Возвращает словарь с текущими настройками, считанными из QSettings.
        Это используется для передачи настроек в AIAnalyzer и другие модули.
        """
        # Убедимся, что self.settings содержит актуальные данные (на случай если диалог не открывался)
        # или если значения могли быть изменены программно.
        # Однако, обычно QSettings хранит последнее сохраненное состояние.
        return {
            CONFIG_FFMPEG_PATH: self.settings.value(CONFIG_FFMPEG_PATH, "ffmpeg"),
            CONFIG_DEFAULT_EXPORT_FOLDER: self.settings.value(CONFIG_DEFAULT_EXPORT_FOLDER, get_default_output_folder()),
            'pyscenedetect_threshold': float(self.settings.value(CONFIG_AI_PYSCENEDETECT_THRESHOLD, 27.0)),
            'min_scene_len_sec': float(self.settings.value(CONFIG_AI_MIN_SCENE_DURATION_SEC, 2.0)),
            'final_min_highlight_duration_sec': float(self.settings.value(CONFIG_AI_FINAL_MIN_HIGHLIGHT_DURATION_SEC, 3.0)),
            'planner_posts_per_day': int(self.settings.value(CONFIG_PLANNER_POSTS_PER_DAY, 1)),
            'planner_start_time_hour': int(self.settings.value(CONFIG_PLANNER_START_TIME_HOUR, 10)),
            # Добавьте другие настройки по мере необходимости
        }

    # --- Методы-заглушки для аутентификации ---
    def authenticate_instagram_placeholder(self):
        if self.parent_window and hasattr(self.parent_window, 'api_manager'):
            # В реальном приложении здесь был бы вызов self.parent_window.api_manager.authenticate("instagram")
            # и обработка результата (открытие браузера, получение токена и т.д.)
            if self.parent_window.api_manager.authenticate("instagram"): # Вызываем имитацию
                 QMessageBox.information(self, "Аутентификация Instagram",
                                         "Процесс аутентификации Instagram (имитация) запущен.\n"
                                         "В реальном приложении здесь бы открылся браузер.")
            else:
                 QMessageBox.warning(self, "Аутентификация Instagram", "Имитация аутентификации Instagram не удалась.")
        else:
            QMessageBox.critical(self, "Ошибка", "Менеджер API не доступен.")


    def authenticate_youtube_placeholder(self):
        if self.parent_window and hasattr(self.parent_window, 'api_manager'):
            if self.parent_window.api_manager.authenticate("youtube"): # Вызываем имитацию
                 QMessageBox.information(self, "Аутентификация YouTube",
                                         "Процесс аутентификации YouTube (имитация) запущен.\n"
                                         "В реальном приложении это потребовало бы настройки Google Cloud Console и OAuth2.")
            else:
                 QMessageBox.warning(self, "Аутентификация YouTube", "Имитация аутентификации YouTube не удалась.")
        else:
            QMessageBox.critical(self, "Ошибка", "Менеджер API не доступен.")