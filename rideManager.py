"""
Ride Management Server - Port 9998
Handles: add_ride, cancel_ride, request_ride operations

This server manages all ride-related operations for the AUBus system.
It communicates with the main gateway on port 9999 for user authentication
and database operations.

Usage:
    python ride_management_server.py

Requirements:
    - Main gateway server running on port 9999
    - Python 3.7+
"""

import socket
import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration
HOST = '0.0.0.0'
PORT = 9998
GATEWAY_HOST = socket.gethostname()
GATEWAY_PORT = 9999
MAX_CONNECTIONS = 10

# In-memory storage for active rides and requests
active_rides: Dict[str, Dict] = {}
pending_requests: Dict[str, Dict] = {}
ride_counter = 0
request_counter = 0

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_timestamp():
    """Get current timestamp in a readable format"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(message: str, level: str = "INFO"):
    """Log messages with timestamp"""
    print(f"[{get_timestamp()}] [{level}] {message}")

def send_to_gateway(payload: Dict) -> Dict:
    """Send request to main gateway server"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((GATEWAY_HOST, GATEWAY_PORT))
        s.send(json.dumps(payload).encode('utf-8'))
        data = s.recv(16384).decode('utf-8')
        s.close()
        return json.loads(data)
    except Exception as e:
        log(f"Gateway communication error: {e}", "ERROR")
        return {"status": "500", "message": f"Gateway error: {str(e)}"}

# ============================================================================
# RIDE MANAGEMENT FUNCTIONS
# ============================================================================

def handle_add_ride(data: Dict) -> Dict:
    """
    Add a new ride offered by a driver
    
    Expected data:
    {
        "action": "add_ride",
        "userID": "driver_id",
        "carId": "optional_car_id",
        "area": "pickup_area",
        "direction": "to_aub" or "from_aub",
        "startTime": "HH:MM",
        "endTime": "HH:MM",
        "scheduleID": "schedule_id",
        "pickup_lat": float (optional),
        "pickup_lng": float (optional)
    }
    """
    global ride_counter
    
    try:
        # Validate required fields
        required = ["userID", "area", "direction", "startTime", "endTime"]
        for field in required:
            if field not in data:
                return {
                    "status": "400",
                    "message": f"Missing required field: {field}"
                }
        
        user_id = data["userID"]
        area = data["area"]
        direction = data["direction"]
        start_time = data["startTime"]
        end_time = data["endTime"]
        
        # Validate direction
        if direction not in ["to_aub", "from_aub"]:
            return {
                "status": "400",
                "message": "Direction must be 'to_aub' or 'from_aub'"
            }
        
        # Set source and destination based on direction
        if direction == "to_aub":
            source = area
            destination = "AUB, Beirut"
        else:  # from_aub
            source = "AUB, Beirut"
            destination = area
        
        # Verify user is a driver (check with gateway)
        user_check = send_to_gateway({
            "action": "update_personal_info",
            "type_of_connection": "give_user_personal_informations",
            "userID": user_id
        })
        
        if user_check.get("status") != "200":
            return {
                "status": "401",
                "message": "User verification failed"
            }
        
        user_data = user_check.get("data", {})
        if not user_data.get("isDriver", False):
            return {
                "status": "403",
                "message": "Only drivers can add rides"
            }
        
        # Generate unique ride ID
        ride_counter += 1
        ride_id = f"RIDE_{user_id}_{ride_counter}_{int(time.time())}"
        
        # Create ride object
        ride = {
            "rideID": ride_id,
            "driverID": user_id,
            "driverUsername": user_data.get("userName", "Unknown"),
            "carId": data.get("carId"),
            "source": source,
            "destination": destination,
            "area": area,
            "direction": direction,
            "startTime": start_time,
            "endTime": end_time,
            "scheduleID": data.get("scheduleID", "1"),
            "pickup_lat": data.get("pickup_lat"),
            "pickup_lng": data.get("pickup_lng"),
            "status": "active",
            "passengers": [],
            "createdAt": get_timestamp()
        }
        
        # Store ride
        active_rides[ride_id] = ride
        
        # Also send to main gateway for persistent storage
        gateway_payload = {
            "action": "update_personal_info",
            "type_of_connection": "add_ride",
            "userID": user_id,
            "carId": data.get("carId"),
            "source": source,
            "destination": destination,
            "startTime": start_time,
            "endTime": end_time,
            "scheduleID": data.get("scheduleID", "1"),
            "pickup_lat": data.get("pickup_lat"),
            "pickup_lng": data.get("pickup_lng")
        }
        gateway_response = send_to_gateway(gateway_payload)
        
        log(f"Ride added: {ride_id} by driver {user_id} ({direction})")
        
        return {
            "status": "201",
            "message": "Ride added successfully",
            "data": {
                "rideID": ride_id,
                "ride": ride,
                "gatewayResponse": gateway_response
            }
        }
        
    except Exception as e:
        log(f"Error adding ride: {e}", "ERROR")
        return {
            "status": "500",
            "message": f"Internal error: {str(e)}"
        }

