import json
import sqlite3
import time  


def personal_info_manager(data):
    req_code = data.get("type_of_connection")
    if req_code == "edit_role":
        return handle_edit_role(data)
    elif req_code == "edit_name":
        return handle_edit_name(data)
    elif req_code == "edit_schdule":
        return handle_edit_schedule(data)
    elif req_code == "add_ride":
        return add_ride(data)
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
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM "user" WHERE username=?', (new_name,))
        existing_user = cur.fetchone()
        if existing_user:
            conn.close()
            return {"status": "400", "message": "Username already exists"}
        cur.execute('UPDATE "user" SET username=? WHERE userID=?', (new_name, userID))
        conn.commit()
        conn.close()
        return {"status": "200", "message": "Name updated successfully"}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}
    

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
        cur.execute("SELECT startTime, endTime FROM schedule WHERE scheduleID=?", (scheduleID,))
        existing_schedule = cur.fetchone()
        if not existing_schedule:
            conn.close()
            return {"status": "400", "message": "Schedule does not exist"}
        existing_schedule = list(existing_schedule)
        if checkIntersection(existing_schedule, (startTime, endTime)):
            conn.close()
            return {"status": "400", "message": "Ride time conflicts with existing schedule"}

        cur.execute('INSERT INTO Ride (rideID, ownerID, carId, source, destination, startTime, endTime, scheduleID) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (rideID, userID, carId, source, destination, startTime, endTime, scheduleID))
        conn.commit()
        conn.close()
        return {"status": "201", "message": "Ride added successfully", "data":{"rideID": rideID, "ownerID": userID, "carId": carId, "source": source, "destination": destination, "startTime": startTime, "endTime": endTime, "scheduleID": scheduleID}}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}

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
    
def remove_schedule(data):
    schedule_id = data.get("scheduleID")
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('DELETE FROM schedule WHERE scheduleID=?', (schedule_id,))
        conn.commit()
        conn.close()
        return {"status": "200", "message": "Schedule removed successfully"}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}

def handle_edit_schedule(data):
    pass

