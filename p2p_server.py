import socket
import threading
import json
import traceback

HOST = "0.0.0.0"
PORT = 10000

clients_lock = threading.Lock()
clients = {}       
client_info = {}
waiting = {}      

def send_json_raw(sock, obj):
    try:
        sock.sendall(json.dumps(obj).encode())
        return True
    except Exception:
        return False

def handle_management_connection(conn, addr):
    username = None
    try:
        conn.settimeout(8.0)
        raw = conn.recv(8192)
        if not raw:
            return
        data = json.loads(raw.decode())
        username = data.get("UserID")
        p2p_port = int(data.get("P2P_Port"))
        destination = data.get("DestinationID")

        if not username or p2p_port is None or destination is None:
            send_json_raw(conn, {"status":"400", "message":"UserID, P2P_Port, DestinationID required"})
            return

        with clients_lock:
            clients[username] = conn
            client_info[username] = {"ip": addr[0], "port": p2p_port}

        print(f"[REGISTER] {username} @ {addr[0]}:{p2p_port}")

        with clients_lock:
            waiting_list = waiting.pop(username, [])

        for source_name, source_conn in waiting_list:
            try:
                payload = {
                    "status": "200",
                    "message": "destination_now_online",
                    "destination_name": username,
                    "destination_ip": addr[0],
                    "destination_port": p2p_port
                }
                send_json_raw(source_conn, payload)
            except Exception:
                pass

        with clients_lock:
            dest_online = destination in clients
            dest_info = client_info.get(destination)

        if dest_online and dest_info:
            resp = {
                "status": "200",
                "message": "destination_online",
                "destination_name": destination,
                "destination_ip": dest_info["ip"],
                "destination_port": dest_info["port"]
            }
            send_json_raw(conn, resp)

            try:
                notify = {
                    "type": "connection_request",
                    "from": username,
                    "source_name": username,
                    "source_ip": addr[0],
                    "source_port": p2p_port
                }
                dest_conn = clients.get(destination)
                if dest_conn:
                    send_json_raw(dest_conn, notify)
            except Exception:
                pass
        else:
            with clients_lock:
                waiting.setdefault(destination, []).append( (username, conn) )
            send_json_raw(conn, {"status":"200", "message":"registered_waiting", "destination_name": destination})

        conn.settimeout(None)
        while True:
            try:
                chunk = conn.recv(1024)
                if not chunk:
                    break
            except Exception:
                break

    except Exception as e:
        print("[MANAGE ERROR]", e)
        traceback.print_exc()
    finally:
        if username:
            print(f"[UNREGISTER] {username}")
            with clients_lock:
                clients.pop(username, None)
                client_info.pop(username, None)
                for dest, lst in list(waiting.items()):
                    waiting[dest] = [pair for pair in lst if pair[0] != username]
                    if not waiting[dest]:
                        waiting.pop(dest, None)
        try:
            conn.close()
        except:
            pass

def start_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(100)
    print(f"[MANAGEMENT] listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = srv.accept()
            t = threading.Thread(target=handle_management_connection, args=(conn, addr), daemon=True)
            t.start()
    finally:
        srv.close()

if __name__ == "__main__":
    start_server()
