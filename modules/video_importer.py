# automated_content_creator/modules/video_importer.py

from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QStandardPaths
import os

class VideoImporter:
    def __init__(self, parent=None):
        self.parent = parent
        self.allowed_formats = "Видео файлы (*.mp4 *.mov *.avi *.mkv);;Все файлы (*)"

    def import_video(self):
        """
        Открывает диалоговое окно для выбора видеофайла.
        Возвращает путь к выбранному файлу или None, если выбор отменен.
        """
        # Попробуем получить стандартную папку "Видео" пользователя
        default_dir = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.MoviesLocation)
        start_path = default_dir[0] if default_dir else os.path.expanduser("~")

        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Импортировать видео",
            start_path,
            self.allowed_formats
        )
        if file_path:
            # TODO: Добавить проверку на реальную поддержку формата, а не только расширение
            return file_path
        return None

    def get_supported_formats_for_dialog(self):
        """Возвращает строку форматов для QFileDialog."""
        return self.allowed_formats