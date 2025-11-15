import socket
import json


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
    


t = send_request({"action":"update_personal_info", "type_of_connection":"give_user_personal_informations" ,"userID":"1763216971"})
f = send_request({
            "action": "update_personal_info",
            "type_of_connection": "add_ride",
            "userID": "1763228265",
            "carId": "1",
            "source": (33.888630, 35.495480),
            "destination": (33.888630, 35.495480),
            "startTime": 9,
            "endTime": 99,
            "scheduleID": "1763228265",
        })
print(t)
print(f)