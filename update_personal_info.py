import json
import sqlite3
import time  


def personal_info_manager(data):
    req_code = data.get("type_of_connection")
    if req_code == "edit_role":
        return handle_edit_role(data)
    elif req_code == "edit_name":
        return handle_edit_name(data)
    elif req_code == "add_ride":
        return add_ride(data)
    elif req_code == "remove_ride":
        return remove_ride(data)
    elif req_code == "give_all_rides":
        return give_all_rides(data)
    elif req_code == "give_user_personal_informations":
        return give_user_personal_informations(data)
    elif req_code == "get_rating":
        return get_rating(data)
    elif req_code == "update_zone":
        return update_zone(data)
    elif req_code == "get_zone":
        return get_zone(data)
    elif req_code == "get_cars":
        return get_cars(data)
    elif req_code == "add_car":
        return add_car(data)
    elif req_code == "update_car":  
        return update_car(data)
    elif req_code == "remove_car": 
        return remove_car(data)
    else:
        return {"status": "400", "message": "Invalid request type"}


def handle_edit_role(data):
    userID = data.get("userID")
    new_role = data.get("new_role")
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('UPDATE "user" SET isDriver=? WHERE userID=?', (new_role == "driver", userID))
        conn.commit()
        conn.close()
        return {"status": "200", "message": "Role updated successfully"}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}


def handle_edit_name(data):
    userID = data.get("userID")
    new_name = data.get("new_name")
    
    if not userID or not new_name:
        return {"status": "400", "message": "UserID and new_name are required"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Check if username already exists (excluding current user)
        cur.execute('SELECT userID FROM "user" WHERE username=? AND userID!=?', (new_name, userID))
        existing_user = cur.fetchone()
        
        if existing_user:
            conn.close()
            return {"status": "400", "message": "Username already exists"}
        
        # Update username
        cur.execute('UPDATE "user" SET username=? WHERE userID=?', (new_name, userID))
        conn.commit()
        conn.close()
        
        return {"status": "200", "message": "Name updated successfully"}
    
    except sqlite3.Error as e:
        return {"status": "400", "message": f"Database error: {str(e)}"}

def checkIntersection(schedule, ride):
    schedule.sort()
    for ride_i in schedule:
        ride_start = ride_i[0]
        ride_end = ride_i[1]
        if ride_start <= ride[1] and ride_end >= ride[0]:
            return True
    return False
        
        

def add_ride(data):
    userID = data.get("userID")
    carId = data.get("carId")
    source = data.get("source")
    destination = data.get("destination")
    startTime = data.get("startTime")
    endTime = data.get("endTime")
    scheduleID = data.get("scheduleID")
    rideID = str(int(time.time() * 17 * 1000)) + userID[:3] + str(int(time.time() * 11 * 1000))

    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()

        cur.execute('SELECT * FROM "schedule" WHERE scheduleID=?', (scheduleID,))
        schedule_row = cur.fetchone()
        if not schedule_row:
            return {"status": "400", "message": "Schedule does not exist"}
        cur.execute('SELECT * FROM "Car" WHERE ownerID=?', (carId, userID))
        car_row = cur.fetchone()
        if not car_row:
            return {"status": "400", "message": "Car does not belong to user"}
        cur.execute('SELECT * FROM "ride" WHERE scheduleID=?', (scheduleID,))
        ride_row = cur.fetchone()
        if ride_row:
            ride_data = list(ride_row)
            if checkIntersection(ride_data, (startTime, endTime)):
                return {"status": "400", "message": "Ride time conflicts with existing schedule"}
        zone0 = str(source[0] + source[1])
        zone1 = str(destination[0] + destination[1])
        cur.execute('SELECT * FROM "Zone" WHERE zoneID=? AND userID=?', (zone0,userID))
        source_row = cur.fetchone()
        if not source_row:
            cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', (zone0,float(source[0]),float(source[1]), "Zone " + zone0, userID))
        cur.execute('SELECT * FROM "Zone" WHERE zoneID=?', (zone1,))
        source_row = cur.fetchone()
        if not source_row:
            cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', (zone1,float(destination[0]),float(destination[1]), "Zone " + zone1, userID))
        cur.execute(
            'INSERT INTO "Ride" (rideID, ownerID, carId, sourceID, destinationID, startTime, endTime, scheduleID) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (rideID, userID, carId, zone0, zone1, startTime, endTime, scheduleID)
        )
        conn.commit()
        return {
            "status": "201",
            "message": "Ride added successfully",
            "data": {
                "rideID": rideID,
                "ownerID": userID,
                "carId": carId,
                "source": source,
                "destination": destination,
                "startTime": startTime,
                "endTime": endTime,
                "scheduleID": scheduleID
            }
        }

    except sqlite3.Error:
        return {"status": "400", "message": "An unexpected error occurred: it seems that the service is down"}
    
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def remove_ride(data):
    ride_id = data.get("rideID")
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('DELETE FROM Ride WHERE rideID=?', (ride_id,))
        conn.commit()
        conn.close()
        return {"status": "200", "message": "Ride removed successfully"}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}
    
