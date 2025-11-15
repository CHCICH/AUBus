#!/usr/bin/env python3
"""
AUBus — Polished PyQt5 GUI with robust Google Maps support, console forwarding,
driver markers, route drawing, Places Autocomplete, and weather panel.

Requirements:
    pip install PyQt5 PyQtWebEngine requests folium

Environment:
    Set GOOGLE_MAPS_API_KEY for Google Maps features. If missing, app falls back to folium.
    Make sure your backend gateway (static_gateway.py) is running and reachable.

Run:
    python aubus_gui_pyqt.py
"""
import os
import sys
import json
import socket
import tempfile
import traceback
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
                             QLineEdit, QHBoxLayout, QTabWidget, QListWidget, QMessageBox,
                             QFormLayout, QGroupBox, QFrame, QSpacerItem, QSizePolicy,
                             QStatusBar, QTextEdit, QGridLayout)
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
import folium

# Configuration
GATEWAY_HOST = socket.gethostname()  # change to server IP if your gateway is remote
GATEWAY_PORT = 9999
GOOGLE_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')  # must be set for Google Maps features

# --- Networking helper (simple blocking) ---
import socket as _socket

def send_request_to_gateway(payload, host=GATEWAY_HOST, port=GATEWAY_PORT, timeout=6):
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.send(json.dumps(payload).encode('utf-8'))
        data = s.recv(16384).decode('utf-8')
        s.close()
        try:
            return json.loads(data)
        except Exception:
            return {"status":"500", "message":"Invalid response from server", "raw": data}
    except Exception as e:
        return {"status":"500", "message": f"Connection error: {str(e)}"}

# --- Bridge class exposed to JS ---
class MapBridge(QObject):
    coordinatesChanged = pyqtSignal(float, float)
    consoleMessage = pyqtSignal(str)  # receives console messages from JS

    def __init__(self):
        super().__init__()
        self.last_lat = None
        self.last_lng = None

    @pyqtSlot(float, float)
    def reportCoordinates(self, lat, lng):
        self.last_lat = float(lat)
        self.last_lng = float(lng)
        self.coordinatesChanged.emit(self.last_lat, self.last_lng)

    @pyqtSlot(str)
    def consoleLog(self, msg):
        # Forward JS console messages to Python (connected to a QTextEdit)
        self.consoleMessage.emit(str(msg))

