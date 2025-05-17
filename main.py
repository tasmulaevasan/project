import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    """
    Главная функция для запуска приложения.
    Инициализирует QApplication и отображает главное окно.
    """
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()