import socket
import threading
import json


#this is for abdulsater to see how he can use the services in the backend to fetch from the backend
#all these informations

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((socket.gethostname(), 9999))

def send_request(request_data):
    client.send(json.dumps(request_data).encode('utf-8'))
    response = client.recv(4096).decode('utf-8')
    return json.loads(response)

print(send_request({"action": "sign_up", "userName": "testuser", "password": "testpass","email":"aaa12@mail.aub.edu","isDriver":True,"aubID":"123456"}))
print(send_request({"action": "login", "userName": "testuser", "password": "testpass"}))