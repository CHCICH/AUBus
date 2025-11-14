# ride_manager.py
import sqlite3
import time
import math
from datetime import datetime
from mapsHelper import geocode_address, distance_matrix

DB = "aubus.db"

TIME_TOLERANCE_MIN = 15  # minutes for schedule time tolerance

def haversine(lat1, lon1, lat2, lon2):
    R = 6371e3  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def create_request(riderID, area, req_time, direction="to_aub"):
    requestID = f"req_{int(time.time()*1000)}"
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO Request (requestID, riderID, rideID, status, requestTime, area, reqTime) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (requestID, riderID, None, "pending", datetime.utcnow().isoformat(), area, req_time))
    conn.commit()
    conn.close()
    return requestID

def lookup_ipinfo_for_user(userID):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT userCurrentIP, userPort FROM IpInfos WHERE userID=?", (userID,))
    r = cur.fetchone()
    conn.close()
    if r:
        return {"ip": r[0], "port": r[1]}
    return None

def find_candidate_drivers_by_area_time(area, req_time, direction="to_aub", radius_m=3000, refine_with_google=True):
    """
    Returns candidate drivers near 'area' within radius_m, optionally refine with Distance Matrix for ETA.
    """
    # Geocode passenger area
    geoc = geocode_address(area)  # returns (lat,lng) or None
    if geoc:
        plat, plng = geoc
    else:
        # fallback: area text match on Ride.source; return all rides matching source string
        plat = plng = None

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT Ride.rideID, Ride.ownerID, Ride.source, Ride.destination, Ride.startTime, Ride.endTime, Ride.pickup_lat, Ride.pickup_lng, user.username FROM Ride JOIN \"user\" ON Ride.ownerID=user.userID")
    rows = cur.fetchall()
    conn.close()

    candidates = []
    for rideID, ownerID, source, dest, startTime, endTime, pickup_lat, pickup_lng, username in rows:
        # match area string first (coarse)
        if source is None:
            continue
        if area.lower().strip() not in source.lower().strip() and plat is None:
            continue

        # if pickup coords exist use them, else try to geocode ride.source
        if pickup_lat is None or pickup_lng is None:
            if source:
                g = geocode_address(source) if plat is not None else None
                if g:
                    ride_lat, ride_lng = g
                else:
                    continue
            else:
                continue
        else:
            ride_lat, ride_lng = pickup_lat, pickup_lng

        # compute straight-line distance if we have passenger coords
        if plat is not None:
            dist = haversine(plat, plng, ride_lat, ride_lng)
            if dist > radius_m:
                continue
        else:
            dist = None

        # time tolerance: optionally check startTime/endTime vs req_time (if present)
        # (we keep it simple here)
        candidate = {
            "rideID": rideID,
            "ownerID": ownerID,
            "owner_username": username,
            "ride_source": source,
            "ride_destination": dest,
            "ride_lat": ride_lat,
            "ride_lng": ride_lng,
            "distance_m": dist
        }
        candidates.append(candidate)

    # Optionally refine top candidates by driving ETA using Distance Matrix API
    if refine_with_google and plat is not None and candidates and len(candidates) > 0:
        origins = [(plat, plng)]
        destinations = [(c["ride_lat"], c["ride_lng"]) for c in candidates]
        dm = distance_matrix(origins, destinations)
        if dm and dm.get("status") == "OK":
            rows = dm.get("rows", [])
            if rows:
                elements = rows[0].get("elements", [])
                for i, c in enumerate(candidates):
                    if i < len(elements):
                        el = elements[i]
                        if el.get("status") == "OK":
                            c["duration_text"] = el["duration"]["text"]
                            c["duration_value"] = el["duration"]["value"]
                            c["distance_text"] = el["distance"]["text"]
                            c["distance_value"] = el["distance"]["value"]
    # Sort candidates by distance_value or straight-line distance
    candidates.sort(key=lambda x: x.get("distance_value") or (x.get("distance_m") or 1e12))
    return candidates

def get_requests_for_driver(driver_userid):
    """
    Return list of pending Request rows; later filter on driver rides.
    """
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT requestID, riderID, status, area, reqTime, requestTime FROM Request WHERE status='pending' ORDER BY requestTime DESC")
    rows = cur.fetchall()
    conn.close()
    res = []
    for requestID, riderID, status, area, reqTime, requestTime in rows:
        res.append({
            "requestID": requestID,
            "riderID": riderID,
            "area": area,
            "reqTime": reqTime,
            "requestTime": requestTime
        })
    return res

def accept_request(requestID, driver_userid, selected_rideID=None):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT requestID, riderID, status FROM Request WHERE requestID=?", (requestID,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"status": "400", "message": "Request not found"}
    if row[2] != "pending":
        conn.close()
        return {"status": "400", "message": "Request already handled"}
    riderID = row[1]

    # find a ride for driver if not provided
    if not selected_rideID:
        cur.execute("SELECT rideID FROM Ride WHERE ownerID=? LIMIT 1", (driver_userid,))
        r = cur.fetchone()
        if r:
            selected_rideID = r[0]
        else:
            conn.close()
            return {"status": "400", "message": "Driver has no ride to accept with"}

    cur.execute("UPDATE Request SET rideID=?, status=? WHERE requestID=?", (selected_rideID, "accepted", requestID))
    conn.commit()

    # lookup passenger ip
    cur.execute("SELECT userCurrentIP, userPort FROM IpInfos WHERE userID=?", (riderID,))
    ipdata = cur.fetchone()
    passenger_ip = ipdata[0] if ipdata else None
    passenger_port = ipdata[1] if ipdata else None

    cur.execute('SELECT username, email FROM "user" WHERE userID=?', (riderID,))
    u = cur.fetchone()
    username = u[0] if u else None
    email = u[1] if u else None

    conn.close()
    return {"status": "200", "message": "Request accepted", "passenger": {"userID": riderID, "username": username, "email": email, "ip": passenger_ip, "port": passenger_port}, "rideID": selected_rideID}
