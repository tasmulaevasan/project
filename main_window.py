from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QLabel, QFileDialog, QMenuBar,
                             QStatusBar, QTextEdit, QFrame, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
                             QApplication, QProgressDialog, QTabWidget, QSizePolicy,
                             QSpacerItem, QDialog)  # Добавлены QTabWidget, QSizePolicy, QSpacerItem
from PyQt6.QtCore import Qt, QSize, QStandardPaths, QThread, pyqtSignal, pyqtSlot, QDateTime, QTimer, QUrl, QDate
from PyQt6.QtGui import QAction, QIcon, QPalette, QColor  # Добавлены QPalette, QColor для стилизации

import os
import subprocess
import traceback

from modules.video_importer import VideoImporter
from modules.video_player import VideoPlayerWidget
from modules.ai_analyzer import AIAnalyzer
from modules.cutting_engine import CuttingEngine
from modules.export_module import ExportModule
from modules.content_planner import ContentPlannerWidget
from modules.api_integrations import APIManager
from modules.settings_dialog import SettingsDialog, CONFIG_DEFAULT_EXPORT_FOLDER, CONFIG_FFMPEG_PATH
from modules.clip_exporter_worker import ClipExporterWorker
from utils import get_default_output_folder

MODERN_STYLESHEET = """
    QMainWindow {
        background-color: #2E3440; /* Nord Polar Night */
        color: #D8DEE9; /* Nord Snow Storm */
    }
    QWidget { /* Общий стиль для виджетов, если не переопределен */
        font-size: 10pt;
    }
    QTabWidget::pane {
        border-top: 2px solid #4C566A; /* Nord Polar Night - потемнее */
        background-color: #3B4252; /* Nord Polar Night - посветлее */
    }
    QTabBar::tab {
        background: #434C5E; /* Nord Polar Night - средний */
        color: #ECEFF4; /* Nord Snow Storm - самый светлый */
        border: 1px solid #4C566A;
        border-bottom-color: #3B4252; /* Цвет фона панели, чтобы сливалось */
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        min-width: 120px; /* Минимальная ширина вкладки */
        padding: 8px 12px; /* Отступы внутри вкладки */
        margin-right: 2px; /* Отступ между вкладками */
    }
    QTabBar::tab:selected {
        background: #3B4252; /* Цвет фона панели */
        color: #88C0D0; /* Nord Frost - голубой для акцента */
        border-color: #4C566A;
        border-bottom-color: #3B4252; /* Такой же как фон панели */
    }
    QTabBar::tab:hover {
        background: #4C566A;
        color: #ECEFF4;
    }
    QPushButton {
        background-color: #5E81AC; /* Nord Frost - синий */
        color: #ECEFF4;
        border: 1px solid #4C566A;
        padding: 8px 15px;
        border-radius: 4px;
        min-height: 28px; /* Минимальная высота кнопки */
    }
    QPushButton:hover {
        background-color: #81A1C1; /* Nord Frost - посветлее синий */
    }
    QPushButton:pressed {
        background-color: #4C566A;
    }
    QPushButton:disabled {
        background-color: #4C566A;
        color: #D8DEE9;
    }
    QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox {
        background-color: #434C5E;
        color: #D8DEE9;
        border: 1px solid #4C566A;
        border-radius: 3px;
        padding: 5px;
    }
    QTableWidget {
        background-color: #3B4252;
        color: #D8DEE9;
        gridline-color: #4C566A;
        border: 1px solid #4C566A;
        border-radius: 3px;
    }
    QHeaderView::section {
        background-color: #434C5E;
        color: #ECEFF4;
        padding: 4px;
        border: 1px solid #4C566A;
    }
    QProgressBar {
        border: 1px solid #4C566A;
        border-radius: 3px;
        background-color: #434C5E;
        text-align: center;
        color: #ECEFF4;
    }
    QProgressBar::chunk {
        background-color: #88C0D0; /* Nord Frost - голубой */
        width: 10px;
        margin: 0.5px;
    }
    QLabel {
        color: #D8DEE9;
        padding-top: 5px; /* Небольшой отступ сверху для заголовков секций */
    }
    QMenuBar {
        background-color: #2E3440;
        color: #D8DEE9;
    }
    QMenuBar::item {
        background: transparent;
        padding: 4px 8px;
    }
    QMenuBar::item:selected {
        background: #434C5E;
    }
    QMenu {
        background-color: #3B4252;
        color: #D8DEE9;
        border: 1px solid #4C566A;
    }
    QMenu::item:selected {
        background-color: #5E81AC;
    }
    QStatusBar {
        background-color: #2E3440;
        color: #D8DEE9;
    }
    QScrollBar:horizontal {
        border: none;
        background: #3B4252;
        height: 10px;
        margin: 0px 20px 0 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background: #5E81AC;
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }
    QScrollBar:vertical {
        border: none;
        background: #3B4252;
        width: 10px;
        margin: 20px 0 20px 0;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #5E81AC;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
"""


