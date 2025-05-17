# automated_content_creator/modules/content_planner.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QCalendarWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QDialog, QLineEdit, QDateTimeEdit,
                             QDialogButtonBox, QFormLayout, QComboBox, QTextEdit,
                             QAbstractItemView, QMenu, QMessageBox) # Добавил QAbstractItemView, QMenu, QMessageBox
from PyQt6.QtGui import QAction, QColor, QBrush, QTextCharFormat, QIcon, \
    QFont  # Для подсветки календаря и контекстного меню
from PyQt6.QtCore import QDate, QDateTime, Qt, QTime # Добавил QTime
import random
from datetime import datetime, timedelta # datetime не используется напрямую, но может пригодиться
import os # Для извлечения имени файла

class ContentPlannerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent # MainWindow
        self._init_ui()
        self.content_plan_data = [] # Список словарей для хранения элементов плана
        self.default_platforms = ["Instagram Reels", "YouTube Shorts", "TikTok"]

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Календарь ---
        self.calendar_widget = QCalendarWidget()
        self.calendar_widget.setGridVisible(True)
        self.calendar_widget.setNavigationBarVisible(True)
        self.calendar_widget.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar_widget.clicked[QDate].connect(self.on_calendar_date_selected)
        main_layout.addWidget(self.calendar_widget)

        # --- Таблица для постов ---
        self.plan_table_widget = QTableWidget()
        self.plan_table_widget.setColumnCount(5) # Дата, Время, Платформа, Описание/Заголовок, Хэштеги
        self.plan_table_widget.setHorizontalHeaderLabels(["Дата", "Время", "Платформа", "Описание", "Хэштеги"])
        self.plan_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.plan_table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Дата
        self.plan_table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # Время
        self.plan_table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Платформа
        self.plan_table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plan_table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.plan_table_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # По одному элементу
        self.plan_table_widget.setAlternatingRowColors(True)
        self.plan_table_widget.doubleClicked.connect(self.edit_selected_plan_item_from_table)

        # Контекстное меню для таблицы
        self.plan_table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.plan_table_widget.customContextMenuRequested.connect(self.show_table_context_menu)

        main_layout.addWidget(self.plan_table_widget)

        # --- Кнопки управления планом ---
        buttons_layout = QHBoxLayout()
        # Кнопка "Добавить пост вручную" может быть полезна, но пока уберем для упрощения
        # self.add_post_button = QPushButton("Добавить пост вручную")
        # self.add_post_button.clicked.connect(self.add_new_post_dialog)
        # buttons_layout.addWidget(self.add_post_button)

        self.edit_post_button = QPushButton(QIcon.fromTheme("document-edit")," Редактировать")
        self.edit_post_button.setToolTip("Редактировать выбранный пост в плане")
        self.edit_post_button.clicked.connect(self.edit_selected_plan_item_from_table)
        buttons_layout.addWidget(self.edit_post_button)

        self.remove_post_button = QPushButton(QIcon.fromTheme("edit-delete"), " Удалить")
        self.remove_post_button.setToolTip("Удалить выбранный пост из плана")
        self.remove_post_button.clicked.connect(self.remove_selected_plan_item)
        buttons_layout.addWidget(self.remove_post_button)

        self.clear_plan_button = QPushButton(QIcon.fromTheme("edit-clear-all"), " Очистить план")
        self.clear_plan_button.setToolTip("Удалить все посты из текущего плана")
        self.clear_plan_button.clicked.connect(self.confirm_clear_plan)
        buttons_layout.addWidget(self.clear_plan_button)

        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def generate_plan(self, clips_info_list, start_date=None, posts_per_day=None, platforms=None, start_hour=None):
        self.clear_plan() # Очищаем старый план перед генерацией нового
        if not clips_info_list:
            if self.parent_window: self.parent_window.log_message("Контент-план: Нет клипов для планирования.")
            return []

        # Получаем настройки по умолчанию, если не переданы
        current_settings = self.parent_window.settings_dialog.get_current_settings() if self.parent_window else {}
        posts_per_day_default = current_settings.get('planner_posts_per_day', 1)
        start_hour_default = current_settings.get('planner_start_time_hour', 10)

        _posts_per_day = posts_per_day if posts_per_day is not None else posts_per_day_default
        _platforms = platforms if platforms else self.default_platforms
        _start_hour = start_hour if start_hour is not None else start_hour_default

        if start_date is None:
            start_date = self.calendar_widget.selectedDate()
            if start_date < QDate.currentDate().addDays(1) : # Если выбрана сегодня или раньше, начинаем с завтра
                start_date = QDate.currentDate().addDays(1)

        current_plan_datetime = QDateTime(start_date, QTime(_start_hour, 0, 0)) # Начальное время

        # Интервал между постами в часах (простое равномерное распределение)
        # Если _posts_per_day = 1, то интервал не важен, пост будет в _start_hour
        # Если > 1, то (22 - _start_hour) / (_posts_per_day -1) (чтобы не выходить за пределы ~22:00)
        # Упростим: если больше 1 поста, то шаг, например, 3-4 часа
        time_increment_hours = 3 if _posts_per_day > 1 else 24 # Если 1 пост, то следующий день

        platform_idx = 0

        for i, clip_info in enumerate(clips_info_list):
            platform = _platforms[platform_idx % len(_platforms)]
            platform_idx += 1

            # Генерация заголовка/описания и хэштегов (можно улучшить)
            clip_filename = os.path.basename(clip_info.get('path', f'Клип_{i+1}'))
            base_title = clip_info.get('title_suggestion', f"Интересный момент: {clip_filename}")
            description = base_title # В данном случае описание = заголовок

            # Хэштеги (можно вынести в настройки или использовать генератор)
            hashtags_base = ["#AZGROUP", "#образование", "#школьники"]
            hashtags_from_clip = clip_info.get("source_highlight_info", {}).get("hashtags", []) # Если есть из AI
            generated_hashtags = self.parent_window.subtitles_generator.generate_hashtags(description, top_n=3) if self.parent_window else []
            all_hashtags = list(set(hashtags_base + hashtags_from_clip + generated_hashtags))
            final_hashtags_str = " ".join(random.sample(all_hashtags, min(len(all_hashtags), 5))) # Берем до 5 уникальных

            plan_item = {
                "datetime": QDateTime(current_plan_datetime), # Копируем QDateTime
                "platform": platform,
                "description": description, # Используем поле "description" для основного текста
                "hashtags": final_hashtags_str,
                "clip_path": clip_info.get('path', 'N/A'), # Путь к файлу клипа
                "source_clip_info": clip_info # Сохраняем всю инфу об исходном клипе
            }
            self.content_plan_data.append(plan_item)

            # Переход к следующему времени/дню
            if (i + 1) % _posts_per_day == 0: # Достигли лимита постов на этот день
                current_plan_datetime = current_plan_datetime.addDays(1)
                current_plan_datetime.setTime(QTime(_start_hour, 0, 0)) # Утро следующего дня
            else: # Следующий пост в тот же день
                current_plan_datetime = current_plan_datetime.addSecs(time_increment_hours * 3600)
                if current_plan_datetime.time().hour() >= 23: # Если вышли за 23:00, переносим на утро следующего дня
                    current_plan_datetime = current_plan_datetime.addDays(1)
                    current_plan_datetime.setTime(QTime(_start_hour, 0,0))


        self.content_plan_data.sort(key=lambda x: x["datetime"])
        self._display_plan_in_table()
        if self.parent_window: self.parent_window.log_message(f"Контент-план: Сгенерировано {len(self.content_plan_data)} постов.")
        return self.content_plan_data


    def _display_plan_in_table(self):
        self.plan_table_widget.setRowCount(0)
        self.plan_table_widget.setRowCount(len(self.content_plan_data))

        for row, item in enumerate(self.content_plan_data):
            # Сохраняем индекс из self.content_plan_data в UserRole первого элемента строки
            # Это поможет при редактировании/удалении найти правильный элемент в self.content_plan_data
            date_item = QTableWidgetItem(item["datetime"].toString("dd.MM.yyyy"))
            date_item.setData(Qt.ItemDataRole.UserRole, row) # Сохраняем индекс
            self.plan_table_widget.setItem(row, 0, date_item)

            self.plan_table_widget.setItem(row, 1, QTableWidgetItem(item["datetime"].toString("HH:mm")))
            self.plan_table_widget.setItem(row, 2, QTableWidgetItem(item.get("platform", "N/A")))
            self.plan_table_widget.setItem(row, 3, QTableWidgetItem(item.get("description", "Без описания")))
            self.plan_table_widget.setItem(row, 4, QTableWidgetItem(item.get("hashtags", "")))

        self._highlight_calendar_dates_with_posts()
        self._update_buttons_state()


    def _highlight_calendar_dates_with_posts(self):
        # Сначала сбросим все предыдущие форматирования дат
        today = QDate.currentDate()
        for year_offset in range(-1, 2): # Для текущего, прошлого и следующего года (для примера)
            for month in range(1, 13):
                for day in range(1, QDate(today.year() + year_offset, month, 1).daysInMonth() + 1):
                    date_to_reset = QDate(today.year() + year_offset, month, day)
                    if date_to_reset.isValid():
                         self.calendar_widget.setDateTextFormat(date_to_reset, QTextCharFormat()) # Сброс

        # Теперь подсветим нужные
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QBrush(QColor("lightyellow"))) # Цвет фона
        highlight_format.setForeground(QBrush(QColor("darkblue")))   # Цвет текста
        highlight_format.setFontWeight(QFont.Weight.Bold)

        planned_qdates = {item["datetime"].date() for item in self.content_plan_data}
        for q_date in planned_qdates:
            if q_date.isValid():
                self.calendar_widget.setDateTextFormat(q_date, highlight_format)

    def on_calendar_date_selected(self, q_date: QDate):
        """Фильтрует таблицу, показывая посты только на выбранную в календаре дату."""
        if not self.content_plan_data:
            return

        # Сначала показываем все строки
        for row in range(self.plan_table_widget.rowCount()):
            self.plan_table_widget.setRowHidden(row, False)

        # Затем скрываем те, что не соответствуют дате
        has_posts_on_date = False
        for row in range(self.plan_table_widget.rowCount()):
            item_data_index = self.plan_table_widget.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if item_data_index is not None and 0 <= item_data_index < len(self.content_plan_data):
                post_date = self.content_plan_data[item_data_index]["datetime"].date()
                if post_date != q_date:
                    self.plan_table_widget.setRowHidden(row, True)
                else:
                    has_posts_on_date = True
        if self.parent_window:
            status_msg = f"Показаны посты на {q_date.toString('dd.MM.yyyy')}" if has_posts_on_date else f"Нет запланированных постов на {q_date.toString('dd.MM.yyyy')}"
            self.parent_window.log_message(f"Контент-план: {status_msg}")


    def confirm_clear_plan(self):
        if not self.content_plan_data:
            QMessageBox.information(self, "План пуст", "Контент-план уже пуст.")
            return
        reply = QMessageBox.question(self, "Очистить контент-план?",
                                     "Вы уверены, что хотите удалить все записи из контент-плана?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_plan()

    def clear_plan(self):
        self.content_plan_data = []
        self._display_plan_in_table() # Это также сбросит подсветку календаря
        if self.parent_window: self.parent_window.log_message("Контент-план: План полностью очищен.")

    def edit_selected_plan_item_from_table(self):
        selected_rows = self.plan_table_widget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Нет выбора", "Пожалуйста, выберите пост для редактирования.")
            return
        # Берем индекс из первой выделенной строки (т.к. SingleSelection)
        # Этот индекс соответствует self.content_plan_data
        item_data_idx = self.plan_table_widget.item(selected_rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        self._edit_plan_item_by_internal_index(item_data_idx)


    def _edit_plan_item_by_internal_index(self, internal_data_index):
        if internal_data_index is None or not (0 <= internal_data_index < len(self.content_plan_data)):
            if self.parent_window: self.parent_window.log_message(f"Контент-план: Ошибка индекса ({internal_data_index}) при редактировании.")
            QMessageBox.warning(self, "Ошибка", "Не удалось найти элемент для редактирования. Индекс некорректен.")
            return

        item_to_edit = self.content_plan_data[internal_data_index]
        dialog = EditPlanItemDialog(item_to_edit, self.default_platforms, self) # Передаем список платформ
        if dialog.exec():
            updated_item_data = dialog.get_data()
            self.content_plan_data[internal_data_index] = updated_item_data
            self.content_plan_data.sort(key=lambda x: x["datetime"]) # Пересортируем, т.к. дата могла измениться
            self._display_plan_in_table()
            if self.parent_window: self.parent_window.log_message(f"Контент-план: Элемент '{updated_item_data['description'][:30]}...' обновлен.")
        else:
            if self.parent_window: self.parent_window.log_message("Контент-план: Редактирование элемента отменено.")

    def remove_selected_plan_item(self):
        selected_rows = self.plan_table_widget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Нет выбора", "Пожалуйста, выберите пост для удаления.")
            return

        item_data_idx = self.plan_table_widget.item(selected_rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)

        if item_data_idx is None or not (0 <= item_data_idx < len(self.content_plan_data)):
            if self.parent_window: self.parent_window.log_message(f"Контент-план: Ошибка индекса ({item_data_idx}) при удалении.")
            QMessageBox.warning(self, "Ошибка", "Не удалось найти элемент для удаления. Индекс некорректен.")
            return

        item_desc_for_log = self.content_plan_data[item_data_idx].get("description", "Без названия")[:30]
        reply = QMessageBox.question(self, "Удалить пост?",
                                     f"Вы уверены, что хотите удалить пост '{item_desc_for_log}...' из плана?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            removed_item = self.content_plan_data.pop(item_data_idx)
            self._display_plan_in_table() # Обновляем таблицу и календарь
            if self.parent_window: self.parent_window.log_message(f"Контент-план: Удален пост '{removed_item['description'][:30]}...'.")
        else:
            if self.parent_window: self.parent_window.log_message("Контент-план: Удаление элемента отменено.")

    def _update_buttons_state(self):
        has_items = bool(self.content_plan_data)
        self.edit_post_button.setEnabled(has_items and self.plan_table_widget.selectionModel().hasSelection())
        self.remove_post_button.setEnabled(has_items and self.plan_table_widget.selectionModel().hasSelection())
        self.clear_plan_button.setEnabled(has_items)

    def show_table_context_menu(self, position):
        menu = QMenu()
        selected_items = self.plan_table_widget.selectedItems()

        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(self.edit_selected_plan_item_from_table)
        edit_action.setEnabled(bool(selected_items))
        menu.addAction(edit_action)

        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(self.remove_selected_plan_item)
        delete_action.setEnabled(bool(selected_items))
        menu.addAction(delete_action)

        menu.addSeparator()
        clear_all_action = QAction("Очистить весь план", self)
        clear_all_action.triggered.connect(self.confirm_clear_plan)
        clear_all_action.setEnabled(bool(self.content_plan_data))
        menu.addAction(clear_all_action)

        menu.exec(self.plan_table_widget.viewport().mapToGlobal(position))


# --- Диалоговое окно для редактирования/добавления элемента плана ---
class EditPlanItemDialog(QDialog):
    def __init__(self, item_data, available_platforms, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование поста в контент-плане")
        self.setMinimumWidth(450)
        self.item_data_original = item_data # Сохраняем оригинал для информации
        self.item_data_copy = item_data.copy() # Работаем с копией

        layout = QFormLayout(self)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow) # Растягивать поля

        self.datetime_edit = QDateTimeEdit(self.item_data_copy["datetime"])
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        layout.addRow("Дата и время публикации:", self.datetime_edit)

        self.platform_combo = QComboBox()
        self.platform_combo.addItems(available_platforms if available_platforms else ["Instagram", "YouTube", "TikTok"])
        current_platform = self.item_data_copy.get("platform", available_platforms[0] if available_platforms else "Instagram")
        if current_platform in [self.platform_combo.itemText(i) for i in range(self.platform_combo.count())]:
            self.platform_combo.setCurrentText(current_platform)
        elif self.platform_combo.count() > 0:
             self.platform_combo.setCurrentIndex(0)

        layout.addRow("Платформа:", self.platform_combo)

        self.description_edit = QTextEdit(self.item_data_copy.get("description", ""))
        self.description_edit.setFixedHeight(100) # Высота для многострочного текста
        self.description_edit.setPlaceholderText("Введите описание или основной текст поста...")
        layout.addRow("Описание/Текст поста:", self.description_edit)

        self.hashtags_edit = QLineEdit(self.item_data_copy.get("hashtags", ""))
        self.hashtags_edit.setPlaceholderText("#хэштег1 #хэштег2 ...")
        layout.addRow("Хэштеги:", self.hashtags_edit)

        clip_path_str = self.item_data_original.get('clip_path', 'N/A')
        self.clip_path_label = QLabel(f"Исходный клип: {os.path.basename(clip_path_str)}")
        self.clip_path_label.setToolTip(clip_path_str) # Полный путь в подсказке
        self.clip_path_label.setWordWrap(True)
        layout.addRow(self.clip_path_label)


        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_data(self):
        """Возвращает обновленные данные из полей диалога."""
        self.item_data_copy["datetime"] = self.datetime_edit.dateTime()
        self.item_data_copy["platform"] = self.platform_combo.currentText()
        self.item_data_copy["description"] = self.description_edit.toPlainText().strip()
        self.item_data_copy["hashtags"] = self.hashtags_edit.text().strip()
        # clip_path и source_clip_info не меняются в этом диалоге, остаются из item_data_copy
        return self.item_data_copy