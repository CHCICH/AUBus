import json
import sqlite3
import threading
import socket


PORT = 10000
ADDRESS = "0.0.0.0"

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((ADDRESS, PORT))

server.listen()

print(f"P2P management Server started on port {PORT} on " + socket.gethostbyname(socket.gethostname()))

def handle_client(client_socket):
    try:
        while True:
            request = client_socket.recv(4096).decode('utf-8')
            if not request:
                break
            data = json.loads(request)
            
            try:
                userID = data.get("UserID")
                destinationID = data.get("DestinationID")

            except Exception as e:
                response = {"status": "400", "message": "Invalid request format"}
            client_socket.send(json.dumps(response).encode('utf-8'))
    except Exception as e:
        error_response = {"status": "500", "message": f"Server error: {str(e)}"}
        client_socket.send(json.dumps(error_response).encode('utf-8'))
    finally:
        client_socket.close()

def start_server():
    while True:
        client_socket, address = server.accept()
        print(f"p2p server connected to {address}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()

start_server()
server.close()