import sys
import socket
import json
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QTabWidget, QListWidget, QComboBox,
                             QMessageBox, QGroupBox, QFormLayout, QCheckBox,
                             QTimeEdit, QListWidgetItem, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QTime, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QLinearGradient, QPainter
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
        
        self.setup_style()
        self.initUI()
        
        # Connect signals after UI is initialized
        self.signal_emitter.message_received.connect(self.show_message)
        self.signal_emitter.candidates_received.connect(self.display_candidates)
        
    def setup_style(self):
        """Setup modern stylesheet"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
            }
            
            QWidget {
                background-color: transparent;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QTabWidget::pane {
                border: 2px solid #0f3460;
                border-radius: 10px;
                background-color: rgba(22, 33, 62, 0.8);
                padding: 10px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16213e, stop:1 #0f3460);
                color: #e0e0e0;
                padding: 12px 25px;
                margin: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e94560, stop:1 #c41e3d);
                color: white;
            }
            
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f4068, stop:1 #16213e);
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e94560, stop:1 #c41e3d);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff577f, stop:1 #e94560);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #c41e3d, stop:1 #a01830);
            }
            
            QLineEdit, QTimeEdit, QComboBox {
                background-color: rgba(31, 64, 104, 0.6);
                border: 2px solid #0f3460;
                border-radius: 6px;
                padding: 10px;
                color: #e0e0e0;
                font-size: 13px;
                selection-background-color: #e94560;
            }
            
            QLineEdit:focus, QTimeEdit:focus, QComboBox:focus {
                border: 2px solid #e94560;
                background-color: rgba(31, 64, 104, 0.8);
            }
            
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
                margin-right: 5px;
            }
            
            QGroupBox {
                background-color: rgba(22, 33, 62, 0.6);
                border: 2px solid #0f3460;
                border-radius: 10px;
                margin-top: 20px;
                padding-top: 25px;
                font-weight: bold;
                font-size: 15px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 5px 15px;
                background-color: #e94560;
                color: white;
                border-radius: 6px;
            }
            
            QListWidget {
                background-color: rgba(31, 64, 104, 0.4);
                border: 2px solid #0f3460;
                border-radius: 8px;
                padding: 8px;
                outline: none;
            }
            
            QListWidget::item {
                background-color: rgba(22, 33, 62, 0.8);
                border: 1px solid #0f3460;
                border-radius: 6px;
                padding: 12px;
                margin: 4px;
                color: #e0e0e0;
            }
            
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e94560, stop:1 #c41e3d);
                color: white;
                border: 1px solid #ff577f;
            }
            
            QListWidget::item:hover {
                background-color: rgba(233, 69, 96, 0.3);
                border: 1px solid #e94560;
            }
            
            QCheckBox {
                spacing: 8px;
                color: #e0e0e0;
            }
            
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #0f3460;
                background-color: rgba(31, 64, 104, 0.6);
            }
            
            QCheckBox::indicator:checked {
                background-color: #e94560;
                border: 2px solid #c41e3d;
            }
            
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: white;
            }
            
            QLabel {
                color: #e0e0e0;
            }
            
            QScrollBar:vertical {
                background-color: rgba(15, 52, 96, 0.3);
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #e94560;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #ff577f;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
    
    def initUI(self):
        self.setWindowTitle('🚗 AUB Ride Share')
        self.setGeometry(100, 100, 1300, 850)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
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
    
    def create_header(self):
        """Create app header"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e94560, stop:1 #c41e3d);
                border-radius: 15px;
                padding: 10px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        
        title = QLabel("🚗 AUB RIDE SHARE")
        title.setFont(QFont('Segoe UI', 24, QFont.Bold))
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.user_label = QLabel("👤 Not logged in")
        self.user_label.setFont(QFont('Segoe UI', 12))
        self.user_label.setStyleSheet("color: white;")
        header_layout.addWidget(self.user_label)
        
        return header_frame
    
    def create_login_tab(self):
        """Create login/signup tab"""
        login_widget = QWidget()
        layout = QVBoxLayout(login_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Welcome message
        welcome_container = QWidget()
        welcome_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(233, 69, 96, 0.3), stop:1 rgba(196, 30, 61, 0.3));
                border-radius: 15px;
                padding: 30px;
            }
        """)
        welcome_layout = QVBoxLayout(welcome_container)
        
        title = QLabel("Welcome to AUB Ride Share")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Segoe UI', 28, QFont.Bold))
        title.setStyleSheet("color: white;")
        welcome_layout.addWidget(title)
        
        subtitle = QLabel("🚗 Connect • Share • Travel Together")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont('Segoe UI', 14))
        subtitle.setStyleSheet("color: #e0e0e0; margin-top: 10px;")
        welcome_layout.addWidget(subtitle)
        
        layout.addWidget(welcome_container)
        
        # Main content with two columns
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        
        # Login Section
        login_group = QGroupBox("🔐 Login")
        login_group.setFont(QFont('Segoe UI', 14, QFont.Bold))
        login_form = QFormLayout()
        login_form.setSpacing(15)
        login_form.setContentsMargins(20, 30, 20, 20)
        
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Enter your username")
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Enter your password")
        self.login_password.setEchoMode(QLineEdit.Password)
        
        login_form.addRow("👤 Username:", self.login_username)
        login_form.addRow("🔒 Password:", self.login_password)
        
        login_btn = QPushButton("🚀 Login")
        login_btn.setMinimumHeight(45)
        login_btn.clicked.connect(self.handle_login)
        login_form.addRow(login_btn)
        
        login_group.setLayout(login_form)
        content_layout.addWidget(login_group)
        
        # Signup Section
        signup_group = QGroupBox("📝 Sign Up")
        signup_group.setFont(QFont('Segoe UI', 14, QFont.Bold))
        signup_form = QFormLayout()
        signup_form.setSpacing(15)
        signup_form.setContentsMargins(20, 30, 20, 20)
        
        self.signup_username = QLineEdit()
        self.signup_username.setPlaceholderText("Choose a username")
        self.signup_password = QLineEdit()
        self.signup_password.setPlaceholderText("Create a password")
        self.signup_password.setEchoMode(QLineEdit.Password)
        self.signup_email = QLineEdit()
        self.signup_email.setPlaceholderText("example@mail.aub.edu")
        self.signup_aub_id = QLineEdit()
        self.signup_aub_id.setPlaceholderText("202500049")
        self.signup_zone = QLineEdit()
        self.signup_zone.setPlaceholderText("Hamra, Beirut")
        self.signup_is_driver = QCheckBox("🚗 I am a driver")
        self.signup_is_driver.setFont(QFont('Segoe UI', 11))
        
        signup_form.addRow("👤 Username:", self.signup_username)
        signup_form.addRow("🔒 Password:", self.signup_password)
        signup_form.addRow("📧 Email:", self.signup_email)
        signup_form.addRow("🎓 AUB ID:", self.signup_aub_id)
        signup_form.addRow("📍 Zone:", self.signup_zone)
        signup_form.addRow("", self.signup_is_driver)
        
        signup_btn = QPushButton("✨ Create Account")
        signup_btn.setMinimumHeight(45)
        signup_btn.clicked.connect(self.handle_signup)
        signup_form.addRow(signup_btn)
        
        signup_group.setLayout(signup_form)
        content_layout.addWidget(signup_group)
        
        layout.addLayout(content_layout)
        layout.addStretch()
        
        self.tabs.addTab(login_widget, "🏠 Home")
    
    def create_driver_tab(self):
        """Create driver interface tab"""
        driver_widget = QWidget()
        layout = QVBoxLayout(driver_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # User info banner
        info_banner = QFrame()
        info_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(31, 64, 104, 0.8), stop:1 rgba(15, 52, 96, 0.8));
                border-radius: 10px;
                padding: 15px;
            }
        """)
        banner_layout = QHBoxLayout(info_banner)
        
        self.driver_info_label = QLabel("🚗 Driver Dashboard")
        self.driver_info_label.setFont(QFont('Segoe UI', 18, QFont.Bold))
        self.driver_info_label.setStyleSheet("color: white;")
        banner_layout.addWidget(self.driver_info_label)
        banner_layout.addStretch()
        
        layout.addWidget(info_banner)
        
        # Add Ride Section
        add_ride_group = QGroupBox("➕ Add New Ride")
        add_ride_form = QFormLayout()
        add_ride_form.setSpacing(15)
        add_ride_form.setContentsMargins(20, 30, 20, 20)
        
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
        
        add_ride_form.addRow("📍 Area/Location:", self.driver_area)
        add_ride_form.addRow("⏰ To AUB Time:", self.driver_to_aub_time)
        add_ride_form.addRow("⏰ From AUB Time:", self.driver_from_aub_time)
        add_ride_form.addRow("🔌 P2P Port:", self.driver_p2p_port)
        
        add_ride_btn = QPushButton("✅ Add Ride")
        add_ride_btn.setMinimumHeight(45)
        add_ride_btn.clicked.connect(self.handle_add_ride)
        add_ride_form.addRow(add_ride_btn)
        
        add_ride_group.setLayout(add_ride_form)
        layout.addWidget(add_ride_group)
        
        # Pending Requests Section
        requests_group = QGroupBox("📋 Pending Ride Requests")
        requests_layout = QVBoxLayout()
        requests_layout.setSpacing(10)
        requests_layout.setContentsMargins(15, 25, 15, 15)
        
        refresh_btn = QPushButton("🔄 Refresh Requests")
        refresh_btn.clicked.connect(self.refresh_requests)
        requests_layout.addWidget(refresh_btn)
        
        self.requests_list = QListWidget()
        self.requests_list.itemDoubleClicked.connect(self.accept_ride_request)
        requests_layout.addWidget(self.requests_list)
        
        requests_group.setLayout(requests_layout)
        layout.addWidget(requests_group)
        
        # Instructions
        info_label = QLabel("💡 Double-click a request to accept it")
        info_label.setStyleSheet("color: #888; font-style: italic; font-size: 12px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        self.tabs.addTab(driver_widget, "🚗 Driver")
    
    def create_passenger_tab(self):
        """Create passenger interface tab"""
        passenger_widget = QWidget()
        layout = QVBoxLayout(passenger_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # User info banner
        info_banner = QFrame()
        info_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(31, 64, 104, 0.8), stop:1 rgba(15, 52, 96, 0.8));
                border-radius: 10px;
                padding: 15px;
            }
        """)
        banner_layout = QHBoxLayout(info_banner)
        
        self.passenger_info_label = QLabel("👤 Passenger Dashboard")
        self.passenger_info_label.setFont(QFont('Segoe UI', 18, QFont.Bold))
        self.passenger_info_label.setStyleSheet("color: white;")
        banner_layout.addWidget(self.passenger_info_label)
        banner_layout.addStretch()
        
        layout.addWidget(info_banner)
        
        # Request Ride Section
        request_group = QGroupBox("🔍 Request a Ride")
        request_form = QFormLayout()
        request_form.setSpacing(15)
        request_form.setContentsMargins(20, 30, 20, 20)
        
        self.passenger_area = QLineEdit()
        self.passenger_area.setPlaceholderText("e.g., Hamra, Beirut")
        self.passenger_time = QTimeEdit()
        self.passenger_time.setDisplayFormat("HH:mm")
        self.passenger_time.setTime(QTime(8, 15))
        self.passenger_direction = QComboBox()
        self.passenger_direction.addItems(["to_aub", "from_aub"])
        self.passenger_p2p_port = QLineEdit()
        self.passenger_p2p_port.setText("50002")
        
        request_form.addRow("📍 Area/Location:", self.passenger_area)
        request_form.addRow("⏰ Time:", self.passenger_time)
        request_form.addRow("🧭 Direction:", self.passenger_direction)
        request_form.addRow("🔌 P2P Port:", self.passenger_p2p_port)
        
        request_btn = QPushButton("🔎 Find Rides")
        request_btn.setMinimumHeight(45)
        request_btn.clicked.connect(self.handle_request_ride)
        request_form.addRow(request_btn)
        
        request_group.setLayout(request_form)
        layout.addWidget(request_group)
        
        # Available Drivers Section
        drivers_group = QGroupBox("🚗 Available Drivers")
        drivers_layout = QVBoxLayout()
        drivers_layout.setSpacing(10)
        drivers_layout.setContentsMargins(15, 25, 15, 15)
        
        self.drivers_list = QListWidget()
        self.drivers_list.itemDoubleClicked.connect(self.accept_driver)
        drivers_layout.addWidget(self.drivers_list)
        
        drivers_group.setLayout(drivers_layout)
        layout.addWidget(drivers_group)
        
        # Instructions
        info_label = QLabel("💡 Double-click a driver to accept their ride")
        info_label.setStyleSheet("color: #888; font-style: italic; font-size: 12px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        self.tabs.addTab(passenger_widget, "👤 Passenger")
    
    def create_map_tab(self):
        """Create map view tab with embedded Google Maps"""
        map_widget = QWidget()
        layout = QVBoxLayout(map_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Map header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(31, 64, 104, 0.8), stop:1 rgba(15, 52, 96, 0.8));
                border-radius: 10px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout(header)
        
        title = QLabel("🗺️ Map View")
        title.setFont(QFont('Segoe UI', 18, QFont.Bold))
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        refresh_map_btn = QPushButton("🔄 Refresh")
        refresh_map_btn.clicked.connect(self.load_map)
        header_layout.addWidget(refresh_map_btn)
        
        layout.addWidget(header)
        
        # Map container
        map_container = QFrame()
        map_container.setStyleSheet("""
            QFrame {
                background-color: rgba(31, 64, 104, 0.3);
                border: 2px solid #0f3460;
                border-radius: 10px;
            }
        """)
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(5, 5, 5, 5)
        
        # Web view for Google Maps
        self.map_view = QWebEngineView()
        self.load_map()
        map_layout.addWidget(self.map_view)
        
        layout.addWidget(map_container)
        
        self.tabs.addTab(map_widget, "🗺️ Map")
    
    def load_map(self):
        """Load Google Maps with OpenStreetMap as fallback"""
        if GOOGLE_MAPS_API_KEY and GOOGLE_MAPS_API_KEY != "YOUR_API_KEY_HERE":
            # Use Google Maps if API key is available
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
                        background: #1a1a2e;
                    }}
                </style>
            </head>
            <body>
                <div id="map"></div>
                <script>
                    function initMap() {{
                        var aub = {{lat: 33.8993, lng: 35.4839}};
                        var map = new google.maps.Map(document.getElementById('map'), {{
                            zoom: 14,
                            center: aub,
                            styles: [
                                {{elementType: 'geometry', stylers: [{{color: '#242f3e'}}]}},
                                {{elementType: 'labels.text.stroke', stylers: [{{color: '#242f3e'}}]}},
                                {{elementType: 'labels.text.fill', stylers: [{{color: '#746855'}}]}},
                                {{
                                    featureType: 'road',
                                    elementType: 'geometry',
                                    stylers: [{{color: '#38414e'}}]
                                }},
                                {{
                                    featureType: 'road',
                                    elementType: 'geometry.stroke',
                                    stylers: [{{color: '#212a37'}}]
                                }},
                                {{
                                    featureType: 'water',
                                    elementType: 'geometry',
                                    stylers: [{{color: '#17263c'}}]
                                }}
                            ]
                        }});
                        
                        var marker = new google.maps.Marker({{
                            position: aub,
                            map: map,
                            title: 'American University of Beirut',
                            icon: {{
                                path: google.maps.SymbolPath.CIRCLE,
                                scale: 10,
                                fillColor: '#e94560',
                                fillOpacity: 1,
                                strokeColor: '#ffffff',
                                strokeWeight: 2
                            }}
                        }});
                        
                        var infowindow = new google.maps.InfoWindow({{
                            content: '<div style="color: #1a1a2e; font-weight: bold;">American University of Beirut</div>'
                        }});
                        
                        marker.addListener('click', function() {{
                            infowindow.open(map, marker);
                        }});
                    }}
                </script>
                <script async defer
                    src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap">
                </script>
            </body>
            </html>
            """
        else:
            # Fallback to OpenStreetMap with Leaflet
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>AUB Ride Share Map</title>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                <style>
                    #map {
                        height: 100%;
                        width: 100%;
                    }
                    html, body {
                        height: 100%;
                        margin: 0;
                        padding: 0;
                        background: #1a1a2e;
                    }
                </style>
            </head>
            <body>
                <div id="map"></div>
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <script>
                    var aub = [33.8993, 35.4839];
                    var map = L.map('map').setView(aub, 14);
                    
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '© OpenStreetMap contributors',
                        maxZoom: 19
                    }).addTo(map);
                    
                    var marker = L.marker(aub).addTo(map);
                    marker.bindPopup("<b>American University of Beirut</b><br>Main Campus").openPopup();
                </script>
            </body>
            </html>
            """
        
        self.map_view.setHtml(html_content)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    # Set application-wide font
    font = QFont('Segoe UI', 10)
    app.setFont(font)
    
    ex = RideShareApp()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()