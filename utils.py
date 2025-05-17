# automated_content_creator/utils.py

import os
from PyQt6.QtCore import QStandardPaths

def get_resource_path(relative_path):
    """Получает абсолютный путь к ресурсу в папке resources."""
    base_path = os.path.abspath(".") # Корень проекта
    return os.path.join(base_path, "resources", relative_path)

def get_default_output_folder():
    """Возвращает папку 'Видео/AutomatedContentCreator' или 'Документы', если 'Видео' нет."""
    videos_location = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.MoviesLocation)
    if videos_location:
        default_folder = os.path.join(videos_location[0], "AutomatedContentCreator_Output")
    else:
        docs_location = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.DocumentsLocation)
        default_folder = os.path.join(docs_location[0], "AutomatedContentCreator_Output")

    os.makedirs(default_folder, exist_ok=True)
    return default_folder


# Можно добавить другие вспомогательные функции, например:
# - Валидаторы
# - Конвертеры форматов времени
# - Функции для работы с файловой системой и т.д.

if __name__ == '__main__':
    print(f"Default output folder: {get_default_output_folder()}")
    # print(f"Path to icon (example): {get_resource_path('icons/app_icon.png')}")