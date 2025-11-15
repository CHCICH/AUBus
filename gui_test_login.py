import sys
import socket
import json
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QTabWidget, QListWidget, QComboBox,
                             QMessageBox, QGroupBox, QFormLayout, QCheckBox,
                             QTimeEdit, QListWidgetItem, QScrollArea)
from PyQt5.QtCore import Qt, QTime, pyqtSignal, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView
import os

# Configuration
STATIC_SERVER_HOST = socket.gethostname()
STATIC_SERVER_PORT = 9999
RIDE_SERVER_HOST = '0.0.0.0'
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
        self.create_map_tab()
        
        # Initially disable driver and passenger tabs
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)
        
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
        
        if response.get("status") == "200":
            self.user_data = {
                "username": username,
                "email": response.get("email"),
                "userID": response.get("userID")
            }
            
            # Get user info to check if driver
            user_info_req = {
                "action": "update_personal_info",
                "type_of_connection": "give_user_personal_informations",
                "userID": self.user_data["userID"]
            }
            user_info_resp = self.send_static_request(user_info_req)
            
            if user_info_resp.get("status") == "200":
                data = user_info_resp.get("data", {})
                self.user_data["is_driver"] = data.get("isDriver", False)
            
            QMessageBox.information(self, "Success", f"Welcome, {username}!")
            
            # Enable appropriate tabs
            if self.user_data.get("is_driver"):
                self.tabs.setTabEnabled(1, True)
                self.driver_info_label.setText(f"Driver: {username}")
            else:
                self.tabs.setTabEnabled(2, True)
                self.passenger_info_label.setText(f"Passenger: {username}")
            
            self.tabs.setTabEnabled(3, True)
            self.tabs.setCurrentIndex(1 if self.user_data.get("is_driver") else 2)
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

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    ex = RideShareApp()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()