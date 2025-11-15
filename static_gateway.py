import socket
import threading
import time
import json
import sqlite3
from authServer import handle_login, handle_sign_up
from update_personal_info import personal_info_manager
from rideManagement import give_rides_using_filter, get_IP
from weather import get_weather_info


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0",9999))
print("Server started on port 9999 on " + socket.gethostbyname(socket.gethostname()))

server.listen()

def handle_client(client_socket):
    try:
        while True:
            request = client_socket.recv(4096).decode('utf-8')
            
            if not request:
                break
            data = json.loads(request)
            action = data.get("action")
            if action == "login":
                response = handle_login(data,client_socket)
            elif action == "sign_up":
                response = handle_sign_up(data,client_socket)
            elif action == "update_personal_info":
                response = personal_info_manager(data)
            elif action == "ride_filter":
                response = give_rides_using_filter(data)
            elif action == "get_ip":
                response = get_IP(data)
            elif action == "get_weather":
                response = get_weather_info(data)
            elif action == "quit":
                try:
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    conn = sqlite3.connect('aubus.db')
                    cur = conn.cursor()
                    cur.execute("SELCECT * FROM IpInfos WHERE userCurrentIP=?", (client_socket.getpeername()[0],))
                    userValidity = cur.fetchone()
                    if not userValidity:
                        response = {"status": "200", "message": "Connection closed"}
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        break
                    else:
                        cur.execute("DELETE FROM IpInfos WHERE userCurrentIP=?", (client_socket.getpeername()[0],))
                        conn.close()
                        response = {"status": "200", "message": "Connection closed"}
                        break
                except sqlite3.Error as e:
                    response = {"status": "500", "message": "Database connection error failed to disconnect properly please try again"}
            else:
                response = {"status": "400", "message": "Invalid action"}
            client_socket.send(json.dumps(response).encode('utf-8'))
    except Exception as e:
        print(str(e))
        error_response = {"status": "500", "message": f"Server error: {str(e)}"}
        client_socket.send(json.dumps(error_response).encode('utf-8'))

    finally:
        client_socket.close()
        print("closing connection")

def start_server():
    while True:
        client_socket, addr = server.accept()
        print(f"Connection from {addr} has been established.")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()
start_server()
server.close()