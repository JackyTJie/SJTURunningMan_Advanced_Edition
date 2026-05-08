import sys
import os
import re
import ctypes
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QProgressBar, QFormLayout, QGroupBox, QDateTimeEdit,
    QMessageBox, QScrollArea, QSizePolicy, QCheckBox, QComboBox,
    QSpacerItem, QFileDialog, QDialog, QFrame
)
from PySide6.QtCore import QThread, Signal, QDateTime, Qt, QUrl, QEvent
from PySide6.QtGui import QTextCursor, QFont, QColor, QTextCharFormat, QPalette, QBrush, QIcon, QDesktopServices

from src.main import run_sports_upload
import src.login as login
from utils.auxiliary_util import SportsUploaderError, get_base_path
import src.config as config


from src.info_dialog import HelpWidget

RESOURCES_SUB_DIR = "assets"

GITHUB_REPO_URL = "https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition"
APP_USER_MODEL_ID = "CEQ151.SJTURunningMan.Windows"


def get_resource_path(relative_path):
    """Return a bundled resource path both in source and PyInstaller builds."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(get_base_path(), relative_path)


RESOURCES_FULL_PATH = get_resource_path(RESOURCES_SUB_DIR)
APP_ICON_PATH = get_resource_path(os.path.join(RESOURCES_SUB_DIR, "SJTURM.ico"))
if not os.path.exists(APP_ICON_PATH):
    APP_ICON_PATH = get_resource_path(os.path.join(RESOURCES_SUB_DIR, "SJTURM.png"))


def set_windows_app_id():
    """Make Windows taskbar grouping prefer this app's icon."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        return

class WorkerThread(QThread):
    """
    工作线程，用于在后台执行跑步数据上传任务，避免UI冻结。
    """
    progress_update = Signal(int, int, str)
    log_output = Signal(str, str)
    finished = Signal(bool, str)
    route_too_long = Signal(str, str)  # Signal to emit when route is too long

    def __init__(self, config_data):
        super().__init__()
        self.config_data = config_data
        self._continue_after_route_check = True  # Default to continue execution

    def run(self):
        success = False
        message = "任务已完成。"
        try:
            success, message = run_sports_upload(
                self.config_data,
                progress_callback=self.progress_callback,
                log_cb=self.log_callback,
                stop_check_cb=self.isInterruptionRequested
            )
        except SportsUploaderError as e:
            self.log_output.emit(f"任务中断: {e}", "error")
            message = str(e)
            success = False
        except Exception as e:
            self.log_output.emit(f"发生未预期的错误: {e}", "error")
            message = f"未预期的错误: {e}"
            success = False
        finally:
            if self.isInterruptionRequested() and not success:
                 self.finished.emit(False, "任务已手动终止。")
            else:
                 self.finished.emit(success, message)

    def progress_callback(self, current, total, message):
        self.progress_update.emit(current, total, message)

    def log_callback(self, message, level):
        # Check if this is a special route too long message
        if message.startswith("SPECIAL_ROUTE_TOO_LONG:"):
            # Extract distances from the message
            parts = message.split(":")
            if len(parts) >= 3:
                detailed_distance = float(parts[1])
                target_distance = float(parts[2])
                # Set the flag to pause execution
                self._continue_after_route_check = False
                # Emit signal to UI to show route too long dialog
                self.route_too_long.emit(str(detailed_distance), str(target_distance))
                # Wait until the UI sets a flag to continue
                while not self._continue_after_route_check:
                    # Small delay to prevent busy waiting
                    self.msleep(100)
                return  # Don't emit the log message when it was a special route message
        self.log_output.emit(message, level)


class SportsUploaderUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SJTU 校园轻松跑 - Version " + config.global_version)
        self.setWindowIcon(QIcon(APP_ICON_PATH))

        # 后台线程引用（私有）
        self._thread = None
        # 关于窗口引用，防止被垃圾回收
        self._help_window = None

        self.config = {}

        self.setup_ui_style()
        self.init_ui()

        self.setGeometry(140, 60, 1180, 780)
        self.setMinimumSize(980, 680)

        # 根据当前窗口宽度调整内容区域宽度
        self.adjust_content_width(self.width())
        # 启动时居中主窗口
        try:
            self.center_window()
        except Exception:
            pass

    def setup_ui_style(self):
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(246, 248, 251))
        palette.setColor(QPalette.WindowText, QColor(51, 51, 51))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(51, 51, 51))
        palette.setColor(QPalette.Text, QColor(51, 51, 51))
        palette.setColor(QPalette.Button, QColor(255, 255, 255))
        palette.setColor(QPalette.ButtonText, QColor(51, 51, 51))
        palette.setColor(QPalette.BrightText, QColor("red"))
        palette.setColor(QPalette.Link, QColor(74, 144, 226))
        palette.setColor(QPalette.Highlight, QColor(74, 144, 226))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)

        self.setStyleSheet("""
            /* 基础设置 */
            QWidget {
                background-color: rgb(246, 248, 251);
                color: rgb(34, 45, 57);
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }

            #appHeader {
                background-color: rgb(255, 255, 255);
                border: 1px solid rgb(225, 231, 238);
                border-radius: 8px;
            }

            #appTitle {
                color: rgb(26, 36, 48);
                font-size: 15pt;
                font-weight: 700;
                background-color: transparent;
            }

            #appSubtitle {
                color: rgb(100, 116, 139);
                font-size: 9pt;
                background-color: transparent;
            }

            #sectionHint {
                color: rgb(100, 116, 139);
                font-size: 8pt;
                background-color: transparent;
            }
            
            /* GroupBox 样式 */
            QGroupBox {
                font-size: 10pt;
                font-weight: bold;
                margin-top: 10px;
                border: 1px solid rgb(225, 231, 238);
                border-radius: 8px;
                padding: 15px;
                color: rgb(42, 111, 151);
                background-color: rgb(255, 255, 255);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px 0 5px;
                color: rgb(42, 111, 151);
                background-color: rgb(246, 248, 251);
            }
            
            /* 确保所有标签和输入框可见 */
            QLabel {
                color: rgb(34, 45, 57);
                background-color: transparent;
                font-size: 9pt;
            }
            
            QLineEdit, QComboBox, QDateTimeEdit {
                background-color: rgb(255, 255, 255);
                border: 1px solid rgb(203, 213, 225);
                border-radius: 6px;
                padding: 8px;
                color: rgb(30, 41, 59);
                font-size: 9pt;
                min-height: 20px;
            }
            
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid rgb(42, 111, 151);
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: rgb(203, 213, 225);
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QPushButton {
                background-color: rgb(255, 255, 255);
                color: rgb(30, 41, 59);
                border: 1px solid rgb(203, 213, 225);
                border-radius: 6px;
                padding: 8px 16px;
                min-height: 24px;
                max-height: 36px;
            }
            QPushButton:hover {
                border: 1px solid rgb(42, 111, 151);
                background-color: rgb(248, 251, 253);
            }
            QPushButton:pressed {
                background-color: rgb(238, 243, 247);
            }
            QPushButton:disabled {
                background-color: rgb(248, 250, 252);
                color: rgb(148, 163, 184);
                border: 1px solid rgb(226, 232, 240);
            }
            QProgressBar {
                border: 1px solid rgb(225, 231, 238);
                border-radius: 6px;
                text-align: center;
                background-color: rgb(255, 255, 255);
                color: rgb(30, 41, 59);
                max-height: 20px;
            }
            QProgressBar::chunk {
                background-color: rgb(42, 111, 151);
                border-radius: 6px;
            }
            QTextEdit {
                background-color: rgb(250, 252, 254);
                border: 1px solid rgb(225, 231, 238);
                border-radius: 6px;
                padding: 8px;
                color: rgb(30, 41, 59);
            }
            QScrollArea {
                border: none;
            }
            QCheckBox {
                spacing: 5px;
                color: rgb(51, 51, 51);
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid rgb(204, 204, 204);
                background-color: rgb(255, 255, 255);
            }
            QCheckBox::indicator:checked {
                background-color: rgb(74, 144, 226);
                border: 1px solid rgb(74, 144, 226);
            }
            QCheckBox::indicator:disabled {
                border: 1px solid rgb(230, 230, 230);
                background-color: rgb(255, 255, 255);
            }
            QFormLayout QLabel {
                padding-top: 8px;
                padding-bottom: 8px;
                color: rgb(71, 85, 105);
            }
            #startButton {
                background-color: rgb(36, 126, 90);
                color: white;
                border: 1px solid rgb(36, 126, 90);
            }
            #startButton:hover {
                background-color: rgb(31, 111, 79);
                border: 1px solid rgb(31, 111, 79);
            }
            #startButton:pressed {
                background-color: rgb(25, 92, 66);
            }
            #stopButton {
                background-color: rgb(197, 48, 69);
                color: white;
                border: 1px solid rgb(197, 48, 69);
            }
            #stopButton:hover {
                background-color: rgb(167, 40, 58);
                border: 1px solid rgb(167, 40, 58);
            }
            #stopButton:pressed {
                background-color: rgb(137, 32, 48);
            }
            #githubButton {
                background-color: rgb(15, 23, 42);
                color: rgb(255, 255, 255);
                border: 1px solid rgb(15, 23, 42);
                font-weight: 600;
            }
            #githubButton:hover {
                background-color: rgb(30, 41, 59);
                border: 1px solid rgb(30, 41, 59);
            }
            #githubButton:pressed {
                background-color: rgb(2, 6, 23);
            }
            QLabel#getCookieLink {
                color: rgb(42, 111, 151);
                text-decoration: underline;
                padding: 0;
            }
            QLabel#getCookieLink:hover {
                color: rgb(34, 91, 125);
            }
        """)

    def create_hint_label(self, text):
        label = QLabel(text)
        label.setObjectName("sectionHint")
        label.setWordWrap(True)
        return label

    def open_github_repo(self):
        QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL))

    def init_ui(self):
        top_h_layout = QHBoxLayout()
        top_h_layout.setContentsMargins(20, 20, 20, 20)
        top_h_layout.setSpacing(0)

        self.center_widget = QWidget()
        main_layout = QVBoxLayout(self.center_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_content = QWidget()
        scroll_layout = QVBoxLayout(self.scroll_content)
        # Add margins to make content look better in the larger window
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        # Reduce spacing to fit more content
        scroll_layout.setSpacing(15)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_content)

        main_layout.addWidget(self.scroll_area)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(15)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(15)

        header = QFrame()
        header.setObjectName("appHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(12)

        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(4)

        title_label = QLabel("SJTU 校园轻松跑")
        title_label.setObjectName("appTitle")
        subtitle_label = QLabel(f"Version {config.global_version} · 轻量桌面版 · 生成记录前请确认日期、时间和路线")
        subtitle_label.setObjectName("appSubtitle")
        subtitle_label.setWordWrap(True)
        title_block.addWidget(title_label)
        title_block.addWidget(subtitle_label)
        header_layout.addLayout(title_block, 1)

        self.github_button = QPushButton("GitHub")
        self.github_button.setObjectName("githubButton")
        github_icon_path = os.path.join(RESOURCES_FULL_PATH, "github-mark.svg")
        if os.path.exists(github_icon_path):
            self.github_button.setIcon(QIcon(github_icon_path))
        self.github_button.setToolTip("打开项目 GitHub 仓库")
        self.github_button.clicked.connect(self.open_github_repo)
        header_layout.addWidget(self.github_button)
        left_column.addWidget(header)

        user_group = QGroupBox("用户配置")
        user_form_layout = QFormLayout()
        user_form_layout.setVerticalSpacing(15)
        user_form_layout.setContentsMargins(15, 15, 15, 15)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Jaccount用户名")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)

        user_form_layout.addRow("用户名:", self.username_input)
        user_form_layout.addRow("密码:", self.password_input)
        user_group.setLayout(user_form_layout)
        left_column.addWidget(user_group)

        status_group = QGroupBox("程序状态")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(15, 15, 15, 15)
        status_layout.setSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("状态: 待命")
        status_layout.addWidget(self.status_label)

        self.log_output_area = QTextEdit()
        self.log_output_area.setReadOnly(True)
        self.log_output_area.setFont(QFont("Monospace", 9))
        self.log_output_area.setMinimumHeight(260)
        self.log_output_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        status_layout.addWidget(self.log_output_area, 1)

        status_group.setLayout(status_layout)
        left_column.addWidget(status_group, 1)

        # 添加运行次数和时间选择组件
        run_settings_group = QGroupBox("上传设置")
        run_settings_layout = QVBoxLayout()
        run_settings_layout.setContentsMargins(15, 15, 15, 15)
        run_settings_layout.setSpacing(20)

        # 跑步次数
        days_layout = QVBoxLayout()
        days_label_layout = QHBoxLayout()
        days_label_layout.addWidget(QLabel("跑步次数:"))
        days_label_layout.addStretch()
        days_layout.addLayout(days_label_layout)

        days_input_layout = QHBoxLayout()
        self.run_days_input = QLineEdit()
        self.run_days_input.setText("1")
        self.run_days_input.setPlaceholderText("正整数，最多 30")
        self.run_days_input.setMaxLength(2)
        self.run_days_input.setToolTip("要生成的跑步记录数量，最多 30 条。")
        days_input_layout.addWidget(self.run_days_input)
        days_layout.addLayout(days_input_layout)
        days_layout.addWidget(self.create_hint_label("生成多少条跑步记录。最多 30 条。"))

        run_settings_layout.addLayout(days_layout)

        # 跑步开始时间
        time_layout = QVBoxLayout()
        time_label_layout = QHBoxLayout()
        time_label_layout.addWidget(QLabel("跑步时间:"))
        time_label_layout.addStretch()
        time_layout.addLayout(time_label_layout)

        time_input_layout = QHBoxLayout()
        self.run_time_input = QLineEdit()
        self.run_time_input.setText("08:00:00")
        self.run_time_input.setMaxLength(8)
        self.run_time_input.setPlaceholderText("HH:MM:SS，例如 08:00:00")
        self.run_time_input.setToolTip("记录的基础开始时间；实际生成时会自动加入随机偏移。")
        time_input_layout.addWidget(self.run_time_input)

        time_layout.addLayout(time_input_layout)
        time_layout.addWidget(self.create_hint_label("格式：HH:MM:SS，例如 08:00:00。实际记录会自动前后随机偏移几分钟。"))

        run_settings_layout.addLayout(time_layout)

        # 结束日期
        date_layout = QVBoxLayout()
        date_label_layout = QHBoxLayout()
        date_label_layout.addWidget(QLabel("结束日期:"))
        date_label_layout.addStretch()
        date_layout.addLayout(date_label_layout)

        date_input_layout = QHBoxLayout()
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.date_input = QLineEdit()
        self.date_input.setText(yesterday)
        self.date_input.setMaxLength(10)
        self.date_input.setPlaceholderText("YYYY-MM-DD，例如 2026-05-07")
        self.date_input.setToolTip("最新一条记录的日期；程序会从这一天向前生成记录。")
        date_input_layout.addWidget(self.date_input)

        date_layout.addLayout(date_input_layout)
        date_layout.addWidget(self.create_hint_label("格式：YYYY-MM-DD，例如 2026-05-07。会以这天作为最新一条记录，向前生成。"))

        run_settings_layout.addLayout(date_layout)

        # 跑步距离
        distance_layout = QVBoxLayout()
        distance_label_layout = QHBoxLayout()
        distance_label_layout.addWidget(QLabel("跑步距离:"))
        distance_label_layout.addStretch()
        distance_layout.addLayout(distance_label_layout)

        distance_input_layout = QHBoxLayout()
        self.run_distance_input = QLineEdit()
        self.run_distance_input.setText("4")
        self.run_distance_input.setPlaceholderText("1-4，单位 km")
        self.run_distance_input.setMaxLength(3)
        self.run_distance_input.setToolTip("每条记录的目标跑步距离，最多 4km。")
        distance_input_layout.addWidget(self.run_distance_input)
        distance_layout.addLayout(distance_input_layout)
        distance_layout.addWidget(self.create_hint_label("单位：km。最多 4km，例如 3 或 4。"))

        run_settings_layout.addLayout(distance_layout)

        run_settings_group.setLayout(run_settings_layout)
        right_column.addWidget(run_settings_group)

        action_button_layout = QVBoxLayout()
        action_button_layout.setSpacing(10)
        primary_button_layout = QHBoxLayout()
        primary_button_layout.setSpacing(12)
        secondary_button_layout = QHBoxLayout()
        secondary_button_layout.setSpacing(12)

        self.start_button = QPushButton("开始生成并上传")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_upload)
        primary_button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止任务")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_upload)
        primary_button_layout.addWidget(self.stop_button)

        self.route_button = QPushButton("设计/更新路线")
        self.route_button.setToolTip("未设置自定义路线时，将使用默认路线。")
        self.route_button.clicked.connect(self.open_route_generator)
        secondary_button_layout.addWidget(self.route_button)

        self.info_button = QPushButton("说明")
        self.info_button.clicked.connect(self.show_info_dialog)
        secondary_button_layout.addWidget(self.info_button)

        action_button_layout.addLayout(primary_button_layout)
        action_button_layout.addLayout(secondary_button_layout)

        right_column.addLayout(action_button_layout)
        right_column.addWidget(self.create_hint_label("未设置自定义路线时会使用默认路线；需要更换路线时点击“设计/更新路线”。"))
        right_column.addStretch(1)

        content_layout.addLayout(left_column, 5)
        content_layout.addLayout(right_column, 4)
        scroll_layout.addLayout(content_layout)

        top_h_layout.addWidget(self.center_widget)

        self.setLayout(top_h_layout)

    def resizeEvent(self, event):
        """
        槽函数，用于处理窗口大小调整事件。
        根据窗口宽度调整内部内容区域的最大宽度。
        """
        super().resizeEvent(event)
        self.adjust_content_width(event.size().width())

    def adjust_content_width(self, window_width):
        """
        根据给定的窗口宽度，计算并设置 center_widget 的固定宽度。
        """
        # 横向布局需要更宽的内容区，同时保留少量边距。
        available_width = max(0, window_width - 40)
        calculated_width = int(min(available_width * 0.98, 1280))
        calculated_width = max(940, calculated_width)
        self.center_widget.setFixedWidth(calculated_width)

    def center_window(self):
        """将主窗口居中到主显示器的可用区域中心。"""
        try:
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            available = screen.availableGeometry()

            fg = self.frameGeometry()
            fg.moveCenter(available.center())
            self.move(fg.topLeft())
        except Exception:
            return

    def get_settings_from_ui(self):
        """从UI获取当前配置并返回字典"""
        try:
            username = self.username_input.text().strip()
            password = self.password_input.text()

            # 获取跑步次数、跑步时间和距离
            run_days_text = self.run_days_input.text().strip()
            if not re.fullmatch(r"\d+", run_days_text):
                raise ValueError("跑步次数应为正整数，例如 5")
            run_times = int(run_days_text)
            if not (1 <= run_times <= 30):
                raise ValueError("跑步次数应在 1-30 之间")

            run_time_text = self.run_time_input.text().strip()
            if not re.fullmatch(r"\d{2}:\d{2}:\d{2}", run_time_text):
                raise ValueError("时间格式应为 HH:MM:SS，例如 08:00:00")
            run_hour, run_minute, run_second = [int(part) for part in run_time_text.split(":")]
            if not (0 <= run_hour <= 23 and 0 <= run_minute <= 59 and 0 <= run_second <= 59):
                raise ValueError("时间范围无效，小时应为 00-23，分钟和秒应为 00-59")

            run_distance_text = self.run_distance_input.text().strip()
            try:
                run_distance_km = float(run_distance_text)
            except ValueError:
                raise ValueError("距离应为数字，单位 km，例如 3 或 4")
            if not (0 < run_distance_km <= 4):
                raise ValueError("距离应大于 0 且不超过 4km")
            if run_distance_km.is_integer():
                run_distance_km = int(run_distance_km)

            current_config = {
                "USER_ID": username,
                "PASSWORD": password,
                "RUN_TIMES": run_times,  # 添加运行次数配置
                "RUN_HOUR": run_hour,    # 添加运行小时配置
                "RUN_MINUTE": run_minute,    # 添加运行分钟配置
                "RUN_SECOND": run_second,    # 添加运行秒钟配置
                "RUN_DISTANCE_KM": run_distance_km,  # 添加运行距离配置
                "START_LATITUDE": float(self.config.get("START_LATITUDE", 31.031599)),
                "START_LONGITUDE": float(self.config.get("START_LONGITUDE", 121.442938)),
                "END_LATITUDE": float(self.config.get("END_LATITUDE", 31.0264)),
                "END_LONGITUDE": float(self.config.get("END_LONGITUDE", 121.4551)),
                "RUNNING_SPEED_MPS": round(1000.0 / (4.0 * 60), 3),  # 4分配对应的速度，约4.17 m/s
                "INTERVAL_SECONDS": int(self.config.get("INTERVAL_SECONDS", 3)),
                "HOST": "pe.sjtu.edu.cn",
                "UID_URL": "https://pe.sjtu.edu.cn/sports/my/uid",
                "MY_DATA_URL": "https://pe.sjtu.edu.cn/sports/my/data",
                "POINT_RULE_URL": "https://pe.sjtu.edu.cn/api/running/point-rule",  # Fixed URL
                "UPLOAD_URL": "https://pe.sjtu.edu.cn/api/running/result/upload"
            }

            # Add start date from direct input (the input is always filled with a default value)
            start_date_text = self.date_input.text().strip()
            if start_date_text:
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(start_date_text, '%Y-%m-%d')
                    current_config["START_DATE"] = parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    raise ValueError("日期格式应为 YYYY-MM-DD，例如 2026-05-07")

            # START_TIME_EPOCH_MS 由后端生成，不从 UI 获取

            if not current_config["USER_ID"] or not current_config["PASSWORD"]:
                raise ValueError("用户名和密码不能为空。")

            return current_config

        except ValueError as e:
            raise ValueError(f"输入错误: {e}")
        except Exception as e:
            raise Exception(f"获取配置时发生未知错误: {e}")

    def _2fa_select_method(self):
        """二次验证：让用户选择验证方式"""
        dialog = QDialog(self)
        dialog.setWindowTitle("异地登录验证")
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        dialog.setFixedSize(360, 180)
        dialog.setWindowModality(Qt.WindowModal)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        label = QLabel("请选择验证方式:")
        label.setStyleSheet("font-size: 11pt; color: #333;")
        layout.addWidget(label)

        combo = QComboBox()
        combo.addItems(["交我办消息", "邮箱", "短信"])
        combo.setStyleSheet("padding: 6px; font-size: 10pt;")
        layout.addWidget(combo)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        method_map = {"交我办消息": "app", "邮箱": "email", "短信": "sms"}
        if dialog.exec() == QDialog.Accepted:
            return method_map.get(combo.currentText(), "app")
        return None

    def _2fa_get_code(self):
        """二次验证：获取用户输入的验证码"""
        dialog = QDialog(self)
        dialog.setWindowTitle("输入验证码")
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        dialog.setFixedSize(360, 180)
        dialog.setWindowModality(Qt.WindowModal)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        label = QLabel("请输入6位验证码（输入 r 可重新发送）:")
        label.setStyleSheet("font-size: 11pt; color: #333;")
        layout.addWidget(label)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText("验证码")
        line_edit.setStyleSheet("padding: 6px; font-size: 10pt;")
        layout.addWidget(line_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            code = line_edit.text().strip()
            return code if code else None
        return None

    def _2fa_show_message(self, msg):
        """二次验证：显示提示信息"""
        self.log_output_text(msg, "info")

    def start_upload(self):
        self.log_output_area.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("状态: 准备中...")
        self.log_output_text("准备开始上传...", "info")

        try:
            current_config_to_send = self.get_settings_from_ui()
        except (ValueError, Exception) as e:
            self.log_output_text(f"配置错误: {e}", "error")
            self.status_label.setText("状态: 错误")
            return

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.info_button.setEnabled(False)

        # 调用 login.py 获取 session，使用 UI 中的用户名/密码
        try:
            username = current_config_to_send.get("USER_ID")
            password = current_config_to_send.get("PASSWORD")

            two_fa_cb = {
                'select_method': self._2fa_select_method,
                'get_code': self._2fa_get_code,
                'show_message': self._2fa_show_message,
            }

            session = login.login(username, password, two_fa_cb=two_fa_cb)
            current_config_to_send["SESSION"] = session
            current_config_to_send["USER_ID"] = username
        except Exception as e:
            self.log_output_text(f"登录失败: {e}", "error")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            self.info_button.setEnabled(True)
            QMessageBox.critical(self, "登录失败", str(e))
            return

        self.stop_button.setEnabled(True)
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)

        # Check if current route exceeds target distance and ask user what to do
        try:
            from src.data_generator import read_gps_coordinates_from_file, calculate_route_distance
            import os
            
            # Only look in the project root directory for route files
            from utils.auxiliary_util import get_base_path
            # Use the base path which works for both compiled and non-compiled versions
            base_path = get_base_path()
            user_loc_path = os.path.join(base_path, 'user.txt')
            default_loc_path = os.path.join(base_path, 'default.txt')

            if os.path.exists(user_loc_path):
                route_path = user_loc_path
            else:
                route_path = default_loc_path
                # Check if default.txt exists
                if not os.path.exists(route_path):
                    raise Exception(f"用户路线文件不存在: {user_loc_path} 和 {route_path} 都不存在")

            route_coordinates = read_gps_coordinates_from_file(route_path)
            route_distance = calculate_route_distance(route_coordinates)
            target_distance_m = current_config_to_send.get('RUN_DISTANCE_KM', 5) * 1000  # Convert to meters
            
            if route_distance > target_distance_m:
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(self, "路线距离提醒", 
                                           f"当前路线长度为 {route_distance/1000:.2f}km，"
                                           f"超过了您选择的 {current_config_to_send.get('RUN_DISTANCE_KM', 5)}km。\n\n"
                                           f"您希望：\n"
                                           f"  - 选择\"是\"：自动削减路线至目标距离\n"
                                           f"  - 选择\"否\"：按照完整路线进行跑步",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.Yes)
                
                if reply == QMessageBox.StandardButton.Yes:
                    # User wants to truncate to target distance
                    self.log_output_text("用户选择自动削减路线至目标距离", "info")
                else:
                    # User wants to continue with full route
                    self.log_output_text("用户选择按照完整路线进行跑步", "info")
                    # Update the target distance to be the actual route distance
                    # We need to adjust the RUN_DISTANCE_KM to match the route distance
                    current_config_to_send['RUN_DISTANCE_KM'] = round(route_distance / 1000, 2)
                    self.log_output_text(f"已更新跑步距离至 {current_config_to_send['RUN_DISTANCE_KM']}km", "info")
        except Exception as e:
            self.log_output_text(f"检查路线距离时出现错误: {e}", "error")
            # Continue anyway, don't block the upload for this check

        self._thread = WorkerThread(current_config_to_send)
        self._thread.progress_update.connect(self.update_progress)
        self._thread.log_output.connect(self.log_output_text)
        self._thread.route_too_long.connect(self.handle_route_too_long)
        self._thread.finished.connect(self.upload_finished)
        self._thread.start()

    def handle_route_too_long(self, detailed_distance_str, target_distance_str):
        """Handle when the route is too long by showing a dialog to the user."""
        detailed_distance = float(detailed_distance_str)
        target_distance = float(target_distance_str)
        
        # Show a message box to the user
        reply = QMessageBox.question(
            self, 
            "路线距离提醒", 
            f"当前路线长度为 {detailed_distance/1000:.2f}km，"
            f"超过了您选择的 {target_distance/1000:.2f}km。\n\n"
            f"您希望：\n"
            f"  - 选择\"是\"：自动削减路线至目标距离\n"
            f"  - 选择\"否\"：按照完整路线继续跑步\n"
            f"  - 选择\"取消\"：停止当前任务",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # User wants to truncate to target distance - set flag to continue
            if self._thread:
                self._thread._continue_after_route_check = True
                self.log_output_text("用户选择自动削减路线至目标距离", "info")
        elif reply == QMessageBox.StandardButton.No:
            # User wants to continue with full route - set flag to continue
            if self._thread:
                self._thread._continue_after_route_check = True
                self.log_output_text("用户选择按照完整路线进行跑步", "info")
        else:  # Cancel
            # User wants to stop - interrupt the thread
            if self._thread and self._thread.isRunning():
                self._thread.requestInterruption()
                self.log_output_text("用户选择停止任务", "info")
                self.stop_button.setEnabled(False)
                self.status_label.setText("状态: 正在停止...")

    def stop_upload(self):
        """请求工作线程停止。"""
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self.log_output_text("已发送停止请求，请等待任务清理并退出...", "warning")
            self.stop_button.setEnabled(False)
            self.status_label.setText("状态: 正在停止...")
        else:
            self.log_output_text("没有运行中的任务可以停止。", "info")


    def update_progress(self, current, total, message):
        """更新进度条和状态信息"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"状态: {message}")

    def log_output_text(self, message, level="info"):
        """将日志信息添加到文本区域，并根据级别着色"""
        cursor = self.log_output_area.textCursor()
        cursor.movePosition(QTextCursor.End)

        format = QTextCharFormat()
        if level == "error":
            format.setForeground(QColor("#DC3545"))
        elif level == "warning":
            format.setForeground(QColor("#FFA500"))
        elif level == "success":
            format.setForeground(QColor("#4CAF50"))
        else:
            format.setForeground(QColor("#333333"))

        # 如果是进度类短消息（例如: 已完成1/25），尝试替换最后一行以便在同一行更新
        try:
            if re.match(r"^已完成\d+/\d+", message):
                # 选择最后一段文本（最后一个 block）并检查是否包含“已完成”关键词
                doc = self.log_output_area.document()
                last_block = doc.lastBlock()
                if last_block.isValid() and "已完成" in last_block.text():
                    # 选中最后一个 block 并替换
                    cursor.movePosition(QTextCursor.End)
                    cursor.select(QTextCursor.BlockUnderCursor)
                    cursor.removeSelectedText()
                    # 插入新的进度信息（不额外换行），随后插入换行字符
                    cursor.insertText(f"[{level.upper()}] {message}\n", format)
                    self.log_output_area.ensureCursorVisible()
                    return
        except Exception:
            # 如果替换失败，退回到普通追加方式
            pass

        cursor.insertText(f"[{level.upper()}] {message}\n", format)
        self.log_output_area.ensureCursorVisible()

    def upload_finished(self, success, message):
        """上传任务完成后的处理"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.info_button.setEnabled(True)
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)

        self.progress_bar.setValue(100)

        if success:
            self.status_label.setText("状态: 上传成功！")
            self.log_output_text(f"操作完成: {message}", "success")
            QMessageBox.information(self, "上传结果", message)
        else:
            self.status_label.setText("状态: 上传失败！")
            self.log_output_text(f"操作失败: {message}", "error")

        self._thread = None


    def show_info_dialog(self):
        """显示关于对话框（非模态）。

        使用 HelpWidget，作为非模态窗口显示，并保留对实例的引用以防止被垃圾回收。
        当窗口关闭时清理引用。
        """
        try:
            # 如果已有关于窗口实例：
            # - 若窗口仍可见，则激活并返回；
            # - 若已被隐藏/关闭但引用未清理，则清理引用并继续创建新的实例
            existing = getattr(self, "_help_window", None)
            if existing is not None:
                try:
                    if existing.isVisible():
                        try:
                            existing.activateWindow()
                            existing.raise_()
                        except Exception:
                            pass
                        return
                    else:
                        # 已存在但不可见，尝试移除事件过滤并清理引用以便重新创建
                        try:
                            existing.removeEventFilter(self)
                        except Exception:
                            pass
                        self._help_window = None
                except Exception:
                    self._help_window = None

            # 创建 HelpWidget 实例并以非模态方式显示
            self._help_window = HelpWidget()
            self._help_window.setWindowModality(Qt.WindowModality.NonModal)
            try:
                self._help_window.installEventFilter(self)
            except Exception:
                pass

            def _on_help_destroyed():
                try:
                    if getattr(self, "_help_window", None) is not None:
                        self._help_window = None
                except Exception:
                    self._help_window = None

            try:
                self._help_window.destroyed.connect(_on_help_destroyed)
            except Exception:
                pass

            # 显示窗口（非模态）
            self._help_window.show()

        except Exception as e:
            # 记录异常并弹出对话框，不影响后台线程
            self.log_output_text(f"无法显示关于窗口: {e}", "error")
            QMessageBox.warning(self, "显示失败", f"无法显示关于窗口: {e}")

    def open_route_generator(self):
        """打开路线规划器"""
        try:
            # 将导入移到方法开头，避免作用域问题
            from src.data_generator import generate_baidu_map_html
            import os
            import webbrowser

            # Inform user about the route planning process
            reply = QMessageBox.question(self, "路线规划", 
                                    "此功能将启动路线规划器，您可以：\n\n"
                                    "1. 在浏览器中打开百度地图\n"
                                    "2. 点击地图采集坐标点形成路线\n"
                                    "3. 点击\"保存路线\"按钮下载user.txt文件\n"
                                    "4. 将user.txt文件保存到项目根目录\n\n"
                                    "注意：user.txt将成为新的默认路线文件\n"
                                    "是否现在开始？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.Yes)

            if reply == QMessageBox.StandardButton.Yes:
                # Generate the route planner HTML with the provided API key
                try:
                    map_path = generate_baidu_map_html()
                    webbrowser.open(f'file://{os.path.abspath(map_path)}')
                    
                    QMessageBox.information(self, "路线规划器", 
                                        "路线规划器已在浏览器中打开！\n\n"
                                        "请在地图上点击选择路径坐标点，\n"
                                        "点击\"保存路线\"按钮将下载user.txt文件，\n"
                                        "请将user.txt保存到项目根目录以替换默认路线。")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"生成路线规划器失败：\n{str(e)}")
            else:
                # Check if user.txt exists
                from utils.auxiliary_util import get_base_path
                base_path = get_base_path()
                user_txt_path = os.path.join(base_path, 'user.txt')
                default_txt_path = os.path.join(base_path, 'default.txt') 
                
                if os.path.exists(user_txt_path):
                    QMessageBox.information(self, "当前路线", 
                                        "将使用当前路线文件：user.txt\n\n"
                                        "如需修改路线，请选择\"设计/更新路线\"按钮并创建新路线。")
                else:
                    QMessageBox.information(self, "默认路线", 
                                        "将使用默认路线文件：default.txt\n\n"
                                        "如需修改路线，请选择\"设计/更新路线\"按钮并创建自定义路线。")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开路线规划器时出错：\n{str(e)}")

    def eventFilter(self, watched, event):
        """拦截 HelpWidget 的 Close/Hide 事件，清理保存的引用以允许再次打开。"""
        try:
            if watched is getattr(self, "_help_window", None):
                # 使用数值来避免某些静态类型检查器对 QEvent 枚举成员的误报
                ev_type = event.type()
                if ev_type in (19, 5):  # 19 = Close, 5 = Hide
                    try:
                        watched.removeEventFilter(self)
                    except Exception:
                        pass
                    self._help_window = None
        except Exception:
            pass

        return super().eventFilter(watched, event)

if __name__ == "__main__":
    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(APP_ICON_PATH))
    ui = SportsUploaderUI()
    ui.show()
    sys.exit(app.exec())