def give_all_rides(data):
    userID = data.get("userID")
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM Ride WHERE ownerID=?', (userID,))
        rides = cur.fetchall()
        conn.close()
        rides_list = []
        for ride in rides:
            rides_list.append({
                "rideID": ride[0],
                "ownerID": ride[1],
                "carId": ride[2],
                "sourceID": ride[3],
                "destinationID": ride[4],
                "startTime": ride[5],
                "endTime": ride[6],
                "scheduleID": ride[7]
            })
        return {"status": "200", "message": "Rides retrieved successfully", "data": rides_list}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}

def give_user_personal_informations(data):
    userID  = data.get("userID")
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('SELECT username, email, isDriver, aubID FROM "user" WHERE userID=?', (userID,))
        user = cur.fetchone()
        conn.close()
        if user is None:
            return {"status": "404", "message": "User not found"}
        user_info = {
            "username": user[0],
            "email": user[1],
            "isDriver": bool(user[2]),
            "aubID": user[3]
        }
        return {"status": "200", "message": "User information retrieved successfully", "data": user_info}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}

def get_rating(data):
    userID = data.get("userID")
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('SELECT score, comment FROM Rating WHERE rateeID=?', (userID,))
        ratings = cur.fetchall()
        conn.close()
        ratings_list = []
        average_score = 0
        for rating in ratings:
            average_score += rating[0]
            ratings_list.append({
                "score": rating[0],
                "comment": rating[1]
            })
        if ratings:
            average_score /= len(ratings)
        return {"status": "200", "message": "Ratings retrieved successfully", "data": ratings_list, "average_score": average_score}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}
    
def update_zone(data):
    """Update user's zone information"""
    userID = data.get("userID")
    zone = data.get("zone")
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Check if zone exists for user
        cur.execute('SELECT zoneID FROM Zone WHERE UserID=?', (userID,))
        existing_zone = cur.fetchone()
        
        if existing_zone:
            # Update existing zone
            cur.execute('UPDATE Zone SET zoneName=? WHERE UserID=?', (zone, userID))
        else:
            # Create new zone entry
            zone_id = f"zone_{int(time.time()*1000)}"
            cur.execute('INSERT INTO Zone (zoneID, zoneName, UserID) VALUES (?, ?, ?)', 
                       (zone_id, zone, userID))
        
        conn.commit()
        conn.close()
        return {"status": "200", "message": "Zone updated successfully"}
    
    except sqlite3.Error as e:
        return {"status": "400", "message": f"Database error: {str(e)}"}

def get_zone(data):
    """Get user's current zone"""
    userID = data.get("userID")
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('SELECT zoneName FROM Zone WHERE UserID=?', (userID,))
        zone_result = cur.fetchone()
        conn.close()
        
        if zone_result:
            return {"status": "200", "data": {"zoneName": zone_result[0]}}
        else:
            return {"status": "404", "message": "Zone not found for user"}
    
    except sqlite3.Error as e:
        return {"status": "400", "message": f"Database error: {str(e)}"}
    
