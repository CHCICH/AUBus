import json
import sqlite3
import time

"""
what we can do is filter using different parameters
filter{
    rating:[ratingStart, ratingEnd]
    distance: to the driver
    date:[startDate, endDate]
}

the client alwyas has to give a start and an end they should be valid integers 
"""

def give_rides_using_filter(data):
    userID = data.get("userID")
    data_filter = data.get("filter")
    userCurrentLocation = data.get("userLocation")
    try:
        conn = sqlite3.connect("aubus.db")
        curr = conn.cursor()
        
        rating_range = data_filter.get("rating", [None, None])
        dist_km = data_filter.get("distance")
        date_range = data_filter.get("date")
        if not date_range or rating_range[0] is None or rating_range[1] is None or dist_km is None:
            return {"status": "400", "message": "missing required filters (rating, date, distance)"}

        start_ts = int(date_range[0])
        end_ts = int(date_range[1])
        r_start = float(rating_range[0])
        r_end = float(rating_range[1])

        try:
            user_lat = float(userCurrentLocation.get("lat", userCurrentLocation[0]))
            user_lon = float(userCurrentLocation.get("lon", userCurrentLocation[1]))
        except Exception:
            return {"status": "400", "message": "invalid userLocation"}
        
        deg_thresh = float(dist_km) / 111.0
        deg_thresh_sq = deg_thresh * deg_thresh

        sql = """
            SELECT Ride.* FROM Ride
            JOIN User ON Ride.ownerID = User.userID
            WHERE User.rating BETWEEN ? AND ?
              AND Ride.startTime >= ? AND Ride.endTime <= ?
              AND ((Ride.sourceLat - ?)*(Ride.sourceLat - ?) + (Ride.sourceLon - ?)*(Ride.sourceLon - ?)) <= ?
        """
        params = (r_start, r_end, start_ts, end_ts, user_lat, user_lat, user_lon, user_lon, deg_thresh_sq)
        curr.execute(sql, params)
        rows = curr.fetchall()
        conn.close()
        rides_list = []
        for ride in rows:
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
    
    