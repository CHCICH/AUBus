import socket
import threading
import time
import json
from authServer import handle_login, handle_sign_up
from update_personal_info import personal_info_manager

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((socket.gethostname(),9999))
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
                response = handle_login(data)
            elif action == "sign_up":
                response = handle_sign_up(data)
            elif action == "update_personal_info":
                response = personal_info_manager(data)
            elif action == "quit":
                response = {"status": "200", "message": "Connection closed"}
                client_socket.send(json.dumps(response).encode('utf-8'))
                break
            else:
                response = {"status": "400", "message": "Invalid action"}
            client_socket.send(json.dumps(response).encode('utf-8'))
    except Exception as e:
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