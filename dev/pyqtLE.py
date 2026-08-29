from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

#LE = Logan Edition
class TextEditLE(QTextEdit):
    # Allows for pressing Enter/Return to take you to the next option
    # Also allows triggering on click

    clicked = Signal()

    def __init__(self, clicked=None, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(27)
        self.setTabChangesFocus(True)

    def keyPressEvent(self, event):
        #Makes it so pressing 'Enter' takes you to the next child just like tabbing
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.focusNextChild()

            event.ignore()
        else: 
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class PushButtonLE(QPushButton):
    # Quick fix for TextEditLE not liking the default Focus Policy
    
    def __init__(self, text, clicked=None, parent=None):
        super().__init__(text, parent)
        
        self.setFocusPolicy(Qt.StrongFocus)

        if clicked:
            self.clicked.connect(clicked)

class GroupBoxLE(QGroupBox):
    # allows GroupBox to be clicked like a buttton
    
    clicked = Signal()

    def __init__(self, text, clicked=None, parent=None):
        super().__init__(text, parent)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)