import random
import math
import os
from utils.auxiliary_util import get_base_path

import src.config as config

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
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

RESOURCES_SUB_DIR = "assets"

RESOURCES_FULL_PATH = os.path.join(get_base_path(), RESOURCES_SUB_DIR)

class Ui_HelpWindow(object):
    def setupUi(self, HelpWindow):
        if not HelpWindow.objectName():
            HelpWindow.setObjectName(u"HelpWindow")
        HelpWindow.setWindowModality(Qt.WindowModality.WindowModal)
        HelpWindow.resize(415, 238)
        HelpWindow.setMinimumSize(QSize(415, 238))
        HelpWindow.setMaximumSize(QSize(415, 238))
        HelpWindow.setWindowIcon(QIcon(os.path.join(RESOURCES_FULL_PATH, "SJTURM.png")))
        HelpWindow.setStyleSheet(u"/* 感谢语标签样式 */\n"
"#thankYouLabel {\n"
"	color: #2980b9; /* 醒目的彼得里弗蓝色 */\n"
"	font: 700 14pt \"Microsoft YaHei UI\"; /* 字体更大更突出 */\n"
"	background-color: transparent;\n"
"}\n"
"\n"
"/* 信息文本标签样式 */\n"
"#infoLabel {\n"
"	color: #34495e; /* 深灰蓝色字体，保证清晰度 */\n"
"	font: 700 12pt \"Microsoft YaHei UI\";\n"
"	background-color: transparent; /* 透明背景 */\n"
"}\n"
"\n"
"/* 头像标签样式 */\n"
"#avatarLabel {\n"
"	border-radius: 50px; /* 圆形头像的关键：半径为宽/高的一半 */\n"
"	border: 2px solid rgba(255, 255, 255, 0.9); /* 更清晰的半透明白色边框 */\n"
"}\n"
"\n"
"/* 确认按钮样式 */\n"
"#okButton {\n"
"	background-color: rgba(255, 255, 255, "
                        "0.85); /* 半透明白色背景 */\n"
"	border: 1px solid #bdc3c7; /* 柔和的灰色边框 */\n"
"	border-radius: 15px; /* 圆角，使其呈药丸形状 */\n"
"	color: #2c3e50; /* 深色字体，与背景形成对比 */\n"
"	font: 700 10pt \"Microsoft YaHei UI\";\n"
"}\n"
"\n"
"/* 按钮悬停效果 */\n"
"#okButton:hover {\n"
"	background-color: #ffffff; /* 悬停时变为不透明白色 */\n"
"	border: 1px solid #95a5a6; /* 边框颜色加深 */\n"
"}\n"
"\n"
"/* 按钮按下效果 */\n"
"#okButton:pressed {\n"
"	background-color: #f5f5f5; /* 按下时变为浅灰色 */\n"
"	border: 1px solid #7f8c8d;\n"
"}")
        self.backgroundLabel = QLabel(HelpWindow)
        self.backgroundLabel.setObjectName(u"backgroundLabel")
        self.backgroundLabel.setGeometry(QRect(0, 0, 415, 238))
        self.backgroundLabel.setPixmap(QPixmap(u":/resources/bg.png"))
        self.backgroundLabel.setScaledContents(True)
        self.infoLabel = QLabel(HelpWindow)
        self.infoLabel.setObjectName(u"infoLabel")
        self.infoLabel.setGeometry(QRect(20, 64, 261, 120))
        font = QFont()
        font.setFamilies([u"Microsoft YaHei UI"])
        font.setPointSize(12)
        font.setBold(True)
        font.setItalic(False)
        self.infoLabel.setFont(font)
        self.infoLabel.setCursor(QCursor(Qt.ArrowCursor))
        self.infoLabel.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.avatarLabel = QLabel(HelpWindow)
        self.avatarLabel.setObjectName(u"avatarLabel")
        self.avatarLabel.setGeometry(QRect(285, 48, 100, 100))
        self.avatarLabel.setCursor(QCursor(Qt.PointingHandCursor))
        self.avatarLabel.setPixmap(QPixmap(u":/resources/head.png"))
        self.avatarLabel.setScaledContents(True)
        self.okButton = QPushButton(HelpWindow)
        self.okButton.setObjectName(u"okButton")
        self.okButton.setGeometry(QRect(150, 198, 100, 30))
        self.okButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.thankYouLabel = QLabel(HelpWindow)
        self.thankYouLabel.setObjectName(u"thankYouLabel")
        self.thankYouLabel.setGeometry(QRect(55, 25, 196, 36))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.thankYouLabel.sizePolicy().hasHeightForWidth())
        self.thankYouLabel.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setFamilies([u"Microsoft YaHei UI"])
        font1.setPointSize(14)
        font1.setBold(True)
        font1.setItalic(False)
        self.thankYouLabel.setFont(font1)
        self.thankYouLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.retranslateUi(HelpWindow)

        QMetaObject.connectSlotsByName(HelpWindow)
    # setupUi

    def retranslateUi(self, HelpWindow):
        HelpWindow.setWindowTitle(QCoreApplication.translate("HelpWindow", u"关于本工具", None))
        self.backgroundLabel.setText("")
        self.infoLabel.setText(QCoreApplication.translate("HelpWindow", u"<html><head/><body><p>界面优化：Github@CEQ151</p><p>三改：Github@JackyTJie</p><p>二改：Github@accelerator-s</p><p>原作者：Github@Labyrinth0419</p><p>Version: " + config.global_version + "</p></body></html>", None))
        self.avatarLabel.setText("")
        self.okButton.setText(QCoreApplication.translate("HelpWindow", u"确定", None))
        self.thankYouLabel.setText(QCoreApplication.translate("HelpWindow", u"<html><head/><body><p><span style=\" font-size:20pt;\">感谢您的使用！</span></p></body></html>", None))
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
        self.background_pixmap = QPixmap(":/resources/bg.png")
        # 当点击关于窗口的“确定”按钮时，隐藏此窗口
        try:
            self.ui.okButton.clicked.connect(self.on_ok_clicked)
        except Exception:
            try:
                self.ui.okButton.clicked.connect(self.close)
            except Exception:
                pass
        self.ui.backgroundLabel.hide()
        self.frames_sprayed = 0

        # --- 创建并设置遮罩层 ---
        self.overlay = ConfettiOverlay(self)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)

    def closeEvent(self, event):
        """处理窗口关闭事件，确保主窗口恢复可关闭状态"""
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

    def showEvent(self, event):
        """窗口显示时，重置并启动彩带动画"""
        super().showEvent(event)
        self.particles = []
        self.frames_sprayed = 0
        self.animation_timer.start(16)

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
