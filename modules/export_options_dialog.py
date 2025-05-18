# automated_content_creator/modules/export_options_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QLabel, QDialogButtonBox, QTextBrowser
)
from PyQt6.QtCore import Qt

class ExportOptionsDialog(QDialog):
    """
    Диалоговое окно для выбора параметров экспорта, в частности пресета.
    """
    def __init__(self, export_module_instance, parent=None):
        super().__init__(parent)
        self.export_module = export_module_instance
        self.selected_preset_name = None

        self.setWindowTitle("Параметры экспорта клипов")
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.preset_combo = QComboBox()
        presets = self.export_module.get_available_presets()
        if presets:
            self.preset_combo.addItems(presets)
        form_layout.addRow("Пресет экспорта:", self.preset_combo)

        self.preset_description_label = QLabel("Описание пресета:")
        form_layout.addRow(self.preset_description_label)

        self.preset_description_browser = QTextBrowser()
        self.preset_description_browser.setFixedHeight(80) # Ограничим высоту
        self.preset_description_browser.setReadOnly(True)
        form_layout.addRow(self.preset_description_browser)


        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept_options)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.preset_combo.currentTextChanged.connect(self._update_preset_description)
        if presets:
            self._update_preset_description(presets[0]) # Инициализация описания для первого пресета

        if parent and hasattr(parent, 'log_message'):
            parent.log_message("ExportOptionsDialog: Инициализирован.", level="DEBUG")

    def _update_preset_description(self, preset_name):
        """Обновляет описание пресета при выборе в QComboBox."""
        if not preset_name:
            self.preset_description_browser.setText("Пресет не выбран.")
            return

        config = self.export_module.get_preset_config(preset_name)
        if config:
            desc_parts = [f"<b>{preset_name}</b>"]
            if config.get("description"):
                desc_parts.append(config.get("description"))
            if config.get("recode", False):
                desc_parts.append(f"<i>Требуется перекодирование.</i>")
                if config.get("target_resolution"):
                    desc_parts.append(f"Разрешение: {config.get('target_resolution')}")
                if config.get("extension"):
                     desc_parts.append(f"Расширение: {config.get('extension')}")
            else:
                desc_parts.append("<i>Копирование без перекодирования.</i>")
                if config.get("extension"):
                     desc_parts.append(f"Расширение: {config.get('extension')}")

            self.preset_description_browser.setHtml("<br>".join(desc_parts))
        else:
            self.preset_description_browser.setText(f"Описание для '{preset_name}' не найдено.")

    def accept_options(self):
        """Сохраняет выбранный пресет и принимает диалог."""
        self.selected_preset_name = self.preset_combo.currentText()
        if self.parent() and hasattr(self.parent(), 'log_message'):
            self.parent().log_message(f"ExportOptionsDialog: Выбран пресет '{self.selected_preset_name}'. Диалог принят.", level="INFO")
        self.accept()

    def get_selected_preset_name(self):
        """Возвращает имя выбранного пресета."""
        return self.selected_preset_name

if __name__ == '__main__':
    # Пример использования (требует QApplication и мок ExportModule)
    from PyQt6.QtWidgets import QApplication
    import sys

    class MockExportModule:
        def get_available_presets(self):
            return ["Original", "Reels (9:16)", "YouTube Shorts (16:9)"]
        def get_preset_config(self, preset_name):
            if preset_name == "Original":
                return {"description": "Копирует как есть.", "recode": False, "extension": ".mp4"}
            elif preset_name == "Reels (9:16)":
                return {"description": "Вертикальное видео для соцсетей.", "recode": True, "target_resolution": "1080x1920", "extension": ".mp4"}
            elif preset_name == "YouTube Shorts (16:9)":
                return {"description": "Горизонтальное видео для Shorts.", "recode": True, "target_resolution": "1920x1080", "extension": ".mp4"}
            return None

    app = QApplication(sys.argv)
    mock_exporter = MockExportModule()
    dialog = ExportOptionsDialog(mock_exporter)
    if dialog.exec():
        print(f"Выбранный пресет: {dialog.get_selected_preset_name()}")
    sys.exit(app.exec())