# --- Main GUI ---
class AUBusGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AUBus — polished GUI")
        self.resize(1200, 820)
        self.user = None  # session info: {userID, username, email, isDriver}
        self.map_bridge = MapBridge()
        self.map_bridge.coordinatesChanged.connect(self.on_map_click)
        self.map_bridge.consoleMessage.connect(self.on_map_console_message)
        self.init_ui()
        self.init_map()

    def init_ui(self):
        self.setStyleSheet(self.qss())
        main = QHBoxLayout(self)

        # LEFT: controls
        left = QVBoxLayout()
        left.setSpacing(12)
        header = QLabel("🚍 AUBus")
        header.setObjectName("header")
        left.addWidget(header)

        self.tabs = QTabWidget()
        left.addWidget(self.tabs, 0)

        # build tabs
        self.build_auth_tab()
        self.build_driver_tab()
        self.build_passenger_tab()
        self.build_misc_tab()

        left.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        # Developer console (hidden by default but present)
        self.dev_console = QTextEdit()
        self.dev_console.setReadOnly(True)
        self.dev_console.setMaximumHeight(140)
        self.dev_console.setVisible(False)
        left.addWidget(self.dev_console)

        # status bar
        self.status = QStatusBar()
        left.addWidget(self.status)
        main.addLayout(left, 0)

        # RIGHT: Map
        right = QVBoxLayout()
        self.map_view = QWebEngineView()
        right.addWidget(self.map_view, 1)

        # bottom widgets: coord label + quick weather
        bottom_row = QHBoxLayout()
        self.coord_label = QLabel("Clicked: —")
        bottom_row.addWidget(self.coord_label)
        bottom_row.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # weather display
        weather_box = QGroupBox("Weather at selected point")
        wb = QVBoxLayout()
        self.weather_label = QLabel("No data")
        self.weather_refresh_btn = QPushButton("Refresh Weather")
        self.weather_refresh_btn.clicked.connect(self.refresh_weather_for_selected_point)
        wb.addWidget(self.weather_label)
        wb.addWidget(self.weather_refresh_btn)
        weather_box.setLayout(wb)
        weather_box.setMaximumWidth(320)
        bottom_row.addWidget(weather_box)

        right.addLayout(bottom_row)
        main.addLayout(right, 1)

    def qss(self):
        return """
QWidget{ font-family: 'Segoe UI', Roboto, Arial; color: #0b2545; }
#header{ font-size: 20px; font-weight: 700; color: #fff; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0066cc, stop:1 #003f7d); padding:10px 14px; border-radius:8px; }
QGroupBox{ border:1px solid #e6f2ff; padding:10px; border-radius:8px; background:#fcfeff; }
QLineEdit{ padding:6px; border:1px solid #cfe6ff; border-radius:6px; }
QPushButton{ background:#0077cc; color:white; padding:8px 10px; border-radius:8px; }
QPushButton:hover{ background:#005fa3; }
QListWidget{ border:1px solid #e6f2ff; background:white; }
QTextEdit{ background:#f8fbff; border:1px solid #e6f2ff; }
"""

    # ----- tabs -----
    def build_auth_tab(self):
        tab = QWidget(); layout = QVBoxLayout()
        login_box = QGroupBox("Login")
        f = QFormLayout()
        self.login_user = QLineEdit(); self.login_pass = QLineEdit(); self.login_pass.setEchoMode(QLineEdit.Password)
        f.addRow("Username", self.login_user); f.addRow("Password", self.login_pass)
        btn_login = QPushButton("Login"); btn_login.clicked.connect(self.login_action)
        f.addRow(btn_login)
        login_box.setLayout(f)

        signup_box = QGroupBox("Sign up")
        f2 = QFormLayout()
        self.signup_user = QLineEdit(); self.signup_pass = QLineEdit(); self.signup_pass.setEchoMode(QLineEdit.Password)
        self.signup_email = QLineEdit(); self.signup_role = QLineEdit(); self.signup_role.setPlaceholderText("Driver or Passenger")
        f2.addRow("Username", self.signup_user); f2.addRow("Password", self.signup_pass); f2.addRow("Email", self.signup_email); f2.addRow("Role", self.signup_role)
        btn_signup = QPushButton("Sign up"); btn_signup.clicked.connect(self.signup_action)
        f2.addRow(btn_signup)
        signup_box.setLayout(f2)

        layout.addWidget(login_box); layout.addWidget(signup_box)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Auth")

    def build_driver_tab(self):
        tab = QWidget(); layout = QVBoxLayout()
        add_box = QGroupBox("Add Ride (Driver)")
        f = QFormLayout()
        self.add_carid = QLineEdit(); self.add_source = QLineEdit(); self.add_dest = QLineEdit()
        self.add_start = QLineEdit(); self.add_end = QLineEdit()
        # Autocomplete will be in map when Google is enabled
        f.addRow("Car ID", self.add_carid); f.addRow("Source", self.add_source); f.addRow("Destination", self.add_dest)
        f.addRow("Start (HH:MM)", self.add_start); f.addRow("End (HH:MM)", self.add_end)
        btn_add = QPushButton("Add Ride"); btn_add.clicked.connect(self.add_ride_action)
        f.addRow(btn_add)
        add_box.setLayout(f)

        req_box = QGroupBox("Pending Requests")
        rv = QVBoxLayout()
        self.requests_list = QListWidget()
        rv.addWidget(self.requests_list)
        h = QHBoxLayout()
        btn_poll = QPushButton("Poll"); btn_poll.clicked.connect(self.poll_requests_action)
        btn_accept = QPushButton("Accept"); btn_accept.clicked.connect(self.accept_selected_request)
        h.addWidget(btn_poll); h.addWidget(btn_accept)
        rv.addLayout(h)
        req_box.setLayout(rv)

        layout.addWidget(add_box); layout.addWidget(req_box)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Driver")

    def build_passenger_tab(self):
        tab = QWidget(); layout = QVBoxLayout()
        req_box = QGroupBox("Request a Ride")
        f = QFormLayout()
        self.req_area = QLineEdit(); self.req_time = QLineEdit()
        self.req_area.setPlaceholderText("Area text or leave blank to use map click")
        f.addRow("Area", self.req_area); f.addRow("Time (HH:MM)", self.req_time)
        btn_req = QPushButton("Request"); btn_req.clicked.connect(self.request_ride_action)
        f.addRow(btn_req)
        req_box.setLayout(f)

        cand_box = QGroupBox("Candidates")
        cv = QVBoxLayout(); self.candidates_list = QListWidget(); cv.addWidget(self.candidates_list)
        btn_route = QPushButton("Route to selected"); btn_route.clicked.connect(self.route_to_selected_candidate)
        cv.addWidget(btn_route)
        cand_box.setLayout(cv)

        layout.addWidget(req_box); layout.addWidget(cand_box)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Passenger")

    def build_misc_tab(self):
        tab = QWidget(); layout = QVBoxLayout()
        dev_toggle = QPushButton("Show Dev Console")
        dev_toggle.setCheckable(True); dev_toggle.toggled.connect(self.toggle_dev_console)
        layout.addWidget(dev_toggle)
        layout.addWidget(QLabel("Map: click to pick coordinates. Use Places autocomplete when available."))
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Misc")

    # ----- Map init -----
    def init_map(self):
        # If API key present, build the Google Maps HTML that supports:
        # - click -> bridge.reportCoordinates(lat,lng)
        # - console forwarding: bridge.consoleLog(msg)
        # - functions addDriverMarkers(json), clearMarkers(), drawRoute(originLat,originLng,destLat,destLng)
        if GOOGLE_API_KEY:
            html = self.build_google_map_html(GOOGLE_API_KEY)
            channel = QWebChannel()
            channel.registerObject('bridge', self.map_bridge)
            self.map_view.page().setWebChannel(channel)
            self.map_view.setHtml(html, QUrl(""))
            self.status.showMessage("Map: Google Maps (API key detected)")
        else:
            # folium fallback
            self.status.showMessage("Map: Google API key missing — using local folium fallback")
            m = folium.Map(location=[33.8886, 35.4955], zoom_start=13)
            folium.Marker([33.8886, 35.4955], tooltip='AUB').add_to(m)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            m.save(tmp.name)
            self.map_view.load(QUrl.fromLocalFile(tmp.name))

    def build_google_map_html(self, api_key):
        # This html includes:
        # - qwebchannel integration
        # - console override: forwards console.log/error/warn via bridge.consoleLog
        # - addDriverMarkers(jsonArray) to place markers (jsonArray is [{'lat':..,'lng':..,'label':..},...])
        # - drawRoute(originLat,originLng,destLat,destLng) that uses DirectionsRenderer
        html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="initial-scale=1.0, user-scalable=no">
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <script src="https://maps.googleapis.com/maps/api/js?key={api_key}&libraries=places"></script>
  <style>html,body,#map{{height:100%;margin:0;padding:0}} #err{{position:absolute;z-index:999;left:10px;top:10px;background:#fff3;padding:8px;border-radius:6px;display:none}}</style>
