import random
import math
import os
import sys
from utils.auxiliary_util import get_base_path

import src.config as config
from src.update_checker import UpdateCheckTask

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QThreadPool, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QDesktopServices, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QStatusBar, QTableView,
    QWidget, QInputDialog, QMessageBox, QVBoxLayout, QAbstractItemView,
    QStyledItemDelegate, QStyleOptionViewItem, QToolTip)
import assets.resources_rc as resources_rc
from PySide6.QtCore import QModelIndex, QEvent, QTimer, QPointF, QRectF, QSizeF, Qt

# 存活中的检查更新任务，防止未结束时被垃圾回收
_LIVE_UPDATE_TASKS = []


def prune_update_tasks():
    """清掉已跑完但没被回调清理的任务（例如检查途中窗口就被关了）。"""
    try:
        for task in list(_LIVE_UPDATE_TASKS):
            if task.done:
                _LIVE_UPDATE_TASKS.remove(task)
    except Exception:
        pass

# 界面字体族：macOS 上没有微软雅黑，优先用系统中文字体，避免 Qt 反复做字体回退
if sys.platform == "darwin":
    UI_FONT_FAMILIES_LIST = ["PingFang SC", "Hiragino Sans GB", "Heiti SC",
                             "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"]
else:
    UI_FONT_FAMILIES_LIST = ["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI",
                             "PingFang SC"]

UI_FONT_FAMILIES = ", ".join(f'"{name}"' for name in UI_FONT_FAMILIES_LIST) + ", sans-serif"

# 状态文字配色：发现新版本 / 已是最新 / 出错
UPDATE_STATUS_COLORS = {
    "update": "#7cffb2",
    "ok": "rgba(255, 255, 255, 0.72)",
    "error": "#ff9c9c",
}

RESOURCES_SUB_DIR = "assets"

RESOURCES_FULL_PATH = os.path.join(get_base_path(), RESOURCES_SUB_DIR)
HELP_BACKGROUND_PATH = os.path.join(RESOURCES_FULL_PATH, "background.jpg")

