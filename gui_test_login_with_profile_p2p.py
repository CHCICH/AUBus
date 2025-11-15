import sys
import socket
import json
import threading
from datetime import datetime
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QTabWidget, QListWidget, QComboBox,
                             QMessageBox, QGroupBox, QFormLayout, QCheckBox,
                             QTimeEdit, QListWidgetItem, QScrollArea, QDialog)
from PyQt5.QtCore import Qt, QTime, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QIntValidator 
from PyQt5.QtWebEngineWidgets import QWebEngineView
import os

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    # Doesn't need to actually connect
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
finally:
    s.close()

# Configuration
STATIC_SERVER_HOST = local_ip
STATIC_SERVER_PORT = 9999
RIDE_SERVER_HOST = local_ip
RIDE_SERVER_PORT = 9000
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_API_KEY_HERE")

class SignalEmitter(QObject):
    """Helper class for thread-safe signals"""
    message_received = pyqtSignal(str)
    candidates_received = pyqtSignal(list)

class RideShareApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_data = None
        self.socket_connection = None
        self.signal_emitter = SignalEmitter()
        self.signal_emitter.message_received.connect(self.show_message)
        self.signal_emitter.candidates_received.connect(self.display_candidates)
        self.current_request_id = None
        self.current_candidates = []
        self.selected_car_id = None 
        self.selected_ride_id = None

        self.setStyleSheet("""
            QMainWindow, QWidget {
                font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial, sans-serif;
                font-size: 13px;
                color: #2c3e50;
            }
            
            #header {
                font-size: 22px;
                font-weight: bold;
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0066cc, stop:0.5 #0052a3, stop:1 #003f7d);
                padding: 16px;
                border-radius: 10px;
                margin-bottom: 8px;
            }
            
            #userInfo {
                font-size: 14px;
                font-weight: 600;
                color: #0066cc;
                background: #e3f2fd;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            
            QGroupBox {
                font-weight: 600;
                border: 2px solid #b3d9ff;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background: #f8fbff;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 4px 8px;
                background: white;
                border-radius: 4px;
            }
            
            QLineEdit, QTimeEdit, QComboBox {
                padding: 8px 10px;
                border: 2px solid #cfe6ff;
                border-radius: 6px;
                background: white;
                selection-background-color: #0066cc;
            }
            
            QLineEdit:focus, QTimeEdit:focus, QComboBox:focus {
                border: 2px solid #0066cc;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0077cc, stop:1 #0066bb);
                color: white;
                padding: 10px 16px;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                min-height: 28px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0088dd, stop:1 #0077cc);
            }
            
            QPushButton:pressed {
                background: #0055aa;
            }
            
            QPushButton:disabled {
                background: #cccccc;
                color: #666666;
            }
            
            QListWidget {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            
            QListWidget::item:selected {
                background: #e3f2fd;
                color: #0066cc;
            }
            
            QListWidget::item:hover {
                background: #f5f5f5;
            }
            
            QTabWidget::pane {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            
            QTabBar::tab {
                background: #f0f0f0;
                padding: 10px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            
            QTabBar::tab:selected {
                background: white;
                color: #0066cc;
                font-weight: 600;
            }
            
            QTabBar::tab:hover:!selected {
                background: #e8e8e8;
            }
            
            QCheckBox {
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #cfe6ff;
                border-radius: 4px;
                background: white;
            }
            
            QCheckBox::indicator:checked {
                background: #0066cc;
                border-color: #0066cc;
            }
            
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background: #fafafa;
                padding: 6px;
            }
            
            QStatusBar {
                background: #f8f9fa;
                color: #666;
                font-size: 12px;
            }
            
            QFrame {
                background: white;
            }
        """)
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('AUB Ride Share')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs
        self.create_login_tab()
        self.create_driver_tab()
        self.create_passenger_tab()
        self.create_profile_tab()
        self.create_map_tab()
        
        # Initially disable driver and passenger tabs
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)
        self.tabs.setTabEnabled(4, False)
        
        self.show()
    
    def create_login_tab(self):
        """Create login/signup tab"""
        login_widget = QWidget()
        layout = QVBoxLayout(login_widget)
        
        # Title
        title = QLabel("AUB Ride Share System")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 20, QFont.Bold))
        layout.addWidget(title)
        
        # Login Section
        login_group = QGroupBox("Login")
        login_form = QFormLayout()
        
        self.login_username = QLineEdit()
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)
        
        login_form.addRow("Username:", self.login_username)
        login_form.addRow("Password:", self.login_password)
        
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.handle_login)
        login_form.addRow(login_btn)
        
        login_group.setLayout(login_form)
        layout.addWidget(login_group)
        
        # Signup Section
        signup_group = QGroupBox("Sign Up")
        signup_form = QFormLayout()
        
        self.signup_username = QLineEdit()
        self.signup_password = QLineEdit()
        self.signup_password.setEchoMode(QLineEdit.Password)
        self.signup_email = QLineEdit()
        self.signup_email.setPlaceholderText("example@mail.aub.edu")
        self.signup_aub_id = QLineEdit()
        self.signup_aub_id.setPlaceholderText("202500049")
        self.signup_zone = QLineEdit()
        self.signup_zone.setPlaceholderText("Hamra, Beirut")
        self.signup_is_driver = QCheckBox("I am a driver")
        
        signup_form.addRow("Username:", self.signup_username)
        signup_form.addRow("Password:", self.signup_password)
        signup_form.addRow("Email:", self.signup_email)
        signup_form.addRow("AUB ID:", self.signup_aub_id)
        signup_form.addRow("Zone:", self.signup_zone)
        signup_form.addRow("", self.signup_is_driver)
        
        signup_btn = QPushButton("Sign Up")
        signup_btn.clicked.connect(self.handle_signup)
        signup_form.addRow(signup_btn)
        
        signup_group.setLayout(signup_form)
        layout.addWidget(signup_group)
        
        layout.addStretch()
        self.tabs.addTab(login_widget, "Login/Signup")
    
    def create_driver_tab(self):
        """Create driver interface tab"""
        driver_widget = QWidget()
        layout = QVBoxLayout(driver_widget)
        
        # User info
        self.driver_info_label = QLabel("Driver Dashboard")
        self.driver_info_label.setFont(QFont('Arial', 16, QFont.Bold))
        layout.addWidget(self.driver_info_label)
        
        # Add Ride Section
        add_ride_group = QGroupBox("Add New Ride")
        add_ride_form = QFormLayout()
        
        self.driver_area = QLineEdit()
        self.driver_area.setPlaceholderText("e.g., Hamra, Beirut")
        self.driver_to_aub_time = QTimeEdit()
        self.driver_to_aub_time.setDisplayFormat("HH:mm")
        self.driver_to_aub_time.setTime(QTime(8, 0))
        self.driver_from_aub_time = QTimeEdit()
        self.driver_from_aub_time.setDisplayFormat("HH:mm")
        self.driver_from_aub_time.setTime(QTime(16, 0))
        self.driver_p2p_port = QLineEdit()
        self.driver_p2p_port.setText("50001")
        
        add_ride_form.addRow("Area/Location:", self.driver_area)
        add_ride_form.addRow("To AUB Time:", self.driver_to_aub_time)
        add_ride_form.addRow("From AUB Time:", self.driver_from_aub_time)
        add_ride_form.addRow("P2P Port:", self.driver_p2p_port)
        
        add_ride_btn = QPushButton("Add Ride")
        add_ride_btn.clicked.connect(self.handle_add_ride)
        add_ride_form.addRow(add_ride_btn)
        
        add_ride_group.setLayout(add_ride_form)
        layout.addWidget(add_ride_group)
        
        # Pending Requests Section
        requests_group = QGroupBox("Pending Ride Requests")
        requests_layout = QVBoxLayout()
        
        refresh_btn = QPushButton("Refresh Requests")
        refresh_btn.clicked.connect(self.refresh_requests)
        requests_layout.addWidget(refresh_btn)
        
        self.requests_list = QListWidget()
        self.requests_list.itemDoubleClicked.connect(self.accept_ride_request)
        requests_layout.addWidget(self.requests_list)
        
        requests_group.setLayout(requests_layout)
        layout.addWidget(requests_group)
        
        # Instructions
        info_label = QLabel("Double-click a request to accept it")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        self.tabs.addTab(driver_widget, "Driver")
    
    def create_passenger_tab(self):
        """Create passenger interface tab"""
        passenger_widget = QWidget()
        layout = QVBoxLayout(passenger_widget)
        
        # User info
        self.passenger_info_label = QLabel("Passenger Dashboard")
        self.passenger_info_label.setFont(QFont('Arial', 16, QFont.Bold))
        layout.addWidget(self.passenger_info_label)
        
        # Request Ride Section
        request_group = QGroupBox("Request a Ride")
        request_form = QFormLayout()
        
        self.passenger_area = QLineEdit()
        self.passenger_area.setPlaceholderText("e.g., Hamra, Beirut")
        self.passenger_time = QTimeEdit()
        self.passenger_time.setDisplayFormat("HH:mm")
        self.passenger_time.setTime(QTime(8, 15))
        self.passenger_direction = QComboBox()
        self.passenger_direction.addItems(["to_aub", "from_aub"])
        self.passenger_p2p_port = QLineEdit()
        self.passenger_p2p_port.setText("50002")
        
        request_form.addRow("Area/Location:", self.passenger_area)
        request_form.addRow("Time:", self.passenger_time)
        request_form.addRow("Direction:", self.passenger_direction)
        request_form.addRow("P2P Port:", self.passenger_p2p_port)
        
        request_btn = QPushButton("Request Ride")
        request_btn.clicked.connect(self.handle_request_ride)
        request_form.addRow(request_btn)
        
        request_group.setLayout(request_form)
        layout.addWidget(request_group)
        
        # Available Drivers Section
        drivers_group = QGroupBox("Available Drivers")
        drivers_layout = QVBoxLayout()
        
        self.drivers_list = QListWidget()
        self.drivers_list.itemDoubleClicked.connect(self.accept_driver)
        drivers_layout.addWidget(self.drivers_list)
        
        drivers_group.setLayout(drivers_layout)
        layout.addWidget(drivers_group)
        
        # Instructions
        info_label = QLabel("Double-click a driver to accept their ride")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        self.tabs.addTab(passenger_widget, "Passenger")
    
    def create_map_tab(self):
        """Create map view tab with Google Maps"""
        map_widget = QWidget()
        layout = QVBoxLayout(map_widget)
        
        # Map title
        title = QLabel("Map View")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        layout.addWidget(title)
        
        # Web view for Google Maps
        self.map_view = QWebEngineView()
        self.load_map()
        layout.addWidget(self.map_view)
        
        # Refresh button
        refresh_map_btn = QPushButton("Refresh Map")
        refresh_map_btn.clicked.connect(self.load_map)
        layout.addWidget(refresh_map_btn)
        
        self.tabs.addTab(map_widget, "Map")
    
    def load_map(self):
        """Load Google Maps in the web view"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AUB Ride Share Map</title>
            <style>
                #map {{
                    height: 100%;
                    width: 100%;
                }}
                html, body {{
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                function initMap() {{
                    // Center on AUB
                    var aub = {{lat: 33.8993, lng: 35.4839}};
                    var map = new google.maps.Map(document.getElementById('map'), {{
                        zoom: 13,
                        center: aub
                    }});
                    
                    // Add marker for AUB
                    var marker = new google.maps.Marker({{
                        position: aub,
                        map: map,
                        title: 'American University of Beirut'
                    }});
                }}
            </script>
            <script async defer
                src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap">
            </script>
        </body>
        </html>
        """
        self.map_view.setHtml(html_content)
    
    def send_static_request(self, request_data):
        """Send request to static gateway server"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((STATIC_SERVER_HOST, STATIC_SERVER_PORT))
            s.send(json.dumps(request_data).encode('utf-8'))
            response = s.recv(8192).decode('utf-8')
            s.close()
            return json.loads(response)
        except Exception as e:
            return {"status": "500", "message": f"Connection error: {str(e)}"}
    
    def send_ride_request(self, conn, msg):
        """Send request to ride server"""
        try:
            data = json.dumps(msg).encode()
            conn.sendall(len(data).to_bytes(4, 'big') + data)
            
            raw_len = conn.recv(4)
            if not raw_len:
                return None
            length = int.from_bytes(raw_len, 'big')
            data = b''
            while len(data) < length:
                more = conn.recv(length - len(data))
                if not more:
                    return None
                data += more
            return json.loads(data.decode())
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def handle_login(self):
        """Handle login button click"""
        username = self.login_username.text()
        password = self.login_password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter username and password")
            return
        
        request = {
            "action": "login",
            "userName": username,
            "password": password
        }
        
        response = self.send_static_request(request)
        
        data_login = response.get("data")
        print(response)
        if response.get("status") == "200":
            self.user_data = {
                "username": username,
                "email": data_login.get("email"),
                "userID": data_login.get("userID")
            }

            print(data_login.get("userID"))
            
            # Get user info to check if driver
            user_info_req = {
                "action": "update_personal_info",
                "type_of_connection": "give_user_personal_informations",
                "userID": self.user_data["userID"]
            }
            user_info_resp = self.send_static_request(user_info_req)
            
            print(user_info_resp)
            if user_info_resp.get("status") == "200":
                data = user_info_resp.get("data")
                self.user_data["is_driver"] = data.get("isDriver")
            
            QMessageBox.information(self, "Success", f"Welcome, {username}!")
            
            # Enable appropriate tabs
            if self.user_data.get("is_driver"):
                self.tabs.setTabEnabled(1, True)
                self.driver_info_label.setText(f"Driver: {username}")
            else:
                self.tabs.setTabEnabled(2, True)
                self.passenger_info_label.setText(f"Passenger: {username}")
            
            self.tabs.setTabEnabled(0, False)
            self.tabs.setTabEnabled(3,True)
            self.tabs.setTabEnabled(4, True)
            self.tabs.setCurrentIndex(1 if self.user_data.get("is_driver") else 2)
            self.refresh_profile_data()
        else:
            QMessageBox.warning(self, "Login Failed", response.get("message", "Unknown error"))
    
    def handle_signup(self):
        """Handle signup button click"""
        username = self.signup_username.text()
        password = self.signup_password.text()
        email = self.signup_email.text()
        aub_id = self.signup_aub_id.text()
        zone = self.signup_zone.text()
        is_driver = self.signup_is_driver.isChecked()
        
        if not all([username, password, email, aub_id, zone]):
            QMessageBox.warning(self, "Input Error", "Please fill all fields")
            return
        
        request = {
            "action": "sign_up",
            "userName": username,
            "password": password,
            "email": email,
            "aubID": aub_id,
            "zone": zone,
            "isDriver": is_driver
        }
        
        response = self.send_static_request(request)
        
        if response.get("status") == "201":
            QMessageBox.information(self, "Success", "Account created successfully! Please login.")
            # Clear signup fields
            self.signup_username.clear()
            self.signup_password.clear()
            self.signup_email.clear()
            self.signup_aub_id.clear()
            self.signup_zone.clear()
            self.signup_is_driver.setChecked(False)
        else:
            QMessageBox.warning(self, "Signup Failed", response.get("message", "Unknown error"))
    
    def handle_add_ride(self):
        """Handle add ride button click for drivers"""
        if not self.user_data:
            QMessageBox.warning(self, "Error", "Please login first")
            return
        
        area = self.driver_area.text()
        to_aub_time = self.driver_to_aub_time.time().toString("HH:mm")
        from_aub_time = self.driver_from_aub_time.time().toString("HH:mm")
        p2p_port = int(self.driver_p2p_port.text())
        
        if not area:
            QMessageBox.warning(self, "Input Error", "Please enter area/location")
            return
        
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((RIDE_SERVER_HOST, RIDE_SERVER_PORT))
            
            msg = {
                "type": "ADD_RIDE",
                "payload": {
                    "username": self.user_data["username"],
                    "area": area,
                    "to_aub_time": to_aub_time,
                    "from_aub_time": from_aub_time,
                    "p2p_port": p2p_port
                }
            }
            
            response = self.send_ride_request(conn, msg)
            conn.close()
            
            if response and response.get("type") == "ADD_RIDE_RESPONSE":
                payload = response.get("payload", {})
                if payload.get("status") == "OK":
                    QMessageBox.information(self, "Success", "Ride added successfully!")
                    self.driver_area.clear()
                else:
                    QMessageBox.warning(self, "Error", payload.get("message", "Failed to add ride"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to ride server: {str(e)}")
    
    def handle_request_ride(self):
        """Handle request ride button click for passengers"""
        if not self.user_data:
            QMessageBox.warning(self, "Error", "Please login first")
            return
        
        area = self.passenger_area.text()
        time = self.passenger_time.time().toString("HH:mm")
        direction = self.passenger_direction.currentText()
        
        if not area:
            QMessageBox.warning(self, "Input Error", "Please enter area/location")
            return
        
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((RIDE_SERVER_HOST, RIDE_SERVER_PORT))
            
            msg = {
                "type": "REQUEST_RIDE",
                "payload": {
                    "passenger": self.user_data["username"],
                    "area": area,
                    "time": time,
                    "direction": direction,
                    "min_rating": 0
                }
            }
            
            response = self.send_ride_request(conn, msg)
            conn.close()
            
            if response and response.get("type") == "REQUEST_RIDE_RESPONSE":
                payload = response.get("payload", {})
                if payload.get("status") == "OK":
                    candidates = payload.get("candidates", [])
                    self.current_request_id = payload.get("request_id")
                    self.display_candidates(candidates)
                    QMessageBox.information(self, "Success", 
                                          f"Found {len(candidates)} available drivers!")
                else:
                    QMessageBox.warning(self, "Error", payload.get("message", "No drivers found"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to ride server: {str(e)}")
    
    def display_candidates(self, candidates):
        """Display available drivers in the list"""
        self.drivers_list.clear()
        self.current_candidates = candidates
        
        for candidate in candidates:
            driver = candidate.get("driver")
            to_aub = candidate.get("to_aub_time", "N/A")
            from_aub = candidate.get("from_aub_time", "N/A")
            
            item_text = f"Driver: {driver} | To AUB: {to_aub} | From AUB: {from_aub}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, candidate)
            self.drivers_list.addItem(item)
    
    def accept_driver(self, item):
        """Handle accepting a driver"""
        candidate = item.data(Qt.UserRole)
        driver = candidate.get("driver")
        
        reply = QMessageBox.question(self, "Confirm", 
                                     f"Accept ride from {driver}?",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.connect((RIDE_SERVER_HOST, RIDE_SERVER_PORT))
                
                msg = {
                    "type": "ACCEPT_RIDE",
                    "payload": {
                        "request_id": self.current_request_id,
                        "driver": driver
                    }
                }
                
                response = self.send_ride_request(conn, msg)
                conn.close()
                
                if response and response.get("type") == "ACCEPT_RIDE_RESPONSE":
                    payload = response.get("payload", {})
                    if payload.get("status") == "OK":
                        p2p_info = payload.get("p2p_info", {})
                        msg = f"Ride accepted!\nDriver: {driver}\n"
                        if p2p_info:
                            msg += f"IP: {p2p_info.get('ip')}\nPort: {p2p_info.get('p2p_port')}"
                        QMessageBox.information(self, "Success", msg)
                    else:
                        QMessageBox.warning(self, "Error", payload.get("message", "Failed to accept"))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Connection error: {str(e)}")
    
    def refresh_requests(self):
        """Refresh pending ride requests for drivers"""
        # This would need to be implemented in the backend
        # For now, show a placeholder message
        QMessageBox.information(self, "Info", "Request refresh feature coming soon!")
    
    def accept_ride_request(self, item):
        """Handle accepting a ride request (driver side)"""
        # This would need backend support for drivers to see and accept requests
        QMessageBox.information(self, "Info", "Accept request feature coming soon!")
    
    def show_message(self, message):
        """Show message in message box (thread-safe)"""
        QMessageBox.information(self, "Message", message)

    def create_profile_tab(self):
        """Create user profile tab"""
        profile_widget = QWidget()
        layout = QVBoxLayout(profile_widget)
        
        # Title
        title = QLabel("My Profile")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 20, QFont.Bold))
        layout.addWidget(title)
        
        # Create scroll area for better layout
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # User Information Section
        user_info_group = QGroupBox("Personal Information")
        user_info_layout = QFormLayout()
        
        # Display fields (read-only)
        self.profile_username = QLabel("Not loaded")
        self.profile_email = QLabel("Not loaded")
        self.profile_role = QLabel("Not loaded")
        self.profile_aub_id = QLabel("Not loaded")
        self.profile_zone = QLabel("Not loaded")
        self.profile_rating = QLabel("Not loaded")
        
        user_info_layout.addRow("Username:", self.profile_username)
        user_info_layout.addRow("Email:", self.profile_email)
        user_info_layout.addRow("Role:", self.profile_role)
        user_info_layout.addRow("AUB ID:", self.profile_aub_id)
        user_info_layout.addRow("Zone:", self.profile_zone)
        user_info_layout.addRow("Rating:", self.profile_rating)
        
        user_info_group.setLayout(user_info_layout)
        scroll_layout.addWidget(user_info_group)
        
        # Driver-Specific Section (initially hidden)
        self.driver_section = QGroupBox("Driver Information")
        driver_layout = QVBoxLayout()
        
        # My Rides section
        rides_label = QLabel("My Rides:")
        driver_layout.addWidget(rides_label)
        
        self.my_rides_list = QListWidget()
        driver_layout.addWidget(self.my_rides_list)
        
        refresh_rides_btn = QPushButton("Refresh My Rides")
        refresh_rides_btn.clicked.connect(self.refresh_my_rides)
        driver_layout.addWidget(refresh_rides_btn)
        
        self.driver_section.setLayout(driver_layout)
        self.driver_section.setVisible(False)  # Hidden by default
        scroll_layout.addWidget(self.driver_section)
        
        # Passenger-Specific Section
        self.passenger_section = QGroupBox("Passenger Information")
        passenger_layout = QVBoxLayout()
        
        # Ride History
        history_label = QLabel("Ride History:")
        passenger_layout.addWidget(history_label)
        
        self.ride_history_list = QListWidget()
        passenger_layout.addWidget(self.ride_history_list)
        
        refresh_history_btn = QPushButton("Refresh History")
        refresh_history_btn.clicked.connect(self.refresh_ride_history)
        passenger_layout.addWidget(refresh_history_btn)
        
        self.passenger_section.setLayout(passenger_layout)
        scroll_layout.addWidget(self.passenger_section)
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        
        refresh_profile_btn = QPushButton("Refresh Profile")
        refresh_profile_btn.clicked.connect(self.refresh_profile_data)
        buttons_layout.addWidget(refresh_profile_btn)
        
        edit_profile_btn = QPushButton("Edit Profile")
        edit_profile_btn.clicked.connect(self.edit_profile)
        buttons_layout.addWidget(edit_profile_btn)
        
        scroll_layout.addLayout(buttons_layout)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self.tabs.addTab(profile_widget, "Profile")

    def refresh_profile_data(self):
        """Refresh all profile data"""
        if not self.user_data:
            QMessageBox.warning(self, "Error", "Please login first")
            return
        
        # Get user personal information
        user_info_req = {
            "action": "update_personal_info",
            "type_of_connection": "give_user_personal_informations", 
            "userID": self.user_data["userID"]
        }
        
        print(self.user_data["userID"])
        response = self.send_static_request(user_info_req)
        
        print(response)

        is_driver = False
        if response.get("status") == "200":
            data = response.get("data", {})
            self.profile_username.setText(data.get("username", "N/A"))
            self.profile_email.setText(data.get("email", "N/A"))
            self.profile_aub_id.setText(str(data.get("aubID", "N/A")))
            
            is_driver = data.get("isDriver", False)
            self.profile_role.setText("Driver" if is_driver else "Passenger")
            
            # Show/hide role-specific sections
            self.driver_section.setVisible(is_driver)
            self.passenger_section.setVisible(not is_driver)
        
        # Get user rating
        rating_req = {
            "action": "update_personal_info", 
            "type_of_connection": "get_rating",
            "userID": self.user_data["userID"]
        }
        
        rating_response = self.send_static_request(rating_req)
        if rating_response.get("status") == "200":
            avg_score = rating_response.get("average_score", 0)
            self.profile_rating.setText(f"{avg_score:.1f}")

        zone_req = {
            "action": "update_personal_info", 
            "type_of_connection": "get_zone",
            "userID": self.user_data["userID"]
        }
        
        zone_response = self.send_static_request(zone_req)
        zone_name = zone_response.get('data')
        self.profile_zone.setText(zone_name.get('zoneName', "N/A"))
        
        # Refresh role-specific data
        if is_driver:
            self.refresh_my_rides()
        else:
            self.refresh_ride_history()

    def refresh_my_rides(self):
        """Refresh driver's rides"""
        if not self.user_data:
            return
        
        rides_req = {
            "action": "update_personal_info",
            "type_of_connection": "give_all_rides",
            "userID": self.user_data["userID"]
        }
        
        response = self.send_static_request(rides_req)
        self.my_rides_list.clear()
        
        if response.get("status") == "200":
            rides = response.get("data", [])
            for ride in rides:
                item_text = f"Ride {ride.get('rideID', '')} - From {ride.get('sourceID', '')} to {ride.get('destinationID', '')}"
                self.my_rides_list.addItem(item_text)

    def refresh_ride_history(self):
        """Refresh passenger's ride history"""
        # You'll need to implement this endpoint in your backend
        self.ride_history_list.clear()
        self.ride_history_list.addItem("Ride history feature coming soon!")
        # Implementation would be similar to refresh_my_rides but for passenger history

    def edit_profile(self):
        """Open profile editing dialog based on user role"""
        if not self.user_data:
            QMessageBox.warning(self, "Error", "Please login first")
            return
        
        # Create editing dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Profile")
        dialog.setModal(True)
        
        if self.user_data.get("is_driver"):
            dialog.resize(600, 700)  # Larger for driver
            self.create_driver_edit_dialog(dialog)
        else:
            dialog.resize(400, 300)  # Smaller for passenger
            self.create_passenger_edit_dialog(dialog)
        
        dialog.exec_()

    def create_passenger_edit_dialog(self, dialog):
        """Create passenger editing dialog (your existing code)"""
        layout = QVBoxLayout(dialog)
        
        # Personal Information Section
        personal_group = QGroupBox("Personal Information")
        personal_layout = QFormLayout()
        
        # Username field
        self.edit_username = QLineEdit(self.user_data.get("username", ""))
        personal_layout.addRow("Username:", self.edit_username)
        
        # Email field (read-only for display)
        email_display = QLabel(self.user_data.get("email", ""))
        email_display.setStyleSheet("color: gray;")
        personal_layout.addRow("Email:", email_display)
        
        # Role field (read-only for display)
        role_display = QLabel("Passenger")
        role_display.setStyleSheet("color: gray;")
        personal_layout.addRow("Role:", role_display)
        
        # Zone field
        self.edit_zone = QComboBox()
        self.edit_zone.setEditable(True)
        zones = ["Dahyeh", "Haret Hreik", "Khaldeh", "Jbeil", "Baalback", "Chwayfet", 
                "Baabda", "Mansouriyeh", "Nabatiyeh", "Tyre", "Tripoli", "Hermel"]
        self.edit_zone.addItems(zones)
        personal_layout.addRow("Zone:", self.edit_zone)
        
        personal_group.setLayout(personal_layout)
        layout.addWidget(personal_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(lambda: self.save_passenger_profile(dialog))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        # Load existing zone data
        self.load_passenger_zone()

    def create_driver_edit_dialog(self, dialog):
        """Create driver editing dialog with cars and rides management"""
        layout = QVBoxLayout(dialog)
        
        # Create scroll area for driver (more content)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Personal Information Section
        personal_group = QGroupBox("Personal Information")
        personal_layout = QFormLayout()
        
        # Username field
        self.edit_username = QLineEdit(self.user_data.get("username", ""))
        personal_layout.addRow("Username:", self.edit_username)
        
        # Email field (read-only for display)
        email_display = QLabel(self.user_data.get("email", ""))
        email_display.setStyleSheet("color: gray;")
        personal_layout.addRow("Email:", email_display)
        
        # Role field (read-only for display)
        role_display = QLabel("Driver")
        role_display.setStyleSheet("color: gray;")
        personal_layout.addRow("Role:", role_display)
        
        # Zone field
        self.edit_zone = QComboBox()
        self.edit_zone.setEditable(True)
        zones = ["Dahyeh", "Haret Hreik", "Khaldeh", "Jbeil", "Baalback", "Chwayfet", 
                "Baabda", "Mansouriyeh", "Nabatiyeh", "Tyre", "Tripoli", "Hermel"]
        self.edit_zone.addItems(zones)
        personal_layout.addRow("Zone:", self.edit_zone)
        
        personal_group.setLayout(personal_layout)
        scroll_layout.addWidget(personal_group)
        
        # Cars Management Section
        cars_group = QGroupBox("Car Management")
        cars_layout = QVBoxLayout()
        
        # Current cars list
        cars_label = QLabel("Your Cars:")
        cars_layout.addWidget(cars_label)
        
        self.cars_list = QListWidget()
        self.cars_list.itemSelectionChanged.connect(self.on_car_selected)
        cars_layout.addWidget(self.cars_list)
        
        # Car details form
        car_form = QFormLayout()
        self.edit_car_type = QLineEdit()
        self.edit_car_type.setPlaceholderText("e.g., Sedan, SUV, etc.")
        self.edit_car_plate = QLineEdit()
        self.edit_car_plate.setPlaceholderText("e.g., ABC123")
        self.edit_car_capacity = QLineEdit()
        self.edit_car_capacity.setPlaceholderText("e.g., 4")
        self.edit_car_capacity.setValidator(QIntValidator(1, 10))
        
        car_form.addRow("Car Type:", self.edit_car_type)
        car_form.addRow("Car Plate:", self.edit_car_plate)
        car_form.addRow("Capacity:", self.edit_car_capacity)
        cars_layout.addLayout(car_form)
        
        # Car action buttons
        car_buttons_layout = QHBoxLayout()
        self.add_car_btn = QPushButton("Add New Car")
        self.add_car_btn.clicked.connect(self.add_new_car)
        self.update_car_btn = QPushButton("Update Selected Car")
        self.update_car_btn.clicked.connect(self.update_selected_car)
        self.remove_car_btn = QPushButton("Remove Selected Car")
        self.remove_car_btn.clicked.connect(self.remove_selected_car)
        
        self.update_car_btn.setEnabled(False)
        self.remove_car_btn.setEnabled(False)
        
        car_buttons_layout.addWidget(self.add_car_btn)
        car_buttons_layout.addWidget(self.update_car_btn)
        car_buttons_layout.addWidget(self.remove_car_btn)
        cars_layout.addLayout(car_buttons_layout)
        
        cars_group.setLayout(cars_layout)
        scroll_layout.addWidget(cars_group)
        
        # Rides Management Section
        rides_group = QGroupBox("Ride Schedule Management")
        rides_layout = QVBoxLayout()
        
        # Current rides list
        rides_label = QLabel("Your Rides:")
        rides_layout.addWidget(rides_label)
        
        self.rides_list = QListWidget()
        self.rides_list.itemSelectionChanged.connect(self.on_ride_selected)
        rides_layout.addWidget(self.rides_list)
        
        # Ride details form
        ride_form = QFormLayout()
        self.edit_ride_source = QComboBox()
        self.edit_ride_source.setEditable(True)
        self.edit_ride_source.addItems(zones)  # Same zones as above
        self.edit_ride_destination = QLabel("American University of Beirut")
        self.edit_ride_destination.setStyleSheet("color: gray;")
        
        self.edit_ride_to_time = QTimeEdit()
        self.edit_ride_to_time.setDisplayFormat("HH:mm")
        self.edit_ride_to_time.setTime(QTime(8, 0))
        self.edit_ride_from_time = QTimeEdit()
        self.edit_ride_from_time.setDisplayFormat("HH:mm")
        self.edit_ride_from_time.setTime(QTime(16, 0))
        
        self.edit_ride_car = QComboBox()
        
        ride_form.addRow("Source Area:", self.edit_ride_source)
        ride_form.addRow("Destination:", self.edit_ride_destination)
        ride_form.addRow("To AUB Time:", self.edit_ride_to_time)
        ride_form.addRow("From AUB Time:", self.edit_ride_from_time)
        ride_form.addRow("Car:", self.edit_ride_car)
        
        rides_layout.addLayout(ride_form)
        
        # Ride action buttons
        ride_buttons_layout = QHBoxLayout()
        self.add_ride_btn = QPushButton("Add New Ride")
        self.add_ride_btn.clicked.connect(self.add_new_ride)
        self.update_ride_btn = QPushButton("Update Selected Ride")
        self.update_ride_btn.clicked.connect(self.update_selected_ride)
        self.remove_ride_btn = QPushButton("Remove Selected Ride")
        self.remove_ride_btn.clicked.connect(self.remove_selected_ride)
        
        self.update_ride_btn.setEnabled(False)
        self.remove_ride_btn.setEnabled(False)
        
        ride_buttons_layout.addWidget(self.add_ride_btn)
        ride_buttons_layout.addWidget(self.update_ride_btn)
        ride_buttons_layout.addWidget(self.remove_ride_btn)
        rides_layout.addLayout(ride_buttons_layout)
        
        rides_group.setLayout(rides_layout)
        scroll_layout.addWidget(rides_group)
        
        # Save/Cancel buttons
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save All Changes")
        save_btn.clicked.connect(lambda: self.save_passenger_profile(dialog))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        scroll_layout.addLayout(buttons_layout)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Load existing data
        self.load_driver_data()

    def load_driver_data(self):
        """Load driver's existing data"""
        self.load_passenger_zone()  # Load zone (same as passenger)
        self.load_driver_cars()
        self.load_driver_rides()

    def load_driver_cars(self):
        """Load driver's cars"""
        if not self.user_data:
            return
        
        cars_req = {
            "action": "update_personal_info",
            "type_of_connection": "get_cars",
            "userID": self.user_data["userID"]
        }
        
        response = self.send_static_request(cars_req)
        self.cars_list.clear()
        self.edit_ride_car.clear()
        
        if response.get("status") == "200":
            cars = response.get("data", [])
            for car in cars:
                item_text = f"{car.get('cartype', 'Unknown')} - {car.get('carPlate', 'No Plate')} ({car.get('capacity', 0)} seats)"
                self.cars_list.addItem(item_text)
                self.edit_ride_car.addItem(f"{car.get('carPlate', '')} - {car.get('cartype', '')}", car.get('carId'))

    def load_driver_rides(self):
        """Load driver's rides"""
        if not self.user_data:
            return
        
        rides_req = {
            "action": "update_personal_info",
            "type_of_connection": "give_all_rides",
            "userID": self.user_data["userID"]
        }
        
        response = self.send_static_request(rides_req)
        self.rides_list.clear()
        
        if response.get("status") == "200":
            rides = response.get("data", [])
            for ride in rides:
                item_text = f"From {ride.get('sourceID', 'Unknown')} - To AUB: {ride.get('startTime', '')} - From AUB: {ride.get('endTime', '')}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, ride)
                self.rides_list.addItem(item)

    def on_ride_selected(self):
        """When a ride is selected, load its details into the form"""
        selected_items = self.rides_list.selectedItems()
        if selected_items:
            self.update_ride_btn.setEnabled(True)
            self.remove_ride_btn.setEnabled(True)
            self.add_ride_btn.setEnabled(False)
            
            # Load ride details into form
            ride_data = selected_items[0].data(Qt.UserRole)
            
            # Populate the form fields with the selected ride data
            if ride_data:
                # Set source
                source = ride_data.get("sourceID", "").replace("zone_", "").replace("_", " ").title()
                index = self.edit_ride_source.findText(source)
                if index >= 0:
                    self.edit_ride_source.setCurrentIndex(index)
                else:
                    self.edit_ride_source.setCurrentText(source)
                
                # Set times (convert from string to QTime)
                start_time = ride_data.get("startTime", "08:00")
                end_time = ride_data.get("endTime", "16:00")
                
                try:
                    start_qtime = QTime.fromString(start_time, "HH:mm")
                    end_qtime = QTime.fromString(end_time, "HH:mm")
                    self.edit_ride_to_time.setTime(start_qtime)
                    self.edit_ride_from_time.setTime(end_qtime)
                except:
                    # Fallback to default times
                    self.edit_ride_to_time.setTime(QTime(8, 0))
                    self.edit_ride_from_time.setTime(QTime(16, 0))
                
                # Store the ride ID for update/remove operations
                self.selected_ride_id = ride_data.get("rideID")
                
        else:
            self.add_ride_btn.setEnabled(True)
            self.update_ride_btn.setEnabled(False)
            self.remove_ride_btn.setEnabled(False)
            self.selected_ride_id = None

    def add_new_car(self):
        """Add a new car for the driver"""
        car_type = self.edit_car_type.text().strip()
        car_plate = self.edit_car_plate.text().strip()
        capacity = self.edit_car_capacity.text().strip()
        
        if not all([car_type, car_plate, capacity]):
            QMessageBox.warning(self, "Error", "Please fill all car fields")
            return
        
        car_req = {
            "action": "update_personal_info",
            "type_of_connection": "add_car",
            "userID": self.user_data["userID"],
            "car_type": car_type,
            "car_plate": car_plate,
            "capacity": int(capacity)
        }
        
        response = self.send_static_request(car_req)
        if response.get("status") == "200":
            QMessageBox.information(self, "Success", "Car added successfully!")
            self.load_driver_cars()
            # Clear form
            self.edit_car_type.clear()
            self.edit_car_plate.clear()
            self.edit_car_capacity.clear()
        else:
            QMessageBox.warning(self, "Error", f"Failed to add car: {response.get('message')}")

    def on_car_selected(self):
        """When a car is selected, load its details into the form"""
        selected_items = self.cars_list.selectedItems()
        if selected_items:
            self.update_car_btn.setEnabled(True)
            self.remove_car_btn.setEnabled(True)
            
            # Get the selected car index
            selected_index = self.cars_list.currentRow()
            
            # Get car data from backend to populate form
            cars_req = {
                "action": "update_personal_info",
                "type_of_connection": "get_cars",
                "userID": self.user_data["userID"]
            }
            
            response = self.send_static_request(cars_req)
            if response.get("status") == "200":
                cars = response.get("data", [])
                if selected_index < len(cars):
                    selected_car = cars[selected_index]
                    # Store car ID for later use
                    self.selected_car_id = selected_car.get("carId")
                    # Populate form fields
                    self.edit_car_type.setText(selected_car.get("cartype", ""))
                    self.edit_car_plate.setText(selected_car.get("carPlate", ""))
                    self.edit_car_capacity.setText(str(selected_car.get("capacity", "")))
        else:
            self.update_car_btn.setEnabled(False)
            self.remove_car_btn.setEnabled(False)
            self.selected_car_id = None

    def update_selected_car(self):
        """Update the selected car"""
        if not hasattr(self, 'selected_car_id') or not self.selected_car_id:
            QMessageBox.warning(self, "Error", "No car selected")
            return
        
        car_type = self.edit_car_type.text().strip()
        car_plate = self.edit_car_plate.text().strip()
        capacity = self.edit_car_capacity.text().strip()
        
        if not all([car_type, car_plate, capacity]):
            QMessageBox.warning(self, "Error", "Please fill all car fields")
            return
        
        try:
            capacity_int = int(capacity)
            if capacity_int < 1 or capacity_int > 10:
                QMessageBox.warning(self, "Error", "Capacity must be between 1 and 10")
                return
        except ValueError:
            QMessageBox.warning(self, "Error", "Capacity must be a valid number")
            return
        
        update_req = {
            "action": "update_personal_info",
            "type_of_connection": "update_car",
            "userID": self.user_data["userID"],
            "carId": self.selected_car_id,
            "car_type": car_type,
            "car_plate": car_plate,
            "capacity": capacity_int
        }
        
        response = self.send_static_request(update_req)
        if response.get("status") == "200":
            QMessageBox.information(self, "Success", "Car updated successfully!")
            self.load_driver_cars()
            # Clear selection and form
            self.cars_list.clearSelection()
            self.selected_car_id = None
            self.edit_car_type.clear()
            self.edit_car_plate.clear()
            self.edit_car_capacity.clear()
        else:
            QMessageBox.warning(self, "Error", f"Failed to update car: {response.get('message')}")

    def remove_selected_car(self):
        """Remove the selected car"""
        if not hasattr(self, 'selected_car_id') or not self.selected_car_id:
            QMessageBox.warning(self, "Error", "No car selected")
            return
        
        reply = QMessageBox.question(self, "Confirm", 
                                    "Are you sure you want to remove this car?\nThis action cannot be undone.",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            remove_req = {
                "action": "update_personal_info",
                "type_of_connection": "remove_car",
                "userID": self.user_data["userID"],
                "carId": self.selected_car_id
            }
            
            response = self.send_static_request(remove_req)
            if response.get("status") == "200":
                QMessageBox.information(self, "Success", "Car removed successfully!")
                self.load_driver_cars()
                # Clear selection and form
                self.cars_list.clearSelection()
                self.selected_car_id = None
                self.edit_car_type.clear()
                self.edit_car_plate.clear()
                self.edit_car_capacity.clear()
            else:
                QMessageBox.warning(self, "Error", f"Failed to remove car: {response.get('message')}")

    def add_new_ride(self):
        """Add a new ride/schedule"""
        source = self.edit_ride_source.currentText().strip()
        to_time = self.edit_ride_to_time.time().toString("HH:mm")
        from_time = self.edit_ride_from_time.time().toString("HH:mm")
        car_index = self.edit_ride_car.currentIndex()
        
        if not source or car_index < 0:
            QMessageBox.warning(self, "Error", "Please fill all ride fields")
            return
        
        car_id = self.edit_ride_car.currentData()
        
        ride_req = {
            "action": "update_personal_info",
            "type_of_connection": "add_ride",
            "userID": self.user_data["userID"],
            "carId": car_id,
            "source": source,
            "destination": "American University of Beirut",
            "startTime": to_time,
            "endTime": from_time,
            "scheduleID": self.user_data["userID"]
        }
        
        response = self.send_static_request(ride_req)
        if response.get("status") == "200" or response.get("status") == "201":
            QMessageBox.information(self, "Success", "Ride added successfully!")
            self.load_driver_rides()
        else:
            QMessageBox.warning(self, "Error", f"Failed to add ride: {response.get('message')}")

    def update_selected_ride(self):
        """Update the selected ride"""
        if not hasattr(self, 'selected_ride_id') or not self.selected_ride_id:
            QMessageBox.warning(self, "Error", "No ride selected")
            return
        
        source = self.edit_ride_source.currentText().strip()
        to_time = self.edit_ride_to_time.time().toString("HH:mm")
        from_time = self.edit_ride_from_time.time().toString("HH:mm")
        car_index = self.edit_ride_car.currentIndex()
        
        if not source or car_index < 0:
            QMessageBox.warning(self, "Error", "Please fill all ride fields")
            return
        
        car_id = self.edit_ride_car.currentData()
        
        # For update, we need to implement an update_ride backend function
        # Since you don't have it yet, show info message
        QMessageBox.information(self, "Info", "Update ride feature requires backend implementation. Please remove and re-add the ride for now.")
        
        update_req = {
            "action": "update_personal_info",
            "type_of_connection": "update_ride",
            "rideID": self.selected_ride_id,
            "userID": self.user_data["userID"],
            "carId": car_id,
            "source": source,
            "destination": "American University of Beirut",
            "startTime": to_time,
            "endTime": from_time
        }
        
        response = self.send_static_request(update_req)
        if response.get("status") == "200":
            QMessageBox.information(self, "Success", "Ride updated successfully!")
            self.load_driver_rides()
            # Clear selection
            self.rides_list.clearSelection()
            self.selected_ride_id = None
        else:
            QMessageBox.warning(self, "Error", f"Failed to update ride: {response.get('message')}")

    def remove_selected_ride(self):
        """Remove the selected ride"""
        selected_items = self.rides_list.selectedItems()
        if not selected_items:
            return
        
        ride_data = selected_items[0].data(Qt.UserRole)
        ride_id = ride_data.get("rideID")
        
        reply = QMessageBox.question(self, "Confirm", "Are you sure you want to remove this ride?")
        if reply == QMessageBox.Yes:
            ride_req = {
                "action": "update_personal_info",
                "type_of_connection": "remove_ride",
                "rideID": ride_id
            }
            
            response = self.send_static_request(ride_req)
            if response.get("status") == "200":
                QMessageBox.information(self, "Success", "Ride removed successfully!")
                self.load_driver_rides()
            else:
                QMessageBox.warning(self, "Error", f"Failed to remove ride: {response.get('message')}")


    def load_passenger_zone(self):
        """Load passenger's current zone"""
        if not self.user_data:
            return
        
        # Get current zone from database
        zone_req = {
            "action": "update_personal_info",
            "type_of_connection": "get_zone",
            "userID": self.user_data["userID"]
        }
        
        response = self.send_static_request(zone_req)
        if response.get("status") == "200":
            zone_name = response.get("data", {}).get("zoneName", "")
            if zone_name:
                # Find and set the zone in combobox
                index = self.edit_zone.findText(zone_name)
                if index >= 0:
                    self.edit_zone.setCurrentIndex(index)
                else:
                    self.edit_zone.setCurrentText(zone_name)

    def save_passenger_profile(self, dialog):
        """Save passenger profile changes"""
        try:
            new_username = self.edit_username.text().strip()
            new_zone = self.edit_zone.currentText().strip()
            
            if not new_username:
                QMessageBox.warning(self, "Error", "Username cannot be empty")
                return
            
            # 1. Update username if changed
            if new_username != self.user_data.get("username"):
                name_req = {
                    "action": "update_personal_info",
                    "type_of_connection": "edit_name",
                    "userID": self.user_data["userID"],
                    "new_name": new_username
                }
                name_response = self.send_static_request(name_req)
                
                if name_response.get("status") != "200":
                    QMessageBox.warning(self, "Error", f"Failed to update username: {name_response.get('message')}")
                    return
            
            # 2. Update zone
            if new_zone:
                zone_req = {
                    "action": "update_personal_info",
                    "type_of_connection": "update_zone",
                    "userID": self.user_data["userID"],
                    "zone": new_zone
                }
                zone_response = self.send_static_request(zone_req)
                
                if zone_response.get("status") != "200":
                    QMessageBox.warning(self, "Error", f"Failed to update zone: {zone_response.get('message')}")
                    # Continue anyway, as username might have been updated
            
            # Update local user data
            self.user_data["username"] = new_username
            
            QMessageBox.information(self, "Success", "Profile updated successfully!")
            dialog.accept()
            
            # Refresh profile display
            self.refresh_profile_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save profile: {str(e)}")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    ex = RideShareApp()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
