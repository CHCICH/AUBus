"""
AUBus Ultimate — Fixed Google Maps Integration
Key fixes:
- Improved Qt WebChannel communication
- Better coordinate handling
- Auto-fill location fields
- Fixed map click event propagation
- Added Profile Window
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
    QSplitter, QFrame, QSpacerItem, QSizePolicy, QComboBox, QScrollArea, QDialog
)
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl, Qt, QTime, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QFont, QIcon, QIntValidator

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    # Doesn't need to actually connect
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
finally:
    s.close()

# Configuration
GATEWAY_HOST = local_ip
GATEWAY_PORT = 9999
RIDE_SERVER_HOST = local_ip
RIDE_SERVER_PORT = 9998

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

GOOGLE_API_KEY = get_GGM_api_key()

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

def send_request_to_ride_server(payload, timeout=8):
    """Send JSON request to ride management server (port 9998)"""
    return send_request_to_gateway(payload, host=RIDE_SERVER_HOST, port=RIDE_SERVER_PORT, timeout=timeout)

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
        print(f"\n{'='*60}")
        print(f"[MapBridge] reportCoordinates() called!")
        print(f"[MapBridge] Latitude: {lat}")
        print(f"[MapBridge] Longitude: {lng}")
        print(f"{'='*60}\n")
        
        self.last_lat = float(lat)
        self.last_lng = float(lng)
        self.coordinatesChanged.emit(self.last_lat, self.last_lng)
    
    @pyqtSlot(str)
    def consoleLog(self, msg):
        """Forward JavaScript console messages to Python"""
        print(f"[JS Console] {msg}")
        self.consoleMessage.emit(str(msg))

# ============================================================================
# PROFILE WINDOW
# ============================================================================
class ProfileWindow(QDialog):
    def __init__(self, parent=None, user_data=None, send_static_request=None, isd = False):
        super().__init__(parent)
        self.user_data = user_data
        print(self.user_data)
        self.send_static_request = send_static_request
        self.selected_car_id = None
        self.selected_ride_id = None
        self.isd = isd
        
        self.setWindowTitle("My Profile")
        self.setGeometry(200, 200, 800, 700)
        self.setStyleSheet(self.get_stylesheet())
        self.init_ui()
        self.refresh_profile_data()
    
    def init_ui(self):
        """Initialize profile window UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("My Profile")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0066cc; margin: 10px;")
        layout.addWidget(title)
        
        # Create scroll area
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
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(close_btn)
        
        scroll_layout.addLayout(buttons_layout)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
    
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
        
        response = self.send_static_request(user_info_req)
        
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
        self.ride_history_list.clear()
        self.ride_history_list.addItem("Ride history feature coming soon!")

    def edit_profile(self):
        """Open profile editing dialog based on user role"""
        if not self.user_data:
            QMessageBox.warning(self, "Error", "Please login first")
            return
        
        # Create editing dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Profile")
        dialog.setModal(True)
        
        if self.user_data.get('isDriver'):
            dialog.resize(600, 700)  # Larger for driver
            self.create_driver_edit_dialog(dialog)
        else:
            dialog.resize(400, 300)  # Smaller for passenger
            self.create_passenger_edit_dialog(dialog)
        
        dialog.exec_()

    def create_passenger_edit_dialog(self, dialog):
        """Create passenger editing dialog"""
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
        save_btn.clicked.connect(lambda: self.save_driver_profile(dialog))
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

    def save_driver_profile(self, dialog):
        """Save driver profile changes"""
        self.save_passenger_profile(dialog)  # Use same logic for basic info

    def get_stylesheet(self):
        """Return profile window stylesheet"""
        return """
            QDialog {
                background-color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QLabel {
                color: #2c3e50;
                font-size: 13px;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0077cc, stop:1 #0066bb);
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-weight: 600;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0088dd, stop:1 #0077cc);
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
            
            QLineEdit, QComboBox, QTimeEdit {
                padding: 6px 10px;
                border: 2px solid #cfe6ff;
                border-radius: 6px;
                background: white;
            }
            
            QListWidget {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
        """

