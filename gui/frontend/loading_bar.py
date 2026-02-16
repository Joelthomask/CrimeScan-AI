"""
loading_bar.py
Cyan fireball loading bar with:
• Black outer border
• Image texture fill
• Smooth fade-in fill
• Fireball + particles
"""

import sys
import math
import random

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QPainter,
    QColor,
    QRadialGradient,
    QPixmap,
    QPen,
)
from PyQt5.QtWidgets import QWidget, QApplication


# ---------------------------
# Particle
# ---------------------------
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2.5, -0.5)
        self.vy = random.uniform(-1, 1)
        self.life = random.randint(18, 35)
        self.size = random.uniform(3, 7)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size *= 0.96


# ---------------------------
# Loader Widget
# ---------------------------
class LoadingBar(QWidget):
    def __init__(self, texture_path=None):
        super().__init__()

        self.setMinimumSize(500, 80)

        self.progress = 0
        self.time = 0
        self.particles = []

        self.texture = QPixmap()
        if texture_path:
            self.texture.load(texture_path)

        self.finished = False
        self.burst_timer = 0


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    # ---------------------------
    # Animation update
    # ---------------------------
    def animate(self):


        self.time += 0.1
        if self.finished:
            self.burst_timer += 1
            if self.burst_timer > 25:
                self.particles.clear()

        bar_margin = 40
        bar_w = self.width() - 80
        head_x = bar_margin + bar_w * self.progress / 100
        head_y = self.height() // 2

        # spawn particles
        if not self.finished:
            for _ in range(3):
                self.particles.append(Particle(head_x, head_y))


        # update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

        self.update()
    def finish(self):
        if self.finished:
            return

        self.finished = True

        # fireball position
        margin = 40
        width = self.width() - margin * 2
        head_x = margin + width * self.progress / 100
        head_y = self.height() // 2

        # create burst particles
        for _ in range(80):
            p = Particle(head_x, head_y)

            # radial explosion
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2.5, 6)

            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.life = random.randint(25, 45)
            p.size = random.uniform(4, 8)

            self.particles.append(p)


    # ---------------------------
    # Fireball
    # ---------------------------
    def draw_fireball(self, painter, x, y):
        pulse = abs(math.sin(self.time)) * 6
        radius = 12 + pulse

        grad = QRadialGradient(x, y, radius)
        grad.setColorAt(0, QColor(255, 255, 255, 240))
        grad.setColorAt(0.25, QColor(0, 255, 255, 220))
        grad.setColorAt(0.7, QColor(0, 200, 255, 120))
        grad.setColorAt(1, QColor(0, 255, 255, 0))

        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(x - radius),
            int(y - radius),
            int(radius * 2),
            int(radius * 2),
        )

    # ---------------------------
    # Painting
    # ---------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margin = 40
        width = self.width() - margin * 2
        height = 20
        y = self.height() // 2 - height // 2

        # --- Black border ---
        border_pen = QPen(QColor(0, 0, 0))
        border_pen.setWidth(6)
        painter.setPen(border_pen)
        painter.setBrush(QColor(25, 25, 30))
        painter.drawRoundedRect(margin - 3, y - 3,
                                width + 6, height + 6, 12, 12)

        # --- Inner bar ---
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(20, 30, 40))
        painter.drawRoundedRect(margin, y, width, height, 10, 10)

        # --- Fill width ---
        fill_w = int(width * self.progress / 100)
        from PyQt5.QtGui import QPainterPath

        if not self.texture.isNull() and fill_w > 0:

            # Clip to loading bar
            path = QPainterPath()
            path.addRoundedRect(margin, y, fill_w, height, 10, 10)
            painter.setClipPath(path)

            # Draw original texture without scaling
            painter.drawPixmap(
                margin, y,
                self.texture,
                0, 0,
                fill_w, self.texture.height()
            )

            painter.setClipping(False)




        else:
            painter.setBrush(QColor(0, 200, 220))
            painter.drawRoundedRect(margin, y, fill_w, height, 10, 10)

        # --- Particle trail ---
        for p in self.particles:
            alpha = max(0, min(255, p.life * 7))
            painter.setBrush(QColor(0, 255, 255, alpha))
            painter.drawEllipse(
                int(p.x),
                int(p.y),
                int(p.size),
                int(p.size),
            )

        # --- Fireball ---
        head_x = margin + fill_w
        head_y = self.height() // 2
        self.draw_fireball(painter, head_x, head_y)


# ---------------------------
# Test
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Put your texture path here
    from pathlib import Path

    BASE = Path(__file__).resolve().parents[2]
    texture = BASE / "assets" / "bar_texture.png"

    bar = LoadingBar(str(texture))



    bar.resize(600, 100)
    bar.show()

    sys.exit(app.exec_())
