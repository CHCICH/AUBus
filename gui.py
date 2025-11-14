from PyQt5.QtWidgets import *
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import json
import sys

app = QApplication(sys.argv)
window = QWidget()
window.setMinimumSize(1000, 950)
window.resize(1100, 1000)
window.setWindowTitle("AUB RideShare")

# AUB themed stylesheet with larger fonts and proper spacing
window.setStyleSheet("""
    QWidget {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 #1a1a1a, stop:0.5 #2d2d2d, stop:1 #1a1a1a
        );
        font-family: 'Segoe UI', Arial, sans-serif;
    }

    QTabWidget::pane {
        border: none;
        background: white;
        border-radius: 20px;
        margin-top: 50px;
    }

    QTabBar {
        background: transparent;
        qproperty-alignment: AlignCenter;
    }

    QTabBar::tab {
        background: rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.7);
        padding: 18px 70px;
        font-weight: 700;
        font-size: 20px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        margin-right: 15px;
        border-radius: 15px 15px 0px 0px;
        margin-bottom: -2px;
    }

    QTabBar::tab:selected {
        background: white;
        color: #8B0000;
        border: 2px solid white;
        border-bottom: none;
    }

    QTabBar::tab:hover:!selected {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        border: 2px solid rgba(255, 255, 255, 0.5);
    }

    QTabBar::tab:hover:!selected {
        color: white;
    }

    QFrame {
        background-color: transparent;
        border-radius: 0px;
        padding: 0px;
        border: none;
    }

    QScrollArea {
        background: white;
        border: none;
    }

    QScrollBar:vertical {
        background: transparent;
        width: 12px;
        margin: 0px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical {
        background: rgba(139, 0, 0, 0.3);
        border-radius: 6px;
        min-height: 30px;
    }

    QScrollBar::handle:vertical:hover {
        background: rgba(139, 0, 0, 0.5);
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }

    QLabel {
        color: #1a1a1a;
        font-size: 16px;
        font-weight: 500;
        border: none;
        background: transparent;
        padding: 5px 0px;
    }

    QLabel#header {
        font-size: 36px;
        font-weight: 700;
        color: #8B0000;
        margin-bottom: 15px;
        padding: 10px;
    }

    QLabel#subtitle {
        font-size: 16px;
        color: #666666;
        font-weight: 400;
        margin-bottom: 30px;
        padding: 5px;
    }

    QLineEdit {
        background-color: #f8f8f8;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px 20px;
        color: #1a1a1a;
        font-size: 16px;
        selection-background-color: #8B0000;
        selection-color: white;
    }

    QLineEdit:focus {
        border: 2px solid #8B0000;
        background-color: white;
    }

    QPushButton {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #8B0000, stop:1 #B22222
        );
        color: white;
        border-radius: 12px;
        padding: 16px 24px;
        font-weight: 600;
        font-size: 16px;
        border: none;
    }

    QPushButton:hover {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #A00000, stop:1 #C93030
        );
    }

    QPushButton:pressed {
        padding-top: 18px;
        padding-bottom: 14px;
    }

    QPushButton#show_btn {
        background: #2d2d2d;
        color: white;
        padding: 12px 20px;
        font-size: 14px;
    }

    QPushButton#show_btn:hover {
        background: #3d3d3d;
    }

    QComboBox {
        background-color: #f8f8f8;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px 20px;
        color: #1a1a1a;
        font-size: 16px;
    }

    QComboBox:focus {
        border: 2px solid #8B0000;
    }

    QComboBox::drop-down {
        border: none;
        width: 35px;
    }

    QComboBox QAbstractItemView {
        background-color: white;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        selection-background-color: #8B0000;
        selection-color: white;
        padding: 8px;
        font-size: 16px;
    }

    QLabel#error {
        color: #8B0000;
        font-weight: 600;
        font-size: 15px;
        padding: 15px;
        background: #ffe6e6;
        border-radius: 10px;
    }

    QLabel#success {
        color: #1a5f1a;
        font-weight: 600;
        font-size: 15px;
        padding: 15px;
        background: #e6f5e6;
        border-radius: 10px;
    }
""")

