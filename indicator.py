import sys
import os
import yaml
import subprocess
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

def resource_path(relative_path):
    """Получить абсолютный путь к ресурсу, работает для PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # --add-data "notavail.png:notavail.png" кладёт ресурс в что-то/notavail.png/notavail.png
        # Поэтому имя ресурса дублируем:
        return os.path.join(sys._MEIPASS, relative_path, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DEFAULT_ICON = resource_path('notavail.png')

STATUS_TRANSLATION = {
    'busy': {'status': 'Синхронизация', 'icon': resource_path('sync.png')},
    'idle': {'status': 'Синхронизировано', 'icon': resource_path('ok.png')},
    'index': {'status': 'Индексация', 'icon': resource_path('error.png')},
}

class SettingsWindow(QMainWindow):
    def __init__(self, config_data=None):
        super().__init__()
        self.setWindowTitle("Настройки")
        self.setGeometry(200, 200, 400, 200)

        # Устанавливаем атрибут, чтобы окно не закрывало приложение
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # Виджеты
        self.yandex_disk_path_label = QLabel("Путь к бинарному файлу YandexDisk:", self)
        self.yandex_disk_path_input = QLineEdit(self)
        self.yandex_disk_path_input.setText(config_data.get('yandex_disk_path', "/usr/bin/yandex-disk status"))

        self.data_directory_label = QLabel("Путь к каталогу с данными:", self)
        self.data_directory_input = QLineEdit(self)
        self.data_directory_input.setText(config_data.get('data_directory', os.path.expanduser("~") + "~/Yandex-disk"))

        self.polling_frequency_label = QLabel("Частота опроса демона (секунд):", self)
        self.polling_frequency_input = QLineEdit(self)
        self.polling_frequency_input.setText(str(config_data.get('polling_frequency', 30)))

        self.save_button = QPushButton("Сохранить", self)
        self.save_button.clicked.connect(self.save_settings)

        # Размещение виджетов
        layout = QVBoxLayout()
        layout.addWidget(self.yandex_disk_path_label)
        layout.addWidget(self.yandex_disk_path_input)
        layout.addWidget(self.data_directory_label)
        layout.addWidget(self.data_directory_input)
        layout.addWidget(self.polling_frequency_label)
        layout.addWidget(self.polling_frequency_input)
        layout.addWidget(self.save_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def save_settings(self):
        # Считывание значений
        yandex_disk_path = self.yandex_disk_path_input.text()
        data_directory = self.data_directory_input.text()
        polling_frequency = int(self.polling_frequency_input.text())

        # Сохранение настроек в файл .yaml
        config_path = os.path.expanduser("~/.config/yadiskindicator.yaml")
        config_data = {
            'yandex_disk_path': yandex_disk_path,
            'data_directory': data_directory,
            'polling_frequency': polling_frequency
        }

        with open(config_path, 'w') as config_file:
            yaml.dump(config_data, config_file)

        print(f"Настройки сохранены в {config_path}")
        self.close()  # Закрытие только окна настроек

def load_config():
    config_path = os.path.expanduser("~/.config/yadiskindicator.yaml")
    
    # Если файл существует, загружаем его
    if os.path.exists(config_path):
        with open(config_path, 'r') as config_file:
            config_data = yaml.safe_load(config_file) or {}
    else:
        config_data = {}

    # Устанавливаем значения по умолчанию для отсутствующих настроек
    return {
        'yandex_disk_path': config_data.get('yandex_disk_path', "/usr/bin/yandex-disk"),
        'data_directory': config_data.get('data_directory', os.path.expanduser("~") + "/Yandex-disk"),
        'polling_frequency': config_data.get('polling_frequency', 30)  # Частота опроса по умолчанию 5 секунд
    }

def get_sync_status(yandex_disk_path):
    try:
        # Выполняем команду yandex-disk status и захватываем вывод
        result = subprocess.run([yandex_disk_path, "status"], capture_output=True, text=True, check=True)
        output = result.stdout

        sync_progress = ""
        # Ищем строку с состоянием демона
        for line in output.splitlines():
            if "Sync progress:" in line:
                sync_progress = line.split(':')[-1].strip()
            if "Synchronization core status" in line:
                raw_status = line.split(':')[-1].strip()
                return (raw_status, sync_progress)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")

    return ("Не удалось получить статус", "")

def get_space_info(yandex_disk_path):
    total = "0"
    used = "0"
    try:
        # Выполняем команду yandex-disk status и захватываем вывод
        result = subprocess.run([yandex_disk_path, "status"], capture_output=True, text=True, check=True)
        output = result.stdout

        for line in output.splitlines():
            if "Total" in line:
                total = line.split(':')[-1].strip()
            if "Used" in line:
                used = line.split(':')[-1].strip()
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")

    return f"{used}/{total}"

def main():
    def update_status():
        new_status, progress = get_sync_status(config_data['yandex_disk_path'])
        indicator_status = STATUS_TRANSLATION.get(new_status, {}).get('status', new_status)
        indicator_icon = STATUS_TRANSLATION.get(new_status, {}).get('icon', DEFAULT_ICON)
        if progress != "":
            status_action.setText(f"{indicator_status} {progress}")
        else:
            status_action.setText(f"{indicator_status}")
        tray_icon.setIcon(QIcon(indicator_icon))

    def update_space():
        new_space = get_space_info(config_data['yandex_disk_path'])
        space_action.setText(f"Занято/Доступно: {new_space}")

    app = QApplication(sys.argv)

    # Загружаем конфигурацию
    config_data = load_config()

    tray_icon = QSystemTrayIcon()
    tray_icon.setIcon(QIcon(DEFAULT_ICON))

    menu = QMenu()

    status_action = QAction("Получаем статус") 
    status_action.setEnabled(False) 
    menu.addAction(status_action)

    space_action = QAction("Занято/Доступно:") 
    space_action.setEnabled(False) 
    menu.addAction(space_action)

    action_settings = QAction("Настройки")
    settings_window = SettingsWindow(config_data)
    action_settings.triggered.connect(settings_window.show)
    menu.addAction(action_settings)

    action_quit = QAction("Выход")
    action_quit.triggered.connect(QApplication.instance().quit)
    menu.addAction(action_quit)

    # Запуск цикла обновления статуса синхронизации
    statustimer = QTimer()
    # timerCallback = functools.partial(lambda: update_status())
    statustimer.timeout.connect(update_status)
    statustimer.start(config_data['polling_frequency'] * 1000)  # Частота опроса в миллисекундах

    spacetimer = QTimer()
    # timerCallback = functools.partial(lambda: update_status())
    spacetimer.timeout.connect(update_space)
    spacetimer.start(10 * 1000)  # Частота опроса в миллисекундах

    # QTimer.singleShot(3000, lambda: update_status("Обновляется..."))

    tray_icon.setContextMenu(menu)
    tray_icon.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