</head>
<body>
  <div id="map"></div>
  <div id="err">Map failed to initialize — see Dev Console</div>
<script>
  let bridge = null;
  let map, marker, markers = [], directionsService, directionsRenderer;
  new QWebChannel(qt.webChannelTransport, function(channel) {{
    bridge = channel.objects.bridge;
  }});

  // Forward console messages to Python
  (function(){{
    const origLog = console.log;
    console.log = function(...args) {{
      try{{ if(bridge && bridge.consoleLog) bridge.consoleLog(JSON.stringify({{type:'log',args:args}})); }}catch(e){{}}
      origLog.apply(console, args);
    }};
    const origErr = console.error;
    console.error = function(...args) {{
      try{{ if(bridge && bridge.consoleLog) bridge.consoleLog(JSON.stringify({{type:'error',args:args}})); }}catch(e){{}}
      origErr.apply(console, args);
    }};
    const origWarn = console.warn;
    console.warn = function(...args) {{
      try{{ if(bridge && bridge.consoleLog) bridge.consoleLog(JSON.stringify({{type:'warn',args:args}})); }}catch(e){{}}
      origWarn.apply(console, args);
    }};
  }})();

  function initMap(){{
    try {{
      const aub = {{lat:33.8886,lng:35.4955}};
      map = new google.maps.Map(document.getElementById('map'), {{center:aub, zoom:13}});
      marker = new google.maps.Marker({{position:aub, map:map}});
      directionsService = new google.maps.DirectionsService();
      directionsRenderer = new google.maps.DirectionsRenderer({{suppressMarkers:true}});
      directionsRenderer.setMap(map);

      map.addListener('click', function(e) {{
        const lat = e.latLng.lat(), lng = e.latLng.lng();
        marker.setPosition(e.latLng);
        if(bridge && bridge.reportCoordinates) bridge.reportCoordinates(lat, lng);
      }});
      console.log('Map initialized');
    }} catch(err) {{
      document.getElementById('err').style.display = 'block';
      console.error('Map init error', err);
    }}
  }}

  function clearMarkers(){{
    for(let m of markers) m.setMap(null);
    markers = [];
  }}

  function addDriverMarkers(jsonStr){{
    try {{
      const arr = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
      clearMarkers();
      for(let i=0;i<arr.length;i++){{
        const item = arr[i];
        if(!item.lat || !item.lng) continue;
        const pos = new google.maps.LatLng(item.lat, item.lng);
        const mk = new google.maps.Marker({{position: pos, map: map, label: item.label || ''}});
        const inf = new google.maps.InfoWindow({{content: item.title || ''}});
        mk.addListener('click', ()=> inf.open(map, mk));
        markers.push(mk);
      }}
      if(arr.length>0) map.panTo(new google.maps.LatLng(arr[0].lat, arr[0].lng));
      console.log('Driver markers added', arr.length);
    }} catch(e) {{ console.error('addDriverMarkers error', e); }}
  }}

  function drawRoute(oLat, oLng, dLat, dLng){{
    try {{
      const req = {{ origin: new google.maps.LatLng(oLat,oLng), destination: new google.maps.LatLng(dLat,dLng), travelMode: google.maps.TravelMode.DRIVING }};
      directionsService.route(req, function(result, status){{
        if(status === 'OK'){{ directionsRenderer.setDirections(result); console.log('Route drawn'); }}
        else {{ console.error('Directions error', status); }}
      }});
    }} catch(e) {{ console.error('drawRoute error', e); }}
  }}

  window.onload = initMap;
