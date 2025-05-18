# automated_content_creator/modules/video_player.py

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QSlider, QLabel, QStyle, QSizePolicy, QSpacerItem, QMessageBox)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime, qFormatLogMessage, QDateTime, QTimer  # Добавил QDateTime, QTimer


class VideoPlayerWidget(QWidget):
    """
    Виджет для воспроизведения видео с элементами управления.
    """

    def __init__(self, parent_window=None):  # parent_window - это MainWindow
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.media_player = None
        self.audio_output = None
        self._video_loaded = False
        self._log_prefix = self.__class__.__name__

        self._init_ui()
        self._create_connections()

        if not (self.parent_window and hasattr(self.parent_window, 'log_message')):
            print(
                f"{self._log_prefix}: ВНИМАНИЕ! Родительское окно не имеет метода log_message. Логирование будет в консоль.")
            # self.parent_window = None # Не сбрасываем, чтобы _log все равно пытался вызвать
        self._log("VideoPlayerWidget инициализирован.")

    def _log(self, message: str, level: str = "INFO"):
        # Используем логгер MainWindow, если доступен
        if self.parent_window and hasattr(self.parent_window, 'log_message'):
            # MainWindow.log_message сам добавит свой префикс и временную метку
            self.parent_window.log_message(f"({self._log_prefix}) {message}", level=level)
        else:
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
            print(f"{timestamp} [{self._log_prefix}] [{level}]: {message}")

    def _init_ui(self):
        """Инициализация пользовательского интерфейса плеера."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.video_widget)

        control_panel_layout = QVBoxLayout()
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 0)
        self.time_slider.setEnabled(False)
        control_panel_layout.addWidget(self.time_slider)

        buttons_and_time_layout = QHBoxLayout()
        self.play_pause_button = QPushButton()
        self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_pause_button.setEnabled(False)
        self.play_pause_button.setToolTip("Воспроизвести/Пауза (Пробел)")
        buttons_and_time_layout.addWidget(self.play_pause_button)

        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip("Остановить (S)")
        buttons_and_time_layout.addWidget(self.stop_button)

        self.time_label = QLabel("00:00:00 / 00:00:00")
        buttons_and_time_layout.addWidget(self.time_label)
        buttons_and_time_layout.addSpacerItem(
            QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.volume_icon_label = QLabel()
        self.volume_icon_label.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume).pixmap(16, 16))
        buttons_and_time_layout.addWidget(self.volume_icon_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75)
        self.volume_slider.setMaximumWidth(120)
        self.volume_slider.setToolTip("Громкость")
        buttons_and_time_layout.addWidget(self.volume_slider)

        control_panel_layout.addLayout(buttons_and_time_layout)
        main_layout.addLayout(control_panel_layout)
        self.setLayout(main_layout)

    def _create_media_player(self):
        self._log("_create_media_player: Начало создания/обновления медиаплеера.", level="DEBUG")
        if self.media_player:
            self._log("  Предыдущий экземпляр media_player существует. Остановка и отсоединение сигналов.",
                      level="DEBUG")
            self.media_player.stop()
            # Попытка отсоединить сигналы, чтобы избежать ошибок при их отсутствии
            try:
                self.media_player.errorOccurred.disconnect(self._handle_media_error)
            except TypeError:
                pass
            try:
                self.media_player.playbackStateChanged.disconnect(self._handle_playback_state_changed)
            except TypeError:
                pass
            try:
                self.media_player.positionChanged.disconnect(self._handle_position_changed)
            except TypeError:
                pass
            try:
                self.media_player.durationChanged.disconnect(self._handle_duration_changed)
            except TypeError:
                pass

            # Отсоединяем от video_widget и audio_output
            self.media_player.setVideoOutput(None)
            if self.audio_output:
                self.media_player.setAudioOutput(None)
                # QAudioOutput не имеет deleteLater, и обычно управляется QMediaPlayer
                # Просто удаляем ссылку Python, Qt должен справиться с C++ объектом
                self._log("  Удаление ссылки на старый audio_output.", level="DEBUG")
                del self.audio_output  # или self.audio_output = None
                self.audio_output = None

            self._log("  Планирование удаления старого media_player (deleteLater).", level="DEBUG")
            self.media_player.deleteLater()  # Безопасное удаление Qt объекта
            self.media_player = None

        self._log("  Создание новых экземпляров QMediaPlayer и QAudioOutput.", level="DEBUG")
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        self.media_player.errorOccurred.connect(self._handle_media_error)
        self.media_player.playbackStateChanged.connect(self._handle_playback_state_changed)
        self.media_player.positionChanged.connect(self._handle_position_changed)
        self.media_player.durationChanged.connect(self._handle_duration_changed)

        # Громкость подключается здесь, так как audio_output только что создан
        if self.audio_output:  # Убедимся что он создан
            try:
                self.volume_slider.valueChanged.disconnect(self._set_volume_from_slider)  # Отсоединяем старый, если был
            except TypeError:
                pass
            self._set_volume_from_slider(self.volume_slider.value())  # Устанавливаем текущее значение
            self.volume_slider.valueChanged.connect(self._set_volume_from_slider)
            self._log("  Слайдер громкости подключен к новому audio_output.", level="DEBUG")

        self._log("Экземпляры QMediaPlayer и QAudioOutput созданы/обновлены.", level="INFO")

    def _create_connections(self):
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.stop_button.clicked.connect(self.stop_playback)
        self.time_slider.sliderMoved.connect(self._set_position_from_slider)
        # self.volume_slider.valueChanged уже подключен в _create_media_player

    def load_video(self, file_path: str):
        self._log(f"load_video: Попытка загрузки видео '{file_path}'", level="INFO")
        if not file_path or not os.path.exists(file_path):
            err_msg = f"Ошибка загрузки: Файл не найден или путь не указан '{file_path}'"
            self._log(err_msg, level="ERROR")
            QMessageBox.critical(self, "Ошибка видео", f"Файл видео не найден:\n{file_path}")
            self._set_controls_enabled(False)
            self._video_loaded = False
            return

        self._create_media_player()  # Пересоздаем плеер для нового видео

        source = QUrl.fromLocalFile(file_path)
        self.media_player.setSource(source)

        self._set_controls_enabled(True)
        self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._video_loaded = True
        self._log(f"Видео '{os.path.basename(file_path)}' загружено. Готово к воспроизведению.", level="INFO")

    def toggle_play_pause(self):
        if not self._video_loaded or not self.media_player:
            self._log("Воспроизведение/пауза: Видео не загружено.", level="WARN")
            return

        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self._log("Пауза.", level="INFO")
        else:
            self.media_player.play()
            self._log("Воспроизведение...", level="INFO")

    def stop_playback(self):
        if not self._video_loaded or not self.media_player:
            self._log("Остановка: Видео не загружено.", level="WARN")
            return
        self.media_player.stop()
        self._log("Воспроизведение остановлено.", level="INFO")

    def _handle_media_error(self, error_code, error_string=""):
        error_type = type(error_code)
        self._log(
            f"_handle_media_error: Получена ошибка. Тип: {error_type}, Код/Строка: {error_code}, Строка: '{error_string}'",
            level="ERROR")

        final_error_string = "Неизвестная ошибка медиаплеера"
        if isinstance(error_code, QMediaPlayer.Error):  # PyQt6 < 6.5, error_code is enum
            final_error_string = f"{error_code.name}: {self.media_player.errorString()}"
        elif isinstance(error_code, str):  # PyQt6 >= 6.5, error_code is error_string
            final_error_string = error_code  # Это уже строка ошибки
        elif error_string:  # Если error_code это int, а error_string передан (новый API)
            final_error_string = error_string

        self._log(f"Ошибка медиаплеера: {final_error_string}", level="ERROR")
        QMessageBox.critical(self, "Ошибка воспроизведения", f"Не удалось воспроизвести видео:\n{final_error_string}")
        self._set_controls_enabled(False)
        self._video_loaded = False

    def _handle_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._log(f"Состояние плеера изменено на: {state.name}", level="DEBUG")

    def _handle_position_changed(self, position_ms: int):
        if not self.time_slider.isSliderDown():
            self.time_slider.setValue(position_ms)
        self._update_time_label(position_ms, self.media_player.duration() if self.media_player else 0)

    def _handle_duration_changed(self, duration_ms: int):
        self.time_slider.setRange(0, duration_ms)
        self._update_time_label(self.media_player.position() if self.media_player else 0, duration_ms)
        self._log(f"Длительность видео изменена: {duration_ms} мс", level="DEBUG")

    def _set_position_from_slider(self, position_ms: int):
        if self.media_player:
            self.media_player.setPosition(position_ms)
            self._update_time_label(position_ms, self.media_player.duration())

    def _set_volume_from_slider(self, volume_level: int):
        if self.audio_output:
            volume_float = float(volume_level) / 100.0
            self.audio_output.setVolume(volume_float)
            if volume_level == 0:
                self.volume_icon_label.setPixmap(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted).pixmap(16, 16))
            else:
                self.volume_icon_label.setPixmap(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume).pixmap(16, 16))

    def _update_time_label(self, current_ms: int, total_ms: int):
        current_time = QTime(0, 0, 0, 0).addMSecs(current_ms)
        total_time = QTime(0, 0, 0, 0).addMSecs(total_ms)
        format_str = "mm:ss" if total_time.hour() == 0 else "hh:mm:ss"
        self.time_label.setText(f"{current_time.toString(format_str)} / {total_time.toString(format_str)}")

    def _set_controls_enabled(self, enabled: bool):
        self.play_pause_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.time_slider.setEnabled(enabled)
        self.volume_slider.setEnabled(bool(self.audio_output))  # Зависит от наличия audio_output

    def set_playback_position(self, position_ms: int):
        if self.media_player and self._video_loaded:
            self._log(f"Установка позиции воспроизведения на {position_ms} мс.", level="DEBUG")
            self.media_player.setPosition(position_ms)
            # Не запускаем воспроизведение автоматически, просто устанавливаем позицию.
            # Пользователь сам решит, нажимать Play или нет.
            # if self.media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            #     self.media_player.play()
            #     QTimer.singleShot(50, lambda: self.media_player.pause() if self.media_player else None)

    def get_current_media_player(self) -> QMediaPlayer | None:
        return self.media_player

    def cleanup(self):
        self._log("cleanup: Начало очистки VideoPlayerWidget...", level="INFO")
        if self.media_player:
            self._log("  Остановка медиаплеера...", level="DEBUG")
            self.media_player.stop()

            self._log("  Отсоединение видеовыхода...", level="DEBUG")
            self.media_player.setVideoOutput(None)  # Важно отсоединить от виджета

            if self.audio_output:
                self._log("  Отсоединение аудиовыхода...", level="DEBUG")
                self.media_player.setAudioOutput(None)
                # QAudioOutput не имеет deleteLater и обычно не требует явного удаления,
                # если QMediaPlayer правильно управляет его жизненным циклом.
                # Обнуление ссылки помогает сборщику мусора Python.
                self._log("  Обнуление ссылки на audio_output...", level="DEBUG")
                self.audio_output = None  # Просто обнуляем ссылку Python

            self._log("  Установка пустого источника для медиаплеера...", level="DEBUG")
            self.media_player.setSource(QUrl())  # Очищаем источник, чтобы освободить файл

            self._log("  Планирование удаления QMediaPlayer (deleteLater)...", level="DEBUG")
            self.media_player.deleteLater()  # Безопасное удаление Qt-объекта
            self.media_player = None  # Обнуляем ссылку Python

            self._log("Медиаплеер остановлен, ресурсы очищены/запланированы к удалению.", level="INFO")
        else:
            self._log("Медиаплеер не был активен, активная очистка не требуется.", level="DEBUG")

        self._video_loaded = False  # Сбрасываем флаг
        self._set_controls_enabled(False)  # Отключаем контролы
        self._log("cleanup: VideoPlayerWidget очищен.", level="INFO")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Space:
            self.toggle_play_pause()
            event.accept()
        elif key == Qt.Key.Key_S:
            self.stop_playback()
            event.accept()
        else:
            super().keyPressEvent(event)