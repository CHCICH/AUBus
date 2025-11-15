"""
AUBus Ultimate — Enhanced PyQt5 GUI combining best features
with robust Google Maps, real-time updates, and comprehensive ride management.

Requirements:
    pip install PyQt5 PyQtWebEngine requests folium

Environment:
    Set GOOGLE_MAPS_API_KEY for Google Maps features
    Ensure static_gateway.py is running on port 9999

Run:
    python aubus_ultimate_gui.py
"""
import os
import sys
import json
import socket
import tempfile
import folium
import threading
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTabWidget, QListWidget, QMessageBox, QFormLayout, 
    QGroupBox, QStatusBar, QTextEdit, QCheckBox, QTimeEdit, QListWidgetItem,
    QSplitter, QFrame, QSpacerItem, QSizePolicy, QComboBox, QScrollArea
)
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl, Qt, QTime, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QFont, QIcon

# Configuration
GATEWAY_HOST = socket.gethostname()
GATEWAY_PORT = 9999
def get_GGM_api_key():
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith('API_MAPS_KEY='):
                    return line.strip().split('=')[1]
    except FileNotFoundError:
        return None
    return None

GOOGLE_API_KEY  = get_GGM_api_key()

# ============================================================================
# NETWORKING HELPER
# ============================================================================
def send_request_to_gateway(payload, host=GATEWAY_HOST, port=GATEWAY_PORT, timeout=8):
    """Send JSON request to gateway server and return response"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.send(json.dumps(payload).encode('utf-8'))
        data = s.recv(16384).decode('utf-8')
        s.close()
        return json.loads(data)
    except json.JSONDecodeError:
        return {"status": "500", "message": "Invalid JSON response from server"}
    except Exception as e:
        return {"status": "500", "message": f"Connection error: {str(e)}"}

# ============================================================================
# MAP BRIDGE (JavaScript ↔ Python communication)
# ============================================================================
class MapBridge(QObject):
    """Bridge for communicating between JavaScript map and Python"""
    coordinatesChanged = pyqtSignal(float, float)
    consoleMessage = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.last_lat = None
        self.last_lng = None
    
    @pyqtSlot(float, float)
    def reportCoordinates(self, lat, lng):
        """Called from JavaScript when user clicks map"""
        self.last_lat = float(lat)
        self.last_lng = float(lng)
        self.coordinatesChanged.emit(self.last_lat, self.last_lng)
    
    @pyqtSlot(str)
    def consoleLog(self, msg):
        """Forward JavaScript console messages to Python"""
        self.consoleMessage.emit(str(msg))

# ============================================================================
# MAIN APPLICATION
# ============================================================================
class AUBusUltimateGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AUBus Ultimate — Ride Sharing System")
        self.setGeometry(100, 50, 1400, 900)
        
        # Session data
        self.user = None  # {userID, username, email, isDriver}
        self.current_candidates = []
        self.current_request_id = None
        self.pending_requests = []
        
        # Map bridge
        self.map_bridge = MapBridge()
        self.map_bridge.coordinatesChanged.connect(self.on_map_click)
        self.map_bridge.consoleMessage.connect(self.on_map_console_message)
        
        # Auto-refresh timer for drivers
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_requests)
        
        self.init_ui()
        self.init_map()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setStyleSheet(self.get_stylesheet())
        
        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # LEFT PANEL: Controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # RIGHT PANEL: Map
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([450, 950])
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — Please login to continue")
    
    def create_left_panel(self):
        """Create left control panel with tabs"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("🚍 AUBus Ultimate")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # User info label
        self.user_info_label = QLabel("Not logged in")
        self.user_info_label.setObjectName("userInfo")
        self.user_info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.user_info_label)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs, 1)
        
        self.create_auth_tab()
        self.create_driver_tab()
        self.create_passenger_tab()
        self.create_settings_tab()
        
        # Initially disable driver and passenger tabs
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        
        # Developer console (collapsible)
        console_group = QGroupBox("Developer Console")
        console_group.setCheckable(True)
        console_group.setChecked(False)
        console_layout = QVBoxLayout()
        self.dev_console = QTextEdit()
        self.dev_console.setReadOnly(True)
        self.dev_console.setMaximumHeight(120)
        self.dev_console.setStyleSheet("font-family: 'Courier New'; font-size: 10px;")
        console_layout.addWidget(self.dev_console)
        console_group.setLayout(console_layout)
        console_group.toggled.connect(lambda checked: self.dev_console.setVisible(checked))
        self.dev_console.setVisible(False)
        layout.addWidget(console_group)
        
        return panel
    
    def create_right_panel(self):
        """Create right panel with map and info"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Map view
        self.map_view = QWebEngineView()
        layout.addWidget(self.map_view, 1)
        
        # Bottom info bar
        bottom_bar = QFrame()
        bottom_bar.setMaximumHeight(140)
        bottom_layout = QHBoxLayout(bottom_bar)
        
        # Coordinates display with preset locations
        coord_group = QGroupBox("Selected Location")
        coord_layout = QVBoxLayout()
        self.coord_label = QLabel("Click map to select")
        self.coord_label.setWordWrap(True)
        coord_layout.addWidget(self.coord_label)
        
        # Add preset location buttons
        preset_layout = QHBoxLayout()
        preset_aub_btn = QPushButton("📍 AUB")
        preset_aub_btn.setMaximumWidth(100)
        preset_aub_btn.clicked.connect(lambda: self.set_preset_location(33.9006, 35.4812, "AUB"))
        
        preset_hamra_btn = QPushButton("📍 Hamra")
        preset_hamra_btn.setMaximumWidth(100)
        preset_hamra_btn.clicked.connect(lambda: self.set_preset_location(33.8958, 35.4787, "Hamra"))
        
        preset_layout.addWidget(preset_aub_btn)
        preset_layout.addWidget(preset_hamra_btn)
        preset_layout.addStretch()
        coord_layout.addLayout(preset_layout)
        
        coord_group.setLayout(coord_layout)
        bottom_layout.addWidget(coord_group)
        
        # Weather display
        weather_group = QGroupBox("Weather Info")
        weather_layout = QVBoxLayout()
        self.weather_label = QLabel("Select location first")
        self.weather_label.setWordWrap(True)
        weather_layout.addWidget(self.weather_label)
        self.weather_refresh_btn = QPushButton("🌤 Refresh Weather")
        self.weather_refresh_btn.clicked.connect(self.refresh_weather)
        weather_layout.addWidget(self.weather_refresh_btn)
        weather_group.setLayout(weather_layout)
        bottom_layout.addWidget(weather_group)
        
        layout.addWidget(bottom_bar)
        
        return panel
    
    # ========================================================================
    # TAB CREATION
    # ========================================================================
    def create_auth_tab(self):
        """Create authentication tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Welcome to AUBus")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0066cc;")
        layout.addWidget(title)
        
        # Login section
        login_group = QGroupBox("Login")
        login_form = QFormLayout()
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Enter username")
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Enter password")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.returnPressed.connect(self.handle_login)
        
        login_form.addRow("Username:", self.login_username)
        login_form.addRow("Password:", self.login_password)
        
        login_btn = QPushButton("🔑 Login")
        login_btn.clicked.connect(self.handle_login)
        login_form.addRow(login_btn)
        login_group.setLayout(login_form)
        layout.addWidget(login_group)
        
        # Signup section
        signup_group = QGroupBox("Create New Account")
        signup_form = QFormLayout()
        
        self.signup_username = QLineEdit()
        self.signup_username.setPlaceholderText("Choose username")
        self.signup_password = QLineEdit()
        self.signup_password.setPlaceholderText("Choose password")
        self.signup_password.setEchoMode(QLineEdit.Password)
        self.signup_email = QLineEdit()
        self.signup_email.setPlaceholderText("user@mail.aub.edu")
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
        
        signup_btn = QPushButton("📝 Sign Up")
        signup_btn.clicked.connect(self.handle_signup)
        signup_form.addRow(signup_btn)
        signup_group.setLayout(signup_form)
        layout.addWidget(signup_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🏠 Login")
    
    def create_driver_tab(self):
        """Create driver interface tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Add ride section
        add_ride_group = QGroupBox("➕ Add New Ride")
        add_form = QFormLayout()
        
        self.driver_source = QLineEdit()
        self.driver_source.setPlaceholderText("e.g., Hamra, Beirut (or use map)")
        self.driver_dest = QLineEdit()
        self.driver_dest.setPlaceholderText("AUB, Beirut")
        self.driver_start_time = QTimeEdit()
        self.driver_start_time.setDisplayFormat("HH:mm")
        self.driver_start_time.setTime(QTime(8, 0))
        self.driver_end_time = QTimeEdit()
        self.driver_end_time.setDisplayFormat("HH:mm")
        self.driver_end_time.setTime(QTime(16, 0))
        self.driver_car_id = QLineEdit()
        self.driver_car_id.setPlaceholderText("Optional")
        self.driver_use_map_coords = QCheckBox("Use map coordinates for pickup")
        self.driver_use_map_coords.setChecked(True)
        
        add_form.addRow("Source:", self.driver_source)
        add_form.addRow("Destination:", self.driver_dest)
        add_form.addRow("Start Time:", self.driver_start_time)
        add_form.addRow("End Time:", self.driver_end_time)
        add_form.addRow("Car ID:", self.driver_car_id)
        add_form.addRow("", self.driver_use_map_coords)
        
        add_ride_btn = QPushButton("✅ Add Ride")
        add_ride_btn.clicked.connect(self.handle_add_ride)
        add_form.addRow(add_ride_btn)
        add_ride_group.setLayout(add_form)
        layout.addWidget(add_ride_group)
        
        # Pending requests section
        requests_group = QGroupBox("📋 Pending Ride Requests")
        requests_layout = QVBoxLayout()
        
        refresh_controls = QHBoxLayout()
        self.auto_refresh_checkbox = QCheckBox("Auto-refresh (10s)")
        self.auto_refresh_checkbox.toggled.connect(self.toggle_auto_refresh)
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.clicked.connect(self.refresh_requests)
        refresh_controls.addWidget(self.auto_refresh_checkbox)
        refresh_controls.addWidget(refresh_btn)
        refresh_controls.addStretch()
        requests_layout.addLayout(refresh_controls)
        
        self.requests_list = QListWidget()
        self.requests_list.itemDoubleClicked.connect(self.accept_selected_request)
        requests_layout.addWidget(self.requests_list)
        
        info_label = QLabel("💡 Double-click a request to accept it")
        info_label.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")
        requests_layout.addWidget(info_label)
        
        requests_group.setLayout(requests_layout)
        layout.addWidget(requests_group)
        
        self.tabs.addTab(tab, "🚗 Driver")
    
    def create_passenger_tab(self):
        """Create passenger interface tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Request ride section
        request_group = QGroupBox("🎯 Request a Ride")
        request_form = QFormLayout()
        
        self.passenger_area = QLineEdit()
        self.passenger_area.setPlaceholderText("e.g., Hamra, Beirut (or use map)")
        self.passenger_time = QTimeEdit()
        self.passenger_time.setDisplayFormat("HH:mm")
        self.passenger_time.setTime(QTime(8, 15))
        self.passenger_direction = QComboBox()
        self.passenger_direction.addItems(["to_aub", "from_aub"])
        self.passenger_use_map = QCheckBox("Use map coordinates")
        self.passenger_use_map.setChecked(False)
        
        request_form.addRow("Area:", self.passenger_area)
        request_form.addRow("Time:", self.passenger_time)
        request_form.addRow("Direction:", self.passenger_direction)
        request_form.addRow("", self.passenger_use_map)
        
        request_btn = QPushButton("🔍 Find Drivers")
        request_btn.clicked.connect(self.handle_request_ride)
        request_form.addRow(request_btn)
        request_group.setLayout(request_form)
        layout.addWidget(request_group)
        
        # Available drivers section
        drivers_group = QGroupBox("🚙 Available Drivers")
        drivers_layout = QVBoxLayout()
        
        self.drivers_list = QListWidget()
        self.drivers_list.itemDoubleClicked.connect(self.accept_selected_driver)
        drivers_layout.addWidget(self.drivers_list)
        
        driver_actions = QHBoxLayout()
        show_route_btn = QPushButton("🗺 Show Route")
        show_route_btn.clicked.connect(self.show_route_to_driver)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.drivers_list.clear)
        driver_actions.addWidget(show_route_btn)
        driver_actions.addWidget(clear_btn)
        driver_actions.addStretch()
        drivers_layout.addLayout(driver_actions)
        
        info_label = QLabel("💡 Double-click a driver to accept the ride")
        info_label.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")
        drivers_layout.addWidget(info_label)
        
        drivers_group.setLayout(drivers_layout)
        layout.addWidget(drivers_group)
        
        self.tabs.addTab(tab, "🎒 Passenger")
    
    def create_settings_tab(self):
        """Create settings and info tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Connection settings
        conn_group = QGroupBox("🔌 Connection Settings")
        conn_form = QFormLayout()
        
        self.gateway_host_input = QLineEdit(GATEWAY_HOST)
        self.gateway_port_input = QLineEdit(str(GATEWAY_PORT))
        
        conn_form.addRow("Gateway Host:", self.gateway_host_input)
        conn_form.addRow("Gateway Port:", self.gateway_port_input)
        
        test_conn_btn = QPushButton("Test Connection")
        test_conn_btn.clicked.connect(self.test_connection)
        conn_form.addRow(test_conn_btn)
        conn_group.setLayout(conn_form)
        layout.addWidget(conn_group)
        
        # Map settings
        map_group = QGroupBox("🗺 Map Configuration")
        map_layout = QVBoxLayout()
        
        api_status = QLabel(f"API Key: {'✅ Set' if GOOGLE_API_KEY else '❌ Not set'}")
        map_layout.addWidget(api_status)
        
        reload_map_btn = QPushButton("Reload Map")
        reload_map_btn.clicked.connect(self.init_map)
        map_layout.addWidget(reload_map_btn)
        
        map_group.setLayout(map_layout)
        layout.addWidget(map_group)
        
        # About
        about_group = QGroupBox("ℹ️ About")
        about_layout = QVBoxLayout()
        about_text = QLabel(
            "AUBus Ultimate v1.0\n\n"
            "A comprehensive ride-sharing system for AUB community.\n\n"
            "Features:\n"
            "• Real-time ride matching\n"
            "• Interactive Google Maps integration\n"
            "• Weather information\n"
            "• Driver and passenger modes\n"
            "• Secure authentication"
        )
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "⚙️ Settings")
    
    # ========================================================================
    # MAP INITIALIZATION
    # ========================================================================
    def init_map(self):
        """Initialize Google Maps or fallback to Folium"""
        if GOOGLE_API_KEY:
            html = self.build_google_map_html()
            channel = QWebChannel()
            channel.registerObject('bridge', self.map_bridge)
            self.map_view.page().setWebChannel(channel)
            self.map_view.setHtml(html, QUrl(""))
            self.status_bar.showMessage("Map: Google Maps initialized ✅")
        else:
            # Folium fallback
            try:
                self.status_bar.showMessage("Map: Google API key missing — using local folium fallback")
                
                # AUB coordinates
                aub_lat, aub_lng = 33.9006, 35.4812
                
                m = folium.Map(location=[aub_lat, aub_lng], zoom_start=13)
                folium.Marker([aub_lat, aub_lng], tooltip='AUB').add_to(m)
                
                # You can add click functionality too
                m.add_child(folium.LatLngPopup())
                
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
                m.save(tmp.name)
                self.map_view.load(QUrl.fromLocalFile(tmp.name))
                
                # Automatically set AUB coordinates and fetch weather
                self.map_bridge.last_lat = aub_lat
                self.map_bridge.last_lng = aub_lng
                self.coord_label.setText(f"📍 {aub_lat:.6f}, {aub_lng:.6f} (AUB)")
                
                # Auto-fetch weather for AUB
                self.refresh_weather()
                
            except ImportError:
                # If folium is also not available, show simple HTML
                html = """
                <!DOCTYPE html>
                <html>
                <head><style>body{margin:0;padding:20px;font-family:Arial;background:#e3f2fd;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;}</style></head>
                <body>
                <div>
                <h2>🗺 Map Unavailable</h2>
                <p>Google Maps API key not set and Folium not installed.<br>Set GOOGLE_MAPS_API_KEY environment variable or install folium.</p>
                <p style="color:#666;font-size:12px;">pip install folium</p>
                </div>
                </body>
                </html>
                """
                self.map_view.setHtml(html)
                self.status_bar.showMessage("Map: API key missing and folium not available ⚠️")   
    
    def build_google_map_html(self):
        """Build Google Maps HTML with all features"""
        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="initial-scale=1.0, user-scalable=no">
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_API_KEY}&libraries=places"></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
    #error {{ position: absolute; z-index: 999; left: 10px; top: 10px; 
             background: rgba(255,255,255,0.95); padding: 12px; 
             border-radius: 8px; display: none; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
             max-width: 300px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="error">Map initialization failed. Check console.</div>
<script>
  let bridge = null;
  let map, clickMarker, markers = [], directionsService, directionsRenderer;
  
  // Initialize Qt bridge
  new QWebChannel(qt.webChannelTransport, function(channel) {{
    bridge = channel.objects.bridge;
  }});
  
  // Console forwarding
  (function() {{
    const log = console.log, err = console.error, warn = console.warn;
    console.log = function(...args) {{
      try {{ if(bridge?.consoleLog) bridge.consoleLog(JSON.stringify({{type:'log',msg:args}})); }} catch(e) {{}}
      log.apply(console, args);
    }};
    console.error = function(...args) {{
      try {{ if(bridge?.consoleLog) bridge.consoleLog(JSON.stringify({{type:'error',msg:args}})); }} catch(e) {{}}
      err.apply(console, args);
    }};
    console.warn = function(...args) {{
      try {{ if(bridge?.consoleLog) bridge.consoleLog(JSON.stringify({{type:'warn',msg:args}})); }} catch(e) {{}}
      warn.apply(console, args);
    }};
  }})();
  
  function initMap() {{
    try {{
      const aub = {{lat: 33.8993, lng: 35.4839}};
      
      map = new google.maps.Map(document.getElementById('map'), {{
        center: aub,
        zoom: 14,
        mapTypeControl: true,
        streetViewControl: true,
        fullscreenControl: true
      }});
      
      // Click marker
      clickMarker = new google.maps.Marker({{
        position: aub,
        map: map,
        title: 'Selected Location',
        icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
      }});
      
      // AUB marker
      new google.maps.Marker({{
        position: aub,
        map: map,
        title: 'American University of Beirut',
        icon: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
      }});
      
      // Directions
      directionsService = new google.maps.DirectionsService();
      directionsRenderer = new google.maps.DirectionsRenderer({{
        suppressMarkers: false,
        polylineOptions: {{ strokeColor: '#0066cc', strokeWeight: 4 }}
      }});
      directionsRenderer.setMap(map);
      
      // Click handler
      map.addListener('click', function(e) {{
        const lat = e.latLng.lat();
        const lng = e.latLng.lng();
        clickMarker.setPosition(e.latLng);
        if(bridge?.reportCoordinates) bridge.reportCoordinates(lat, lng);
      }});
      
      console.log('Map initialized successfully');
    }} catch(err) {{
      document.getElementById('error').style.display = 'block';
      console.error('Map init error:', err);
    }}
  }}
  
  function clearMarkers() {{
    markers.forEach(m => m.setMap(null));
    markers = [];
  }}
  
  function addDriverMarkers(data) {{
    try {{
      const arr = typeof data === 'string' ? JSON.parse(data) : data;
      clearMarkers();
      
      const bounds = new google.maps.LatLngBounds();
      
      arr.forEach((item, i) => {{
        if(!item.lat || !item.lng) return;
        
        const pos = new google.maps.LatLng(item.lat, item.lng);
        const marker = new google.maps.Marker({{
          position: pos,
          map: map,
          label: {{
            text: item.label || String(i+1),
            color: 'white',
            fontWeight: 'bold'
          }},
          title: item.title || 'Driver',
          icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
        }});
        
        const infoWindow = new google.maps.InfoWindow({{
          content: `<div style="padding:8px;"><b>${{item.title || 'Driver'}}</b></div>`
        }});
        
        marker.addListener('click', () => infoWindow.open(map, marker));
        markers.push(marker);
        bounds.extend(pos);
      }});
      
      if(arr.length > 0) {{
        map.fitBounds(bounds);
        if(arr.length === 1) map.setZoom(15);
      }}
      
      console.log('Added', arr.length, 'driver markers');
    }} catch(e) {{
      console.error('addDriverMarkers error:', e);
    }}
  }}
  
  function drawRoute(oLat, oLng, dLat, dLng) {{
    try {{
      const req = {{
        origin: new google.maps.LatLng(oLat, oLng),
        destination: new google.maps.LatLng(dLat, dLng),
        travelMode: google.maps.TravelMode.DRIVING
      }};
      
      directionsService.route(req, function(result, status) {{
        if(status === 'OK') {{
          directionsRenderer.setDirections(result);
          console.log('Route drawn successfully');
        }} else {{
          console.error('Directions error:', status);
        }}
      }});
    }} catch(e) {{
      console.error('drawRoute error:', e);
    }}
  }}
  
  function clearRoute() {{
    directionsRenderer.setDirections({{routes: []}});
  }}
  
  window.onload = initMap;
</script>
</body>
</html>
"""
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    def on_map_click(self, lat, lng):
        """Handle map click event"""
        self.coord_label.setText(f"📍 {lat:.6f}, {lng:.6f}")
        self.weather_label.setText("Click 'Refresh Weather' to get forecast")
    
    def on_map_console_message(self, msg):
        """Handle console messages from JavaScript"""
        self.dev_console.append(msg)
        try:
            j = json.loads(msg)
            if j.get('type') == 'error':
                self.dev_console.parent().setChecked(True)
        except:
            pass
    
    # ========================================================================
    # PRESET LOCATION HANDLERS
    # ========================================================================
    def set_preset_location(self, lat, lng, name):
        """Set a preset location and fetch weather"""
        self.map_bridge.last_lat = lat
        self.map_bridge.last_lng = lng
        self.coord_label.setText(f"📍 {lat:.6f}, {lng:.6f} ({name})")
        self.weather_label.setText("Fetching weather...")
        
        # Auto-refresh weather
        self.refresh_weather()
        
        # If using folium, update the map marker
        if not GOOGLE_API_KEY:
            self.update_folium_marker(lat, lng, name)
        else:
            # Update Google Maps marker
            js = f"if(clickMarker) clickMarker.setPosition({{lat: {lat}, lng: {lng}}});"
            self.map_view.page().runJavaScript(js)
    
    def update_folium_marker(self, lat, lng, name):
        """Update folium map with new marker (requires map reload)"""
        try:
            m = folium.Map(location=[lat, lng], zoom_start=14)
            folium.Marker([lat, lng], tooltip=name, 
                         popup=f"{name}<br>{lat:.6f}, {lng:.6f}").add_to(m)
            
            # Add AUB marker if we're not already at AUB
            if name != "AUB":
                folium.Marker([33.9006, 35.4812], tooltip='AUB',
                             icon=folium.Icon(color='blue')).add_to(m)
            
            # Add click popup
            m.add_child(folium.LatLngPopup())
            
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            m.save(tmp.name)
            self.map_view.load(QUrl.fromLocalFile(tmp.name))
            self.status_bar.showMessage(f"Map updated to {name} 📍")
        except Exception as e:
            self.status_bar.showMessage(f"Could not update map: {e}")
    
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    def handle_login(self):
        """Handle login"""
        username = self.login_username.text().strip()
        password = self.login_password.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter username and password")
            return
        
        payload = {
            "action": "login",
            "type_of_connection": "login",
            "userName": username,
            "password": password
        }
        
        response = send_request_to_gateway(payload)
        
        if str(response.get("status")) in ("200", "201"):
            # Get full user info
            user_id = response.get("userID")
            user_info_req = {
                "action": "update_personal_info",
                "type_of_connection": "give_user_personal_informations",
                "userID": user_id
            }
            user_info = send_request_to_gateway(user_info_req)
            
            is_driver = False
            if user_info.get("status") == "200":
                data = user_info.get("data", {})
                is_driver = data.get("isDriver", False)
            
            self.user = {
                "userID": user_id,
                "username": username,
                "email": response.get("email"),
                "isDriver": is_driver
            }
            
            # Register IP
            try:
                my_ip = socket.gethostbyname(socket.gethostname())
                reg_payload = {
                    "action": "register_ip",
                    "userID": user_id,
                    "ip": my_ip,
                    "port": None
                }
                send_request_to_gateway(reg_payload)
            except:
                pass
            
            # Update UI
            role = "Driver" if is_driver else "Passenger"
            self.user_info_label.setText(f"👤 {username} ({role})")
            self.status_bar.showMessage(f"Logged in as {username} ✅")
            
            # Enable appropriate tabs
            if is_driver:
                self.tabs.setTabEnabled(1, True)
                self.tabs.setCurrentIndex(1)
            else:
                self.tabs.setTabEnabled(2, True)
                self.tabs.setCurrentIndex(2)
            
            QMessageBox.information(self, "Success", f"Welcome, {username}!")
            
        else:
            QMessageBox.warning(self, "Login Failed", 
                              response.get("message", "Invalid credentials"))
    
    def handle_signup(self):
        """Handle signup"""
        username = self.signup_username.text().strip()
        password = self.signup_password.text().strip()
        email = self.signup_email.text().strip()
        aub_id = self.signup_aub_id.text().strip()
        zone = self.signup_zone.text().strip()
        is_driver = self.signup_is_driver.isChecked()
        
        if not all([username, password, email, aub_id, zone]):
            QMessageBox.warning(self, "Input Error", "Please fill all fields")
            return
        
        payload = {
            "action": "sign_up",
            "type_of_connection": "signUp",
            "userName": username,
            "password": password,
            "email": email,
            "isDriver": is_driver,
            "aubID": aub_id,
            "zone": zone
        }
        
        response = send_request_to_gateway(payload)
        
        if str(response.get("status")) == "201":
            QMessageBox.information(self, "Success", 
                                  "Account created successfully! Please login.")
            # Clear fields
            self.signup_username.clear()
            self.signup_password.clear()
            self.signup_email.clear()
            self.signup_aub_id.clear()
            self.signup_zone.clear()
            self.signup_is_driver.setChecked(False)
        else:
            QMessageBox.warning(self, "Signup Failed", 
                              response.get("message", "Could not create account"))
    
    # ========================================================================
    # DRIVER FUNCTIONS
    # ========================================================================
    def handle_add_ride(self):
        """Handle add ride for drivers"""
        if not self.user:
            QMessageBox.warning(self, "Error", "Please login first")
            return
        
        source = self.driver_source.text().strip()
        dest = self.driver_dest.text().strip()
        start = self.driver_start_time.time().toString("HH:mm")
        end = self.driver_end_time.time().toString("HH:mm")
        car_id = self.driver_car_id.text().strip() or None
        
        if not source or not dest:
            QMessageBox.warning(self, "Input Error", 
                              "Please enter source and destination")
            return
        
        # Get coordinates if checkbox is checked
        pickup_lat = None
        pickup_lng = None
        if self.driver_use_map_coords.isChecked():
            if self.map_bridge.last_lat and self.map_bridge.last_lng:
                pickup_lat = self.map_bridge.last_lat
                pickup_lng = self.map_bridge.last_lng
            else:
                reply = QMessageBox.question(self, "No Coordinates", 
                    "No map location selected. Continue without coordinates?",
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return
        
        payload = {
            "action": "update_personal_info",
            "type_of_connection": "add_ride",
            "userID": self.user["userID"],
            "carId": car_id,
            "source": source,
            "destination": dest,
            "startTime": start,
            "endTime": end,
            "scheduleID": None,
            "pickup_lat": pickup_lat,
            "pickup_lng": pickup_lng
        }
        
        response = send_request_to_gateway(payload)
        
        if str(response.get("status")) in ("200", "201"):
            QMessageBox.information(self, "Success", "Ride added successfully!")
            self.driver_source.clear()
            self.driver_dest.clear()
            self.status_bar.showMessage("Ride added ✅")
        else:
            QMessageBox.warning(self, "Error", 
                              response.get("message", "Failed to add ride"))
    
    def refresh_requests(self):
        """Refresh pending ride requests for driver"""
        if not self.user:
            return
        
        payload = {
            "action": "get_requests",
            "driver_userid": self.user["userID"]
        }
        
        response = send_request_to_gateway(payload)
        
        self.requests_list.clear()
        
        if response.get("status") == "200":
            requests = response.get("requests", [])
            self.pending_requests = requests
            
            for req in requests:
                req_id = req.get("requestID", "")
                rider_id = req.get("riderID", "")
                area = req.get("area", "")
                req_time = req.get("reqTime", "")
                
                item_text = f"🎫 {req_id} | 👤 Rider: {rider_id} | 📍 {area} | ⏰ {req_time}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, req)
                self.requests_list.addItem(item)
            
            self.status_bar.showMessage(f"Found {len(requests)} pending requests")
        else:
            self.status_bar.showMessage("No pending requests")
    
    def accept_selected_request(self, item):
        """Accept a ride request"""
        if not self.user:
            return
        
        request = item.data(Qt.UserRole)
        req_id = request.get("requestID")
        rider_id = request.get("riderID")
        
        reply = QMessageBox.question(self, "Confirm", 
            f"Accept ride request from rider {rider_id}?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            payload = {
                "action": "accept_ride",
                "requestID": req_id,
                "driver_userid": self.user["userID"]
            }
            
            response = send_request_to_gateway(payload)
            
            if response.get("status") == "200":
                passenger = response.get("passenger", {})
                ride_id = response.get("rideID", "")
                
                msg = f"✅ Request accepted!\n\n"
                msg += f"Passenger: {passenger.get('username', 'N/A')}\n"
                msg += f"Email: {passenger.get('email', 'N/A')}\n"
                msg += f"IP: {passenger.get('ip', 'N/A')}\n"
                msg += f"Ride ID: {ride_id}"
                
                QMessageBox.information(self, "Success", msg)
                self.refresh_requests()
                self.status_bar.showMessage("Request accepted ✅")
            else:
                QMessageBox.warning(self, "Error", 
                    response.get("message", "Failed to accept request"))
    
    def toggle_auto_refresh(self, checked):
        """Toggle auto-refresh for driver requests"""
        if checked:
            self.refresh_timer.start(10000)  # 10 seconds
            self.refresh_requests()
            self.status_bar.showMessage("Auto-refresh enabled (10s)")
        else:
            self.refresh_timer.stop()
            self.status_bar.showMessage("Auto-refresh disabled")
    
    def auto_refresh_requests(self):
        """Auto-refresh callback"""
        if self.user and self.user.get("isDriver"):
            self.refresh_requests()
    
    # ========================================================================
    # PASSENGER FUNCTIONS
    # ========================================================================
    def handle_request_ride(self):
        """Handle ride request for passengers"""
        if not self.user:
            QMessageBox.warning(self, "Error", "Please login first")
            return
        
        area = self.passenger_area.text().strip()
        time_str = self.passenger_time.time().toString("HH:mm")
        direction = self.passenger_direction.currentText()
        
        # Use map coordinates if checkbox is checked
        if self.passenger_use_map.isChecked():
            if self.map_bridge.last_lat and self.map_bridge.last_lng:
                area = f"{self.map_bridge.last_lat:.6f},{self.map_bridge.last_lng:.6f}"
            else:
                QMessageBox.warning(self, "No Location", 
                    "Please click the map to select a location first")
                return
        
        if not area:
            QMessageBox.warning(self, "Input Error", "Please enter an area or use map")
            return
        
        payload = {
            "action": "request_ride",
            "riderID": self.user["userID"],
            "area": area,
            "time": time_str,
            "direction": direction
        }
        
        response = send_request_to_gateway(payload)
        
        if response.get("status") == "200":
            candidates = response.get("candidates", [])
            self.current_candidates = candidates
            self.current_request_id = response.get("requestID")
            
            self.drivers_list.clear()
            drivers_for_map = []
            
            for idx, candidate in enumerate(candidates, 1):
                driver = candidate.get("owner_username", "Unknown")
                source = candidate.get("ride_source", "N/A")
                dest = candidate.get("ride_destination", "N/A")
                distance = candidate.get("distance_text", 
                          f"{candidate.get('distance_m', 0):.0f}m")
                duration = candidate.get("duration_text", "N/A")
                
                item_text = (f"🚗 #{idx} {driver} | 📍 {source} → {dest} | "
                           f"📏 {distance} | ⏱ {duration}")
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, candidate)
                self.drivers_list.addItem(item)
                
                # Prepare for map
                lat = candidate.get("ride_lat")
                lng = candidate.get("ride_lng")
                if lat and lng:
                    drivers_for_map.append({
                        "lat": lat,
                        "lng": lng,
                        "label": str(idx),
                        "title": f"{driver} - {source}"
                    })
            
            # Add markers to map
            if drivers_for_map and GOOGLE_API_KEY:
                js = f"addDriverMarkers({json.dumps(drivers_for_map)});"
                self.map_view.page().runJavaScript(js)
            
            msg = f"Found {len(candidates)} available driver(s)!"
            QMessageBox.information(self, "Success", msg)
            self.status_bar.showMessage(f"{len(candidates)} drivers found ✅")
            
        else:
            QMessageBox.warning(self, "No Drivers", 
                response.get("message", "No drivers found matching your criteria"))
            self.status_bar.showMessage("No drivers found ❌")
    
    def accept_selected_driver(self, item):
        """Accept a driver"""
        candidate = item.data(Qt.UserRole)
        driver = candidate.get("owner_username", "Unknown")
        ride_id = candidate.get("rideID")
        
        reply = QMessageBox.question(self, "Confirm", 
            f"Accept ride from {driver}?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Note: The backend might need enhancement for passenger accepting
            # For now, we'll show the driver info
            msg = f"✅ Ride accepted!\n\n"
            msg += f"Driver: {driver}\n"
            msg += f"Source: {candidate.get('ride_source', 'N/A')}\n"
            msg += f"Destination: {candidate.get('ride_destination', 'N/A')}\n"
            msg += f"Ride ID: {ride_id}"
            
            if candidate.get("distance_text"):
                msg += f"\nDistance: {candidate['distance_text']}"
            if candidate.get("duration_text"):
                msg += f"\nDuration: {candidate['duration_text']}"
            
            QMessageBox.information(self, "Ride Accepted", msg)
            self.status_bar.showMessage(f"Ride accepted with {driver} ✅")
    
    def show_route_to_driver(self):
        """Show route to selected driver on map"""
        item = self.drivers_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a driver first")
            return
        
        if not GOOGLE_API_KEY:
            QMessageBox.warning(self, "Map Unavailable", 
                "Google Maps API key required for route display")
            return
        
        candidate = item.data(Qt.UserRole)
        driver_lat = candidate.get("ride_lat")
        driver_lng = candidate.get("ride_lng")
        
        if not driver_lat or not driver_lng:
            QMessageBox.warning(self, "No Coordinates", 
                "Driver location coordinates not available")
            return
        
        # Use current map selection or passenger area
        if self.map_bridge.last_lat and self.map_bridge.last_lng:
            origin_lat = self.map_bridge.last_lat
            origin_lng = self.map_bridge.last_lng
        else:
            QMessageBox.warning(self, "No Origin", 
                "Please click the map to set your location first")
            return
        
        js = f"drawRoute({origin_lat}, {origin_lng}, {driver_lat}, {driver_lng});"
        self.map_view.page().runJavaScript(js)
        self.status_bar.showMessage("Route displayed on map 🗺")
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    def refresh_weather(self):
        """Refresh weather for selected location"""
        lat = self.map_bridge.last_lat
        lng = self.map_bridge.last_lng
        
        if lat is None or lng is None:
            QMessageBox.warning(self, "No Location", 
                "Please click the map to select a location first")
            return
        
        payload = {
            "action": "get_weather",
            "latitude": lat,
            "longitude": lng
        }
        
        response = send_request_to_gateway(payload)
        
        if isinstance(response, dict):
            if response.get("weather"):
                # OpenWeather format
                try:
                    weather_list = response.get("weather", [{}])
                    main = response.get("main", {})
                    
                    desc = weather_list[0].get("description", "N/A")
                    temp = main.get("temp", "N/A")
                    feels_like = main.get("feels_like", "N/A")
                    humidity = main.get("humidity", "N/A")
                    
                    weather_text = (f"🌤 {desc.title()}\n"
                                  f"🌡 {temp}°C (feels {feels_like}°C)\n"
                                  f"💧 Humidity: {humidity}%")
                    self.weather_label.setText(weather_text)
                    self.status_bar.showMessage("Weather updated ✅")
                except:
                    self.weather_label.setText(str(response))
            elif response.get("status"):
                self.weather_label.setText(response.get("message", "Error"))
            else:
                self.weather_label.setText("Unexpected response format")
        else:
            self.weather_label.setText(str(response))
    
    def test_connection(self):
        """Test connection to gateway"""
        try:
            host = self.gateway_host_input.text().strip()
            port = int(self.gateway_port_input.text().strip())
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((host, port))
            s.close()
            
            QMessageBox.information(self, "Connection Test", 
                f"✅ Successfully connected to {host}:{port}")
            self.status_bar.showMessage(f"Gateway connection OK ✅")
        except Exception as e:
            QMessageBox.critical(self, "Connection Test Failed", 
                f"❌ Could not connect to gateway:\n{str(e)}")
            self.status_bar.showMessage("Gateway connection failed ❌")
    
    # ========================================================================
    # STYLING
    # ========================================================================
    def get_stylesheet(self):
        """Return application stylesheet"""
        return """
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
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMiAxMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMSA1bDMgMyA3LTciIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgZmlsbD0ibm9uZSIvPjwvc3ZnPg==);
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
        """

# ============================================================================
# MAIN
# ============================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AUBus Ultimate")
    app.setStyle('Fusion')
    
    window = AUBusUltimateGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()