def create_input_group(label_text, placeholder, is_password=False):
    """Helper function to create input groups with proper sizing"""
    container = QVBoxLayout()
    container.setSpacing(12)
    
    label = QLabel(label_text)
    label.setFont(QFont("Segoe UI", 16, QFont.Medium))
    container.addWidget(label)
    
    h_layout = QHBoxLayout()
    h_layout.setSpacing(15)
    
    input_box = QLineEdit()
    input_box.setPlaceholderText(placeholder)
    input_box.setFont(QFont("Segoe UI", 15))
    input_box.setMinimumHeight(50)
    
    if is_password:
        input_box.setEchoMode(QLineEdit.Password)
        show_btn = QPushButton("Show")
        show_btn.setObjectName("show_btn")
        show_btn.setFixedSize(100, 50)
        show_btn.setFont(QFont("Segoe UI", 13))
        
        def toggle_password():
            if input_box.echoMode() == QLineEdit.Normal:
                input_box.setEchoMode(QLineEdit.Password)
                show_btn.setText("Show")
            else:
                input_box.setEchoMode(QLineEdit.Normal)
                show_btn.setText("Hide")
        
        show_btn.clicked.connect(toggle_password)
        h_layout.addWidget(input_box, stretch=1)
        h_layout.addWidget(show_btn, stretch=0)
    else:
        h_layout.addWidget(input_box)
    
    container.addLayout(h_layout)
    return container, input_box

# Create tabs with centered alignment
tabs = QTabWidget()
tabs.setTabPosition(QTabWidget.North)
tabs.setDocumentMode(True)

# ==================== LOGIN TAB ====================
login_tab = QWidget()
login_scroll = QScrollArea()
login_scroll.setWidgetResizable(True)
login_scroll.setFrameShape(QFrame.NoFrame)
login_scroll.setStyleSheet("background: white;")

login_content = QWidget()
login_content.setStyleSheet("background: white;")
login_main = QVBoxLayout()
login_main.setContentsMargins(80, 80, 80, 60)

login_layout = QVBoxLayout()
login_layout.setSpacing(25)

# Header
header = QLabel("Welcome Back!")
header.setObjectName("header")
header.setAlignment(Qt.AlignCenter)
login_layout.addWidget(header)

subtitle = QLabel("Sign in to continue to AUB RideShare")
subtitle.setObjectName("subtitle")
subtitle.setAlignment(Qt.AlignCenter)
login_layout.addWidget(subtitle)

login_layout.addSpacing(20)

# Username input
username_layout, login_user_box = create_input_group(
    "Username", 
    "Enter your AUB username"
)
login_layout.addLayout(username_layout)

# Password input
password_layout, login_pass_box = create_input_group(
    "Password", 
    "Enter your password",
    is_password=True
)
login_layout.addLayout(password_layout)

login_layout.addSpacing(10)

# Error label
login_error_lbl = QLabel("")
login_error_lbl.setObjectName("error")
login_error_lbl.hide()
login_layout.addWidget(login_error_lbl)

# Login button
def handle_login():
    pass  # Will implement later

login_btn = QPushButton("Sign In")
login_btn.clicked.connect(handle_login)
login_btn.setMinimumHeight(55)
login_btn.setFont(QFont("Segoe UI", 16, QFont.Bold))
login_layout.addWidget(login_btn)

login_main.addLayout(login_layout)
login_main.addStretch()
login_content.setLayout(login_main)
login_scroll.setWidget(login_content)

login_tab_layout = QVBoxLayout()
login_tab_layout.setContentsMargins(0, 0, 0, 0)
login_tab_layout.addWidget(login_scroll)
login_tab.setLayout(login_tab_layout)

# ==================== SIGNUP TAB ====================
signup_tab = QWidget()
signup_scroll = QScrollArea()
signup_scroll.setWidgetResizable(True)
signup_scroll.setFrameShape(QFrame.NoFrame)
signup_scroll.setStyleSheet("background: white;")

