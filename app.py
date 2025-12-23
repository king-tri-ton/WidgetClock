import sys
import os
import subprocess
from datetime import datetime
from PySide6.QtWidgets import QApplication, QWidget, QMenu
from PySide6.QtGui import QFont, QAction, QColor, QPainter, QBrush, QFontMetrics, QPen
from PySide6.QtCore import Qt, QTimer, QPoint

# ==========================================================
# ПОЛНЫЙ КОНФИГ - НАСТРОЙ ПОД СЕБЯ
# ==========================================================
USER_CONFIG = {
    "W": 210,            # Ширина окна
    "H": 90,            # Высота окна
    "FONT_SIZE": 48,     # Размер шрифта
    "PADDING_TOP": 0,   # Смещение текста по вертикали (отрицательное - вверх)
    "RADIUS": 15,        # Скругление углов
    "FONT_NAME": "Segoe UI Variable Display", 
}

APP_NAME_LINK = "MyUltimateClock.lnk"
# ==========================================================

class FullFeaturedClock(QWidget):
    def __init__(self):
        super().__init__()

        # Системные настройки окна
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Словарь тем: (Фон, Текст, Рамка)
        self.themes = {
            "Titan (Dark)": (QColor(40, 44, 52, 240), QColor(220, 223, 230), QColor(0, 0, 0, 0)),
            "Paper (Light)": (QColor(245, 245, 245, 250), QColor(30, 30, 30), QColor(200, 200, 200)),
            "Cyberpunk": (QColor(10, 10, 20, 245), QColor(0, 255, 255), QColor(255, 0, 128, 200)),
            "Glass Effect": (QColor(0, 0, 0, 100), QColor(255, 255, 255), QColor(255, 255, 255, 50))
        }

        # Установка начальной темы
        self.bg_color, self.text_color, self.border_color = self.themes["Titan (Dark)"]
        
        self.display_time = ""
        self.setFixedSize(USER_CONFIG["W"], USER_CONFIG["H"])

        # Таймер обновления (раз в секунду)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

        self._drag_pos = None

    def update_time(self):
        new_time = datetime.now().strftime("%H:%M")
        if self.display_time != new_time:
            self.display_time = new_time
            self.update() # Вызывает перерисовку (paintEvent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Фон и рамка
        painter.setBrush(QBrush(self.bg_color))
        if self.border_color.alpha() > 0:
            pen = QPen(self.border_color)
            pen.setWidth(2)
            painter.setPen(pen)
        else:
            painter.setPen(Qt.NoPen)
        
        painter.drawRoundedRect(self.rect().adjusted(1,1,-1,-1), USER_CONFIG["RADIUS"], USER_CONFIG["RADIUS"])

        # 2. Математически идеальный текст
        painter.setPen(self.text_color)
        font = QFont(USER_CONFIG["FONT_NAME"], USER_CONFIG["FONT_SIZE"], QFont.Bold)
        if not font.exactMatch():
            font = QFont("Segoe UI", USER_CONFIG["FONT_SIZE"], QFont.Bold)
        painter.setFont(font)

        metrics = QFontMetrics(font)
        
        # Получаем реальную ширину текста
        text_w = metrics.horizontalAdvance(self.display_time)
        # Получаем высоту именно ЦИФР (capHeight), игнорируя пустоту снизу
        text_h = metrics.capHeight()

        # Центрируем
        x = (self.width() - text_w) // 2
        # (Высота окна / 2) + (Высота цифр / 2) дает визуальный центр
        y = (self.height() + text_h) // 2 + USER_CONFIG["PADDING_TOP"]

        painter.drawText(x, y, self.display_time)

    # --- ЛОГИКА МЫШИ ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # --- КОНТЕКСТНОЕ МЕНЮ ---
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # Стиль меню
        menu.setStyleSheet("""
            QMenu { background-color: #2b2b2b; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #4a90e2; }
        """)

        # Меню выбора тем
        theme_menu = menu.addMenu("🎨 Выбрать стиль")
        for name in self.themes:
            action = QAction(name, self)
            # Передача данных через lambda
            action.triggered.connect(lambda checked=False, n=name: self.set_theme(n))
            theme_menu.addAction(action)

        menu.addSeparator()
        
        # Секция автозагрузки
        auto_add = menu.addAction("🚀 В автозагрузку")
        auto_add.triggered.connect(self.create_shortcut)
        
        auto_rm = menu.addAction("🗑 Удалить автозагрузку")
        auto_rm.triggered.connect(self.remove_shortcut)
        
        menu.addSeparator()
        
        exit_act = menu.addAction("❌ Закрыть")
        exit_act.triggered.connect(QApplication.quit)
        
        menu.exec(event.globalPos())

    def set_theme(self, name):
        self.bg_color, self.text_color, self.border_color = self.themes[name]
        self.update()

    # --- ФУНКЦИИ АВТОЗАГРУЗКИ ---
    def get_target_path(self):
        # Работает и для .py и для собранного .exe
        return sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])

    def create_shortcut(self):
        target = self.get_target_path()
        s_folder = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        path_link = os.path.join(s_folder, APP_NAME_LINK)
        
        # Создание ярлыка через временный VBS-скрипт (самый надежный способ для Win без доп. библиотек)
        vbs = (f'Set oWS = WScript.CreateObject("WScript.Shell")\n'
               f'sLinkFile = "{path_link}"\n'
               f'Set oLink = oWS.CreateShortcut(sLinkFile)\n'
               f'oLink.TargetPath = "{target}"\n'
               f'oLink.WorkingDirectory = "{os.path.dirname(target)}"\n'
               f'oLink.Save')
        try:
            vbs_p = os.path.join(os.environ["TEMP"], "create_lnk.vbs")
            with open(vbs_p, "w") as f: f.write(vbs)
            subprocess.call(["cscript", "//Nologo", vbs_p])
            os.remove(vbs_p)
        except Exception as e:
            print(f"Ошибка автозагрузки: {e}")

    def remove_shortcut(self):
        s_folder = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        path_link = os.path.join(s_folder, APP_NAME_LINK)
        if os.path.exists(path_link):
            os.remove(path_link)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    clock = FullFeaturedClock()
    clock.show()
    sys.exit(app.exec())