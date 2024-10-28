import sys
import moderngl as mgl
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from util import *
from camera import Camera
from scene import Scene

class ViewerWidget(QModernGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = None
        self.last_x = None
        self.last_y = None

        self.mouse_left_pressed = False
        self.shift_pressed = False
        self.ctrl_pressed = False

    def init(self):
        self.ctx.viewport = self.viewport
        self.scene = Scene(self.ctx)
        self.ctx_init()

    def render(self):
        self.screen.use()
        self.scene.draw()
    
    def ctx_init(self):
        self.ctx.enable(mgl.DEPTH_TEST)
        self.ctx.enable(mgl.CULL_FACE)

    def mousePressEvent(self, event):
        self.last_x = event.x()
        self.last_y = event.y()
        if event.button() == Qt.LeftButton:
            self.mouse_left_pressed = True
        self.update()

    def mouseReleaseEvent(self, event):
        self.last_x = None
        self.last_y = None
        if event.button() == Qt.LeftButton:
            self.mouse_left_pressed = False
        self.update()

    def mouseMoveEvent(self, event):
        if self.last_x is None or self.last_y is None:
            return

        dx = event.x() - self.last_x
        dy = event.y() - self.last_y
        self.last_x = event.x()
        self.last_y = event.y()

        if self.mouse_left_pressed:
            if self.shift_pressed:
                # Perform panning if Shift is pressed
                self.scene.camera.pan(dx, dy)
            else:
                # Perform orbiting otherwise
                self.scene.camera.orbit(dx, dy)
        
        self.update()
    
    def wheelEvent(self, event):
        offset = event.angleDelta().y() / 120
        self.scene.camera.dolly(offset)
        self.update()
    
    def resizeEvent(self, event):
        width = event.size().width()
        height = event.size().height()
        if width > height:
            self.viewport = (int((width - height) / 2), 0, height, height)
        else:
            self.viewport = (0, int((height - width) / 2), width, width)
        if hasattr(self, 'ctx') and hasattr(self.ctx, 'viewport'):
            self.ctx.viewport = self.viewport

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.shift_pressed = True
        elif event.key() == Qt.Key_Control:
            self.ctrl_pressed = True
        elif event.key() in [Qt.Key_1, Qt.Key_3, Qt.Key_7]:
            view = {Qt.Key_1: 1, Qt.Key_3: 3, Qt.Key_7: 7}[event.key()]
            self.scene.camera.orthogonal(view, self.ctrl_pressed)
        elif event.key() == Qt.Key_F:
            self.focus_on_selected_object()
        self.update()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.shift_pressed = False
        elif event.key() == Qt.Key_Control:
            self.ctrl_pressed = False
    
    def focus_on_selected_object(self):
        """Focus on the selected object."""
        selected_center = [0.0, 0.0, 0.0]  # Adjust this as needed
        self.scene.camera.focus(selected_center)
        self.update()
    
    def load_mesh(self, mesh):
        self.scene.load_mesh(mesh)
        self.update()

    def release_mesh(self):
        self.scene.release_mesh()
        self.update()

def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = ViewerWidget()
    widget.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