# ============================================================================
# MAIN APPLICATION
# ============================================================================
class AUBusUltimateGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AUBus Ultimate — Ride Sharing System")
        self.setGeometry(100, 50, 1400, 900)
        
        # Session data
        self.user = None
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
        # Delay map initialization to ensure UI is ready
        QTimer.singleShot(500, self.init_map)
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setStyleSheet(self.get_stylesheet())
        
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
        
        # Profile button
        self.profile_btn = QPushButton("👤 My Profile")
        self.profile_btn.clicked.connect(self.open_profile_window)
        self.profile_btn.setEnabled(False)
        layout.addWidget(self.profile_btn)
        
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
        bottom_bar.setMaximumHeight(250)
        bottom_layout = QHBoxLayout(bottom_bar)
        
        # Coordinates display with preset locations
        coord_group = QGroupBox("Selected Location")
        coord_layout = QVBoxLayout()
        self.coord_label = QLabel("Click map to select")
        self.coord_label.setWordWrap(True)
        coord_layout.addWidget(self.coord_label)
        
        # Add buttons to use coordinates
        use_btn_layout = QHBoxLayout()
        self.use_for_driver_btn = QPushButton("📝 Use for Driver Pickup")
        self.use_for_driver_btn.clicked.connect(self.use_coords_for_driver)
        self.use_for_driver_btn.setEnabled(False)
        
        self.use_for_passenger_btn = QPushButton("📝 Use for Passenger Area")
        self.use_for_passenger_btn.clicked.connect(self.use_coords_for_passenger)
        self.use_for_passenger_btn.setEnabled(False)
        
        use_btn_layout.addWidget(self.use_for_driver_btn)
        use_btn_layout.addWidget(self.use_for_passenger_btn)
        coord_layout.addLayout(use_btn_layout)
        
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
        
        self.driver_area = QLineEdit()
        self.driver_area.setPlaceholderText("Click 'Use for Driver Pickup' or click map to set location")
        
        self.driver_direction = QComboBox()
        self.driver_direction.addItems(["to_aub", "from_aub"])
        
        self.driver_start_time = QTimeEdit()
        self.driver_start_time.setDisplayFormat("HH:mm")
        self.driver_start_time.setTime(QTime(8, 0))
        self.driver_end_time = QTimeEdit()
        self.driver_end_time.setDisplayFormat("HH:mm")
        self.driver_end_time.setTime(QTime(16, 0))
        self.driver_car_id = QLineEdit()
        self.driver_car_id.setPlaceholderText("Optional")
        
        add_form.addRow("Pickup Area:", self.driver_area)
        add_form.addRow("Direction:", self.driver_direction)
        add_form.addRow("Start Time:", self.driver_start_time)
        add_form.addRow("End Time:", self.driver_end_time)
        add_form.addRow("Car ID:", self.driver_car_id)
        
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
        self.passenger_area.setPlaceholderText("Click 'Use for Passenger Area' to fill from map")
        self.passenger_time = QTimeEdit()
        self.passenger_time.setDisplayFormat("HH:mm")
        self.passenger_time.setTime(QTime(8, 15))
        self.passenger_direction = QComboBox()
        self.passenger_direction.addItems(["to_aub", "from_aub"])
        
        request_form.addRow("Area:", self.passenger_area)
        request_form.addRow("Time:", self.passenger_time)
        request_form.addRow("Direction:", self.passenger_direction)
        
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
        self.ride_server_host_input = QLineEdit(RIDE_SERVER_HOST)
        self.ride_server_port_input = QLineEdit(str(RIDE_SERVER_PORT))
        
        conn_form.addRow("Gateway Host:", self.gateway_host_input)
        conn_form.addRow("Gateway Port:", self.gateway_port_input)
        conn_form.addRow("Ride Server Host:", self.ride_server_host_input)
        conn_form.addRow("Ride Server Port:", self.ride_server_port_input)
        
        test_buttons = QHBoxLayout()
        test_gateway_btn = QPushButton("Test Gateway")
        test_gateway_btn.clicked.connect(self.test_gateway_connection)
        test_ride_btn = QPushButton("Test Ride Server")
        test_ride_btn.clicked.connect(self.test_ride_server_connection)
        test_buttons.addWidget(test_gateway_btn)
        test_buttons.addWidget(test_ride_btn)
        conn_form.addRow(test_buttons)
        
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
            "• Secure authentication\n"
            "• Dedicated ride management server\n\n"
            "Servers:\n"
            "• Port 9999: Authentication & User Management\n"
            "• Port 9998: Ride Management"
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
            # Enable web channel BEFORE anything else
            from PyQt5.QtWebEngineWidgets import QWebEngineSettings
            settings = self.map_view.settings()
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            
            # Create and set up the channel
            self.web_channel = QWebChannel(self.map_view.page())
            self.web_channel.registerObject('bridge', self.map_bridge)
            self.map_view.page().setWebChannel(self.web_channel)
            
            print("[Map] WebChannel created and registered")
            print(f"[Map] Bridge object: {self.map_bridge}")
            
            # Load HTML after a delay
            QTimer.singleShot(200, self._load_map_html)
        else:
            self.load_folium_fallback()
    
    def _load_map_html(self):
        """Load map HTML after channel is ready"""
        html = self.build_google_map_html()
        base_url = QUrl("qrc:///")
        self.map_view.setHtml(html, base_url)
        self.status_bar.showMessage("Map: Google Maps loading...")
        print("[Map] HTML loaded, waiting for JavaScript initialization...")
    
    def load_folium_fallback(self):
        """Load folium fallback map"""
        try:
            self.status_bar.showMessage("Map: Google API key missing — using local folium fallback")
            
            aub_lat, aub_lng = 33.9006, 35.4812
            
            m = folium.Map(location=[aub_lat, aub_lng], zoom_start=13)
            folium.Marker([aub_lat, aub_lng], tooltip='AUB').add_to(m)
            m.add_child(folium.LatLngPopup())
            
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            m.save(tmp.name)
            self.map_view.load(QUrl.fromLocalFile(tmp.name))
            
            self.map_bridge.last_lat = aub_lat
            self.map_bridge.last_lng = aub_lng
            self.coord_label.setText(f"📍 {aub_lat:.6f}, {aub_lng:.6f} (AUB)")
            self.refresh_weather()
            
        except ImportError:
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
        """Build Google Maps HTML with improved bridge communication"""
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
    #status {{
      position: absolute; z-index: 999; left: 10px; top: 10px;
      background: rgba(255,255,255,0.95); padding: 8px 12px;
      border-radius: 6px; font-size: 11px; font-family: monospace;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    }}
    .success {{ color: #27ae60; }}
    .error {{ color: #e74c3c; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="status">Initializing...</div>
<script>
  let bridge = null;
  let map, clickMarker, markers = [], directionsService, directionsRenderer;
  let bridgeReady = false;
  let initAttempts = 0;
  
  // Status display helper
  function setStatus(msg, isError = false) {{
    const status = document.getElementById('status');
    status.textContent = msg;
    status.className = isError ? 'error' : 'success';
    console.log('[MAP STATUS] ' + msg);
    setTimeout(() => {{
      if (!isError) status.style.display = 'none';
    }}, 3000);
  }}
  
  // Initialize Qt WebChannel bridge with retry logic
  function initBridge() {{
    console.log('[BRIDGE] Attempting to initialize bridge...');
    initAttempts++;
    
    try {{
      if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {{
        console.error('[BRIDGE] qt.webChannelTransport not available');
        if (initAttempts < 5) {{
          console.log('[BRIDGE] Retrying in 200ms... (attempt ' + initAttempts + ')');
          setTimeout(initBridge, 200);
          return;
        }} else {{
          setStatus('Bridge init failed after 5 attempts', true);
          return;
        }}
      }}
      
      new QWebChannel(qt.webChannelTransport, function(channel) {{
        console.log('[BRIDGE] QWebChannel callback triggered');
        bridge = channel.objects.bridge;
        
        if (!bridge) {{
          console.error('[BRIDGE] Bridge object is null');
          setStatus('Bridge object is null', true);
          return;
        }}
        
        bridgeReady = true;
        setStatus('Bridge connected ✓');
        console.log('[BRIDGE] Bridge initialized successfully');
        console.log('[BRIDGE] Bridge methods:', Object.keys(bridge));
        
        // Test the bridge
        if (bridge.consoleLog) {{
          bridge.consoleLog('[JS] Bridge test - connection verified');
        }} else {{
          console.warn('[BRIDGE] consoleLog method not found');
        }}
        
        if (bridge.reportCoordinates) {{
          console.log('[BRIDGE] reportCoordinates method found');
        }} else {{
          console.error('[BRIDGE] reportCoordinates method NOT found');
        }}
      }});
    }} catch(err) {{
      console.error('[BRIDGE] Error during initialization:', err);
      setStatus('Bridge error: ' + err.message, true);
    }}
  }}
  
  // Initialize Google Map
  function initMap() {{
    console.log('[MAP] Initializing Google Map...');
    try {{
      const aub = {{lat: 33.8993, lng: 35.4839}};
      
      map = new google.maps.Map(document.getElementById('map'), {{
        center: aub,
        zoom: 14,
        mapTypeControl: true,
        streetViewControl: true,
        fullscreenControl: true
      }});
      
      console.log('[MAP] Map object created');
      
      // Click marker (red)
      clickMarker = new google.maps.Marker({{
        position: aub,
        map: map,
        title: 'Selected Location',
        icon: {{
          url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
        }},
        draggable: false
      }});
      
      // AUB marker (blue)
      new google.maps.Marker({{
        position: aub,
        map: map,
        title: 'American University of Beirut',
        icon: {{
          url: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
        }}
      }});
      
      // Directions
      directionsService = new google.maps.DirectionsService();
      directionsRenderer = new google.maps.DirectionsRenderer({{
        suppressMarkers: false,
        polylineOptions: {{ strokeColor: '#0066cc', strokeWeight: 4 }}
      }});
      directionsRenderer.setMap(map);
      
      // Map click handler - CRITICAL SECTION
      map.addListener('click', function(event) {{
        console.log('[MAP CLICK] Event triggered');
        
        const lat = event.latLng.lat();
        const lng = event.latLng.lng();
        
        console.log('[MAP CLICK] Coordinates:', lat, lng);
        console.log('[MAP CLICK] Bridge ready:', bridgeReady);
        console.log('[MAP CLICK] Bridge exists:', !!bridge);
        
        // Update marker position
        clickMarker.setPosition(event.latLng);
        console.log('[MAP CLICK] Marker updated');
        
        // Send to Python through bridge
        if (!bridgeReady) {{
          console.error('[MAP CLICK] Bridge not ready!');
          setStatus('Bridge not ready - click after map loads', true);
          return;
        }}
        
        if (!bridge) {{
          console.error('[MAP CLICK] Bridge is null!');
          setStatus('Bridge is null', true);
          return;
        }}
        
        if (!bridge.reportCoordinates) {{
          console.error('[MAP CLICK] reportCoordinates method not found!');
          setStatus('reportCoordinates not available', true);
          return;
        }}
        
        try {{
          console.log('[MAP CLICK] Calling bridge.reportCoordinates...');
          bridge.reportCoordinates(lat, lng);
          setStatus('Sent: ' + lat.toFixed(6) + ', ' + lng.toFixed(6));
          console.log('[MAP CLICK] Coordinates sent to Python successfully');
        }} catch(err) {{
          console.error('[MAP CLICK] Error calling reportCoordinates:', err);
          setStatus('Error: ' + err.message, true);
        }}
      }});
      
      setStatus('Map ready - click anywhere');
      console.log('[MAP] Map initialized successfully');
      
    }} catch(err) {{
      console.error('[MAP] Initialization error:', err);
      setStatus('Map error: ' + err.message, true);
    }}
  }}
  
  // Clear all markers
  function clearMarkers() {{
    markers.forEach(m => m.setMap(null));
    markers = [];
  }}
  
  // Add driver markers
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
          icon: {{
            url: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
          }}
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
  
  // Draw route between two points
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
  
  // Clear route
  function clearRoute() {{
    directionsRenderer.setDirections({{routes: []}});
  }}
  
  // Initialize everything when page loads
  window.onload = function() {{
    initBridge();
    initMap();
  }};
</script>
</body>
</html>
"""
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    def on_map_click(self, lat, lng):
        """Handle map click event"""
        print(f"[Python] Map click received: {lat}, {lng}")
        self.coord_label.setText(f"📍 {lat:.6f}, {lng:.6f}")
        
        # Enable use buttons
        self.use_for_driver_btn.setEnabled(True)
        self.use_for_passenger_btn.setEnabled(True)
        
        # Auto-fill the appropriate field based on current tab
        current_tab_index = self.tabs.currentIndex()
        coord_str = f"{lat:.6f},{lng:.6f}"
        
        # Tab indices: 0=Login, 1=Driver, 2=Passenger, 3=Settings
        if current_tab_index == 1:  # Driver tab
            self.driver_area.setText(coord_str)
            self.status_bar.showMessage(f"✅ Driver pickup area set to: {lat:.6f}, {lng:.6f}")
        elif current_tab_index == 2:  # Passenger tab
            self.passenger_area.setText(coord_str)
            self.status_bar.showMessage(f"✅ Passenger area set to: {lat:.6f}, {lng:.6f}")
        else:
            self.status_bar.showMessage(f"Location selected: {lat:.6f}, {lng:.6f}")
        
        # Auto-refresh weather
        self.weather_label.setText("Fetching weather...")
        QTimer.singleShot(100, self.refresh_weather)
    
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
    # PROFILE WINDOW
    # ========================================================================
    def open_profile_window(self):
        """Open the profile window"""
        if not self.user:
            QMessageBox.warning(self, "Error", "Please login first")
            return
        self.profile_window = ProfileWindow(
            parent=self,
            user_data=self.user,
            send_static_request=send_request_to_gateway,
        )
        self.profile_window.exec_()
    
    # ========================================================================
    # COORDINATE USE FUNCTIONS
    # ========================================================================
    def use_coords_for_driver(self):
        """Use selected coordinates for driver pickup area"""
        if self.map_bridge.last_lat and self.map_bridge.last_lng:
            # Format as "lat,lng" for the backend
            coord_str = f"{self.map_bridge.last_lat:.6f},{self.map_bridge.last_lng:.6f}"
            self.driver_area.setText(coord_str)
            self.status_bar.showMessage("✅ Coordinates set for driver pickup location")
            QMessageBox.information(self, "Location Set", 
                f"Pickup location set to:\n{coord_str}\n\nSelect direction (to/from AUB) and add your ride.")
        else:
            QMessageBox.warning(self, "No Location", 
                "Please click the map to select a location first")
    
    def use_coords_for_passenger(self):
        """Use selected coordinates for passenger area"""
        if self.map_bridge.last_lat and self.map_bridge.last_lng:
            # Format as "lat,lng" for the backend
            coord_str = f"{self.map_bridge.last_lat:.6f},{self.map_bridge.last_lng:.6f}"
            self.passenger_area.setText(coord_str)
            self.status_bar.showMessage("✅ Coordinates set for passenger area")
            QMessageBox.information(self, "Location Set", 
                f"Pickup area set to:\n{coord_str}\n\nYou can now search for drivers.")
        else:
            QMessageBox.warning(self, "No Location", 
                "Please click the map to select a location first")
    
    # ========================================================================
    # PRESET LOCATION HANDLERS
    # ========================================================================
    def set_preset_location(self, lat, lng, name):
        """Set a preset location and fetch weather"""
        self.map_bridge.last_lat = lat
        self.map_bridge.last_lng = lng
        self.coord_label.setText(f"📍 {lat:.6f}, {lng:.6f} ({name})")
        self.weather_label.setText("Fetching weather...")
        
        # Enable use buttons
        self.use_for_driver_btn.setEnabled(True)
        self.use_for_passenger_btn.setEnabled(True)
        
        # Auto-refresh weather
        self.refresh_weather()
        
        # Update map marker
        if GOOGLE_API_KEY:
            js = f"if(clickMarker) {{ clickMarker.setPosition({{lat: {lat}, lng: {lng}}}); map.setCenter({{lat: {lat}, lng: {lng}}}); }}"
            self.map_view.page().runJavaScript(js)
        else:
            self.update_folium_marker(lat, lng, name)
    
    def update_folium_marker(self, lat, lng, name):
        """Update folium map with new marker"""
        try:
            m = folium.Map(location=[lat, lng], zoom_start=14)
            folium.Marker([lat, lng], tooltip=name, 
                         popup=f"{name}<br>{lat:.6f}, {lng:.6f}").add_to(m)
            
            if name != "AUB":
                folium.Marker([33.9006, 35.4812], tooltip='AUB',
                             icon=folium.Icon(color='blue')).add_to(m)
            
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
        data_login = response.get("data")
        if str(response.get("status")) in ("200", "201"):
            user_id = data_login.get("userID")
            user_info_req = {
                "action": "update_personal_info",
                "type_of_connection": "give_user_personal_informations",
                "userID": user_id
            }
            user_info = send_request_to_gateway(user_info_req)
            
            is_driver = False
            if user_info.get("status") == "200":
                data = user_info.get("data", {})
                # Check both possible field names for driver status
                is_driver = data.get("isDriver") or data.get("is_driver", False)
                # Convert to boolean if it's string
                if isinstance(is_driver, str):
                    is_driver = is_driver.lower() == "true"
            
            self.user = {
                "userID": user_id,
                "username": username,
                "email": data_login.get("email"),
                "isDriver": bool(is_driver)  # Ensure it's boolean
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
            
            # Enable profile button and appropriate tabs
            self.profile_btn.setEnabled(True)
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
        
        area = self.driver_area.text().strip()
        direction = self.driver_direction.currentText()
        start = self.driver_start_time.time().toString("HH:mm")
        end = self.driver_end_time.time().toString("HH:mm")
        car_id = self.driver_car_id.text().strip() or None
        
        if not area:
            QMessageBox.warning(self, "Input Error", 
                              "Please enter a pickup area or use the map")
            return
        
        # Extract coordinates if area is in "lat,lng" format
        pickup_lat = None
        pickup_lng = None
        
        if ',' in area:
            try:
                parts = area.split(',')
                pickup_lat = float(parts[0])
                pickup_lng = float(parts[1])
                print(f"[Driver] Using coordinates: {pickup_lat}, {pickup_lng}")
            except:
                pass
        
        # Send to ride management server (port 9998)
        payload = {
            "action": "add_ride",
            "userID": self.user["userID"],
            "carId": car_id,
            "area": area,
            "direction": direction,
            "startTime": start,
            "endTime": end,
            "scheduleID": "1",
            "pickup_lat": pickup_lat,
            "pickup_lng": pickup_lng
        }

        startTime = start.split(":")
        endTime = end.split(":")
        startTime = int(startTime[1]) + int(startTime[0]) * 60
        endTime = int(endTime[1]) + int(endTime[0]) * 60

        payload_static = {
            "action": "update_personal_info",
            "type_of_connection": "add_ride",
            "userID": self.user["userID"],
            "carId": car_id,
            "source": (pickup_lat, pickup_lng) if direction == "to_aub" else (33.9006, 35.4812),
            "destination": (33.9006, 35.4812) if direction == "to_aub" else (pickup_lat, pickup_lng),
            "startTime": startTime,
            "endTime": endTime,
            "scheduleID": self.user["userID"],
        }
        print("here ",payload_static)
        static_response = send_request_to_gateway(payload_static)
        print("static ",static_response)

        print(f"[Driver] Sending to ride server: {payload}")
        response = send_request_to_ride_server(payload)

        print(f"[Driver] Response: {response}")
        
        if str(response.get("status")) in ("200", "201"):
            ride_data = response.get("data", {})
            ride_id = ride_data.get("rideID", "N/A")
            
            # Determine source and destination for display
            if direction == "to_aub":
                source = area
                dest = "AUB, Beirut"
            else:
                source = "AUB, Beirut"
                dest = area
            
            QMessageBox.information(self, "Success", 
                f"Ride added successfully!\n\n"
                f"Ride ID: {ride_id}\n"
                f"Direction: {direction}\n"
                f"From: {source}\n"
                f"To: {dest}\n"
                f"Time: {start} - {end}")
            
            self.driver_area.clear()
            self.status_bar.showMessage(f"Ride added ✅ (ID: {ride_id})")
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
            self.refresh_timer.start(10000)
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
        
        if not area:
            QMessageBox.warning(self, "Input Error", "Please enter an area or use map")
            return
        
        # Send to ride management server (port 9998)
        payload = {
            "action": "request_ride",
            "riderID": self.user["userID"],
            "area": area,
            "time": time_str,
            "direction": direction
        }
        
        print(f"[Passenger] Sending to ride server: {payload}")
        response = send_request_to_ride_server(payload)
        print(f"[Passenger] Response: {response}")


        pickup_lat = None
        pickup_lng = None
        
        if ',' in area:
            try:
                parts = area.split(',')
                pickup_lat = float(parts[0])
                pickup_lng = float(parts[1])
            except:
                pass

        static_payload = {
            "userID": self.user["userID"],
            "filter": {
              "rating": [0, 5],
              "distance": 3,
              "date": [int(time_str.split(":")[0]) * 60 + int(time_str.split(":")[1]), 9999999]
            },
            "userLocation": {
              "lat": pickup_lat,
              "lon": pickup_lng
            }
        }
        print(static_payload)
        static_response = send_request_to_gateway(static_payload)
        print(static_response)
        
        if response.get("status") == "200":
            data = response.get("data", {})
            candidates = data.get("candidates", [])
            gateway_candidates = data.get("gatewayCandidates", [])
            
            # Combine both sources of candidates
            all_candidates = candidates + gateway_candidates
            
            # Remove duplicates based on rideID
            seen_ride_ids = set()
            unique_candidates = []
            for candidate in all_candidates:
                ride_id = candidate.get("rideID")
                if ride_id and ride_id not in seen_ride_ids:
                    seen_ride_ids.add(ride_id)
                    unique_candidates.append(candidate)
            
            self.current_candidates = unique_candidates
            self.current_request_id = data.get("requestID")
            
            self.drivers_list.clear()
            drivers_for_map = []
            
            for idx, candidate in enumerate(unique_candidates, 1):
                driver = candidate.get("driverUsername", "Unknown")
                source = candidate.get("source", "N/A")
                dest = candidate.get("destination", "N/A")
                distance = candidate.get("distance_text", 
                          f"{candidate.get('distance_m', 0):.0f}m")
                duration = candidate.get("duration_text", "N/A")
                start_time = candidate.get("startTime", "N/A")
                end_time = candidate.get("endTime", "N/A")
                
                item_text = (f"🚗 #{idx} {driver} | 📍 {source} → {dest} | "
                           f"⏱ {start_time}-{end_time}")
                
                if distance != "N/A":
                    item_text += f" | 📏 {distance}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, candidate)
                self.drivers_list.addItem(item)
                
                lat = candidate.get("pickup_lat") or candidate.get("ride_lat")
                lng = candidate.get("pickup_lng") or candidate.get("ride_lng")
                if lat and lng:
                    drivers_for_map.append({
                        "lat": lat,
                        "lng": lng,
                        "label": str(idx),
                        "title": f"{driver} - {source}"
                    })
            
            if drivers_for_map and GOOGLE_API_KEY:
                js = f"addDriverMarkers({json.dumps(drivers_for_map)});"
                self.map_view.page().runJavaScript(js)
            
            msg = f"Found {len(unique_candidates)} available driver(s)!"
            QMessageBox.information(self, "Success", msg)
            self.status_bar.showMessage(f"{len(unique_candidates)} drivers found ✅")
            
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
    
    def test_gateway_connection(self):
        """Test connection to gateway server"""
        try:
            host = self.gateway_host_input.text().strip()
            port = int(self.gateway_port_input.text().strip())
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((host, port))
            s.close()
            
            QMessageBox.information(self, "Gateway Connection Test", 
                f"✅ Successfully connected to Gateway\n{host}:{port}")
            self.status_bar.showMessage(f"Gateway connection OK ✅")
        except Exception as e:
            QMessageBox.critical(self, "Gateway Connection Failed", 
                f"❌ Could not connect to gateway:\n{str(e)}")
            self.status_bar.showMessage("Gateway connection failed ❌")
    
    def test_ride_server_connection(self):
        """Test connection to ride management server"""
        try:
            host = self.ride_server_host_input.text().strip()
            port = int(self.ride_server_port_input.text().strip())
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((host, port))
            s.close()
            
            QMessageBox.information(self, "Ride Server Connection Test", 
                f"✅ Successfully connected to Ride Server\n{host}:{port}")
            self.status_bar.showMessage(f"Ride server connection OK ✅")
        except Exception as e:
            QMessageBox.critical(self, "Ride Server Connection Failed", 
                f"❌ Could not connect to ride server:\n{str(e)}\n\n"
                f"Make sure ride_management_server.py is running!")
            self.status_bar.showMessage("Ride server connection failed ❌")
    
    def test_connection(self):
        """Test both connections (legacy function)"""
        self.test_gateway_connection()
        self.test_ride_server_connection()
    
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