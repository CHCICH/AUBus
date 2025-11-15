"""
A minimal PyQt5 GUI for AUBus implementing Login and Sign-up functionality.

UI design notes:
- Color palette: red (#cc0000), black, white
- Two tabs: Login and Sign Up
- Communicates with the project's TCP gateway (static_gateway.py) on port 9999.

Run:
    python gui.py

If PyQt5 is not installed: pip install PyQt5
"""

import sys
import socket
import json
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

GATEWAY_HOST = socket.gethostbyname(socket.gethostname())
GATEWAY_PORT = 9999


def send_gateway_request(payload, host=GATEWAY_HOST, port=GATEWAY_PORT, timeout=5.0):
    """Send a JSON payload to the static gateway and return parsed JSON response.
    Uses a short-lived TCP connection per request.
    Returns a dict on success or a dict with status '500' on error.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.send(json.dumps(payload).encode("utf-8"))
        resp_raw = s.recv(8192).decode("utf-8")
        try:
            resp = json.loads(resp_raw)
        except Exception:
            resp = {"status": "500", "message": "Invalid JSON response from gateway", "raw": resp_raw}
        # politely close
        try:
            s.send(json.dumps({"action": "quit"}).encode("utf-8"))
        except Exception:
            pass
        s.close()
        return resp
    except Exception as e:
        return {"status": "500", "message": f"Gateway connection error: {e}"}


class AUBusWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AUBus")
        self.resize(1000, 700)
        self.apply_styles()
        self.init_ui()

    def apply_styles(self):
        red = "#cc0000"
        dark = "#0f0f10"
        mid = "#1b1b1c"
        white = "#ffffff"
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {dark}, stop:1 {mid});
            }}
            
            QWidget {{
                background: transparent;
                color: {white};
                font-family: Arial;
                font-size: 16px;
            }}
            
            QTabWidget::pane {{
                border: 0;
                background: transparent;
                margin-top: 70px;
            }}
            
            QTabBar::tab {{
                background: rgba(255, 255, 255, 0.1);
                color: {white};
                padding: 25px 80px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                font-size: 20px;
                font-weight: bold;
                margin-right: 15px;
                border-radius: 15px 15px 0px 0px;
                margin-bottom: 0px;
                min-width: 120px;
            }}
            
            QTabBar::tab:selected {{
                background: white;
                color: {red};
                border: 2px solid white;
                border-bottom: none;
            }}
            
            QTabBar::tab:hover:!selected {{
                background: rgba(255, 255, 255, 0.2);
                border: 2px solid rgba(255, 255, 255, 0.5);
            }}
            
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            
            QScrollBar:vertical {{
                background: transparent;
                width: 14px;
                margin: 0px;
                border-radius: 7px;
            }}
            
            QScrollBar::handle:vertical {{
                background: rgba(204, 0, 0, 0.4);
                border-radius: 7px;
                min-height: 30px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: rgba(204, 0, 0, 0.6);
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            
            QLabel {{
                color: {white};
                font-size: 16px;
                padding: 5px;
            }}
            
            QLabel#title {{
                font-size: 32px;
                font-weight: bold;
                color: {red};
                margin-bottom: 20px;
            }}
            
            QLineEdit {{
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(255, 255, 255, 0.2);
                padding: 15px;
                color: {white};
                border-radius: 10px;
                font-size: 16px;
                min-height: 20px;
            }}
            
            QLineEdit:focus {{
                border: 2px solid {red};
                background: rgba(255, 255, 255, 0.08);
            }}
            
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {red}, stop:1 #a80000);
                color: {white};
                border-radius: 10px;
                padding: 15px 30px;
                font-weight: bold;
                font-size: 16px;
                min-width: 150px;
            }}
            
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e53939, stop:1 {red});
            }}
            
            QPushButton:pressed {{
                padding-top: 17px;
                padding-bottom: 13px;
            }}
            
            QCheckBox {{
                color: {white};
                font-size: 16px;
                spacing: 10px;
            }}
            
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.05);
            }}
            
            QCheckBox::indicator:checked {{
                background: {red};
                border: 2px solid {red};
            }}
        """)

    def init_ui(self):
        # Main container with padding
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(60, 60, 60, 60)
        
        tabs = QTabWidget()
        tabs.addTab(self.build_login_tab(), "Login")
        tabs.addTab(self.build_signup_tab(), "Sign Up")
        
        container_layout.addWidget(tabs)
        container.setLayout(container_layout)
        self.setCentralWidget(container)

    def build_login_tab(self):
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create content widget
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(120, 100, 120, 100)
        main_layout.setSpacing(20)
        
        # Title
        title = QLabel("AUBus — Login")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        main_layout.addSpacing(30)
        
        # Username
        username_label = QLabel("Username:")
        main_layout.addWidget(username_label)
        
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Enter your username")
        main_layout.addWidget(self.login_username)
        
        main_layout.addSpacing(20)
        
        # Password
        password_label = QLabel("Password:")
        main_layout.addWidget(password_label)
        
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Enter your password")
        self.login_password.setEchoMode(QLineEdit.Password)
        main_layout.addWidget(self.login_password)
        
        main_layout.addSpacing(30)
        
        # Button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.clicked.connect(self.on_login)
        main_layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)
        
        main_layout.addSpacing(20)
        
        # Message
        self.login_msg = QLabel("")
        self.login_msg.setAlignment(Qt.AlignCenter)
        self.login_msg.setWordWrap(True)
        main_layout.addWidget(self.login_msg)
        
        main_layout.addStretch()
        
        widget.setLayout(main_layout)
        scroll.setWidget(widget)
        return scroll

    def build_signup_tab(self):
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create content widget
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(120, 100, 120, 100)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("AUBus — Sign Up")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        main_layout.addSpacing(30)
        
        # Username
        username_label = QLabel("Username:")
        main_layout.addWidget(username_label)
        
        self.su_username = QLineEdit()
        self.su_username.setPlaceholderText("Choose a username")
        main_layout.addWidget(self.su_username)
        
        main_layout.addSpacing(15)
        
        # Password
        password_label = QLabel("Password:")
        main_layout.addWidget(password_label)
        
        self.su_password = QLineEdit()
        self.su_password.setPlaceholderText("Create a password")
        self.su_password.setEchoMode(QLineEdit.Password)
        main_layout.addWidget(self.su_password)
        
        main_layout.addSpacing(15)
        
        # Email
        email_label = QLabel("Email:")
        main_layout.addWidget(email_label)
        
        self.su_email = QLineEdit()
        self.su_email.setPlaceholderText("your.email@aub.edu.lb")
        main_layout.addWidget(self.su_email)
        
        main_layout.addSpacing(15)
        
        # AUB ID
        aubid_label = QLabel("AUB ID (optional):")
        main_layout.addWidget(aubid_label)
        
        self.su_aubid = QLineEdit()
        self.su_aubid.setPlaceholderText("e.g., 202012345")
        main_layout.addWidget(self.su_aubid)
        
        main_layout.addSpacing(15)
        
        # Checkbox
        self.su_isdriver = QCheckBox("I am a driver")
        main_layout.addWidget(self.su_isdriver)
        
        main_layout.addSpacing(30)
        
        # Button
        self.signup_btn = QPushButton("Create Account")
        self.signup_btn.clicked.connect(self.on_signup)
        main_layout.addWidget(self.signup_btn, alignment=Qt.AlignCenter)
        
        main_layout.addSpacing(20)
        
        # Message
        self.signup_msg = QLabel("")
        self.signup_msg.setAlignment(Qt.AlignCenter)
        self.signup_msg.setWordWrap(True)
        main_layout.addWidget(self.signup_msg)
        
        main_layout.addStretch()
        
        widget.setLayout(main_layout)
        scroll.setWidget(widget)
        return scroll

    def on_login(self):
        username = self.login_username.text().strip()
        password = self.login_password.text().strip()
        
        if not username or not password:
            self.login_msg.setText("Please enter username and password")
            return
            
        self.login_msg.setText("Connecting...")
        payload = {"action": "login", "userName": username, "password": password}
        resp = send_gateway_request(payload)
        self.login_msg.setText(f"{resp.get('status')}: {resp.get('message')}")
        
        if resp.get("status") == "200":
            email = resp.get("email")
            if email:
                QMessageBox.information(self, "Logged in", f"Authenticated — email: {email}")

    def on_signup(self):
        username = self.su_username.text().strip()
        password = self.su_password.text().strip()
        email = self.su_email.text().strip()
        aubid = self.su_aubid.text().strip() or None
        isdriver = self.su_isdriver.isChecked()
        
        if not username or not password or not email:
            self.signup_msg.setText("Please enter username, password and email")
            return
            
        self.signup_msg.setText("Connecting...")
        payload = {
            "action": "sign_up",
            "userName": username,
            "password": password,
            "email": email,
            "isDriver": isdriver,
            "aubID": aubid,
        }
        resp = send_gateway_request(payload)
        self.signup_msg.setText(f"{resp.get('status')}: {resp.get('message')}")
        
        if resp.get("status") == "201":
            data = resp.get("data", {})
            QMessageBox.information(self, "Account created", f"User created: {data.get('username')}\nEmail: {data.get('email')}")


def main():
    app = QApplication(sys.argv)
    win = AUBusWindow()
    win.showMaximized()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()