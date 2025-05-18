# automated_content_creator/main_window.py
# ... (начало файла без изменений) ...
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QLabel, QFileDialog, QMenuBar,
                             QStatusBar, QTextEdit, QFrame, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
                             QApplication, QProgressDialog, QTabWidget, QSizePolicy,
                             QSpacerItem, QDialog,
                             QComboBox)  # Добавлен QComboBox для примера, если понадобится где-то еще
from PyQt6.QtCore import Qt, QSize, QStandardPaths, QThread, pyqtSignal, pyqtSlot, QDateTime, QTimer, QUrl, QDate
from PyQt6.QtGui import QAction, QIcon, QPalette, QColor

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
from modules.export_options_dialog import ExportOptionsDialog  # <--- ДОБАВЛЕНО
from utils import get_default_output_folder

MODERN_STYLESHEET = """
    QCalendarWidget QWidget { /* Viewport календаря */
    alternate-background-color: #434C5E; /* Nord Polar Night - средний, для дней */
    background-color: #3B4252; /* Nord Polar Night - светлее, основной фон */
    }
    QCalendarWidget QToolButton { /* Кнопки навигации */
        background-color: #5E81AC;
        color: #ECEFF4;
        border: 1px solid #4C566A;
        border-radius: 3px;
        padding: 5px;
        margin: 2px;
    }
    QCalendarWidget QToolButton:hover {
        background-color: #81A1C1;
    }
    QCalendarWidget QAbstractItemView:enabled { /* Дни месяца */
        color: #D8DEE9; /* Цвет текста чисел */
        selection-background-color: #88C0D0; /* Цвет фона выделенного дня */
        selection-color: #2E3440; /* Цвет текста выделенного дня */
    }
    QCalendarWidget QAbstractItemView:disabled { /* Дни не текущего месяца */
        color: #4C566A;
    }
    /* Для таблицы plan_table_widget, если нужны особые стили ячеек или выделения */
    QTableWidget::item {
        padding: 5px;
         /* border-bottom: 1px solid #4C566A; (если нужны разделители строк) */
    }
    QTableWidget::item:selected {
        background-color: #5E81AC; /* Nord Frost - синий, для выделенной строки */
        color: #ECEFF4;
    }
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
    QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { /* Добавлен QComboBox */
        background-color: #434C5E;
        color: #D8DEE9;
        border: 1px solid #4C566A;
        border-radius: 3px;
        padding: 5px;
    }
    QComboBox QAbstractItemView { /* Стили для выпадающего списка QComboBox */
        background-color: #434C5E;
        color: #D8DEE9;
        border: 1px solid #4C566A;
        selection-background-color: #5E81AC; /* Цвет выделения */
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
    QTextBrowser { /* Стили для QTextBrowser в диалоге опций экспорта */
        background-color: #434C5E;
        color: #D8DEE9;
        border: 1px solid #4C566A;
        border-radius: 3px;
        padding: 5px;
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
        self.log_message(f"MainWindow: Инициализация QMainWindow (PID: {os.getpid()})", level="DEBUG")

        self.setStyleSheet(MODERN_STYLESHEET)

        self.settings_dialog = SettingsDialog(self)
        self.log_message("MainWindow: SettingsDialog инициализирован.", level="DEBUG")

        self._create_status_bar()
        self._create_actions()
        self._create_menu_bar()
        self.log_message("MainWindow: Статус-бар, действия и меню созданы.", level="DEBUG")

        self._init_ui()
        self.log_message("MainWindow: Основной UI (_init_ui) завершен.", level="DEBUG")

        self.video_importer = VideoImporter(self)
        self.cutting_engine = CuttingEngine(self)
        ffmpeg_path_on_init = self.settings_dialog.settings.value(CONFIG_FFMPEG_PATH, "ffmpeg")
        self.cutting_engine.set_ffmpeg_path(ffmpeg_path_on_init)
        self.export_module = ExportModule(self)  # Передаем self (MainWindow) как parent_logger
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

    # ... (остальные методы _init_ui, _create_actions, и т.д. без изменений) ...

    def _init_ui(self):
        self.log_message("MainWindow: _init_ui() начало (новая версия с вкладками).", level="DEBUG")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        processing_tab = QWidget()
        processing_layout = QVBoxLayout(processing_tab)

        top_control_panel = QHBoxLayout()
        self.import_button = QPushButton(QIcon.fromTheme("document-open", QIcon()), " Импорт видео")
        self.import_button.setIconSize(QSize(20, 20))
        self.import_button.setToolTip("Открыть видеофайл для анализа (Ctrl+O)")
        self.import_button.clicked.connect(self.import_video)
        top_control_panel.addWidget(self.import_button)

        self.analyze_button = QPushButton(QIcon.fromTheme("system-search", QIcon()), " Анализировать")
        self.analyze_button.setIconSize(QSize(20, 20))
        self.analyze_button.setToolTip("Начать анализ загруженного видео на хайлайты")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self.start_video_analysis)
        top_control_panel.addWidget(self.analyze_button)

        top_control_panel.addStretch(1)

        self.settings_button = QPushButton(QIcon.fromTheme("preferences-system", QIcon()), " Настройки")
        self.settings_button.setIconSize(QSize(20, 20))
        self.settings_button.setToolTip("Открыть диалог настроек приложения (Ctrl+,)")
        self.settings_button.clicked.connect(self.open_settings)
        top_control_panel.addWidget(self.settings_button)
        processing_layout.addLayout(top_control_panel)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Анализ: %p%")
        processing_layout.addWidget(self.progress_bar)

        processing_workspace_layout = QHBoxLayout()

        self.video_player_widget = VideoPlayerWidget(self)
        processing_workspace_layout.addWidget(self.video_player_widget, stretch=3)

        highlights_section_layout = QVBoxLayout()
        self.clips_label = QLabel("Найденные хайлайты:")
        highlights_section_layout.addWidget(self.clips_label)

        self.clips_table_widget = QTableWidget()
        self.clips_table_widget.setColumnCount(5)
        self.clips_table_widget.setHorizontalHeaderLabels(["Выбор", "Описание", "Старт", "Конец", "Оценка"])
        self.clips_table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.clips_table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
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
        self.export_clips_button.clicked.connect(self.export_selected_clips)  # ИЗМЕНЕНО НА НОВЫЙ МЕТОД
        highlights_section_layout.addWidget(self.export_clips_button)

        processing_workspace_layout.addLayout(highlights_section_layout, stretch=2)

        processing_layout.addLayout(processing_workspace_layout, stretch=1)
        self.tab_widget.addTab(processing_tab, QIcon.fromTheme("video-x-generic"), "Обработка видео")

        content_plan_tab = QWidget()
        content_plan_layout = QVBoxLayout(content_plan_tab)

        plan_controls_layout = QHBoxLayout()
        self.generate_content_plan_button = QPushButton(QIcon.fromTheme("view-calendar-list", QIcon()),
                                                        " Сгенерировать контент-план")
        self.generate_content_plan_button.setIconSize(QSize(20, 20))
        self.generate_content_plan_button.setToolTip("Создать расписание публикаций на основе экспортированных клипов")
        self.generate_content_plan_button.setEnabled(False)
        self.generate_content_plan_button.clicked.connect(self.generate_content_plan_for_exported_clips)
        plan_controls_layout.addWidget(self.generate_content_plan_button)
        plan_controls_layout.addStretch(1)
        content_plan_layout.addLayout(plan_controls_layout)

        self.content_planner_widget = ContentPlannerWidget(self)
        content_plan_layout.addWidget(self.content_planner_widget, stretch=1)
        self.tab_widget.addTab(content_plan_tab, QIcon.fromTheme("view-calendar"), "Контент-план")

        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        self.log_label_tab = QLabel("Лог операций приложения:")
        logs_layout.addWidget(self.log_label_tab)
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
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
        self.export_action.triggered.connect(self.export_selected_clips)  # ИЗМЕНЕНО НА НОВЫЙ МЕТОД
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

        view_menu = menu_bar.addMenu("&Вид")
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
        if hasattr(self, 'log_text_edit') and self.log_text_edit:
            self.log_text_edit.append(full_log_message)
            self.log_text_edit.ensureCursorVisible()
        else:
            print(f"INTERNAL LOG ERROR (append target missing): {full_log_message}")

    def log_message(self, message: str, level: str = "INFO"):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        log_prefix = "MainWindow"
        effective_level = level
        if level == "DEBUG_EXTRA":
            effective_level = "DEBUG"

        full_log_message = f"{timestamp} [{log_prefix}] [{level}]: {message}"
        print(full_log_message)

        if hasattr(self, 'log_text_edit') and self.log_text_edit:
            if QThread.currentThread() != self.thread():
                self.log_updated_signal.emit(full_log_message)
            else:
                self._append_log_message_to_widget(full_log_message)

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
            if hasattr(self, 'content_planner_widget'):  # Проверка на существование
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

        self.import_button.setEnabled(not effective_busy)
        self.analyze_button.setEnabled(not effective_busy and bool(self.current_video_path))
        self.settings_button.setEnabled(not effective_busy)
        self.settings_action.setEnabled(not effective_busy)

        can_export = False
        if not effective_busy and self.clips_table_widget.rowCount() > 0:
            for row in range(self.clips_table_widget.rowCount()):
                item = self.clips_table_widget.item(row, 0)
                if item and item.checkState() == Qt.CheckState.Checked:
                    can_export = True
                    break
        self.export_clips_button.setEnabled(can_export)
        self.export_action.setEnabled(can_export)

        can_generate_plan = not effective_busy and bool(self.last_exported_clips_info)
        self.generate_content_plan_button.setEnabled(can_generate_plan)
        self.generate_plan_action.setEnabled(can_generate_plan)

        status_msg = "Готов"
        if analysis_running:
            status_msg = "Идет анализ видео..."
        elif export_running:
            status_msg = "Идет экспорт клипов..."
        self.status_bar.showMessage(status_msg, 3000 if not effective_busy else 0)

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

    @pyqtSlot(int)
    def on_analysis_progress(self, percent):
        self.progress_bar.setValue(percent)

    @pyqtSlot(list)
    def on_analysis_finished(self, highlights):
        self.display_highlights_in_table(highlights)
        self.progress_bar.hide()

    def cleanup_analyzer_instance(self):
        if self.ai_analyzer_instance:
            self.ai_analyzer_instance.deleteLater()
            self.ai_analyzer_instance = None
        # self.analysis_thread уже должен быть None или удален через finished.connect(deleteLater)
        if self.analysis_thread:
            self.analysis_thread.quit()
            self.analysis_thread.wait()  # дожидаемся завершения
            self.analysis_thread.deleteLater()
            self.analysis_thread = None
        self._update_buttons_state_after_long_op(False)
        self.log_message("Очистка экземпляра анализатора завершена", level="DEBUG")

    def handle_analysis_finished(self, highlights):
        self.log_message(f"Анализ завершен. Найдено {len(highlights)} хайлайтов", level="INFO")
        self.detected_highlights = highlights.copy()

        try:
            self.progress_bar.setVisible(False)
            self.display_highlights_in_table(highlights)
            # self._update_buttons_state_after_long_op(False) # Вызывается в cleanup_analyzer_instance

            if self.analysis_thread and self.analysis_thread.isRunning():
                self.log_message("handle_analysis_finished: останавливаем analysis_thread (если еще работает)",
                                 level="DEBUG")
                self.analysis_thread.quit()
                # self.analysis_thread.wait(1500) # wait() здесь может заблокировать GUI, лучше через finished

            QApplication.processEvents()

            if highlights:
                QMessageBox.information(self, "Анализ завершён", f"Найдено {len(highlights)} потенциальных клипов")
            else:
                QMessageBox.warning(self, "Анализ завершён", "Яркие моменты не обнаружены")
        except Exception as e:
            self.log_message(f"Ошибка обработки результатов анализа: {str(e)}\n{traceback.format_exc()}", level="ERROR")
        finally:
            # Убедимся, что cleanup вызывается, даже если поток не завершился сам
            if self.analysis_thread and not self.analysis_thread.isFinished():
                self.log_message(
                    "handle_analysis_finished: Принудительный вызов cleanup_analyzer_instance, т.к. поток еще не завершен.",
                    level="WARN")
            self.cleanup_analyzer_instance()

    def handle_analysis_error(self, error_message):
        self.log_message(f"handle_analysis_error: КРИТИЧЕСКАЯ ОШИБКА АНАЛИЗА: {error_message}", level="CRITICAL")
        QMessageBox.critical(self, "Ошибка анализа",
                             f"Произошла критическая ошибка во время анализа видео:\n{error_message}")
        self.detected_highlights = []
        self.display_highlights_in_table([])
        self.progress_bar.setVisible(False)
        # self._update_buttons_state_after_long_op(False) # Вызывается в cleanup_analyzer_instance

        if self.analysis_thread and self.analysis_thread.isRunning():
            self.log_message("handle_analysis_error: Analysis thread is running after error, attempting to quit.",
                             level="WARN")
            self.analysis_thread.quit()
        self.cleanup_analyzer_instance()

    def display_highlights_in_table(self, highlights):
        self.log_message(f"display_highlights_in_table: Отображение {len(highlights)} хайлайтов.", level="DEBUG")
        try:
            self.clips_table_widget.itemChanged.disconnect(self._on_clips_table_item_changed)
        except TypeError:
            pass

        self.clips_table_widget.setRowCount(0)
        if not highlights:
            self.log_message("display_highlights_in_table: Хайлайты не найдены.", level="INFO")
            # ... (код для сообщения "Хайлайты не найдены" в таблице)
            return

        self.clips_table_widget.setRowCount(len(highlights))
        for row, hl in enumerate(highlights):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            checkbox_item.setData(Qt.ItemDataRole.UserRole, hl)
            self.clips_table_widget.setItem(row, 0, checkbox_item)
            desc_item = QTableWidgetItem(hl.get('description', f'Хайлайт {row + 1}'))
            self.clips_table_widget.setItem(row, 1, desc_item)
            start_str = self.format_seconds_to_time(hl.get('start_time', 0))
            self.clips_table_widget.setItem(row, 2, QTableWidgetItem(start_str))
            end_str = self.format_seconds_to_time(hl.get('end_time', 0))
            self.clips_table_widget.setItem(row, 3, QTableWidgetItem(end_str))
            score_str = f"{hl.get('score', 0.0):.2f}"
            self.clips_table_widget.setItem(row, 4, QTableWidgetItem(score_str))
        self.clips_table_widget.itemChanged.connect(self._on_clips_table_item_changed)
        self._update_buttons_state_after_long_op(False)  # Обновляем состояние кнопок после заполнения таблицы
        self.log_message("Таблица хайлайтов успешно обновлена", level="INFO")

    def _on_clips_table_item_changed(self, item):
        if item.column() == 0:  # Если изменился чекбокс
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

    def export_selected_clips(self):  # <--- ОБНОВЛЕННЫЙ МЕТОД
        self.log_message("export_selected_clips: Начало процесса экспорта.", level="INFO")
        self._export_actually_started_and_not_cancelled = False

        if self.export_thread and self.export_thread.isRunning():
            self.log_message("export_selected_clips: Экспорт уже выполняется.", level="WARN")
            QMessageBox.information(self, "Экспорт", "Процесс экспорта уже выполняется.")
            return

        self._update_buttons_state_after_long_op(True)  # Блокируем UI

        if hasattr(self, 'video_player_widget') and self.video_player_widget:
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

        # --- Показываем диалог выбора параметров экспорта ---
        options_dialog = ExportOptionsDialog(self.export_module, self)
        if not options_dialog.exec():
            self.log_message("export_selected_clips: Выбор параметров экспорта отменен.", level="INFO")
            self._update_buttons_state_after_long_op(False)
            return

        selected_preset_name = options_dialog.get_selected_preset_name()
        if not selected_preset_name:
            self.log_message("export_selected_clips: Пресет не был выбран в диалоге.", level="WARN")
            self._update_buttons_state_after_long_op(False)
            return
        self.log_message(f"export_selected_clips: Выбран пресет для экспорта: '{selected_preset_name}'", level="INFO")
        # --- Конец диалога выбора параметров ---

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
        self.log_message(
            f"export_selected_clips: Запуск экспорта {total_clips_to_export} клипов с пресетом '{selected_preset_name}'.",
            level="INFO")
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
            export_module_instance=self.export_module,  # Передаем экземпляр ExportModule
            parent_logger=self
        )
        self.export_worker.set_temp_dir(app_temp_dir_for_cutting)

        if not self.export_worker.temp_dir_for_cutting:  # Проверка после set_temp_dir
            self.log_message(
                "export_selected_clips: Ошибка установки временной папки в ClipExporterWorker. Экспорт прерван.",
                level="CRITICAL")
            # ... (очистка ресурсов)
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
                output_folder=output_folder,
                export_preset_name=selected_preset_name  # <--- ПЕРЕДАЕМ ВЫБРАННЫЙ ПРЕСЕТ
            )
        )
        self.export_thread.finished.connect(self.export_thread.deleteLater)  # Очистка потока
        self.export_thread.finished.connect(self.cleanup_export_worker)

        self.export_progress_dialog.setValue(0)
        if total_clips_to_export > 0: self.export_progress_dialog.show()
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

    @pyqtSlot(str, bool, str)  # path, success, original_description
    def handle_single_clip_exported(self, exported_path, success, original_description):
        # Этот слот вызывается из ClipExporterWorker для каждого клипа
        # Обновляем self.last_exported_clips_info здесь, если успешно
        if success and exported_path:
            self.log_message(
                f"handle_single_clip_exported: Клип '{original_description}' успешно экспортирован в '{exported_path}'.",
                level="INFO")
            # Находим соответствующий хайлайт в self.detected_highlights, чтобы получить всю информацию
            source_hl_info = {}
            for hl in self.detected_highlights:
                # Сравнение может быть неточным, если description генерируется.
                # Лучше передавать уникальный ID или индекс изначального хайлайта.
                # Пока что оставим по description.
                if hl.get("description") == original_description:
                    source_hl_info = hl.copy()
                    break

            clip_info_for_plan = {
                "path": exported_path,
                "description": original_description,  # Это описание хайлайта
                "title_suggestion": f"Яркий момент: {original_description}",  # Простое предложение
                "source_highlight_info": source_hl_info  # Исходная информация о хайлайте
            }
            self.last_exported_clips_info.append(clip_info_for_plan)
        else:
            self.log_message(
                f"handle_single_clip_exported: Ошибка экспорта клипа '{original_description}'. Путь: '{exported_path}', Успех: {success}",
                level="WARN")

    @pyqtSlot(list, int)  # exported_clips_info_list_from_worker, successful_exports_count_from_worker
    def handle_all_clips_exported(self, exported_clips_info_list_from_worker, successful_exports_count_from_worker):
        # exported_clips_info_list_from_worker - это список, который собрал сам воркер
        # successful_exports_count_from_worker - количество, которое посчитал воркер

        # Используем self.last_exported_clips_info, который мы наполняли в handle_single_clip_exported
        final_successful_count = len(self.last_exported_clips_info)

        self.log_message(
            f"handle_all_clips_exported: Экспорт завершен. Успешно (по данным MainWindow): "
            f"{final_successful_count}. Worker сообщил: {successful_exports_count_from_worker} успешных.",
            level="INFO"
        )
        # Если есть расхождения, можно добавить дополнительное логирование
        if final_successful_count != successful_exports_count_from_worker:
            self.log_message(f"  ВНИМАНИЕ: Расхождение в подсчете успешных экспортов "
                             f"(MainWindow: {final_successful_count}, Worker: {successful_exports_count_from_worker})",
                             level="WARN")

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
                QMessageBox.information(self, "Экспорт завершен",
                                        f"{final_successful_count} клипов было успешно экспортировано.")
            elif len(self.get_selected_highlights_for_export()) > 0:  # Если пытались экспортировать, но не вышло
                QMessageBox.warning(self, "Экспорт завершен",
                                    "Не удалось экспортировать ни одного из выбранных клипов. Проверьте лог.")
            # Если ничего не было выбрано, то сюда не дойдем, т.к. будет выход раньше

        self._export_actually_started_and_not_cancelled = False
        # self._update_buttons_state_after_long_op(False) # Вызывается в cleanup_export_worker

        if self.export_thread and self.export_thread.isRunning():
            self.log_message("handle_all_clips_exported: Явный вызов quit для потока экспорта.", level="DEBUG")
            self.export_thread.quit()
        # cleanup_export_worker вызовется по сигналу finished от потока

    @pyqtSlot(str)
    def handle_export_error(self, error_message):
        self.log_message(f"handle_export_error: КРИТИЧЕСКАЯ ОШИБКА ЭКСПОРТА: {error_message}", level="CRITICAL")
        self._export_actually_started_and_not_cancelled = False  # Сбрасываем флаг

        if self.export_progress_dialog:
            try:
                self.export_progress_dialog.canceled.disconnect(self.cancel_export_process)
            except TypeError:
                pass
            if self.export_progress_dialog.isVisible(): self.export_progress_dialog.close()
            self.export_progress_dialog = None

        QMessageBox.critical(self, "Ошибка экспорта", f"Произошла ошибка во время экспорта:\n{error_message}")

        if self.export_thread and self.export_thread.isRunning():
            self.log_message("handle_export_error: Явный вызов quit для потока экспорта после ошибки.", level="DEBUG")
            self.export_thread.quit()
        # cleanup_export_worker вызовется по сигналу finished от потока или если поток не был запущен

    def cancel_export_process(self):
        self.log_message("cancel_export_process: Запрошена отмена экспорта.", level="WARN")
        self._export_actually_started_and_not_cancelled = False
        if self.export_thread and self.export_thread.isRunning():
            if self.export_worker:
                self.export_worker.cancel_export()  # Сообщаем воркеру об отмене
            if self.export_progress_dialog and self.export_progress_dialog.isVisible():
                self.export_progress_dialog.setLabelText("Отмена экспорта...")
                # Не закрываем диалог сразу, даем воркеру шанс завершиться
        else:  # Если поток уже не активен
            self.log_message("cancel_export_process: Поток экспорта уже не активен.", level="DEBUG")
            if self.export_progress_dialog and self.export_progress_dialog.isVisible():
                self.export_progress_dialog.close()
            self.export_progress_dialog = None
            self._update_buttons_state_after_long_op(False)

    def cleanup_export_worker(self):
        self.log_message("cleanup_export_worker: Начало очистки ресурсов потока экспорта.", level="DEBUG")

        # Удаляем воркер и сбрасываем на него ссылку
        if self.export_worker:
            self.export_worker.deleteLater()
            self.export_worker = None
            self.log_message("cleanup_export_worker: ClipExporterWorker помечен для удаления.", level="DEBUG")

        # Обнуляем ссылку на QThread, чтобы не держать обёртку после deleteLater()
        if self.export_thread:
            self.export_thread = None  # больше не вызываем isRunning() на удалённом объекте :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}

        # Закрываем и обнуляем диалог прогресса
        if self.export_progress_dialog and self.export_progress_dialog.isVisible():
            self.export_progress_dialog.close()
            self.export_progress_dialog = None
            self.log_message("cleanup_export_worker: Диалог прогресса (если был) закрыт/обнулен.", level="DEBUG")

        # Обновляем состояние кнопок/UI
        self._update_buttons_state_after_long_op(False)
        self._export_actually_started_and_not_cancelled = False  # сброс флага
        self.log_message("cleanup_export_worker: UI обновлен.", level="DEBUG")

        # При необходимости перезагружаем видео в плеер
        if self.current_video_path and self.video_player_widget:
            self.log_message(
                "cleanup_export_worker: Перезагрузка видео в плеер после экспорта (если необходимо).",
                level="DEBUG"
            )
            # здесь может быть код перезагрузки, если он нужен :contentReference[oaicite:2]{index=2}:contentReference[oaicite:3]{index=3}

        # Ещё раз на всякий случай обновляем состояния
        self._update_buttons_state_after_long_op(False)

    def generate_content_plan_for_exported_clips(self):
        if not self.last_exported_clips_info:
            QMessageBox.warning(self, "Нет данных для плана",
                                "Сначала экспортируйте клипы—тогда на их основе можно составить расписание.")
            return

        # Передаем self.last_exported_clips_info в ContentPlannerWidget
        if hasattr(self, 'content_planner_widget') and self.content_planner_widget:
            self.log_message(
                f"generate_content_plan_for_exported_clips: Генерация плана на основе {len(self.last_exported_clips_info)} клипов.",
                level="INFO")
            self.content_planner_widget.generate_plan(self.last_exported_clips_info)
            self.tab_widget.setCurrentWidget(
                self.content_planner_widget.parentWidget())  # Переключаемся на вкладку с планом
        else:
            self.log_message("generate_content_plan_for_exported_clips: ContentPlannerWidget не найден.", level="ERROR")
            QMessageBox.critical(self, "Ошибка", "Компонент планировщика контента не инициализирован.")

    def open_settings(self):
        self.log_message("open_settings: Открытие диалога настроек.", level="INFO")
        if (self.analysis_thread and self.analysis_thread.isRunning()) or \
                (self.export_thread and self.export_thread.isRunning()):
            QMessageBox.information(self, "Занято",
                                    "Дождитесь завершения текущих операций (анализа или экспорта) перед изменением настроек.")
            return

        # self.settings_dialog уже создан в __init__
        self.settings_dialog.load_settings()  # Загружаем актуальные настройки
        if self.settings_dialog.exec() == QDialog.DialogCode.Accepted:
            # Настройки были сохранены через save_settings() внутри accept_settings() диалога
            # Применяем специфичные настройки, если нужно
            new_ffmpeg_path = self.settings_dialog.settings.value(CONFIG_FFMPEG_PATH, "ffmpeg")
            if self.cutting_engine.ffmpeg_path != new_ffmpeg_path:
                # Проверка FFmpeg (можно вынести в отдельный метод)
                try:
                    self.log_message(f"open_settings: Проверка нового пути FFmpeg: {new_ffmpeg_path}", level="DEBUG")
                    result = subprocess.run(
                        [new_ffmpeg_path, '-version'],
                        capture_output=True, text=True, check=False,  # check=False чтобы не выбрасывать исключение
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                        timeout=3
                    )
                    if result.returncode == 0 and 'ffmpeg version' in result.stdout.lower():
                        self.cutting_engine.set_ffmpeg_path(new_ffmpeg_path)
                        self.log_message(f"Путь к FFmpeg успешно обновлен на: {new_ffmpeg_path}", level="INFO")
                    else:
                        old_path = self.cutting_engine.ffmpeg_path
                        self.settings_dialog.settings.setValue(CONFIG_FFMPEG_PATH,
                                                               old_path)  # Возвращаем старое значение в QSettings
                        self.settings_dialog.ffmpeg_path_edit.setText(old_path)  # И в поле диалога
                        self.log_message(
                            f"Ошибка проверки FFmpeg по пути '{new_ffmpeg_path}'. Оставлен старый путь: {old_path}. STDERR: {result.stderr.strip()}",
                            level="ERROR")
                        QMessageBox.warning(self, "Ошибка FFmpeg",
                                            f"Не удалось проверить FFmpeg по указанному пути:\n{new_ffmpeg_path}\n\nПроверьте путь или вывод FFmpeg:\n{result.stderr.strip()[:200]}")
                except FileNotFoundError:
                    old_path = self.cutting_engine.ffmpeg_path
                    self.settings_dialog.settings.setValue(CONFIG_FFMPEG_PATH, old_path)
                    self.settings_dialog.ffmpeg_path_edit.setText(old_path)
                    self.log_message(
                        f"Файл FFmpeg не найден по пути '{new_ffmpeg_path}'. Оставлен старый путь: {old_path}.",
                        level="ERROR")
                    QMessageBox.warning(self, "Ошибка FFmpeg",
                                        f"Файл FFmpeg не найден по указанному пути:\n{new_ffmpeg_path}")
                except subprocess.TimeoutExpired:
                    old_path = self.cutting_engine.ffmpeg_path
                    self.settings_dialog.settings.setValue(CONFIG_FFMPEG_PATH, old_path)
                    self.settings_dialog.ffmpeg_path_edit.setText(old_path)
                    self.log_message(
                        f"Проверка FFmpeg по пути '{new_ffmpeg_path}' заняла слишком много времени. Оставлен старый путь: {old_path}.",
                        level="ERROR")
                    QMessageBox.warning(self, "Ошибка FFmpeg",
                                        f"Проверка FFmpeg по пути '{new_ffmpeg_path}' заняла слишком много времени.")
                except Exception as e:
                    old_path = self.cutting_engine.ffmpeg_path
                    self.settings_dialog.settings.setValue(CONFIG_FFMPEG_PATH, old_path)
                    self.settings_dialog.ffmpeg_path_edit.setText(old_path)
                    self.log_message(
                        f"Непредвиденная ошибка при проверке FFmpeg '{new_ffmpeg_path}': {e}. Оставлен старый путь: {old_path}.",
                        level="CRITICAL")
                    QMessageBox.critical(self, "Ошибка FFmpeg", f"Непредвиденная ошибка при проверке FFmpeg:\n{e}")
            self.log_message("Настройки сохранены и применены.", level="INFO")
        else:
            self.log_message("Изменение настроек отменено.", level="INFO")

    def show_about_dialog(self):
        self.log_message("show_about_dialog: Открытие окна 'О программе'.", level="INFO")
        QMessageBox.about(self, "О программе Automated Content Creator",
                          "<html><head/><body>"
                          "<p><b>Автоматизированный Создатель Контента</b></p>"
                          "<p>Версия: 0.3.1 (Alpha)</p>"
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

        # Безопасно проверяем, живы ли потоки
        analysis_running = False
        export_running = False

        if self.analysis_thread:
            try:
                analysis_running = self.analysis_thread.isRunning()
            except RuntimeError:
                analysis_running = False

        if self.export_thread:
            try:
                export_running = self.export_thread.isRunning()
            except RuntimeError:
                export_running = False

        # Если какой-нибудь поток ещё работает — предупреждаем пользователя
        if analysis_running or export_running:
            reply = QMessageBox.question(
                self,
                "Закрытие",
                "Анализ или экспорт всё ещё выполняются. Вы действительно хотите закрыть приложение?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Останавливаем потоки корректно, если они всё ещё живы
                if analysis_running:
                    self.analysis_thread.quit()
                if export_running:
                    self.export_thread.quit()
                event.accept()
            else:
                event.ignore()
        else:
            # Обычный диалог подтверждения закрытия
            reply = QMessageBox.question(
                self,
                "Закрытие",
                "Вы действительно хотите выйти из приложения?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