def get_cars(data):
    """Get driver's cars"""
    userID = data.get("userID")
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('SELECT carId, cartype, carPlate, capacity FROM Car WHERE ownerID=?', (userID,))
        cars = cur.fetchall()
        conn.close()
        
        cars_list = []
        for car in cars:
            cars_list.append({
                "carId": car[0],
                "cartype": car[1],
                "carPlate": car[2],
                "capacity": car[3]
            })
        
        return {"status": "200", "data": cars_list}
    
    except sqlite3.Error as e:
        return {"status": "400", "message": f"Database error: {str(e)}"}

def add_car(data):
    """Add a new car for driver"""
    userID = data.get("userID")
    car_type = data.get("car_type")
    car_plate = data.get("car_plate")
    capacity = data.get("capacity")
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Check if car plate already exists
        cur.execute('SELECT carId FROM Car WHERE carPlate=?', (car_plate,))
        existing_car = cur.fetchone()
        
        if existing_car:
            conn.close()
            return {"status": "400", "message": "Car with this plate already exists"}
        
        # Create new car
        car_id = f"car_{int(time.time()*1000)}"
        cur.execute('INSERT INTO Car (carId, cartype, carPlate, capacity, ownerID) VALUES (?, ?, ?, ?, ?)',
                   (car_id, car_type, car_plate, capacity, userID))
        
        conn.commit()
        conn.close()
        return {"status": "200", "message": "Car added successfully", "carId": car_id}
    
    except sqlite3.Error as e:
        return {"status": "400", "message": f"Database error: {str(e)}"}
    
def update_car(data):
    """Update an existing car"""
    userID = data.get("userID")
    car_id = data.get("carId")
    car_type = data.get("car_type")
    car_plate = data.get("car_plate")
    capacity = data.get("capacity")
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Check if user owns this car
        cur.execute('SELECT ownerID FROM Car WHERE carId=?', (car_id,))
        car_owner = cur.fetchone()
        
        if not car_owner or car_owner[0] != userID:
            conn.close()
            return {"status": "403", "message": "You don't own this car"}
        
        # Check if new plate already exists (excluding current car)
        cur.execute('SELECT carId FROM Car WHERE carPlate=? AND carId!=?', (car_plate, car_id))
        existing_car = cur.fetchone()
        
        if existing_car:
            conn.close()
            return {"status": "400", "message": "Car with this plate already exists"}
        
        # Update car
        cur.execute('UPDATE Car SET cartype=?, carPlate=?, capacity=? WHERE carId=?', 
                   (car_type, car_plate, capacity, car_id))
        
        conn.commit()
        conn.close()
        return {"status": "200", "message": "Car updated successfully"}
    
    except sqlite3.Error as e:
        return {"status": "400", "message": f"Database error: {str(e)}"}

def remove_car(data):
    """Remove a car"""
    userID = data.get("userID")
    car_id = data.get("carId")
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Check if user owns this car
        cur.execute('SELECT ownerID FROM Car WHERE carId=?', (car_id,))
        car_owner = cur.fetchone()
        
        if not car_owner or car_owner[0] != userID:
            conn.close()
            return {"status": "403", "message": "You don't own this car"}
        
        # Check if car is used in any rides
        cur.execute('SELECT rideID FROM Ride WHERE carId=?', (car_id,))
        active_rides = cur.fetchall()
        
        if active_rides:
            conn.close()
            return {"status": "400", "message": "Cannot remove car that has active rides"}
        
        # Remove car
        cur.execute('DELETE FROM Car WHERE carId=?', (car_id,))
        
        conn.commit()
        conn.close()
        return {"status": "200", "message": "Car removed successfully"}
    
    except sqlite3.Error as e:
        return {"status": "400", "message": f"Database error: {str(e)}"}