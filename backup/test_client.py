# import socket
# import threading
# import json


# #this is for abdulsater to see how he can use the services in the backend to fetch from the backend
# #all these informations

# client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# client.connect((socket.gethostname(), 9999))

# def send_request(request_data):
#     client.send(json.dumps(request_data).encode('utf-8'))
#     response = client.recv(4096).decode('utf-8')
#     return json.loads(response)

# print(send_request({"action": "sign_up", "userName": "testuser", "password": "testpass","email":"aaa12@mail.aub.edu","isDriver":True,"aubID":"123456"}))
# print(send_request({"action": "login", "userName": "testuser", "password": "testpass"}))



import socket, json, sys, time

SERVER_HOST = socket.gethostname()
SERVER_PORT = 9999

def send_request(req):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_HOST, SERVER_PORT))
    s.send(json.dumps(req).encode('utf-8'))
    resp = s.recv(8192).decode('utf-8')
    s.close()
    try:
        return json.loads(resp)
    except:
        return resp

def signup(username, password, email, isDriver=False, aubID="202500049"):
    req = {"action":"sign_up", "type_of_connection":"signUp", "userName":username, "password":password, "email":email, "isDriver":isDriver, "aubID":aubID}
    return send_request(req)

def login(username, password):
    req = {"action":"login", "type_of_connection":"login", "userName":username, "password":password}
    return send_request(req)

def register_ip(userID, ip=None, port=None):
    req = {"action":"register_ip", "userID": userID, "ip": ip, "port": port}
    return send_request(req)

def add_ride(userID, source, dest, startTime, endTime, pickup_lat=None, pickup_lng=None):
    req = {"action":"update_personal_info", "type_of_connection":"add_ride", "userID": userID, "carId":None, "source": source, "destination": dest, "startTime": startTime, "endTime": endTime, "scheduleID": None, "pickup_lat": pickup_lat, "pickup_lng": pickup_lng}
    return send_request(req)

def request_ride(riderID, area, time_str, direction="to_aub"):
    req = {"action":"request_ride", "riderID": riderID, "area": area, "time": time_str, "direction": direction}
    return send_request(req)

def get_requests(driver_userid):
    req = {"action":"get_requests", "driver_userid": driver_userid}
    return send_request(req)

def accept_ride(requestID, driver_userid, selected_rideID=None):
    req = {"action":"accept_ride", "requestID": requestID, "driver_userid": driver_userid, "selected_rideID": selected_rideID}
    return send_request(req)

if __name__ == "__main__":
    # Example quick flow:
    # 1) create two users (driver & passenger)
    print("Signing up driver1...")
    print(signup("driver1", "pass123", "driver1@mail.aub.edu", isDriver=True))
    print("Signing up passenger1...")
    print(signup("passenger1", "pass123", "passenger1@mail.aub.edu", isDriver=False))
    time.sleep(0.5)
    # 2) login to get userIDs
    d = login("driver1", "pass123")
    p = login("passenger1", "pass123")
    print("driver login:", d)
    print("passenger login:", p)
    driver_id = d.get("userID")
    passenger_id = p.get("userID")
    # 3) register IPs (simulate P2P readiness)
    print("Registering driver IP...")
    print(register_ip(driver_id, ip="127.0.0.1", port=50001))
    print("Registering passenger IP...")
    print(register_ip(passenger_id, ip="127.0.0.1", port=50002))
    # 4) driver adds a ride
    print("Driver adding ride (source='Hamra') ...")
    print(add_ride(driver_id, source="Hamra, Beirut", dest="AUB, Beirut", startTime="08:10", endTime="16:00"))
    # 5) passenger requests a ride
    print("Passenger requesting ride for 'Hamra' at 08:12 ...")
    req_res = request_ride(passenger_id, "Hamra, Beirut", "08:12", direction="to_aub")
    print("Request response:", req_res)
    # 6) driver polls for requests (in real app driver filters)
    print("Driver polling requests...")
    print(get_requests(driver_id))
    # 7) simulate driver accepts the first request id returned earlier
    req_id = req_res.get("requestID")
    if req_id:
        print("Driver accepting request", req_id)
        print(accept_ride(req_id, driver_id))
    else:
        print("No requestID returned")


