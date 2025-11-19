import sys
import os
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QProgressBar, QFormLayout, QGroupBox, QDateTimeEdit,
    QMessageBox, QScrollArea, QSizePolicy, QCheckBox, QComboBox,
    QSpacerItem, QFileDialog
)
from PySide6.QtCore import QThread, Signal, QDateTime, QDate, Qt, QUrl, QEvent
from PySide6.QtGui import QTextCursor, QFont, QColor, QTextCharFormat, QPalette, QBrush, QIcon, QDesktopServices

from src.main import run_sports_upload
import src.login as login
from utils.auxiliary_util import SportsUploaderError, get_base_path
import src.config as config


from src.info_dialog import HelpWidget

RESOURCES_SUB_DIR = "assets"

RESOURCES_FULL_PATH = os.path.join(get_base_path(), RESOURCES_SUB_DIR)

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
        self.setWindowIcon(QIcon(os.path.join(RESOURCES_FULL_PATH, "SJTURM.png")))

        # 后台线程引用（私有）
        self._thread = None
        # 关于窗口引用，防止被垃圾回收
        self._help_window = None

        self.config = {}

        self.setup_ui_style()
        self.init_ui()

        self.setGeometry(300, 50, 520, 750)
        self.setMinimumSize(520, 750)

        # 根据当前窗口宽度调整内容区域宽度
        self.adjust_content_width(self.width())
        # 启动时居中主窗口
        try:
            self.center_window()
        except Exception:
            pass

    def setup_ui_style(self):
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(255, 255, 255))
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
                background-color: rgb(255, 255, 255);
                color: rgb(51, 51, 51);
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            
            /* GroupBox 样式 */
            QGroupBox {
                font-size: 10pt;
                font-weight: bold;
                margin-top: 10px;
                border: 1px solid rgb(220, 220, 220);
                border-radius: 6px;
                padding: 15px;
                color: rgb(74, 144, 226);
                background-color: rgb(248, 249, 250);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px 0 5px;
                color: rgb(74, 144, 226);
                background-color: rgb(255, 255, 255);
            }
            
            /* 确保所有标签和输入框可见 */
            QLabel {
                color: rgb(51, 51, 51);
                background-color: transparent;
                font-size: 9pt;
            }
            
            QLineEdit, QComboBox, QDateTimeEdit {
                background-color: rgb(255, 255, 255);
                border: 1px solid rgb(204, 204, 204);
                border-radius: 4px;
                padding: 8px;
                color: rgb(51, 51, 51);
                font-size: 9pt;
            }
            
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid rgb(74, 144, 226);
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: rgb(204, 204, 204);
                border-left-style: solid;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QPushButton {
                background-color: rgb(255, 255, 255);
                color: rgb(51, 51, 51);
                border: 1px solid rgb(204, 204, 204);
                border-radius: 4px;
                padding: 8px 16px;
                min-height: 24px;
                max-height: 36px;
            }
            QPushButton:hover {
                border: 1px solid rgb(74, 144, 226);
                background-color: rgb(250, 250, 250);
            }
            QPushButton:pressed {
                background-color: rgb(240, 240, 240);
            }
            QPushButton:disabled {
                background-color: rgb(255, 255, 255);
                color: rgb(180, 180, 180);
                border: 1px solid rgb(230, 230, 230);
            }
            QProgressBar {
                border: 1px solid rgb(220, 220, 220);
                border-radius: 4px;
                text-align: center;
                background-color: rgb(255, 255, 255);
                color: rgb(51, 51, 51);
                max-height: 20px;
            }
            QProgressBar::chunk {
                background-color: rgb(74, 144, 226);
                border-radius: 4px;
            }
            QTextEdit {
                background-color: rgb(245, 245, 247);
                border: 1px solid rgb(220, 220, 220);
                border-radius: 4px;
                padding: 8px;
                color: rgb(51, 51, 51);
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
                color: rgb(102, 102, 102);
            }
            #startButton {
                background-color: rgb(76, 175, 80);
                color: white;
                border: 1px solid rgb(76, 175, 80);
            }
            #startButton:hover {
                background-color: rgb(67, 160, 71);
                border: 1px solid rgb(67, 160, 71);
            }
            #startButton:pressed {
                background-color: rgb(56, 142, 60);
            }
            #stopButton {
                background-color: rgb(220, 53, 69);
                color: white;
                border: 1px solid rgb(220, 53, 69);
            }
            #stopButton:hover {
                background-color: rgb(179, 43, 56);
                border: 1px solid rgb(179, 43, 56);
            }
            #stopButton:pressed {
                background-color: rgb(140, 34, 44);
            }
            QLabel#getCookieLink {
                color: rgb(74, 144, 226);
                text-decoration: underline;
                padding: 0;
            }
            QLabel#getCookieLink:hover {
                color: rgb(52, 120, 198);
            }
        """)

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
        scroll_layout.addWidget(user_group)

        # 添加运行次数和时间选择组件
        run_settings_group = QGroupBox("上传设置")
        run_settings_layout = QVBoxLayout()
        run_settings_layout.setContentsMargins(15, 15, 15, 15)
        run_settings_layout.setSpacing(20)

        # 运行次数选择 - 天数 (垂直布局)
        days_layout = QVBoxLayout()
        days_label_layout = QHBoxLayout()
        days_label_layout.addWidget(QLabel("上传天数:"))
        days_label_layout.addStretch()
        days_layout.addLayout(days_label_layout)

        days_input_layout = QHBoxLayout()
        self.run_days_combo = QComboBox()
        self.run_days_combo.addItems(["自定义", "1", "5", "10", "15", "20", "25"])
        self.run_days_combo.setCurrentIndex(1)  # 默认选择1天
        days_input_layout.addWidget(self.run_days_combo)

        # 自定义天数输入框（默认隐藏）
        self.custom_days_input = QLineEdit()
        self.custom_days_input.setPlaceholderText("输入自定义天数")
        self.custom_days_input.setVisible(False)  # 默认隐藏
        days_input_layout.addWidget(self.custom_days_input)
        days_layout.addLayout(days_input_layout)

        run_settings_layout.addLayout(days_layout)

        # 连接天数下拉框变化事件
        self.run_days_combo.currentTextChanged.connect(self.on_run_days_changed)

        # 运行时间选择 - 时间 (垂直布局)
        time_layout = QVBoxLayout()
        time_label_layout = QHBoxLayout()
        time_label_layout.addWidget(QLabel("跑步时间:"))
        time_label_layout.addStretch()
        time_layout.addLayout(time_label_layout)

        time_input_layout = QHBoxLayout()
        self.run_time_combo = QComboBox()
        # Add "Custom" option for precise time selection at the top
        self.run_time_combo.addItem("自定义时间 (HH:MM:SS)")

        # Add hours from 6 to 23 (6:00 AM to 11:00 PM) - just hour intervals
        for hour in range(6, 24):  # 6 AM to 11 PM (23:00)
            self.run_time_combo.addItem(f"{hour:02d}:00")

        # Default to 8:00 AM (index 3: custom option at index 0, then 6:00, 7:00, 8:00 at index 2+1=3)
        default_index = 8 - 6 + 1  # 8 AM minus 6 AM plus 1 for the custom option at the beginning
        self.run_time_combo.setCurrentIndex(default_index)
        time_input_layout.addWidget(self.run_time_combo)

        # Custom time input layout (initially hidden)
        self.custom_time_input = QLineEdit()
        self.custom_time_input.setPlaceholderText("HH:MM:SS (例如: 08:30:45, 24小时制)")
        self.custom_time_input.setVisible(False)  # Initially hidden
        time_input_layout.addWidget(self.custom_time_input)

        time_layout.addLayout(time_input_layout)

        run_settings_layout.addLayout(time_layout)

        # Connect time combo change to show/hide custom time input
        self.run_time_combo.currentTextChanged.connect(self.on_run_time_changed)

        # 运行日期选择 - 日期 (垂直布局)
        date_layout = QVBoxLayout()
        date_label_layout = QHBoxLayout()
        date_label_layout.addWidget(QLabel("开始日期:"))
        date_label_layout.addStretch()
        date_layout.addLayout(date_label_layout)

        date_input_layout = QHBoxLayout()
        self.date_input = QLineEdit()
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.date_input.setText(yesterday)  # 默认显示昨天的日期
        self.date_input.setPlaceholderText("YYYY-MM-DD (例如: " + yesterday + ")")
        date_input_layout.addWidget(self.date_input)

        date_layout.addLayout(date_input_layout)

        run_settings_layout.addLayout(date_layout)

        # 运行距离选择
        distance_layout = QVBoxLayout()
        distance_label_layout = QHBoxLayout()
        distance_label_layout.addWidget(QLabel("跑步距离:"))
        distance_label_layout.addStretch()
        distance_layout.addLayout(distance_label_layout)

        distance_input_layout = QHBoxLayout()
        self.run_distance_combo = QComboBox()
        # Add distances from 1 to 5 km
        for distance in range(1, 6):  # 1 to 5 km
            self.run_distance_combo.addItem(f"{distance} km")

        self.run_distance_combo.setCurrentIndex(4)  # 默认选择5 km (index 4)
        distance_input_layout.addWidget(self.run_distance_combo)
        distance_layout.addLayout(distance_input_layout)

        run_settings_layout.addLayout(distance_layout)

        run_settings_group.setLayout(run_settings_layout)
        scroll_layout.addWidget(run_settings_group)

        action_button_layout = QHBoxLayout()
        action_button_layout.setSpacing(12)
        self.start_button = QPushButton("一键跑步")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_upload)
        action_button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_upload)
        action_button_layout.addWidget(self.stop_button)

        self.route_button = QPushButton("生成路线")
        self.route_button.clicked.connect(self.open_route_generator)
        action_button_layout.addWidget(self.route_button)

        self.info_button = QPushButton("关于")
        self.info_button.clicked.connect(self.show_info_dialog)
        action_button_layout.addWidget(self.info_button)

        scroll_layout.addLayout(action_button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        scroll_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("状态: 待命")
        scroll_layout.addWidget(self.status_label)
        
        self.log_output_area = QTextEdit()
        self.log_output_area.setReadOnly(True)
        self.log_output_area.setFont(QFont("Monospace", 9))
        # Reduce the vertical stretch factor to give more space to other components
        self.log_output_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        scroll_layout.addWidget(self.log_output_area)

        top_h_layout.addWidget(self.center_widget)

        self.setLayout(top_h_layout)

    def on_run_days_changed(self, text):
        """处理运行天数选择变化事件"""
        if text == "自定义":
            self.custom_days_input.setVisible(True)
        else:
            self.custom_days_input.setVisible(False)

    def on_run_time_changed(self, text):
        """处理运行时间选择变化事件"""
        if text == "自定义时间 (HH:MM:SS)":
            self.custom_time_input.setVisible(True)
        else:
            self.custom_time_input.setVisible(False)

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
        # 不强制很大的最小宽度，使用窗口宽度的 90% 或最大 600 的限制
        calculated_width = int(min(window_width * 0.9, 600))
        # 保证最小为 280，以适配窄窗口（比如 300px）
        calculated_width = max(280, calculated_width)
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

            # 获取运行次数
            run_times_text = self.run_days_combo.currentText()
            if run_times_text == "自定义":
                custom_days_text = self.custom_days_input.text().strip()
                if not custom_days_text:
                    raise ValueError("请输入自定义天数。")
                try:
                    run_times = int(custom_days_text)
                    if run_times <= 0:
                        raise ValueError("运行次数必须大于0。")
                except ValueError:
                    raise ValueError("自定义天数必须是正整数。")
            else:
                run_times = int(run_times_text)

            # 获取运行时间
            run_time_text = self.run_time_combo.currentText()
            if run_time_text == "自定义时间 (HH:MM:SS)":
                # Use custom time input
                custom_time_text = self.custom_time_input.text().strip()
                if not custom_time_text:
                    raise ValueError("请输入自定义时间，格式为 HH:MM:SS")

                try:
                    # Parse custom time in HH:MM:SS format
                    time_parts = custom_time_text.split(':')
                    if len(time_parts) != 3:
                        raise ValueError("时间格式错误，应为 HH:MM:SS")
                    run_hour = int(time_parts[0])
                    run_minute = int(time_parts[1])
                    run_second = int(time_parts[2])

                    if not (0 <= run_hour <= 23):
                        raise ValueError("小时应在 0-23 之间")
                    if not (0 <= run_minute <= 59):
                        raise ValueError("分钟应在 0-59 之间")
                    if not (0 <= run_second <= 59):
                        raise ValueError("秒钟应在 0-59 之间")
                except ValueError:
                    raise ValueError("时间格式错误，应为 HH:MM:SS，例如 08:30:45")
            else:
                # Use predefined time - format is "HH:00"
                time_parts = run_time_text.split(':')
                run_hour = int(time_parts[0])  # Extract hour from "HH:00" format
                run_minute = int(time_parts[1])  # Extract minute from "HH:00" format (should be 00)
                run_second = 0  # Default second for predefined times

            # 获取运行距离（公里）
            run_distance_text = self.run_distance_combo.currentText()
            run_distance_km = int(run_distance_text.split()[0])  # Extract km from "X km" format

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
                "RUNNING_SPEED_MPS": round(1000.0 / (3.5 * 60), 3),
                "INTERVAL_SECONDS": int(self.config.get("INTERVAL_SECONDS", 3)),
                "HOST": "pe.sjtu.edu.cn",
                "UID_URL": "https://pe.sjtu.edu.cn/sports/my/uid",
                "MY_DATA_URL": "https://pe.sjtu.edu.cn/sports/my/data",
                "POINT_RULE_URL": "https://pe.sjtu.edu.cn/api/running/point-rule",  # Fixed URL
                "UPLOAD_URL": "https://pe.sjtu.edu.cn/api/running/result/upload"
            }

            # Add start date from text input (the input is always filled with a default value)
            start_date_text = self.date_input.text().strip()
            if start_date_text:
                current_config["START_DATE"] = start_date_text

            # START_TIME_EPOCH_MS 由后端生成，不从 UI 获取

            if not current_config["USER_ID"] or not current_config["PASSWORD"]:
                raise ValueError("用户名和密码不能为空。")

            return current_config

        except ValueError as e:
            raise ValueError(f"输入错误: {e}")
        except Exception as e:
            raise Exception(f"获取配置时发生未知错误: {e}")

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
        self.stop_button.setEnabled(True)
        self.info_button.setEnabled(False)
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)

        # 调用 login.py 获取 session，使用 UI 中的用户名/密码
        try:
            username = current_config_to_send.get("USER_ID")
            password = current_config_to_send.get("PASSWORD")
            session = login.login(username, password)
            current_config_to_send["SESSION"] = session
            # USER_ID 即 Jaccount 用户名
            current_config_to_send["USER_ID"] = username
        except Exception as e:
            self.log_output_text(f"登录失败: {e}", "error")
            QMessageBox.critical(self, "登录失败", str(e))
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            self.info_button.setEnabled(True)
            return

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
                                        "如需修改路线，请选择\"生成路线\"按钮并创建新路线。")
                else:
                    QMessageBox.information(self, "默认路线", 
                                        "将使用默认路线文件：default.txt\n\n"
                                        "如需修改路线，请选择\"生成路线\"按钮并创建自定义路线。")
                    
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
    app = QApplication(sys.argv)
    ui = SportsUploaderUI()
    ui.show()
    sys.exit(app.exec())