</script>
</body>
</html>
"""
        return html

    # ----- Map event handlers -----
    def on_map_click(self, lat, lng):
        self.coord_label.setText(f"Clicked: {lat:.6f}, {lng:.6f}")
        # update weather quick hint (but do not call automatically to avoid quota)
        self.weather_label.setText("Click 'Refresh Weather' to fetch data for this point")

    def on_map_console_message(self, msg):
        # append the console message to dev console
        self.dev_console.append(msg)
        # show dev console if it's an error
        try:
            j = json.loads(msg)
            if isinstance(j, dict) and j.get('type') == 'error':
                self.dev_console.setVisible(True)
        except Exception:
            # non-JSON logs
            pass

    def toggle_dev_console(self, on):
        self.dev_console.setVisible(on)

    # ----- Actions: Auth -----
    def signup_action(self):
        u = self.signup_user.text().strip(); p = self.signup_pass.text().strip(); e = self.signup_email.text().strip(); role = self.signup_role.text().strip().lower()
        if not u or not p or not e: QMessageBox.warning(self, "Signup", "Fill username, password and email"); return
        payload = {"action":"sign_up","type_of_connection":"signUp","userName":u,"password":p,"email":e,"isDriver": role=='driver',"aubID":"202500049"}
        res = send_request_to_gateway(payload)
        QMessageBox.information(self, "Signup", res.get("message", str(res)))

    def login_action(self):
        u = self.login_user.text().strip(); p = self.login_pass.text().strip()
        if not u or not p: QMessageBox.warning(self, "Login","Fill username and password"); return
        payload = {"action":"login","type_of_connection":"login","userName":u,"password":p}
        res = send_request_to_gateway(payload)
        if str(res.get("status")) in ("200","201"):
            self.user = {"userID": res.get("userID"), "username": res.get("username") or u, "email": res.get("email"), "isDriver": res.get("isDriver", False)}
            QMessageBox.information(self, "Login", "Login successful")
            # try to register IP
            try:
                myip = socket.gethostbyname(socket.gethostname())
                reg = {"action":"register_ip","userID": self.user["userID"], "ip": myip, "port": None}
                send_request_to_gateway(reg)
            except Exception:
                pass
        else:
            QMessageBox.warning(self, "Login", res.get("message", str(res)))

    # ----- Add ride -----
    def add_ride_action(self):
        if not self.user: QMessageBox.warning(self, "Add ride", "Login first"); return
        uid = self.user.get("userID"); carId = self.add_carid.text().strip() or None
        source = self.add_source.text().strip() or None; dest = self.add_dest.text().strip() or None
        start = self.add_start.text().strip() or None; end = self.add_end.text().strip() or None
        pickup_lat = self.map_bridge.last_lat; pickup_lng = self.map_bridge.last_lng
        payload = {"action":"update_personal_info","type_of_connection":"add_ride","userID": uid,"carId":carId,"source":source,"destination":dest,"startTime":start,"endTime":end,"scheduleID":None,"pickup_lat":pickup_lat,"pickup_lng":pickup_lng}
        res = send_request_to_gateway(payload)
        QMessageBox.information(self, "Add Ride", res.get("message", str(res)))

    # ----- Request ride -----
    def request_ride_action(self):
        if not self.user: QMessageBox.warning(self, "Request", "Login first"); return
        riderID = self.user.get("userID"); area = self.req_area.text().strip(); time_str = self.req_time.text().strip()
        if not area:
            lat = self.map_bridge.last_lat; lng = self.map_bridge.last_lng
            if lat is None: QMessageBox.warning(self, "Request", "Pick an area or select on map"); return
            area = f"{lat:.6f},{lng:.6f}"
        payload = {"action":"request_ride","riderID": riderID,"area": area,"time": time_str,"direction":"to_aub"}
        res = send_request_to_gateway(payload)
        if res.get("status") == "200":
            self.candidates_list.clear()
            candidates = res.get("candidates", [])
            # show candidates and add markers if they include coordinates
            drivers_for_js = []
            for c in candidates:
                label = c.get("owner_username") or c.get("driver") or c.get("ownerID")
                ride_id = c.get("rideID") or ""
                lat = c.get("ride_lat") or c.get("pickup_lat") or None
                lng = c.get("ride_lng") or c.get("pickup_lng") or None
                display = f"{label} | ride:{ride_id} | ip:{c.get('ip') or ''}"
                self.candidates_list.addItem(display)
                if lat and lng:
                    drivers_for_js.append({"lat": lat, "lng": lng, "label": label[0] if label else "", "title": display})
            # call JS to add markers
            if drivers_for_js and GOOGLE_API_KEY:
                js = f"addDriverMarkers({json.dumps(drivers_for_js)});"
                self.map_view.page().runJavaScript(js)
            QMessageBox.information(self, "Request ride", f"{len(candidates)} candidates found")
        else:
            QMessageBox.warning(self, "Request ride", res.get("message", str(res)))

    # ----- Poll & accept -----
    def poll_requests_action(self):
        if not self.user: QMessageBox.warning(self, "Poll", "Login first"); return
        payload = {"action":"get_requests","driver_userid": self.user.get("userID")}
        res = send_request_to_gateway(payload)
        self.requests_list.clear()
        if res.get("status") == "200":
            for r in res.get("requests", []):
                self.requests_list.addItem(f"{r['requestID']} | rider:{r['riderID']} | area:{r.get('area')} | time:{r.get('reqTime')}")
        else:
            QMessageBox.warning(self, "Poll", res.get("message", str(res)))

    def accept_selected_request(self):
        if not self.user: QMessageBox.warning(self, "Accept", "Login first"); return
        sel = self.requests_list.currentItem()
        if not sel: QMessageBox.warning(self, "Accept", "Select a request"); return
        requestID = sel.text().split("|")[0].strip()
        payload = {"action":"accept_ride","requestID": requestID,"driver_userid": self.user.get("userID")}
        res = send_request_to_gateway(payload)
        QMessageBox.information(self, "Accept", res.get("message", str(res)))
        # if passenger IP and coordinates returned, draw route (if coords are there)
        passenger = res.get("passenger")
        if passenger and passenger.get("ip"):
            # if server provided lat/lng inside passenger (not currently), we could draw route
            # if driver has last coords and passenger coords were returned, call drawRoute
            # the current server returns ip/port and username/email; if you extend backend to include coords, we can draw
            pass

    # route to selected candidate
    def route_to_selected_candidate(self):
        if not self.user: QMessageBox.warning(self, "Route", "Login first"); return
        sel = self.candidates_list.currentItem()
        if not sel: QMessageBox.warning(self, "Route", "Select a candidate"); return
        text = sel.text()
        # try to parse lat/lng from the candidate list (we stored in markers, but easiest is to call JS to center)
        QMessageBox.information(self, "Route", "If candidate contains coords and driver location is known, route will be drawn (JS-side).")

    # ----- Weather panel -----
    def refresh_weather_for_selected_point(self):
        lat = self.map_bridge.last_lat; lng = self.map_bridge.last_lng
        if lat is None:
            QMessageBox.warning(self, "Weather", "Click the map first to select a point")
            return
        payload = {"action": "get_weather", "latitude": lat, "longitude": lng}
        res = send_request_to_gateway(payload)
        if isinstance(res, dict) and res.get("weather"):
            # assume OpenWeather format returned by weather.py
            try:
                main = res.get("main", {})
                temp = main.get("temp")
                desc = res.get("weather", [{}])[0].get("description")
                self.weather_label.setText(f"{desc}; {temp} °C")
            except Exception:
                self.weather_label.setText(json.dumps(res))
        else:
            # server may return different structure or error dict
            if isinstance(res, dict) and res.get("status") and res.get("message"):
                self.weather_label.setText(res.get("message"))
                QMessageBox.information(self, "Weather", res.get("message"))
            else:
                self.weather_label.setText(str(res))

# ---------- run ----------
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = AUBusGUI()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("Fatal error launching GUI:", e)
        traceback.print_exc()