def handle_cancel_ride(data: Dict) -> Dict:
    """
    Cancel an existing ride
    
    Expected data:
    {
        "action": "cancel_ride",
        "rideID": "ride_id",
        "userID": "driver_id"
    }
    """
    try:
        ride_id = data.get("rideID")
        user_id = data.get("userID")
        
        if not ride_id or not user_id:
            return {
                "status": "400",
                "message": "Missing rideID or userID"
            }
        
        # Check if ride exists
        if ride_id not in active_rides:
            return {
                "status": "404",
                "message": "Ride not found"
            }
        
        ride = active_rides[ride_id]
        
        # Verify user is the driver
        if ride["driverID"] != user_id:
            return {
                "status": "403",
                "message": "Only the driver can cancel this ride"
            }
        
        # Mark as cancelled
        ride["status"] = "cancelled"
        ride["cancelledAt"] = get_timestamp()
        
        # Notify passengers if any
        passengers = ride.get("passengers", [])
        
        # Remove from active rides
        del active_rides[ride_id]
        
        log(f"Ride cancelled: {ride_id} by driver {user_id}")
        
        return {
            "status": "200",
            "message": "Ride cancelled successfully",
            "data": {
                "rideID": ride_id,
                "notifiedPassengers": len(passengers)
            }
        }
        
    except Exception as e:
        log(f"Error cancelling ride: {e}", "ERROR")
        return {
            "status": "500",
            "message": f"Internal error: {str(e)}"
        }

def handle_request_ride(data: Dict) -> Dict:
    """
    Request a ride (passenger looking for drivers)
    
    Expected data:
    {
        "action": "request_ride",
        "riderID": "passenger_id",
        "area": "pickup_area",
        "time": "HH:MM",
        "direction": "to_aub" or "from_aub"
    }
    """
    global request_counter
    
    try:
        # Validate required fields
        required = ["riderID", "area", "time", "direction"]
        for field in required:
            if field not in data:
                return {
                    "status": "400",
                    "message": f"Missing required field: {field}"
                }
        
        rider_id = data["riderID"]
        area = data["area"]
        time_str = data["time"]
        direction = data["direction"]
        
        # Validate direction
        if direction not in ["to_aub", "from_aub"]:
            return {
                "status": "400",
                "message": "Direction must be 'to_aub' or 'from_aub'"
            }
        
        # Get user info
        user_check = send_to_gateway({
            "action": "update_personal_info",
            "type_of_connection": "give_user_personal_informations",
            "userID": rider_id
        })
        
        if user_check.get("status") != "200":
            return {
                "status": "401",
                "message": "User verification failed"
            }
        
        user_data = user_check.get("data", {})
        
        # Generate unique request ID
        request_counter += 1
        request_id = f"REQ_{rider_id}_{request_counter}_{int(time.time())}"
        
        # Create request object
        request = {
            "requestID": request_id,
            "riderID": rider_id,
            "riderUsername": user_data.get("userName", "Unknown"),
            "area": area,
            "time": time_str,
            "direction": direction,
            "status": "pending",
            "createdAt": get_timestamp()
        }
        
        # Store request
        pending_requests[request_id] = request
        
        # Find matching rides
        candidates = find_matching_rides(area, time_str, direction)
        
        # Also send to gateway
        gateway_payload = {
            "action": "request_ride",
            "riderID": rider_id,
            "area": area,
            "time": time_str,
            "direction": direction
        }
        gateway_response = send_to_gateway(gateway_payload)
        
        # Merge candidates from gateway if available
        gateway_candidates = gateway_response.get("candidates", [])
        
        log(f"Ride request: {request_id} by rider {rider_id} - Found {len(candidates)} local matches")
        
        return {
            "status": "200",
            "message": f"Found {len(candidates)} matching drivers",
            "data": {
                "requestID": request_id,
                "candidates": candidates,
                "gatewayCandidates": gateway_candidates
            }
        }
        
    except Exception as e:
        log(f"Error requesting ride: {e}", "ERROR")
        return {
            "status": "500",
            "message": f"Internal error: {str(e)}"
        }

def find_matching_rides(area: str, time_str: str, direction: str) -> List[Dict]:
    """Find rides matching the passenger's requirements"""
    candidates = []
    
    for ride_id, ride in active_rides.items():
        if ride["status"] != "active":
            continue
        
        # Check direction
        if ride["direction"] != direction:
            continue
        
        # Check if time is within window
        ride_start = ride["startTime"]
        ride_end = ride["endTime"]
        
        # Simple time comparison (you can make this more sophisticated)
        if ride_start <= time_str <= ride_end:
            candidate = {
                "rideID": ride_id,
                "driverID": ride["driverID"],
                "driverUsername": ride["driverUsername"],
                "source": ride["source"],
                "destination": ride["destination"],
                "area": ride["area"],
                "direction": ride["direction"],
                "startTime": ride["startTime"],
                "endTime": ride["endTime"],
                "pickup_lat": ride.get("pickup_lat"),
                "pickup_lng": ride.get("pickup_lng"),
                "carId": ride.get("carId")
            }
            candidates.append(candidate)
    
    return candidates