class MainWindow(QMainWindow):
    log_updated_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Автоматизированный Создатель Контента")
        # Геометрия будет установлена в showFullScreen() в main.py
        self.log_message(f"MainWindow: Инициализация QMainWindow (PID: {os.getpid()})", level="DEBUG")

        self.setStyleSheet(MODERN_STYLESHEET)  # Применяем стили

        self.settings_dialog = SettingsDialog(self)
        self.log_message("MainWindow: SettingsDialog инициализирован.", level="DEBUG")

        self._create_status_bar()
        self._create_actions()
        self._create_menu_bar()
        self.log_message("MainWindow: Статус-бар, действия и меню созданы.", level="DEBUG")

        self._init_ui()  # Инициализация UI с вкладками
        self.log_message("MainWindow: Основной UI (_init_ui) завершен.", level="DEBUG")

        # Инициализация модулей
        self.video_importer = VideoImporter(self)
        self.cutting_engine = CuttingEngine(self)
        ffmpeg_path_on_init = self.settings_dialog.settings.value(CONFIG_FFMPEG_PATH, "ffmpeg")
        self.cutting_engine.set_ffmpeg_path(ffmpeg_path_on_init)
        self.export_module = ExportModule(self)
        self.api_manager = APIManager(self)

        self.current_video_path = None
        self.detected_highlights = []
        self.last_exported_clips_info = []

        self.analysis_thread = None
        self.ai_analyzer_instance = None
        self.export_thread = None
        self.export_worker = None
        self.export_progress_dialog = None
        self._export_actually_started_and_not_cancelled = False

        self.log_updated_signal.connect(self._append_log_message_to_widget)
        self.log_message("Приложение полностью инициализировано и готово к работе.", level="INFO")

    def _init_ui(self):
        self.log_message("MainWindow: _init_ui() начало (новая версия с вкладками).", level="DEBUG")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)  # Главный layout для central_widget

        # Создаем QTabWidget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Вкладка 1: Обработка видео ---
        processing_tab = QWidget()
        processing_layout = QVBoxLayout(processing_tab)

        # Верхняя панель с кнопками управления
        top_control_panel = QHBoxLayout()
        self.import_button = QPushButton(QIcon.fromTheme("document-open", QIcon()), " Импорт видео")
        self.import_button.setIconSize(QSize(20, 20))  # Немного уменьшим иконки для панели
        self.import_button.setToolTip("Открыть видеофайл для анализа (Ctrl+O)")
        self.import_button.clicked.connect(self.import_video)
        top_control_panel.addWidget(self.import_button)

        self.analyze_button = QPushButton(QIcon.fromTheme("system-search", QIcon()), " Анализировать")
        self.analyze_button.setIconSize(QSize(20, 20))
        self.analyze_button.setToolTip("Начать анализ загруженного видео на хайлайты")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self.start_video_analysis)
        top_control_panel.addWidget(self.analyze_button)

        top_control_panel.addStretch(1)  # Растягиваем, чтобы кнопки были слева

        self.settings_button = QPushButton(QIcon.fromTheme("preferences-system", QIcon()), " Настройки")
        self.settings_button.setIconSize(QSize(20, 20))
        self.settings_button.setToolTip("Открыть диалог настроек приложения (Ctrl+,)")
        self.settings_button.clicked.connect(self.open_settings)
        top_control_panel.addWidget(self.settings_button)
        processing_layout.addLayout(top_control_panel)

        # Прогресс-бар анализа
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Анализ: %p%")
        processing_layout.addWidget(self.progress_bar)

        # Основная рабочая область (плеер и таблица хайлайтов)
        processing_workspace_layout = QHBoxLayout()

        # Левая часть: Плеер
        self.video_player_widget = VideoPlayerWidget(self)
        processing_workspace_layout.addWidget(self.video_player_widget, stretch=3)  # Плеер занимает больше места

        # Правая часть: Таблица хайлайтов и кнопка экспорта
        highlights_section_layout = QVBoxLayout()
        self.clips_label = QLabel("Найденные хайлайты:")
        highlights_section_layout.addWidget(self.clips_label)

        self.clips_table_widget = QTableWidget()
        self.clips_table_widget.setColumnCount(5)
        self.clips_table_widget.setHorizontalHeaderLabels(["Выбор", "Описание", "Старт", "Конец", "Оценка"])
        self.clips_table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.clips_table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Остальные колонки можно оставить Interactive или Stretch по желанию
        self.clips_table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.clips_table_widget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.clips_table_widget.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.clips_table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.clips_table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.clips_table_widget.setAlternatingRowColors(True)
        self.clips_table_widget.doubleClicked.connect(self.on_highlight_table_double_clicked)
        highlights_section_layout.addWidget(self.clips_table_widget)

        self.export_clips_button = QPushButton(QIcon.fromTheme("document-save-as", QIcon()),
                                               " Экспорт выбранных клипов")
        self.export_clips_button.setIconSize(QSize(20, 20))
        self.export_clips_button.setToolTip("Сохранить выбранные хайлайты как отдельные видеофайлы (Ctrl+E)")
        self.export_clips_button.setEnabled(False)
        self.export_clips_button.clicked.connect(self.export_selected_clips)
        highlights_section_layout.addWidget(self.export_clips_button)

        processing_workspace_layout.addLayout(highlights_section_layout, stretch=2)  # Таблица хайлайтов поменьше

        processing_layout.addLayout(processing_workspace_layout, stretch=1)  # Основная рабочая область растягивается
        self.tab_widget.addTab(processing_tab, QIcon.fromTheme("video-x-generic"), "Обработка видео")

        # --- Вкладка 2: Контент-план ---
        content_plan_tab = QWidget()
        content_plan_layout = QVBoxLayout(content_plan_tab)

        # Кнопка генерации плана (может быть и внутри виджета ContentPlannerWidget)
        plan_controls_layout = QHBoxLayout()
        self.generate_content_plan_button = QPushButton(QIcon.fromTheme("view-calendar-list", QIcon()),
                                                        " Сгенерировать контент-план")
        self.generate_content_plan_button.setIconSize(QSize(20, 20))
        self.generate_content_plan_button.setToolTip("Создать расписание публикаций на основе экспортированных клипов")
        self.generate_content_plan_button.setEnabled(False)
        self.generate_content_plan_button.clicked.connect(self.generate_content_plan_for_exported_clips)
        plan_controls_layout.addWidget(self.generate_content_plan_button)
        plan_controls_layout.addStretch(1)  # Кнопка слева
        content_plan_layout.addLayout(plan_controls_layout)

        self.content_planner_widget = ContentPlannerWidget(self)
        content_plan_layout.addWidget(self.content_planner_widget, stretch=1)
        self.tab_widget.addTab(content_plan_tab, QIcon.fromTheme("view-calendar"), "Контент-план")

        # --- Вкладка 3: Логи ---
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        self.log_label_tab = QLabel("Лог операций приложения:")  # Отдельный label для вкладки
        logs_layout.addWidget(self.log_label_tab)
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        # self.log_text_edit.setFixedHeight(150) # Убираем фиксированную высоту, пусть растягивается
        logs_layout.addWidget(self.log_text_edit, stretch=1)
        self.tab_widget.addTab(logs_tab, QIcon.fromTheme("text-x-generic"), "Логи")

        self.log_message("MainWindow: _init_ui() (новая версия) завершено.", level="INFO")

    def _create_actions(self):
        self.log_message("MainWindow: _create_actions() начало.", level="DEBUG")
        self.import_action = QAction(QIcon.fromTheme("document-open"), "&Импорт видео...", self)
        self.import_action.triggered.connect(self.import_video)
        self.import_action.setShortcut("Ctrl+O")

        self.export_action = QAction(QIcon.fromTheme("document-save-as"), "&Экспорт выбранных клипов...", self)
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self.export_selected_clips)
        self.export_action.setShortcut("Ctrl+E")

        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "&Выход", self)
        self.exit_action.triggered.connect(self.close)
        self.exit_action.setShortcut("Ctrl+Q")

        self.settings_action = QAction(QIcon.fromTheme("preferences-system"), "&Настройки...", self)
        self.settings_action.triggered.connect(self.open_settings)
        self.settings_action.setShortcut("Ctrl+,")

        self.about_action = QAction(QIcon.fromTheme("help-about"), "&О программе", self)
        self.about_action.triggered.connect(self.show_about_dialog)

        self.generate_plan_action = QAction(QIcon.fromTheme("view-calendar-list"), "Сгенерировать &план", self)
        self.generate_plan_action.setEnabled(False)
        self.generate_plan_action.triggered.connect(self.generate_content_plan_for_exported_clips)
        self.log_message("MainWindow: _create_actions() завершено.", level="DEBUG")

    def _create_menu_bar(self):
        self.log_message("MainWindow: _create_menu_bar() начало.", level="DEBUG")
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&Файл")
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        tools_menu = menu_bar.addMenu("&Инструменты")
        tools_menu.addAction(self.generate_plan_action)

        view_menu = menu_bar.addMenu("&Вид")  # Меню для переключения вкладок
        self.processing_tab_action = QAction("Обработка видео", self)
        self.processing_tab_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        view_menu.addAction(self.processing_tab_action)

        self.content_plan_tab_action = QAction("Контент-план", self)
        self.content_plan_tab_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        view_menu.addAction(self.content_plan_tab_action)

        self.logs_tab_action = QAction("Логи", self)
        self.logs_tab_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        view_menu.addAction(self.logs_tab_action)

        help_menu = menu_bar.addMenu("&Помощь")
        help_menu.addAction(self.about_action)
        self.log_message("MainWindow: _create_menu_bar() завершено.", level="DEBUG")

    def _create_status_bar(self):
        self.log_message("MainWindow: _create_status_bar() начало.", level="DEBUG")
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов")
        self.log_message("MainWindow: _create_status_bar() завершено.", level="DEBUG")

    def _append_log_message_to_widget(self, full_log_message):
        # Этот метод вызывается из основного потока через сигнал
        if hasattr(self, 'log_text_edit') and self.log_text_edit:
            self.log_text_edit.append(full_log_message)
            self.log_text_edit.ensureCursorVisible()
        else:
            # Это может случиться, если лог вызывается до полной инициализации log_text_edit
            print(f"INTERNAL LOG ERROR (append target missing): {full_log_message}")

    def log_message(self, message: str, level: str = "INFO"):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        log_prefix = "MainWindow"

        # Map DEBUG_EXTRA to DEBUG for filtering purposes if needed, or handle separately
        # For now, just ensure it's part of the full message
        effective_level = level
        if level == "DEBUG_EXTRA":
            effective_level = "DEBUG"  # Or keep as DEBUG_EXTRA if specific filtering is set up

        full_log_message = f"{timestamp} [{log_prefix}] [{level}]: {message}"  # Keep original level in log

        # Всегда выводим в консоль для отладки
        print(full_log_message)

        if hasattr(self, 'log_text_edit') and self.log_text_edit:
            if QThread.currentThread() != self.thread():
                self.log_updated_signal.emit(full_log_message)
            else:
                self._append_log_message_to_widget(full_log_message)

        # Обновляем статус-бар (если он уже создан)
        # DEBUG_EXTRA messages will not update the status bar to avoid clutter.
        if hasattr(self, 'status_bar') and self.status_bar and level in ["INFO", "WARN", "ERROR", "CRITICAL"]:
            def update_status():
                short_message = message.split('\n')[0]
                timeout = 3000 if level == "INFO" else 5000 if level == "WARN" else 8000
                self.status_bar.showMessage(f"[{level}] {short_message[:100]}", timeout)

            if QThread.currentThread() != self.thread():
                QTimer.singleShot(0, update_status)
            else:
                update_status()

    def import_video(self):
        self.log_message("import_video: Начало импорта видео.", level="INFO")
        video_path = self.video_importer.import_video()
        if video_path:
            self.log_message(f"import_video: Выбран файл: {video_path}", level="INFO")
            if self.current_video_path == video_path and \
                    hasattr(self.video_player_widget, 'media_player') and \
                    self.video_player_widget.media_player and \
                    self.video_player_widget.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                self.log_message(
                    f"import_video: Видео '{os.path.basename(video_path)}' уже загружено и активно. Повторный импорт не требуется.",
                    level="WARN")
                self._update_buttons_state_after_long_op(False)
                return

            self.current_video_path = video_path
            self.video_player_widget.load_video(self.current_video_path)
            self.clips_table_widget.setRowCount(0)
            self.detected_highlights = []
            self.last_exported_clips_info = []
            self.content_planner_widget.clear_plan()
            self.setWindowTitle(f"Создатель Контента - {os.path.basename(self.current_video_path)}")
            self._update_buttons_state_after_long_op(False)
            self.log_message(
                f"import_video: UI обновлен для нового видео '{os.path.basename(self.current_video_path)}'.",
                level="INFO")
        else:
            self.log_message("import_video: Импорт видео отменен пользователем.", level="INFO")
            self._update_buttons_state_after_long_op(False)

    def on_highlight_table_double_clicked(self, item):
        row = item.row()
        self.log_message(f"on_highlight_table_double_clicked: Двойной клик по строке {row}.", level="DEBUG")
        if row < 0 or row >= self.clips_table_widget.rowCount():
            self.log_message(f"on_highlight_table_double_clicked: Некорректный индекс строки {row}.", level="WARN")
            return

        checkbox_item_or_data_item = self.clips_table_widget.item(row, 0)
        if not checkbox_item_or_data_item:
            self.log_message(
                f"on_highlight_table_double_clicked: Отсутствует элемент чекбокса в строке {row}, столбце 0.",
                level="WARN")
            return

        highlight_data = checkbox_item_or_data_item.data(Qt.ItemDataRole.UserRole)
        if highlight_data and self.video_player_widget:
            start_time_sec = highlight_data.get('start_time')
            desc = highlight_data.get('description', 'N/A')
            if start_time_sec is not None:
                start_time_ms = int(start_time_sec * 1000)
                self.log_message(
                    f"on_highlight_table_double_clicked: Переход к хайлайту '{desc}' (старт: {start_time_sec:.3f}s / {start_time_ms}ms).",
                    level="INFO")
                self.video_player_widget.set_playback_position(start_time_ms)
            else:
                self.log_message(f"on_highlight_table_double_clicked: 'start_time' отсутствует для хайлайта '{desc}'.",
                                 level="WARN")
        elif not highlight_data:
            self.log_message(
                f"on_highlight_table_double_clicked: Нет данных (UserRole) в элементе строки {row}, столбца 0.",
                level="WARN")
        else:
            self.log_message(f"on_highlight_table_double_clicked: video_player_widget не доступен.", level="WARN")

    def _update_buttons_state_after_long_op(self, is_busy: bool):
        analysis_running = self.analysis_thread and self.analysis_thread.isRunning()
        export_running = self.export_thread and self.export_thread.isRunning()
        effective_busy = is_busy or analysis_running or export_running

        # Базовые состояния
        self.import_button.setEnabled(not effective_busy)
        self.analyze_button.setEnabled(not effective_busy and bool(self.current_video_path))
        self.settings_button.setEnabled(not effective_busy)
        self.settings_action.setEnabled(not effective_busy)

        # Проверка выбранных клипов
        can_export = False
        if not effective_busy and self.clips_table_widget.rowCount() > 0:
            for row in range(self.clips_table_widget.rowCount()):
                item = self.clips_table_widget.item(row, 0)
                if item and item.checkState() == Qt.CheckState.Checked:
                    can_export = True
                    break

        self.export_clips_button.setEnabled(can_export)
        self.export_action.setEnabled(can_export)

        # Состояние генерации плана
        can_generate_plan = not effective_busy and bool(self.last_exported_clips_info)
        self.generate_content_plan_button.setEnabled(can_generate_plan)
        self.generate_plan_action.setEnabled(can_generate_plan)

        # Статус бар
        status_msg = "Готов"
        if analysis_running:
            status_msg = "Идет анализ видео..."
        elif export_running:
            status_msg = "Идет экспорт клипов..."

        self.status_bar.showMessage(status_msg, 3000)

    def start_video_analysis(self):
        self.log_message("start_video_analysis: Попытка запуска анализа видео.", level="INFO")
        if not self.current_video_path:
            self.log_message("start_video_analysis: Ошибка - видео не импортировано.", level="ERROR")
            QMessageBox.warning(self, "Нет видео", "Пожалуйста, сначала импортируйте видео.")
            return

        if self.analysis_thread and self.analysis_thread.isRunning():
            self.log_message("start_video_analysis: Анализ уже запущен.", level="WARN")
            QMessageBox.information(self, "Анализ", "Процесс анализа уже выполняется.")
            return

        self._update_buttons_state_after_long_op(True)
        self.log_message(f"start_video_analysis: Подготовка к анализу '{os.path.basename(self.current_video_path)}'.",
                         level="INFO")

        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Анализ: %p% (Инициализация...)")
        self.progress_bar.setVisible(True)
        self.clips_table_widget.setRowCount(0)
        self.detected_highlights = []

        self.analysis_thread = QThread(self)
        current_ai_settings = self.settings_dialog.get_current_settings()
        self.ai_analyzer_instance = AIAnalyzer(parent_logger=self, settings=current_ai_settings)
        self.ai_analyzer_instance.moveToThread(self.analysis_thread)

        video_path_for_thread = self.current_video_path
        self.analysis_thread.started.connect(lambda path=video_path_for_thread: self.ai_analyzer_instance.analyze(path))

        self.ai_analyzer_instance.analysis_finished.connect(self.handle_analysis_finished)
        self.ai_analyzer_instance.analysis_progress.connect(self.handle_analysis_progress)
        self.ai_analyzer_instance.analysis_error.connect(self.handle_analysis_error)

        self.analysis_thread.finished.connect(self.cleanup_analyzer_instance)

        self.log_message(
            f"start_video_analysis: Запуск потока анализа для '{os.path.basename(video_path_for_thread)}'.",
            level="INFO")
        self.analysis_thread.start()

    def handle_analysis_progress(self, value, message):
        if self.progress_bar.isVisible():
            self.progress_bar.setValue(value)
            self.progress_bar.setFormat(f"Анализ: {message} (%p%)")

        if value % 10 == 0 or value in [0, 5, 95, 100] or "найдено" in message or "Завершено" in message:
            self.log_message(f"Прогресс анализа: {message} ({value}%)", level="DEBUG")

    def cleanup_analyzer_instance(self):
        if self.analysis_thread:
            if self.analysis_thread.isRunning():
                self.analysis_thread.quit()
                self.analysis_thread.wait(1500)  # Увеличили время ожидания
            self.analysis_thread.deleteLater()
            self.analysis_thread = None

        if self.ai_analyzer_instance:
            self.ai_analyzer_instance.deleteLater()
            self.ai_analyzer_instance = None

        self._update_buttons_state_after_long_op(False)
        self.log_message("Очистка анализатора завершена", level="DEBUG")

    def start_analysis(self):
        """Запускаем AI-анализ в отдельном потоке и показываем прогресс."""
        # 1) Создаём воркер и поток
        self.analysis_thread = QThread(self)
        # предполагается, что AIAnalyzer у вас уже реализован как QObject с сигналом progress(int, int, str) и слотом run()
        self.analysis_worker = AIAnalyzer(self.current_video_path, parent_logger=self)
        self.analysis_worker.moveToThread(self.analysis_thread)

        # 2) Старт и завершение
        self.analysis_thread.started.connect(self.analysis_worker.run)
        self.analysis_worker.finished.connect(self.handle_analysis_finished)
        self.analysis_worker.finished.connect(self.analysis_thread.quit)
        self.analysis_worker.finished.connect(self.analysis_worker.deleteLater)
        self.analysis_thread.finished.connect(self.analysis_thread.deleteLater)

        # 3) Прогресс-бар
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)  # изначально 0–100, можно менять в update
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Анализ: %p%")

        # 4) Подключаем сигнал обновления
        self.analysis_worker.progress.connect(self.on_analysis_progress)

        # 5) Деактивируем кнопки, запускаем
        self._update_buttons_state_after_long_op(is_busy=True)
        self.analysis_thread.start()

    @pyqtSlot(int, int, str)
    def on_analysis_progress(self, current, total, description):
        """Обновляем прогресс-бар во время анализа."""
        # Устанавливаем диапазон по факту
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"Анализ {current}/{total}: {description}")

    def handle_analysis_finished(self, highlights):
        self.log_message(f"Анализ завершен. Найдено {len(highlights)} хайлайтов", level="INFO")

        self.log_message(f"Анализ завершен. Найдено {len(highlights)} хайлайтов", level="INFO")
     # Сохраняем список хайлайтов для дальнейшего экспорта и генерации плана
        self.detected_highlights = highlights.copy()

        try:
            self.progress_bar.setVisible(False)
            self.display_highlights_in_table(highlights)
            self._update_buttons_state_after_long_op(False)

            # Останавливаем поток анализа, чтобы флаг analysis_running стал False
            if self.analysis_thread and self.analysis_thread.isRunning():
                self.log_message("handle_analysis_finished: останавливаем analysis_thread", level="DEBUG")
                self.analysis_thread.quit()
                self.analysis_thread.wait(1500)  # ждём, пока поток корректно завершится

            # Обновляем состояние кнопок
            self._update_buttons_state_after_long_op(False)

            # Принудительное обновление UI
            QApplication.processEvents()

            # Информируем пользователя
            if highlights:
                QMessageBox.information(
                    self,
                    "Анализ завершён",
                    f"Найдено {len(highlights)} потенциальных клипов"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Анализ завершён",
                    "Яркие моменты не обнаружены"
                )
        except Exception as e:
            self.log_message(f"Ошибка обработки результатов: {str(e)}", level="ERROR")


    def handle_analysis_error(self, error_message):
            self.log_message(f"handle_analysis_error: КРИТИЧЕСКАЯ ОШИБКА АНАЛИЗА: {error_message}", level="CRITICAL")
            QMessageBox.critical(self, "Ошибка анализа",
                                 f"Произошла критическая ошибка во время анализа видео:\n{error_message}")
            self.detected_highlights = []
            self.display_highlights_in_table([])

            # More robust cleanup in case of error
            if self.analysis_thread:
                if self.analysis_thread.isRunning():
                    self.log_message("handle_analysis_error: Analysis thread is running after error, attempting to quit.",
                                     level="WARN")
                    self.analysis_thread.quit()
                    if not self.analysis_thread.wait(1000):
                        self.log_message("handle_analysis_error: Analysis thread did not quit gracefully after error.",
                                         level="ERROR")
                # Call cleanup directly to ensure UI updates and resource cleanup.
                # It's designed to be safe if 'finished' also triggers it.
                self.cleanup_analyzer_instance()
            else:
                # If thread is already None, just update buttons and hide progress bar
                self.log_message("handle_analysis_error: Analysis thread is already None. Updating UI.",
                                 level="DEBUG_EXTRA")
                QTimer.singleShot(0, lambda: self.progress_bar.setVisible(False))
                self._update_buttons_state_after_long_op(False)

    def display_highlights_in_table(self, highlights):
        self.log_message(f"display_highlights_in_table: Отображение {len(highlights)} хайлайтов.", level="DEBUG")

        try:
            self.clips_table_widget.itemChanged.disconnect(self._on_clips_table_item_changed)
        except TypeError:
            pass

        self.clips_table_widget.setRowCount(0)

        if not highlights:
            self.log_message("display_highlights_in_table: Хайлайты не найдены.", level="INFO")
            self.clips_table_widget.setRowCount(1)
            item = QTableWidgetItem("Хайлайты не найдены.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.clips_table_widget.setItem(0, 0, item)
            self.clips_table_widget.setSpan(0, 0, 1, self.clips_table_widget.columnCount())
            return

        self.clips_table_widget.setRowCount(len(highlights))
        for row, hl in enumerate(highlights):
            # Checkbox столбец
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable |
                Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsSelectable
            )
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            checkbox_item.setData(Qt.ItemDataRole.UserRole, hl)
            self.clips_table_widget.setItem(row, 0, checkbox_item)

            # Описание
            desc_item = QTableWidgetItem(hl.get('description', f'Хайлайт {row + 1}'))
            self.clips_table_widget.setItem(row, 1, desc_item)

            # Время начала
            start_str = self.format_seconds_to_time(hl.get('start_time', 0))
            self.clips_table_widget.setItem(row, 2, QTableWidgetItem(start_str))

            # Время окончания
            end_str = self.format_seconds_to_time(hl.get('end_time', 0))
            self.clips_table_widget.setItem(row, 3, QTableWidgetItem(end_str))

            # Оценка
            score_str = f"{hl.get('score', 0.0):.2f}"
            self.clips_table_widget.setItem(row, 4, QTableWidgetItem(score_str))

        self.clips_table_widget.itemChanged.connect(self._on_clips_table_item_changed)
        self.log_message("Таблица хайлайтов успешно обновлена", level="INFO")

    def _on_clips_table_item_changed(self, item):
        if item.column() == 0:
            self._update_buttons_state_after_long_op(False)

    @staticmethod
    def format_seconds_to_time(seconds_float):
        if seconds_float is None: return "00:00:00.000"
        seconds_int = int(seconds_float)
        milliseconds = int(round((seconds_float - seconds_int) * 1000))
        if milliseconds >= 1000:
            seconds_int += 1
            milliseconds = 0

        h = seconds_int // 3600
        m = (seconds_int % 3600) // 60
        s = seconds_int % 60
        return f"{h:02d}:{m:02d}:{s:02d}.{milliseconds:03d}"

    def get_selected_highlights_for_export(self):
        selected_for_export = []
        self.log_message("get_selected_highlights_for_export: Сбор выбранных хайлайтов...", level="DEBUG")
        for row in range(self.clips_table_widget.rowCount()):
            checkbox_item = self.clips_table_widget.item(row, 0)
            if checkbox_item and checkbox_item.data(
                    Qt.ItemDataRole.UserRole) and checkbox_item.checkState() == Qt.CheckState.Checked:
                highlight_data = checkbox_item.data(Qt.ItemDataRole.UserRole)
                if highlight_data:
                    selected_for_export.append(highlight_data)
        self.log_message(f"get_selected_highlights_for_export: Всего выбрано {len(selected_for_export)} хайлайтов.",
                         level="INFO")
        return selected_for_export

    def export_selected_clips(self):
        self.log_message("export_selected_clips: Начало процесса экспорта.", level="INFO")
        self._export_actually_started_and_not_cancelled = False

        if self.export_thread and self.export_thread.isRunning():
            self.log_message("export_selected_clips: Экспорт уже выполняется.", level="WARN")
            QMessageBox.information(self, "Экспорт", "Процесс экспорта уже выполняется.")
            return

        self._update_buttons_state_after_long_op(True)

        if hasattr(self, 'video_player_widget') and self.video_player_widget:
            self.log_message("export_selected_clips: Приостановка видеоплеера (если активен)...", level="INFO")
            if self.video_player_widget.media_player and \
                    self.video_player_widget.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.video_player_widget.media_player.pause()

        highlights_to_export = self.get_selected_highlights_for_export()
        if not highlights_to_export:
            self.log_message("export_selected_clips: Хайлайты для экспорта не выбраны.", level="WARN")
            QMessageBox.information(self, "Нет выбора", "Пожалуйста, выберите хайлайты для экспорта.")
            self._update_buttons_state_after_long_op(False)
            return

        if not self.current_video_path:
            self.log_message("export_selected_clips: Исходное видео не загружено.", level="ERROR")
            QMessageBox.warning(self, "Нет исходного видео", "Пожалуйста, сначала импортируйте видео.")
            self._update_buttons_state_after_long_op(False)
            return

        default_export_path = self.settings_dialog.settings.value(CONFIG_DEFAULT_EXPORT_FOLDER,
                                                                  get_default_output_folder())
        output_folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения клипов",
                                                         default_export_path)
        if not output_folder:
            self.log_message("export_selected_clips: Папка для сохранения не выбрана, экспорт отменен.", level="INFO")
            self._update_buttons_state_after_long_op(False)
            return

        temp_dir_base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
        app_temp_dir_for_cutting = os.path.join(temp_dir_base, "AutomatedContentCreator_TempCuts")
        try:
            os.makedirs(app_temp_dir_for_cutting, exist_ok=True)
        except OSError as e:
            self.log_message(
                f"export_selected_clips: Не удалось создать временную папку '{app_temp_dir_for_cutting}': {e}",
                level="CRITICAL")
            QMessageBox.critical(self, "Ошибка временной папки",
                                 f"Не удалось создать временную папку для нарезки:\n{e}")
            self._update_buttons_state_after_long_op(False)
            return

        self.last_exported_clips_info = []
        total_clips_to_export = len(highlights_to_export)
        self.log_message(f"export_selected_clips: Запуск экспорта {total_clips_to_export} клипов.", level="INFO")
        self._export_actually_started_and_not_cancelled = True

        self.export_progress_dialog = QProgressDialog(f"Экспорт {total_clips_to_export} клипов...", "Отмена", 0,
                                                      total_clips_to_export, self)
        self.export_progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.export_progress_dialog.setAutoClose(False)
        self.export_progress_dialog.setAutoReset(False)
        self.export_progress_dialog.canceled.connect(self.cancel_export_process)

        self.export_thread = QThread(self)
        self.export_worker = ClipExporterWorker(
            cutting_engine=self.cutting_engine,
            export_module_instance=self.export_module,
            parent_logger=self
        )
        self.export_worker.set_temp_dir(app_temp_dir_for_cutting)

        if not self.export_worker.temp_dir_for_cutting:
            self.log_message(
                "export_selected_clips: Ошибка установки временной папки в ClipExporterWorker. Экспорт прерван.",
                level="CRITICAL")
            if self.export_progress_dialog: self.export_progress_dialog.close(); self.export_progress_dialog = None
            if self.export_worker: self.export_worker.deleteLater(); self.export_worker = None
            if self.export_thread: self.export_thread.deleteLater(); self.export_thread = None
            self._update_buttons_state_after_long_op(False)
            return

        self.export_worker.moveToThread(self.export_thread)

        self.export_worker.export_progress.connect(self.handle_export_progress_update)
        self.export_worker.export_finished_one.connect(self.handle_single_clip_exported)
        self.export_worker.export_all_finished.connect(self.handle_all_clips_exported)
        self.export_worker.export_error.connect(self.handle_export_error)

        self.export_thread.started.connect(
            lambda: self.export_worker.process_export_list(
                original_video_path=self.current_video_path,
                highlights_to_export=highlights_to_export,
                output_folder=output_folder
            )
        )
        self.export_thread.finished.connect(self.cleanup_export_worker)

        self.export_progress_dialog.setValue(0)
        if total_clips_to_export > 0:
            self.export_progress_dialog.show()

        self.log_message("export_selected_clips: Запуск потока экспорта...", level="INFO")
        self.export_thread.start()

    @pyqtSlot(int, int, str)
    def handle_export_progress_update(self, current_num, total_num, description):
        if self.export_progress_dialog and self.export_progress_dialog.isVisible():
            self.export_progress_dialog.setValue(current_num)
            self.export_progress_dialog.setLabelText(
                f"Обработка клипа {current_num} из {total_num}: {description[:50]}...")

        if current_num == 1 or current_num == total_num or current_num % (max(1, total_num // 10)) == 0:
            self.log_message(f"Прогресс экспорта: {current_num}/{total_num} - '{description}'.", level="DEBUG")

    @pyqtSlot(str, bool, str)
    def handle_single_clip_exported(self, path, success, description):
        # Обновляем прогресс-бар
        value = self.progress_bar.value() + 1
        self.progress_bar.setValue(value)

        # Если экспорт прошёл успешно, добавляем инфу в список для контент-плана
        if success and path:
            for hl in self.detected_highlights:
                if hl.get("description") == description:
                    info = {
                        "path": path,
                        "description": description,
                        # добавляем заголовок — будет показываться в контент-плане
                        "title_suggestion": f"Яркий момент: {description}",
                        "source_highlight_info": hl
                    }
                    self.last_exported_clips_info.append(info)
                    break

    @pyqtSlot(list, int)
    def handle_all_clips_exported(self, exported_clips_info_list_from_worker, successful_exports_count_from_worker):
        # Отключаем сигнал export_error, чтобы не показывать ошибку после того, как экспорт реально завершился
        try:
            self.export_worker.export_error.disconnect(self.handle_export_error)
        except (TypeError, AttributeError):
            # сигнал мог уже быть отключён или export_worker ещё не существовать
            pass

        final_successful_count = len(self.last_exported_clips_info)

        self.log_message(
            f"handle_all_clips_exported: Экспорт завершен. Успешно (по данным MainWindow): "
            f"{final_successful_count}. Worker сообщил: {successful_exports_count_from_worker} успешных, "
            f"{len(exported_clips_info_list_from_worker)} элементов в списке.",
            level="INFO"
        )

        if self.export_progress_dialog:
            try:
                self.export_progress_dialog.canceled.disconnect(self.cancel_export_process)
            except TypeError:
                pass
            if self.export_progress_dialog.isVisible():
                self.export_progress_dialog.setValue(self.export_progress_dialog.maximum())
                self.export_progress_dialog.close()
            self.export_progress_dialog = None

        if self._export_actually_started_and_not_cancelled:
            if final_successful_count > 0:
                QMessageBox.information(
                    self, "Экспорт завершен",
                    f"{final_successful_count} клипов было успешно экспортировано."
                )
            elif len(self.get_selected_highlights_for_export()) > 0:
                QMessageBox.warning(
                    self, "Экспорт завершен",
                    "Не удалось экспортировать ни одного из выбранных клипов. Проверьте лог."
                )

        self._export_actually_started_and_not_cancelled = False

        if self.export_thread and self.export_thread.isRunning():
            self.log_message("handle_all_clips_exported: Явный вызов quit для потока экспорта.", level="DEBUG")
            self.export_thread.quit()
        else:
            self.cleanup_export_worker()

    @pyqtSlot(str)
    def handle_export_error(self, error_message):
        # Если хотя бы один клип всё же экспортировался — подавляем это «ложное» окно ошибки
        if getattr(self, 'last_exported_clips_info', None):
            self.log_message(
                f"handle_export_error: Игнорируем ошибку после успешного экспорта: {error_message}",
                level="WARN"
            )
            return

        # Иначе — стандартная обработка критической ошибки
        self.log_message(f"handle_export_error: КРИТИЧЕСКАЯ ОШИБКА ЭКСПОРТА: {error_message}", level="CRITICAL")
        self._export_actually_started_and_not_cancelled = False

        if self.export_progress_dialog:
            try:
                self.export_progress_dialog.canceled.disconnect(self.cancel_export_process)
            except TypeError:
                pass
            if self.export_progress_dialog.isVisible():
                self.export_progress_dialog.close()
            self.export_progress_dialog = None

        QMessageBox.critical(self, "Ошибка экспорта", f"Произошла ошибка во время экспорта:\n{error_message}")

        if self.export_thread and self.export_thread.isRunning():
            self.log_message("handle_export_error: Явный вызов quit для потока экспорта после ошибки.", level="DEBUG")
            self.export_thread.quit()
        else:
            self.log_message("handle_export_error: Поток экспорта не запущен или уже завершен. Обновление UI.",
                             level="DEBUG")
            self.cleanup_export_worker()

    def cancel_export_process(self):
        self.log_message("cancel_export_process: Запрошена отмена экспорта.", level="WARN")
        self._export_actually_started_and_not_cancelled = False
        if self.export_thread and self.export_thread.isRunning():
            if self.export_worker:
                self.export_worker.cancel_export()
            if self.export_progress_dialog and self.export_progress_dialog.isVisible():
                self.export_progress_dialog.setLabelText("Отмена экспорта...")
        else:
            self.log_message("cancel_export_process: Поток экспорта уже не активен.", level="DEBUG")
            if self.export_progress_dialog and self.export_progress_dialog.isVisible():
                self.export_progress_dialog.close()
            self.export_progress_dialog = None
            self._update_buttons_state_after_long_op(False)

    def cleanup_export_worker(self):
        self.log_message("cleanup_export_worker: Начало очистки ресурсов потока экспорта.", level="DEBUG")
        if self.export_worker:
            self.export_worker.deleteLater()
            self.export_worker = None
            self.log_message("cleanup_export_worker: ClipExporterWorker помечен для удаления.", level="INFO")

        current_thread_ref = self.export_thread
        if current_thread_ref:
            if current_thread_ref.isRunning():
                self.log_message("cleanup_export_worker: Export thread still reported as running, attempting to wait.",
                                 level="WARN")
                current_thread_ref.quit()
                if not current_thread_ref.wait(1000):
                    self.log_message("cleanup_export_worker: Export thread did not quit gracefully.", level="ERROR")
            current_thread_ref.deleteLater()
            self.log_message(
                f"cleanup_export_worker: Export thread object (id: {id(current_thread_ref)}) scheduled for deletion.",
                level="DEBUG")

        self.export_thread = None
        self.log_message("cleanup_export_worker: self.export_thread reference cleared.", level="DEBUG")

        if self.export_progress_dialog and self.export_progress_dialog.isVisible():
            self.export_progress_dialog.close()
            self.export_progress_dialog = None
            self.log_message("cleanup_export_worker: Диалог прогресса (если был) закрыт/обнулен.", level="DEBUG")

        self._update_buttons_state_after_long_op(False)
        self._export_actually_started_and_not_cancelled = False
        self.log_message("cleanup_export_worker: UI обновлен.", level="DEBUG")

        if self.current_video_path and self.video_player_widget:
            self.log_message("cleanup_export_worker: Перезагрузка видео в плеер после экспорта (если необходимо).",
                             level="DEBUG")
            is_player_valid = self.video_player_widget.media_player is not None
            is_source_different = True
            if is_player_valid:
                current_source_url = self.video_player_widget.media_player.source().url() if self.video_player_widget.media_player.source() else QUrl()
                expected_source_url = QUrl.fromLocalFile(self.current_video_path)
                is_source_different = current_source_url != expected_source_url

            if not is_player_valid or is_source_different:
                self.video_player_widget.load_video(self.current_video_path)
        self._update_buttons_state_after_long_op(False)

    def generate_content_plan_for_exported_clips(self):
        if not self.last_exported_clips_info:
            QMessageBox.warning(self, "Нет данных для плана",
                                "Сначала экспортируйте клипы—тогда на их основе можно составить расписание.")
            return

        # Собираем план в список строк
        plan_lines = []
        start_date = QDate.currentDate()
        for i, clip in enumerate(self.last_exported_clips_info):
            date = start_date.addDays(i).toString("yyyy-MM-dd")
            title = clip.get("title_suggestion") or f"Яркий момент: {clip.get('description', '')}"
            plan_lines.append(f"{date}: {title}")
        plan_text = "\n".join(plan_lines)

        # Показываем диалог с возможностью сохранить .txt
        dialog = QDialog(self)
        dialog.setWindowTitle("Контент-план")
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(plan_text)
        layout.addWidget(text_edit)

        btn_save = QPushButton("Сохранить как…")

        def save_plan():
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить контент-план", "",
                                                  "Текстовые файлы (*.txt)")
            if not path: return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text_edit.toPlainText())
                QMessageBox.information(self, "Сохранено", f"План сохранён в:\n{path}")
            except Exception as ex:
                QMessageBox.critical(self, "Ошибка сохранения", str(ex))

        btn_save.clicked.connect(save_plan)
        layout.addWidget(btn_save)

        dialog.resize(500, 400)
        dialog.exec()

    def open_settings(self):
        self.log_message("open_settings: Открытие диалога настроек.", level="INFO")

        # Явная проверка на активные потоки
        if (self.analysis_thread and self.analysis_thread.isRunning()) or \
                (self.export_thread and self.export_thread.isRunning()):
            QMessageBox.information(self, "Занято",
                                    "Дождитесь завершения операций")
            return

        try:
            # Загрузка настроек с проверкой инициализации диалога
            if not hasattr(self, 'settings_dialog'):
                self.settings_dialog = SettingsDialog(self)

            self.settings_dialog.load_settings()

            # Корректная обработка результата диалога
            if self.settings_dialog.exec() == QDialog.DialogCode.Accepted:
                new_ffmpeg_path = self.settings_dialog.settings.value(
                    CONFIG_FFMPEG_PATH,
                    "ffmpeg"
                )

                # Валидация FFmpeg с обработкой исключений
                try:
                    result = subprocess.run(
                        [new_ffmpeg_path, '-version'],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=2
                    )
                    if 'ffmpeg version' not in result.stdout:
                        raise ValueError("Invalid FFmpeg")

                    self.cutting_engine.set_ffmpeg_path(new_ffmpeg_path)
                    self.log_message(f"FFmpeg путь обновлен: {new_ffmpeg_path}",
                                     level="INFO")

                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Ошибка FFmpeg",
                        f"Ошибка проверки FFmpeg:\n{str(e)}"
                    )
                    # Восстановление предыдущего значения
                    self.settings_dialog.ffmpeg_path_edit.setText(
                        self.cutting_engine.ffmpeg_path
                    )

        except Exception as e:
            self.log_message(f"Критическая ошибка в настройках: {str(e)}",
                             level="CRITICAL")
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Фатальная ошибка",
                f"Сбой в работе диалога настроек:\n{str(e)}"
            )

    def start_export_selected_clips(self):
        """Запускаем экспорт выбранных клипов в отдельном потоке."""
        selected = self.get_selected_highlights_for_export()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Нечего экспортировать — ни одного флажка.")
            return

        self.export_thread = QThread(self)
        self.export_worker = ClipExporterWorker(self.cutting_engine, self.export_module, parent_logger=self)
        self.export_worker.moveToThread(self.export_thread)

        self.export_thread.started.connect(lambda: self.export_worker.process_export_list(
            self.current_video_path, selected, self.output_folder, self.current_preset_name))
        self.export_worker.export_finished_one.connect(self.handle_single_clip_exported)
        self.export_worker.export_all_finished.connect(self.handle_all_clips_exported)
        self.export_worker.export_error.connect(self.handle_export_error)
        self.export_worker.export_all_finished.connect(self.export_thread.quit)
        self.export_worker.export_all_finished.connect(self.export_worker.deleteLater)
        self.export_thread.finished.connect(self.export_thread.deleteLater)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(selected))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Экспорт %v из %m")

        self._export_actually_started_and_not_cancelled = True
        self._update_buttons_state_after_long_op(is_busy=True, export_running=True)
        self.export_thread.start()

    def show_about_dialog(self):
        self.log_message("show_about_dialog: Открытие окна 'О программе'.", level="INFO")
        QMessageBox.about(self, "О программе Automated Content Creator",
                          "<html><head/><body>"
                          "<p><b>Автоматизированный Создатель Контента</b></p>"
                          "<p>Версия: 0.3.0 (Alpha)</p>"
                          "<p>Разработано для образовательной компании <b>AZ GROUP</b>.</p>"
                          "<p>Это приложение предназначено для автоматического выявления ярких моментов "
                          "в длинных видео, их нарезки в короткие клипы для социальных сетей "
                          "и генерации примерного плана публикаций.</p>"
                          "<hr/>"
                          "<p><b>Технологии:</b> Python, PyQt6, Qt Multimedia, PySceneDetect, FFmpeg.</p>"
                          "</body></html>"
                          )

    def closeEvent(self, event):
        self.log_message("closeEvent: Запрос на закрытие приложения.", level="INFO")

        if (self.analysis_thread and self.analysis_thread.isRunning()) or \
                (self.export_thread and self.export_thread.isRunning()):
            reply = QMessageBox.question(self, 'Операция в процессе',
                                         "Идет анализ или экспорт. Прервать операцию и выйти?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.log_message("closeEvent: Выход отменен пользователем из-за активной операции.", level="INFO")
                event.ignore()
                return
            else:
                self.log_message("closeEvent: Пользователь решил прервать активные операции и выйти.", level="WARN")
                if self.analysis_thread and self.analysis_thread.isRunning():
                    if self.ai_analyzer_instance: self.ai_analyzer_instance.cancel_analysis()
                if self.export_thread and self.export_thread.isRunning():
                    self.cancel_export_process()
        else:
            reply = QMessageBox.question(self, 'Подтверждение выхода',
                                         "Вы уверены, что хотите выйти?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.log_message("closeEvent: Выход отменен пользователем.", level="INFO")
                event.ignore()
                return

        self.log_message("closeEvent: Пользователь подтвердил выход. Начинается процесс закрытия...", level="INFO")

        active_threads_to_wait = []
        if self.analysis_thread and self.analysis_thread.isRunning():
            active_threads_to_wait.append(self.analysis_thread)
        if self.export_thread and self.export_thread.isRunning():
            active_threads_to_wait.append(self.export_thread)

        for thread_to_wait in active_threads_to_wait:
            thread_name = "Анализа" if thread_to_wait == self.analysis_thread else "Экспорта"
            self.log_message(f"closeEvent: Ожидание завершения потока {thread_name} (до 5 сек)...", level="DEBUG")
            if not thread_to_wait.wait(5000):
                self.log_message(
                    f"closeEvent: Поток {thread_name} не завершился вовремя после отмены, принудительное завершение.",
                    level="ERROR")
                thread_to_wait.terminate()
                thread_to_wait.wait()
            else:
                self.log_message(f"closeEvent: Поток {thread_name} успешно завершен.", level="INFO")

        if hasattr(self, 'video_player_widget') and self.video_player_widget:
            self.log_message("closeEvent: Очистка VideoPlayerWidget.", level="DEBUG")
            self.video_player_widget.cleanup()

        self.log_message("closeEvent: Все основные операции завершены. Приложение закрывается.", level="INFO")
        event.accept()