signup_content = QWidget()
signup_content.setStyleSheet("background: white;")
signup_main = QVBoxLayout()
signup_main.setContentsMargins(80, 80, 80, 60)

signup_layout = QVBoxLayout()
signup_layout.setSpacing(20)

# Header
header2 = QLabel("Create Account")
header2.setObjectName("header")
header2.setAlignment(Qt.AlignCenter)
signup_layout.addWidget(header2)

subtitle2 = QLabel("Join the AUB RideShare community")
subtitle2.setObjectName("subtitle")
subtitle2.setAlignment(Qt.AlignCenter)
signup_layout.addWidget(subtitle2)

signup_layout.addSpacing(15)

# Full Name
name_layout, signup_name_box = create_input_group(
    "Full Name", 
    "John Doe"
)
signup_layout.addLayout(name_layout)

# Email
email_layout, signup_email_box = create_input_group(
    "AUB Email", 
    "username@mail.aub.edu"
)
signup_layout.addLayout(email_layout)

# Username
user_layout, signup_user_box = create_input_group(
    "Username", 
    "Choose a username"
)
signup_layout.addLayout(user_layout)

# Password
pass_layout, signup_pass_box = create_input_group(
    "Password", 
    "Create a strong password",
    is_password=True
)
signup_layout.addLayout(pass_layout)

# Role and Area in a grid
grid_layout = QHBoxLayout()
grid_layout.setSpacing(20)

# Role
role_v = QVBoxLayout()
role_v.setSpacing(12)
role_lbl = QLabel("Role")
role_lbl.setFont(QFont("Segoe UI", 16, QFont.Medium))
signup_role_combo = QComboBox()
signup_role_combo.addItems(["Passenger", "Driver"])
signup_role_combo.setMinimumHeight(50)
signup_role_combo.setFont(QFont("Segoe UI", 15))
role_v.addWidget(role_lbl)
role_v.addWidget(signup_role_combo)
grid_layout.addLayout(role_v, stretch=1)

# Area
area_v = QVBoxLayout()
area_v.setSpacing(12)
area_lbl = QLabel("Area")
area_lbl.setFont(QFont("Segoe UI", 16, QFont.Medium))
signup_area_combo = QComboBox()
signup_area_combo.addItems([
    "Beirut", "Dahyeh", "Haret Hreik", "Khaldeh", 
    "Jbeil", "Baalbek", "Choueifat", "Baabda", 
    "Mansourieh", "Nabatieh", "Tyre", "Tripoli", "Hermel"
])
signup_area_combo.setMinimumHeight(50)
signup_area_combo.setFont(QFont("Segoe UI", 15))
area_v.addWidget(area_lbl)
area_v.addWidget(signup_area_combo)
grid_layout.addLayout(area_v, stretch=1)

signup_layout.addLayout(grid_layout)

signup_layout.addSpacing(10)

# Error label
signup_error_lbl = QLabel("")
signup_error_lbl.setObjectName("error")
signup_error_lbl.hide()
signup_layout.addWidget(signup_error_lbl)

# Signup button
def handle_signup():
    pass  # Will implement later

signup_btn = QPushButton("Create Account")
signup_btn.clicked.connect(handle_signup)
signup_btn.setMinimumHeight(55)
signup_btn.setFont(QFont("Segoe UI", 16, QFont.Bold))
signup_layout.addWidget(signup_btn)

signup_main.addLayout(signup_layout)
signup_main.addStretch()
signup_content.setLayout(signup_main)
signup_scroll.setWidget(signup_content)

signup_tab_layout = QVBoxLayout()
signup_tab_layout.setContentsMargins(0, 0, 0, 0)
signup_tab_layout.addWidget(signup_scroll)
signup_tab.setLayout(signup_tab_layout)

# Add tabs
tabs.addTab(login_tab, "Sign In")
tabs.addTab(signup_tab, "Sign Up")

# Main window layout
main = QVBoxLayout()
main.addWidget(tabs)
main.setContentsMargins(50, 50, 50, 50)
window.setLayout(main)

window.show()
sys.exit(app.exec_())