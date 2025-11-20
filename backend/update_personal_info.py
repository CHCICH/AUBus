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
    elif req_code == "edit_ride":
        return edit_ride(data) 
    elif req_code == "remove_ride":
        return remove_ride(data)
    elif req_code == "cancel_ride":
        return cancel_ride(data)
    elif req_code == "request_ride":
        return request_ride(data)
    elif req_code == "give_all_rides":
        return give_all_rides(data)
    elif req_code == "get_my_rides_detailed":
        return get_my_rides_detailed(data)
    elif req_code == "give_user_personal_informations":
        return give_user_personal_informations(data)
    elif req_code == "get_rating":
        return get_rating(data)
    elif req_code == "submit_rating":  
        return submit_rating(data) 
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
        ride_start = int(ride_i[0])
        ride_end = int(ride_i[1])
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
    rideID = str(int(time.time() * 17 * 1000))

    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()

        cur.execute('SELECT * FROM "schedule" WHERE scheduleID=?', (scheduleID,))
        schedule_row = cur.fetchone()
        if not schedule_row:
            cur.execute('INSERT INTO "schedule" (scheduleID) VALUES (?)', (scheduleID,))
            conn.commit()
        
        cur.execute('SELECT * FROM "Car" WHERE ownerID=?', (userID,))
        car_row = cur.fetchone()
        if not car_row:
            conn.close()
            return {"status": "400", "message": "User has no cars. Please add a car first in your Profile."}
        
        # Verify the specific car exists and belongs to user
        if carId:
            cur.execute('SELECT * FROM "Car" WHERE carId=? AND ownerID=?', (carId, userID))
            specific_car = cur.fetchone()
            if not specific_car:
                conn.close()
                return {"status": "400", "message": "Selected car not found or doesn't belong to you"}
        
        cur.execute('SELECT * FROM "ride" WHERE scheduleID=?', (scheduleID,))
        ride_row = cur.fetchall()
        ride_data = [(ride[5], ride[6]) for ride in ride_row]
        if ride_row:
            print(ride_data)
            if checkIntersection(ride_data, (int(startTime), int(endTime))):
                conn.close()
                return {"status": "400", "message": "Ride time conflicts with existing schedule"}
        
        # Handle zone creation
        zone0 = str(source[0]) + str(source[1]) if isinstance(source, tuple) else str(source)
        zone1 = str(destination[0]) + str(destination[1]) if isinstance(destination, tuple) else str(destination)
        
        # Create source zone if needed
        cur.execute('SELECT * FROM "Zone" WHERE zoneID=?', (zone0,))
        source_row = cur.fetchone()
        if not source_row:
            if isinstance(source, tuple) and len(source) == 2:
                cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                           (zone0, float(source[0]), float(source[1]), "Zone " + zone0, userID))
            else:
                # If source is a string, create zone with default coordinates
                cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                           (zone0, 33.8958, 35.4787, str(source), userID))
        
        # Create destination zone if needed
        cur.execute('SELECT * FROM "Zone" WHERE zoneID=?', (zone1,))
        dest_row = cur.fetchone()
        if not dest_row:
            if isinstance(destination, tuple) and len(destination) == 2:
                cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                           (zone1, float(destination[0]), float(destination[1]), "Zone " + zone1, userID))
            else:
                # If destination is a string, use AUB coordinates
                cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                           (zone1, 33.9006, 35.4812, str(destination), userID))
        
        cur.execute(
            'INSERT INTO "Ride" (rideID, ownerID, carId, sourceID, destinationID, startTime, endTime, scheduleID) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (rideID, userID, carId, zone0, zone1, startTime, endTime, scheduleID)
        )
        conn.commit()
        conn.close()
        
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

    except sqlite3.Error as e:
        return {"status": "400", "message": f"Database error: {str(e)}"}
    finally:
        if 'conn' in locals():
            conn.close()