class Ui_HelpWindow(object):
    def setupUi(self, HelpWindow):
        if not HelpWindow.objectName():
            HelpWindow.setObjectName(u"HelpWindow")
        HelpWindow.setWindowModality(Qt.WindowModality.WindowModal)
        HelpWindow.resize(520, 320)
        HelpWindow.setMinimumSize(QSize(520, 320))
        HelpWindow.setMaximumSize(QSize(520, 320))
        HelpWindow.setWindowIcon(QIcon(os.path.join(RESOURCES_FULL_PATH, "SJTURM.png")))
        HelpWindow.setStyleSheet((u"#HelpWindow {\n"
"	border: none;\n"
"}\n"
"\n"
"#contentPanel {\n"
"	background-color: rgba(8, 14, 24, 0.58);\n"
"	border: 1px solid rgba(255, 255, 255, 0.26);\n"
"	border-radius: 22px;\n"
"}\n"
"\n"
"#thankYouLabel {\n"
"	color: #ffffff;\n"
"	font-family: __UI_FONT__;\n"
"	font-size: 22pt;\n"
"	font-weight: 700;\n"
"	background-color: transparent;\n"
"	letter-spacing: 0px;\n"
"}\n"
"\n"
"#infoLabel {\n"
"	color: rgba(255, 255, 255, 0.90);\n"
"	font-family: __UI_FONT__;\n"
"	font-size: 12pt;\n"
"	font-weight: 500;\n"
"	background-color: transparent;\n"
"	line-height: 150%;\n"
"}\n"
"\n"
"#versionPill {\n"
"	color: rgba(255, 255, 255, 0.92);\n"
"	font-family: __UI_FONT__;\n"
"	font-size: 10pt;\n"
"	font-weight: 700;\n"
"	background-color: rgba(255, 255, 255, 0.14);\n"
"	border: 1px solid rgba(255, 255, 255, 0.26);\n"
"	border-radius: 13px;\n"
"	padding-left: 10px;\n"
"	padding-right: 10px;\n"
"}\n"
"\n"
"#okButton {\n"
"	background-color: rgba(255, 255, 255, 0.12);\n"
"	border: 1px solid rgba(255, 255, 255, 0.34);\n"
"	border-radius: 16px;\n"
"	color: #ffffff;\n"
"	font-family: __UI_FONT__;\n"
"	font-size: 11pt;\n"
"	font-weight: 700;\n"
"	padding: 5px 18px;\n"
"}\n"
"\n"
"#okButton:hover {\n"
"	background-color: rgba(255, 255, 255, 0.22);\n"
"	border: 1px solid rgba(255, 255, 255, 0.52);\n"
"}\n"
"\n"
"#okButton:pressed {\n"
"	background-color: rgba(255, 255, 255, 0.16);\n"
"	border: 1px solid rgba(255, 255, 255, 0.42);\n"
"}\n"
"\n"
"#checkUpdateButton {\n"
"	background-color: rgba(255, 255, 255, 0.08);\n"
"	border: 1px solid rgba(255, 255, 255, 0.26);\n"
"	border-radius: 16px;\n"
"	color: rgba(255, 255, 255, 0.92);\n"
"	font-family: __UI_FONT__;\n"
"	font-size: 11pt;\n"
"	font-weight: 700;\n"
"	padding: 5px 14px;\n"
"}\n"
"\n"
"#checkUpdateButton:hover {\n"
"	background-color: rgba(255, 255, 255, 0.18);\n"
"	border: 1px solid rgba(255, 255, 255, 0.46);\n"
"}\n"
"\n"
"#checkUpdateButton:pressed {\n"
"	background-color: rgba(255, 255, 255, 0.12);\n"
"	border: 1px solid rgba(255, 255, 255, 0.38);\n"
"}\n"
"\n"
"#checkUpdateButton:disabled {\n"
"	color: rgba(255, 255, 255, 0.52);\n"
"	border: 1px solid rgba(255, 255, 255, 0.16);\n"
"}\n"
"\n"
"#updateStatusLabel {\n"
"	font-family: __UI_FONT__;\n"
"	font-size: 10pt;\n"
"	font-weight: 500;\n"
"	background-color: transparent;\n"
"}")
.replace("__UI_FONT__", UI_FONT_FAMILIES))
        self.backgroundLabel = QLabel(HelpWindow)
        self.backgroundLabel.setObjectName(u"backgroundLabel")
        self.backgroundLabel.setGeometry(QRect(0, 0, 520, 320))
        self.backgroundLabel.setPixmap(QPixmap(HELP_BACKGROUND_PATH))
        self.backgroundLabel.setScaledContents(True)
        self.contentPanel = QFrame(HelpWindow)
        self.contentPanel.setObjectName(u"contentPanel")
        self.contentPanel.setGeometry(QRect(28, 28, 464, 264))
        self.infoLabel = QLabel(HelpWindow)
        self.infoLabel.setObjectName(u"infoLabel")
        self.infoLabel.setGeometry(QRect(58, 101, 404, 120))
        font = QFont()
        font.setFamilies(UI_FONT_FAMILIES_LIST)
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        self.infoLabel.setFont(font)
        self.infoLabel.setCursor(QCursor(Qt.ArrowCursor))
        self.infoLabel.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.infoLabel.setWordWrap(True)
        self.avatarLabel = QLabel(HelpWindow)
        self.avatarLabel.setObjectName(u"avatarLabel")
        self.avatarLabel.setGeometry(QRect(285, 48, 100, 100))
        self.avatarLabel.setCursor(QCursor(Qt.PointingHandCursor))
        self.avatarLabel.setPixmap(QPixmap())
        self.avatarLabel.setScaledContents(True)
        self.avatarLabel.hide()
        self.okButton = QPushButton(HelpWindow)
        self.okButton.setObjectName(u"okButton")
        self.okButton.setGeometry(QRect(360, 243, 102, 32))
        self.okButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.thankYouLabel = QLabel(HelpWindow)
        self.thankYouLabel.setObjectName(u"thankYouLabel")
        self.thankYouLabel.setGeometry(QRect(56, 54, 290, 42))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.thankYouLabel.sizePolicy().hasHeightForWidth())
        self.thankYouLabel.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setFamilies(UI_FONT_FAMILIES_LIST)
        font1.setPointSize(22)
        font1.setBold(True)
        font1.setItalic(False)
        self.thankYouLabel.setFont(font1)
        self.thankYouLabel.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.versionPill = QLabel(HelpWindow)
        self.versionPill.setObjectName(u"versionPill")
        self.versionPill.setGeometry(QRect(360, 59, 102, 26))
        self.versionPill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.updateStatusLabel = QLabel(HelpWindow)
        self.updateStatusLabel.setObjectName(u"updateStatusLabel")
        self.updateStatusLabel.setGeometry(QRect(56, 244, 176, 30))
        font2 = QFont()
        font2.setFamilies(UI_FONT_FAMILIES_LIST)
        font2.setPointSize(10)
        font2.setBold(False)
        font2.setItalic(False)
        self.updateStatusLabel.setFont(font2)
        self.updateStatusLabel.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.checkUpdateButton = QPushButton(HelpWindow)
        self.checkUpdateButton.setObjectName(u"checkUpdateButton")
        self.checkUpdateButton.setGeometry(QRect(240, 243, 112, 32))
        self.checkUpdateButton.setCursor(QCursor(Qt.PointingHandCursor))

        self.retranslateUi(HelpWindow)

        QMetaObject.connectSlotsByName(HelpWindow)
    # setupUi

    def retranslateUi(self, HelpWindow):
        HelpWindow.setWindowTitle(QCoreApplication.translate("HelpWindow", u"关于本工具", None))
        self.backgroundLabel.setText("")
        self.infoLabel.setText(QCoreApplication.translate("HelpWindow", u"<html><head/><body><p>界面优化：Github@CEQ151</p><p>三改：Github@JackyTJie</p><p>二改：Github@accelerator-s</p><p>原作者：Github@Labyrinth0419</p></body></html>", None))
        self.avatarLabel.setText("")
        self.okButton.setText(QCoreApplication.translate("HelpWindow", u"知道了", None))
        self.thankYouLabel.setText(QCoreApplication.translate("HelpWindow", u"感谢您的使用", None))
        self.versionPill.setText(QCoreApplication.translate("HelpWindow", config.global_version, None))
        self.updateStatusLabel.setText("")
        self.checkUpdateButton.setText(QCoreApplication.translate("HelpWindow", u"检查更新", None))
    # retranslateUi

