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
            "action": "ride_filter",
            "userID": 1763228265,
            "filter": {
              "rating": [0, 5],
              "distance": 3,
              "date": [0, 9999999]
            },
            "userLocation": {
              "lat": 33.890652,
              "lon": 35.481205
            }
        })
print(t)
print(f)