def edit_ride(data):
    """
    Edit an existing ride with proper validation and conflict checking
    """
    ride_id = data.get("rideID")
    user_id = data.get("userID")
    car_id = data.get("carId")
    source = data.get("source")
    destination = data.get("destination")
    start_time = data.get("startTime")
    end_time = data.get("endTime")
    schedule_id = data.get("scheduleID")
    
    if not all([ride_id, user_id, source, destination, start_time, end_time]):
        return {"status": "400", "message": "Missing required fields"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Verify the user owns this ride
        cur.execute('SELECT ownerID, scheduleID FROM Ride WHERE rideID=?', (ride_id,))
        ride_data = cur.fetchone()
        
        if not ride_data:
            conn.close()
            return {"status": "404", "message": "Ride not found"}
        
        if ride_data[0] != user_id:
            conn.close()
            return {"status": "403", "message": "You can only edit your own rides"}
        
        # Verify car ownership if car_id is provided
        if car_id:
            cur.execute('SELECT ownerID FROM Car WHERE carId=?', (car_id,))
            car_owner = cur.fetchone()
            if not car_owner or car_owner[0] != user_id:
                conn.close()
                return {"status": "403", "message": "You don't own this car"}
        
        # Check for time conflicts with other rides in the same schedule (excluding current ride)
        cur.execute('SELECT startTime, endTime FROM Ride WHERE scheduleID=? AND rideID!=?', 
                   (ride_data[1], ride_id))
        existing_rides = cur.fetchall()
        
        if existing_rides:
            ride_times = [(ride[0], ride[1]) for ride in existing_rides]
            if checkIntersection(ride_times, (int(start_time), int(end_time))):
                conn.close()
                return {"status": "400", "message": "Ride time conflicts with existing schedule"}
        
        # Handle zone creation/updates
        zone0 = str(source[0]) + str(source[1]) if isinstance(source, tuple) else str(source)
        zone1 = str(destination[0]) + str(destination[1]) if isinstance(destination, tuple) else str(destination)
        
        # Create/update source zone
        cur.execute('SELECT * FROM "Zone" WHERE zoneID=?', (zone0,))
        source_row = cur.fetchone()
        if not source_row:
            if isinstance(source, tuple) and len(source) == 2:
                cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                           (zone0, float(source[0]), float(source[1]), "Zone " + zone0, user_id))
            else:
                cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                           (zone0, 33.8958, 35.4787, str(source), user_id))
        
        # Create/update destination zone
        cur.execute('SELECT * FROM "Zone" WHERE zoneID=?', (zone1,))
        dest_row = cur.fetchone()
        if not dest_row:
            if isinstance(destination, tuple) and len(destination) == 2:
                cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                           (zone1, float(destination[0]), float(destination[1]), "Zone " + zone1, user_id))
            else:
                cur.execute('INSERT INTO "Zone" (zoneID,zoneX,zoneY,zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                           (zone1, 33.9006, 35.4812, str(destination), user_id))
        
        # Update the ride
        update_query = '''
            UPDATE Ride 
            SET carId=?, sourceID=?, destinationID=?, startTime=?, endTime=?
            WHERE rideID=?
        '''
        cur.execute(update_query, (car_id, zone0, zone1, start_time, end_time, ride_id))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "200",
            "message": "Ride updated successfully",
            "data": {
                "rideID": ride_id,
                "carId": car_id,
                "source": source,
                "destination": destination,
                "startTime": start_time,
                "endTime": end_time,
                "scheduleID": schedule_id
            }
        }
        
    except sqlite3.Error as e:
        return {"status": "500", "message": f"Database error: {str(e)}"}
    except Exception as e:
        return {"status": "500", "message": f"Error: {str(e)}"}
    finally:
        if 'conn' in locals():
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