# --- 创建一个专门用于绘制彩带的透明遮罩层类 ---
class ConfettiOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置属性使其透明，能够接收绘制事件
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        """只在这个遮罩层上绘制彩带"""
        # 从父窗口获取粒子列表
        particles = self.parent().particles
        if not particles:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for particle in particles:
            color = QColor(particle.color)
            color.setAlphaF(max(0, particle.life))

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)

            painter.save()
            painter.translate(particle.pos)
            painter.rotate(particle.angle)
            rect = QRectF(-particle.size.width() / 2, -particle.size.height() / 2,
                          particle.size.width(), particle.size.height())
            painter.drawRect(rect)
            painter.restore()

# --- 彩带粒子类 ---
class ConfettiParticle:
    """代表一片彩带的类"""
    def __init__(self, pos, velocity, color, size, angular_velocity):
        self.pos = pos
        self.velocity = velocity
        self.color = color
        self.size = size
        self.angle = random.uniform(0, 360)
        self.angular_velocity = angular_velocity
        self.life = 1.0

# --- 窗口类 ---
class HelpWidget(QWidget):
    # 动画参数和物理常量
    GRAVITY = QPointF(0, 0.08)
    DRAG = 0.99
    FADE_SPEED = 0.01
    SPRAY_DURATION_FRAMES = 120
    PARTICLES_PER_FRAME_PER_SIDE = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_HelpWindow()
        self.ui.setupUi(self)

        self.particles = []
        self.background_pixmap = QPixmap(HELP_BACKGROUND_PATH)
        # 当点击关于窗口的“确定”按钮时，隐藏此窗口
        try:
            self.ui.okButton.clicked.connect(self.on_ok_clicked)
        except Exception:
            try:
                self.ui.okButton.clicked.connect(self.close)
            except Exception:
                pass
        # 检查更新相关状态
        self.update_task = None
        self.update_url = ""
        try:
            self.ui.checkUpdateButton.clicked.connect(self.on_check_update_clicked)
        except Exception:
            pass

        self.ui.backgroundLabel.hide()
        self.ui.avatarLabel.hide()
        self.frames_sprayed = 0

        # --- 创建并设置遮罩层 ---
        self.overlay = ConfettiOverlay(self)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)

    def closeEvent(self, event):
        """处理窗口关闭事件，确保主窗口恢复可关闭状态"""
        self.stop_update_check()
        try:
            # 假设父窗口是 ControlPanelWindow 的实例
            if self.parent() and hasattr(self.parent(), 'setClosable'):
                self.parent().setClosable(True)
        except Exception:
            pass
        # 接受事件，让窗口正常隐藏
        super().closeEvent(event)

    def on_ok_clicked(self):
        """点击确定按钮时，隐藏窗口并恢复主窗口的关闭功能"""
        self.stop_update_check()
        try:
            # 停止动画，清理粒子，拆卸 overlay，避免在关闭时产生绘制或定时器调用的竞态
            if hasattr(self, 'animation_timer') and self.animation_timer is not None:
                try:
                    if self.animation_timer.isActive():
                        self.animation_timer.stop()
                except Exception:
                    pass
            try:
                self.particles = []
            except Exception:
                pass
            try:
                # 将 overlay 从层次结构中移除，避免绘制在即将被销毁的窗口上
                if hasattr(self, 'overlay') and self.overlay is not None:
                    self.overlay.setParent(None)
            except Exception:
                pass

            # 延迟关闭窗口以避免在事件链中立即销毁导致的竞态或闪退
            QTimer.singleShot(0, self.close)

        except Exception:
            # 作为兜底，直接尝试关闭
            try:
                self.close()
            except Exception:
                pass

    def set_update_status(self, text, level=None):
        """更新状态文字，level 取 update/ok/error 决定颜色。"""
        try:
            color = UPDATE_STATUS_COLORS.get(level, UPDATE_STATUS_COLORS["ok"])
            self.ui.updateStatusLabel.setStyleSheet(
                f"#updateStatusLabel {{ color: {color}; background-color: transparent; }}"
            )
            self.ui.updateStatusLabel.setText(text)
        except Exception:
            pass

    def on_check_update_clicked(self):
        """点击“检查更新”。发现新版本后按钮变为“前往下载”。"""
        try:
            # 已有可下载链接：直接打开浏览器
            if self.update_url:
                QDesktopServices.openUrl(QUrl(self.update_url))
                return

            if self.update_task is not None:
                return

            prune_update_tasks()
            self.set_update_status("正在检查更新…", None)
            self.ui.checkUpdateButton.setEnabled(False)
            self.ui.checkUpdateButton.setText("检查中…")

            task = UpdateCheckTask()
            task.signals.checked.connect(self.on_update_checked)
            task.signals.failed.connect(self.on_update_failed)
            self.update_task = task
            _LIVE_UPDATE_TASKS.append(task)
            QThreadPool.globalInstance().start(task)
        except Exception as e:
            self.set_update_status(f"检查失败：{e}", "error")
            try:
                self.ui.checkUpdateButton.setEnabled(True)
                self.ui.checkUpdateButton.setText("检查更新")
            except Exception:
                pass

    def on_update_checked(self, has_update, message, url):
        """检查完成：有更新则切到下载按钮，否则只提示。"""
        try:
            self.release_update_task()
            if has_update:
                self.update_url = url or ""
                self.set_update_status(message, "update")
                self.ui.checkUpdateButton.setText("前往下载" if self.update_url else "检查更新")
            else:
                self.update_url = ""
                self.set_update_status(message, "ok")
                self.ui.checkUpdateButton.setText("检查更新")
            self.ui.checkUpdateButton.setEnabled(True)
        except Exception:
            pass

    def on_update_failed(self, message):
        """检查失败：保留重试入口。"""
        try:
            self.release_update_task()
            self.update_url = ""
            self.set_update_status(f"检查失败：{message}", "error")
            self.ui.checkUpdateButton.setText("重试")
            self.ui.checkUpdateButton.setEnabled(True)
        except Exception:
            pass

    def release_update_task(self):
        """任务收尾：从存活列表移除，清掉引用。"""
        try:
            task = self.update_task
            if task is not None and task in _LIVE_UPDATE_TASKS:
                _LIVE_UPDATE_TASKS.remove(task)
        except Exception:
            pass
        try:
            self.update_task = None
        except Exception:
            pass

    def stop_update_check(self):
        """窗口关闭时通知任务别再发信号。"""
        try:
            if self.update_task is not None:
                self.update_task.stop()
        except Exception:
            pass
        prune_update_tasks()

    def reset_update_button(self):
        """窗口重新打开时，避免按钮停在“检查中…”。"""
        try:
            if self.update_task is None and self.ui.checkUpdateButton.text() == "检查中…":
                self.ui.checkUpdateButton.setText("检查更新")
                self.ui.checkUpdateButton.setEnabled(True)
        except Exception:
            pass

    def showEvent(self, event):
        """窗口显示时，重置并启动彩带动画"""
        super().showEvent(event)
        self.particles = []
        self.frames_sprayed = 0
        self.animation_timer.start(16)
        self.reset_update_button()

    def resizeEvent(self, event):
        """窗口大小改变时，确保遮罩层也同步改变大小"""
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())
        # 始终将遮罩层置于所有其他子控件之上
        self.overlay.raise_()

    def init_confetti_animation(self):
        """初始化并启动彩带动画"""
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(16)

    def create_confetti_burst(self, count, origin, from_left=True):
        """在指定位置创建一波彩带"""
        colors = [
            QColor("#f44336"), QColor("#e91e63"), QColor("#9c27b0"),
            QColor("#673ab7"), QColor("#3f51b5"), QColor("#2196f3"),
            QColor("#03a9f4"), QColor("#00bcd4"), QColor("#009688"),
            QColor("#4caf50"), QColor("#8bc34a"), QColor("#cddc39"),
            QColor("#ffeb3b"), QColor("#ffc107"), QColor("#ff9800")
        ]
        for _ in range(count):
            angle = random.uniform(-110, -10)
            if not from_left:
                angle = -180 - angle
            speed = random.uniform(5.0, 9.0)
            vx = speed * math.cos(math.radians(angle))
            vy = speed * math.sin(math.radians(angle))
            color = random.choice(colors)
            size = QSizeF(random.uniform(5, 10), random.uniform(8, 15))
            angular_velocity = random.uniform(-5, 5)
            particle = ConfettiParticle(
                pos=QPointF(origin),
                velocity=QPointF(vx, vy),
                color=color,
                size=size,
                angular_velocity=angular_velocity
            )
            self.particles.append(particle)

    def update_animation(self):
        """更新粒子状态"""
        if self.frames_sprayed < self.SPRAY_DURATION_FRAMES:
            self.create_confetti_burst(self.PARTICLES_PER_FRAME_PER_SIDE, QPointF(20, self.height() - 10), from_left=True)
            self.create_confetti_burst(self.PARTICLES_PER_FRAME_PER_SIDE, QPointF(self.width() - 20, self.height() - 10), from_left=False)
            self.frames_sprayed += 1

        if self.frames_sprayed >= self.SPRAY_DURATION_FRAMES and not self.particles:
            self.animation_timer.stop()
            return

        for particle in self.particles[:]:
            particle.velocity += self.GRAVITY
            particle.velocity *= self.DRAG
            particle.pos += particle.velocity
            particle.angle += particle.angular_velocity
            particle.life -= self.FADE_SPEED
            if particle.life <= 0 or particle.pos.y() > self.height() + 20:
                self.particles.remove(particle)

        self.overlay.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.background_pixmap)