def handle_get_active_rides(data: Dict) -> Dict:
    """Get all active rides (for debugging/admin)"""
    try:
        direction_filter = data.get("direction")
        
        rides = []
        for ride_id, ride in active_rides.items():
            if ride["status"] == "active":
                if direction_filter and ride["direction"] != direction_filter:
                    continue
                rides.append(ride)
        
        return {
            "status": "200",
            "message": f"Found {len(rides)} active rides",
            "data": {
                "rides": rides,
                "count": len(rides)
            }
        }
    except Exception as e:
        return {
            "status": "500",
            "message": f"Error: {str(e)}"
        }

def handle_get_pending_requests(data: Dict) -> Dict:
    """Get all pending requests (for drivers to see)"""
    try:
        driver_id = data.get("driverID")
        
        requests = []
        for req_id, req in pending_requests.items():
            if req["status"] == "pending":
                requests.append(req)
        
        return {
            "status": "200",
            "message": f"Found {len(requests)} pending requests",
            "data": {
                "requests": requests,
                "count": len(requests)
            }
        }
    except Exception as e:
        return {
            "status": "500",
            "message": f"Error: {str(e)}"
        }

# ============================================================================
# REQUEST HANDLER
# ============================================================================

def handle_request(data: Dict) -> Dict:
    """Main request handler - routes to appropriate function"""
    action = data.get("action", "").lower()
    
    log(f"Received request: {action}")
    
    handlers = {
        "add_ride": handle_add_ride,
        "cancel_ride": handle_cancel_ride,
        "request_ride": handle_request_ride,
        "get_active_rides": handle_get_active_rides,
        "get_pending_requests": handle_get_pending_requests
    }
    
    handler = handlers.get(action)
    
    if handler:
        return handler(data)
    else:
        return {
            "status": "400",
            "message": f"Unknown action: {action}",
            "availableActions": list(handlers.keys())
        }

# ============================================================================
# CLIENT HANDLER
# ============================================================================

def handle_client(client_socket: socket.socket, address: tuple):
    """Handle individual client connection"""
    try:
        log(f"New connection from {address[0]}:{address[1]}")
        
        # Receive data
        data = client_socket.recv(4096).decode('utf-8')
        
        if not data:
            log(f"Empty request from {address[0]}", "WARN")
            return
        
        # Parse JSON
        try:
            request = json.loads(data)
        except json.JSONDecodeError as e:
            log(f"Invalid JSON from {address[0]}: {e}", "ERROR")
            response = {
                "status": "400",
                "message": "Invalid JSON format"
            }
            client_socket.send(json.dumps(response).encode('utf-8'))
            return
        
        # Handle request
        response = handle_request(request)
        
        # Send response
        client_socket.send(json.dumps(response).encode('utf-8'))
        
        log(f"Request processed: {request.get('action')} - Status: {response.get('status')}")
        
    except Exception as e:
        log(f"Error handling client {address[0]}: {e}", "ERROR")
        try:
            error_response = {
                "status": "500",
                "message": f"Server error: {str(e)}"
            }
            client_socket.send(json.dumps(error_response).encode('utf-8'))
        except:
            pass
    finally:
        client_socket.close()

# ============================================================================
# MAIN SERVER
# ============================================================================

def start_server():
    """Start the ride management server"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(MAX_CONNECTIONS)
        
        log(f"Ride Management Server started on {HOST}:{PORT}")
        log(f"Gateway connection: {GATEWAY_HOST}:{GATEWAY_PORT}")
        log(f"Waiting for connections...")
        
        while True:
            client_socket, address = server.accept()
            
            # Handle each client in a separate thread
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, address),
                daemon=True
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        log("Server shutdown requested", "INFO")
    except Exception as e:
        log(f"Server error: {e}", "ERROR")
    finally:
        server.close()
        log("Server stopped")

# ============================================================================
# STATISTICS THREAD
# ============================================================================

def print_stats():
    """Print server statistics periodically"""
    while True:
        time.sleep(60)  # Every minute
        active_count = len([r for r in active_rides.values() if r["status"] == "active"])
        pending_count = len([r for r in pending_requests.values() if r["status"] == "pending"])
        log(f"Stats: {active_count} active rides, {pending_count} pending requests", "STATS")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    log("=" * 70)
    log("AUBus Ride Management Server")
    log("=" * 70)
    
    # Start statistics thread
    stats_thread = threading.Thread(target=print_stats, daemon=True)
    stats_thread.start()
    
    # Start main server
    start_server()