def cancel_ride(data):
    """
    Cancel/remove a ride with proper validation
    Enhanced version that verifies ownership
    """
    ride_id = data.get("rideID")
    user_id = data.get("userID")
    
    if not ride_id or not user_id:
        return {"status": "400", "message": "Missing rideID or userID"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Verify the user owns this ride
        cur.execute('SELECT ownerID FROM Ride WHERE rideID=?', (ride_id,))
        ride_owner = cur.fetchone()
        
        if not ride_owner:
            conn.close()
            return {"status": "404", "message": "Ride not found"}
        
        if ride_owner[0] != user_id:
            conn.close()
            return {"status": "403", "message": "You can only cancel your own rides"}
        
        # Delete the ride
        cur.execute('DELETE FROM Ride WHERE rideID=?', (ride_id,))
        conn.commit()
        conn.close()
        
        return {
            "status": "200",
            "message": "Ride cancelled successfully",
            "data": {"rideID": ride_id}
        }
        
    except sqlite3.Error as e:
        return {"status": "500", "message": f"Database error: {str(e)}"}


def request_ride(data):

    rider_id = data.get("riderID")
    area = data.get("area")
    time_str = data.get("time")
    direction = data.get("direction")
    min_rating = data.get("min_rating", 0.0)
    
    if not all([rider_id, area, time_str, direction]):
        return {"status": "400", "message": "Missing required fields"}
    
    try:
        pickup_lat = None
        pickup_lng = None
        if ',' in str(area):
            try:
                parts = str(area).split(',')
                pickup_lat = float(parts[0])
                pickup_lng = float(parts[1])
            except:
                pass
        
        time_parts = time_str.split(':')
        requested_time = int(time_parts[0]) * 60 + int(time_parts[1])
        print(requested_time)
        
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        query = '''
            SELECT r.rideID, r.ownerID, r.carId, r.sourceID, r.destinationID, 
                   r.startTime, r.endTime, r.scheduleID,
                   u.username, u.email,
                   zs.zoneName as source_name, zs.zoneX as source_lat, zs.zoneY as source_lng,
                   zd.zoneName as dest_name, zd.zoneX as dest_lat, zd.zoneY as dest_lng
            FROM Ride r
            JOIN "user" u ON r.ownerID = u.userID
            LEFT JOIN Zone zs ON r.sourceID = zs.zoneID
            LEFT JOIN Zone zd ON r.destinationID = zd.zoneID
            WHERE r.startTime <= ? AND r.endTime >= ?
        '''
        
        time_window_start = requested_time - 30
        time_window_end = requested_time + 30
        
        cur.execute(query, (time_window_end, time_window_start))
        rides = cur.fetchall()
        print(rides)
        conn.close()
        
        candidates = []
        for ride in rides:
            if ride[1] == rider_id:
                continue
            
            source_name = ride[10] or ""
            dest_name = ride[13] or ""
            
            # if direction == "to_aub":
            #     if "AUB" not in dest_name.upper() and "33.9" not in str(ride[14]):
            #         continue
            # else:  
            #     if "AUB" not in source_name.upper() and "33.9" not in str(ride[11]):
            #         continue
            
            distance_km = None
            if pickup_lat and pickup_lng and ride[11] and ride[12]:
                lat_diff = abs(pickup_lat - float(ride[11]))
                lng_diff = abs(pickup_lng - float(ride[12]))
                distance_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111
                
                if distance_km > 5:
                    continue
            
            start_hours = int(ride[5]) // 60
            start_mins = int(ride[5]) % 60
            end_hours = int(ride[6]) // 60
            end_mins = int(ride[6]) % 60
            
            candidate = {
                "rideID": ride[0],
                "driverID": ride[1],
                "driverUsername": ride[8],
                "driverEmail": ride[9],
                "carId": ride[2],
                "source": ride[3],
                "destination": ride[4],
                "source_name": ride[10],
                "dest_name": ride[13],
                "startTime": f"{start_hours:02d}:{start_mins:02d}",
                "endTime": f"{end_hours:02d}:{end_mins:02d}",
                "scheduleID": ride[7],
                "pickup_lat": ride[11],
                "pickup_lng": ride[12],
                "dest_lat": ride[14],
                "dest_lng": ride[15],
                "distance_km": round(distance_km, 2) if distance_km else None
            }
            candidates.append(candidate)
        
        print(candidates)
        if any(c.get('distance_km') for c in candidates):
            candidates.sort(key=lambda x: x.get('distance_km') or 999)
        else:
            candidates.sort(key=lambda x: x.get('startTime', ''))
        
        return {
            "status": "200",
            "message": f"Found {len(candidates)} matching rides",
            "data": {
                "candidates": candidates,
                "count": len(candidates)
            }
        }
        
    except sqlite3.Error as e:
        return {"status": "500", "message": f"Database error: {str(e)}"}
    except Exception as e:
        return {"status": "500", "message": f"Error: {str(e)}"}



def get_my_rides_detailed(data):
    """
    Get detailed list of user's rides with full information
    Includes zone names, car details, and proper time formatting
    """
    user_id = data.get("userID")
    
    if not user_id:
        return {"status": "400", "message": "Missing userID"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        query = '''
            SELECT r.rideID, r.carId, r.sourceID, r.destinationID,
                   r.startTime, r.endTime, r.scheduleID,
                   zs.zoneName as source_name, zs.zoneX as source_lat, zs.zoneY as source_lng,
                   zd.zoneName as dest_name, zd.zoneX as dest_lat, zd.zoneY as dest_lng,
                   c.cartype, c.carPlate, c.capacity
            FROM Ride r
            LEFT JOIN Zone zs ON r.sourceID = zs.zoneID
            LEFT JOIN Zone zd ON r.destinationID = zd.zoneID
            LEFT JOIN Car c ON r.carId = c.carId
            WHERE r.ownerID = ?
            ORDER BY r.startTime
        '''
        
        cur.execute(query, (user_id,))
        rides = cur.fetchall()
        conn.close()
        
        rides_list = []
        for ride in rides:
            # Convert time from minutes to HH:MM
            start_hours = int(ride[4]) // 60
            start_mins = int(ride[4]) % 60
            end_hours = int(ride[5]) // 60
            end_mins = int(ride[5]) % 60
            
            # Determine direction based on destination
            dest_name = ride[10] or ""
            direction = "to_aub" if "AUB" in dest_name.upper() or "33.9" in str(ride[11]) else "from_aub"
            
            ride_data = {
                "rideID": ride[0],
                "carId": ride[1],
                "sourceID": ride[2],
                "destinationID": ride[3],
                "startTime": f"{start_hours:02d}:{start_mins:02d}",
                "endTime": f"{end_hours:02d}:{end_mins:02d}",
                "scheduleID": ride[6],
                "source_name": ride[7] or ride[2],
                "source_lat": ride[8],
                "source_lng": ride[9],
                "dest_name": ride[10] or ride[3],
                "dest_lat": ride[11],
                "dest_lng": ride[12],
                "direction": direction,
                "car_type": ride[13],
                "car_plate": ride[14],
                "capacity": ride[15]
            }
            rides_list.append(ride_data)
        
        return {
            "status": "200",
            "message": "Rides retrieved successfully",
            "data": rides_list
        }
        
    except sqlite3.Error as e:
        return {"status": "500", "message": f"Database error: {str(e)}"}
    

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
    
def submit_rating(data):
    """Submit a rating for a user"""
    rater_username = data.get("raterID")  # This is actually username
    ratee_username = data.get("rateeID")  # This is actually username
    ride_id = data.get("rideID")
    score = data.get("score")
    comment = data.get("comment", "")
    
    print(f"[BACKEND DEBUG] Received rating: rater={rater_username}, ratee={ratee_username}, ride={ride_id}, score={score}")
    
    if not all([rater_username, ratee_username, ride_id, score]):
        return {"status": "400", "message": "Missing required fields"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Convert usernames to user IDs
        cur.execute('SELECT userID FROM "user" WHERE username=?', (rater_username,))
        rater_result = cur.fetchone()
        if not rater_result:
            conn.close()
            return {"status": "400", "message": "Rater user not found"}
        rater_id = rater_result[0]
        
        cur.execute('SELECT userID FROM "user" WHERE username=?', (ratee_username,))
        ratee_result = cur.fetchone()
        if not ratee_result:
            conn.close()
            return {"status": "400", "message": "Ratee user not found"}
        ratee_id = ratee_result[0]
        
        print(f"[BACKEND DEBUG] Converted to IDs: rater_id={rater_id}, ratee_id={ratee_id}")
        
        # Check if rating already exists for this ride
        cur.execute('SELECT ratingID FROM Rating WHERE raterID=? AND rateeID=? AND rideID=?', 
                   (rater_id, ratee_id, ride_id))
        existing_rating = cur.fetchone()
        
        if existing_rating:
            conn.close()
            return {"status": "400", "message": "You have already rated this user for this ride"}
        
        # For chat-based ratings (fallback ride IDs), skip ride validation
        # For real rides, validate they exist in the system
        if not ride_id.startswith('chat_ride_'):
            # Verify the ride exists in the Ride table
            cur.execute('SELECT rideID FROM Ride WHERE rideID = ?', (ride_id,))
            ride_exists = cur.fetchone()
            if not ride_exists:
                conn.close()
                return {"status": "400", "message": "Ride not found in system"}
        
        # Convert score to integer (database expects INTEGER)
        try:
            score_int = int(float(score))  # Convert to float then to int
            if score_int < 0 or score_int > 5:
                conn.close()
                return {"status": "400", "message": "Score must be between 0 and 5"}
        except (ValueError, TypeError):
            conn.close()
            return {"status": "400", "message": "Invalid score format"}
        
        # Insert new rating
        rating_id = f"rating_{int(time.time()*1000)}"
        print(f"[BACKEND DEBUG] Inserting rating: ratingID={rating_id}, raterID={rater_id}, rateeID={ratee_id}, rideID={ride_id}, score={score_int}")
        
        cur.execute('INSERT INTO Rating (ratingID, raterID, rateeID, rideID, score, comment) VALUES (?, ?, ?, ?, ?, ?)',
                   (rating_id, rater_id, ratee_id, ride_id, score_int, comment))
        
        conn.commit()
        
        # Verify the rating was inserted
        cur.execute('SELECT * FROM Rating WHERE ratingID=?', (rating_id,))
        inserted_rating = cur.fetchone()
        print(f"[BACKEND DEBUG] Rating inserted: {inserted_rating is not None}")
        
        conn.close()
        
        return {"status": "200", "message": "Rating submitted successfully"}
    
    except sqlite3.Error as e:
        print(f"[BACKEND DEBUG] Database error: {str(e)}")
        return {"status": "500", "message": f"Database error: {str(e)}"}
    
def update_zone(data):
    """Update user's zone information"""
    userID = data.get("userID")
    zone = data.get("zone")
    zoneX = data.get("zoneX")
    zoneY = data.get("zoneY")
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Check if zone exists for user
        cur.execute('SELECT zoneID FROM Zone WHERE UserID=?', (userID,))
        existing_zone = cur.fetchone()
        
        if existing_zone:
            # Update existing zone
            cur.execute('UPDATE Zone SET zoneName=?, zoneX=?, zoneY=? WHERE UserID=?', (zone, float(zoneX), float(zoneY), userID))
        else:
            # Create new zone entry
            zone_id = f"zone_{int(time.time()*1000)}"
            cur.execute('INSERT INTO Zone (zoneID, zoneX, zoneY, zoneName, UserID) VALUES (?, ?, ?, ?, ?)', 
                       (zone_id, float(zoneX), float(zoneY), zone, userID))
        
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


def get_driver_requests(data):
    """
    Get all pending ride requests for a driver
    Returns list of requests with rider info and ride details
    """
    driver_userid = data.get("driver_userid")
    
    if not driver_userid:
        return {"status": "400", "message": "Missing driver_userid"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Get all pending requests for rides owned by this driver
        query = '''
            SELECT req.requestID, req.riderID, req.rideID, req.status, req.requestTime,
                   u.username as rider_username, u.email as rider_email,
                   r.sourceID, r.destinationID,
                   zs.zoneName as source_name, zd.zoneName as dest_name
            FROM Request req
            JOIN Ride r ON req.rideID = r.rideID
            JOIN "user" u ON req.riderID = u.userID
            LEFT JOIN Zone zs ON r.sourceID = zs.zoneID
            LEFT JOIN Zone zd ON r.destinationID = zd.zoneID
            WHERE r.ownerID = ? AND (req.status = 'pending' OR req.status IS NULL)
            ORDER BY req.requestTime DESC
        '''
        
        cur.execute(query, (driver_userid,))
        rows = cur.fetchall()
        
        requests = []
        for row in rows:
            area = f"{row[9]} → {row[10]}" if row[9] and row[10] else "Unknown route"
            requests.append({
                "requestID": row[0],
                "riderID": row[1],
                "rideID": row[2],
                "status": row[3] or "pending",
                "reqTime": row[4] or "N/A",
                "rider_username": row[5],
                "rider_email": row[6],
                "area": area
            })
        
        conn.close()
        return {
            "status": "200",
            "requests": requests,
            "count": len(requests)
        }
    
    except sqlite3.Error as e:
        return {"status": "500", "message": f"Database error: {str(e)}"}


def accept_ride_request(data):
    """
    Accept a ride request from a passenger
    Updates request status and returns passenger info for P2P chat
    """
    request_id = data.get("requestID")
    driver_userid = data.get("driver_userid")
    
    if not all([request_id, driver_userid]):
        return {"status": "400", "message": "Missing required fields"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Verify the request exists and belongs to a ride owned by this driver
        cur.execute('''
            SELECT req.requestID, req.riderID, req.rideID, r.ownerID
            FROM Request req
            JOIN Ride r ON req.rideID = r.rideID
            WHERE req.requestID = ?
        ''', (request_id,))
        
        request_data = cur.fetchone()
        
        if not request_data:
            conn.close()
            return {"status": "404", "message": "Request not found"}
        
        if request_data[3] != driver_userid:
            conn.close()
            return {"status": "403", "message": "You don't own this ride"}
        
        rider_id = request_data[1]
        ride_id = request_data[2]
        
        # Check ride capacity before accepting
        cur.execute('''
            SELECT c.capacity, r.carId
            FROM Ride r
            JOIN Car c ON r.carId = c.carId
            WHERE r.rideID = ?
        ''', (ride_id,))
        
        capacity_data = cur.fetchone()
        
        if not capacity_data:
            conn.close()
            return {"status": "400", "message": "Car information not found for this ride"}
        
        max_capacity = capacity_data[0]
        
        # Count current riders (excluding driver)
        cur.execute('SELECT COUNT(*) FROM Rider WHERE rideID = ?', (ride_id,))
        current_riders = cur.fetchone()[0]
        
        if current_riders >= max_capacity:
            conn.close()
            return {
                "status": "400", 
                "message": f"Ride is at full capacity ({max_capacity} passengers)"
            }
        
        # Update request status to accepted
        cur.execute('UPDATE Request SET status = ? WHERE requestID = ?', 
                   ('accepted', request_id))
        
        # Add rider to the ride in Rider table
        try:
            cur.execute('INSERT INTO Rider (userID, rideID) VALUES (?, ?)', 
                       (rider_id, ride_id))
        except sqlite3.IntegrityError:
            # Rider already added to this ride
            pass
        
        # Get passenger details for P2P chat
        cur.execute('''
            SELECT u.username, u.email, ip.userCurrentIP
            FROM "user" u
            LEFT JOIN IpInfos ip ON u.userID = ip.userID
            WHERE u.userID = ?
        ''', (rider_id,))
        
        passenger_data = cur.fetchone()
        
        conn.commit()
        conn.close()
        
        if passenger_data:
            return {
                "status": "200",
                "message": "Request accepted successfully",
                "rideID": ride_id,
                "passenger": {
                    "username": passenger_data[0],
                    "email": passenger_data[1],
                    "ip": passenger_data[2] or "Not available"
                }
            }
        else:
            return {"status": "500", "message": "Failed to retrieve passenger info"}
    
    except sqlite3.Error as e:
        return {"status": "500", "message": f"Database error: {str(e)}"}


def send_ride_request_to_driver(data):
    """
    Create a ride request from passenger to driver
    This creates a new Request entry in the database
    """
    rider_id = data.get("riderID")
    ride_id = data.get("rideID")
    driver_username = data.get("driver_username")
    
    if not all([rider_id, ride_id]):
        return {"status": "400", "message": "Missing required fields"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Verify the ride exists
        cur.execute('SELECT rideID, ownerID FROM Ride WHERE rideID = ?', (ride_id,))
        ride_data = cur.fetchone()
        
        if not ride_data:
            conn.close()
            return {"status": "404", "message": "Ride not found"}
        
        driver_id = ride_data[1]
        
        # Check if request already exists
        cur.execute('''
            SELECT requestID, status FROM Request 
            WHERE riderID = ? AND rideID = ?
        ''', (rider_id, ride_id))
        
        existing_request = cur.fetchone()
        
        if existing_request:
            if existing_request[1] == 'accepted':
                conn.close()
                return {"status": "400", "message": "You already have an accepted request for this ride"}
            elif existing_request[1] == 'pending':
                conn.close()
                return {"status": "400", "message": "You already sent a request for this ride"}
        
        # Generate unique request ID
        import uuid
        import time
        request_id = f"REQ_{rider_id}_{ride_id}_{int(time.time())}"
        current_timestamp = int(time.time())
        
        # Create new request
        cur.execute('''
            INSERT INTO Request (requestID, riderID, rideID, status, requestTime)
            VALUES (?, ?, ?, ?, ?)
        ''', (request_id, rider_id, ride_id, 'pending', current_timestamp))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "200",
            "message": "Ride request sent successfully",
            "requestID": request_id
        }
    
    except sqlite3.Error as e:
        return {"status": "500", "message": f"Database error: {str(e)}"}


def check_passenger_accepted_requests(data):
    """
    Check if any of passenger's requests have been accepted by drivers
    Returns list of newly accepted requests with driver info
    """
    rider_id = data.get("riderID")
    
    if not rider_id:
        return {"status": "400", "message": "Missing riderID"}
    
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        
        # Get all accepted requests for this passenger
        query = '''
            SELECT req.requestID, req.rideID, req.status,
                   u.username as driver_username, u.email as driver_email,
                   r.sourceID, r.destinationID,
                   zs.zoneName as source_name, zd.zoneName as dest_name,
                   ip.userCurrentIP as driver_ip
            FROM Request req
            JOIN Ride r ON req.rideID = r.rideID
            JOIN "user" u ON r.ownerID = u.userID
            LEFT JOIN Zone zs ON r.sourceID = zs.zoneID
            LEFT JOIN Zone zd ON r.destinationID = zd.zoneID
            LEFT JOIN IpInfos ip ON u.userID = ip.userID
            WHERE req.riderID = ? AND req.status = 'accepted'
            ORDER BY req.requestTime DESC
        '''
        
        cur.execute(query, (rider_id,))
        rows = cur.fetchall()
        
        accepted_requests = []
        for row in rows:
            route = f"{row[7]} → {row[8]}" if row[7] and row[8] else "Unknown route"
            accepted_requests.append({
                "requestID": row[0],
                "rideID": row[1],
                "status": row[2],
                "driver_username": row[3],
                "driver_email": row[4],
                "driver_ip": row[9] or "Not available",
                "route": route
            })
        
        conn.close()
        return {
            "status": "200",
            "accepted_requests": accepted_requests,
            "count": len(accepted_requests)
        }
    
    except sqlite3.Error as e:
        return {"status": "500", "message": f"Database error: {str(e)}"}