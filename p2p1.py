import sys
import socket
import threading
import json
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QLabel, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QFont

MANAGEMENT_SERVER = "127.0.0.1"
MANAGEMENT_PORT = 10000

class SignalEmitter(QObject):
    message_received = pyqtSignal(str)
    status_update = pyqtSignal(str)
    connection_established = pyqtSignal()

class P2PChatGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # runtime state
        self.username = None
        self.dest_name = None
        self.mgmt_sock = None         # management connection socket (kept open)
        self.mgmt_thread = None
        self.p2p_listener = None      # listening socket for incoming P2P
        self.p2p_port = None
        self.p2p_conn = None          # established P2P connection socket (in/out)
        self.p2p_lock = threading.Lock()
        self.listening_thread = None
        self.running = False

        # UI signals
        self.signals = SignalEmitter()
        self.signals.message_received.connect(self.display_message)
        self.signals.status_update.connect(self.update_status)
        self.signals.connection_established.connect(self.enable_chat)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("P2P Chat")
        self.setGeometry(100,100,640,480)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        h = QHBoxLayout()
        self.user_id_input = QLineEdit(); self.user_id_input.setPlaceholderText("Your username")
        h.addWidget(QLabel("You:")); h.addWidget(self.user_id_input)

        self.dest_id_input = QLineEdit(); self.dest_id_input.setPlaceholderText("Destination username")
        h.addWidget(QLabel("Dest:")); h.addWidget(self.dest_id_input)

        self.connect_btn = QPushButton("Connect"); self.connect_btn.clicked.connect(self.on_connect)
        h.addWidget(self.connect_btn)
        self.disconnect_btn = QPushButton("Disconnect"); self.disconnect_btn.clicked.connect(self.on_disconnect)
        self.disconnect_btn.setEnabled(False); h.addWidget(self.disconnect_btn)
        self.reconnect_btn = QPushButton("Reconnect"); self.reconnect_btn.clicked.connect(self.on_reconnect)
        self.reconnect_btn.setEnabled(False); h.addWidget(self.reconnect_btn)

        layout.addLayout(h)

        self.status_label = QLabel("Status: Not connected"); self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.chat_display = QTextEdit(); self.chat_display.setReadOnly(True); self.chat_display.setFont(QFont("Arial", 11))
        layout.addWidget(self.chat_display)

        h2 = QHBoxLayout()
        self.message_input = QLineEdit(); self.message_input.setEnabled(False); self.message_input.returnPressed.connect(self.on_send)
        h2.addWidget(self.message_input)
        self.send_btn = QPushButton("Send"); self.send_btn.setEnabled(False); self.send_btn.clicked.connect(self.on_send)
        h2.addWidget(self.send_btn)
        layout.addLayout(h2)

    # ---------------- UI helpers ----------------
    def update_status(self, text):
        self.status_label.setText("Status: " + text)
        if "Connected" in text:
            color = "green"
        elif "Waiting" in text or "Connecting" in text:
            color = "orange"
        else:
            color = "red"
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def display_message(self, text):
        self.chat_display.append(text)

    def enable_chat(self):
        self.message_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(True)
        self.connect_btn.setEnabled(False)
        self.reconnect_btn.setEnabled(True)

    # ---------------- user actions ----------------
    def on_connect(self):
        name = self.user_id_input.text().strip()
        dest = self.dest_id_input.text().strip()
        if not name or not dest:
            QMessageBox.warning(self, "Error", "Fill both usernames")
            return
        self.username = name
        self.dest_name = dest
        self.chat_display.clear()
        self.running = True
        # start P2P listener first (dynamic port)
        self._start_p2p_listener()
        # then register with management server and keep mgmt socket
        self.mgmt_thread = threading.Thread(target=self._management_register_and_listen, daemon=True)
        self.mgmt_thread.start()
        self.signals.status_update.emit("Connecting...")

    def on_disconnect(self):
        # manual disconnect: clear chat and shutdown sockets
        self.signals.status_update.emit("Disconnecting...")
        self.running = False
        self._cleanup_all()
        self.chat_display.clear()
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.reconnect_btn.setEnabled(True)
        self.signals.status_update.emit("Disconnected")

    def on_reconnect(self):
        # allow user to change names then connect again
        self.on_disconnect()
        self.user_id_input.clear()
        self.dest_id_input.clear()
        self.connect_btn.setEnabled(True)
        self.reconnect_btn.setEnabled(False)
        self.chat_display.append("\n=== Ready to reconnect ===\n")

    def on_send(self):
        msg = self.message_input.text().strip()
        if not msg:
            return
        with self.p2p_lock:
            if not self.p2p_conn:
                self.signals.status_update.emit("Not connected")
                return
            try:
                self.p2p_conn.sendall(msg.encode())
                self.display_message(f"You: {msg}")
                self.message_input.clear()
            except Exception as e:
                self.signals.status_update.emit("Send error: " + str(e))
                self._close_p2p_conn()

    # ---------------- internal helpers ----------------
    def _start_p2p_listener(self):
        """Open a dynamic listening port and start accept thread"""
        if self.p2p_listener:
            return
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", 0))           # system chooses free port
        srv.listen(1)
        self.p2p_listener = srv
        self.p2p_port = srv.getsockname()[1]
        self.display_message(f"[P2P] Listening on port {self.p2p_port}")
        self.listening_thread = threading.Thread(target=self._accept_p2p_loop, daemon=True)
        self.listening_thread.start()

    def _accept_p2p_loop(self):
        """Accepts one incoming P2P connection (then processes it)"""
        try:
            conn, addr = self.p2p_listener.accept()
            with self.p2p_lock:
                # if we already have a connection, close the new one
                if self.p2p_conn:
                    try: conn.close()
                    except: pass
                    return
                self.p2p_conn = conn
            self.signals.status_update.emit("Connected (incoming)!")
            self.signals.connection_established.emit()
            # start recv loop
            self._p2p_recv_loop(conn, incoming=True)
        except Exception as e:
            # listener closed or error
            pass

    def _management_register_and_listen(self):
        """Register with management server (sending actual dynamic p2p_port),
           then keep mgmt socket open and handle incoming management messages."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(6.0)
            s.connect((MANAGEMENT_SERVER, MANAGEMENT_PORT))
            s.settimeout(None)
            self.mgmt_sock = s
            # send registration
            payload = {"UserID": self.username, "P2P_Port": self.p2p_port, "DestinationID": self.dest_name}
            s.sendall(json.dumps(payload).encode())

            # read initial response
            raw = s.recv(8192)
            if not raw:
                self.signals.status_update.emit("Management server closed")
                self._cleanup_mgmt()
                return
            resp = json.loads(raw.decode())
            # if server gave destination info immediately, attempt connect
            if resp.get("status") == "200" and resp.get("destination_ip"):
                # destination is online now
                dest_ip = resp["destination_ip"]
                dest_port = resp["destination_port"]
                # store dest info
                self._handle_peer_info(dest_ip, dest_port, resp.get("destination_name"))
            else:
                # registered and waiting — mgmt will notify us later
                self.signals.status_update.emit("Registered, waiting for peer...")

            # Now listen on mgmt socket for future notifications
            while self.running and self.mgmt_sock:
                try:
                    raw = self.mgmt_sock.recv(8192)
                    if not raw:
                        break
                    try:
                        msg = json.loads(raw.decode())
                    except Exception:
                        continue
                    # handle messages: either 'destination_now_online' or 'connection_request' or similar
                    if msg.get("message") == "destination_now_online" or msg.get("status") == "200" and msg.get("destination_ip"):
                        dest_ip = msg.get("destination_ip")
                        dest_port = msg.get("destination_port")
                        dest_name = msg.get("destination_name") or self.dest_name
                        self._handle_peer_info(dest_ip, dest_port, dest_name)
                    elif msg.get("type") == "connection_request":
                        # someone is asking us to connect to them (server told us a peer appeared and also sent source info)
                        src_ip = msg.get("source_ip")
                        src_port = msg.get("source_port")
                        src_name = msg.get("source_name") or msg.get("from")
                        self._handle_peer_info(src_ip, src_port, src_name)
                    else:
                        # ignore unknown mgmt messages
                        pass
                except Exception:
                    break
        except Exception as e:
            self.signals.status_update.emit("Management error: " + str(e))
            self._cleanup_mgmt()
        finally:
            self._cleanup_mgmt()

    def _handle_peer_info(self, ip, port, name):
        """Given peer ip/port/name (from mgmt), decide whether to connect or wait."""
        # Do nothing if we're already connected to someone
        with self.p2p_lock:
            if self.p2p_conn:
                return
        # store peer data
        self.peer_name = name
        self.peer_ip = ip
        self.peer_port = port

        # decide who initiates: compare (local port, username) vs (peer port, peer name).
        # This deterministic rule prevents both sides from both connecting at once.
        local_key = (self.p2p_port, self.username)
        remote_key = (int(self.peer_port), self.peer_name)
        # if local_key < remote_key -> initiate outgoing connect; else wait for incoming
        if local_key < remote_key:
            self.signals.status_update.emit("Initiating P2P connection (outgoing)...")
            threading.Thread(target=self._attempt_outgoing_connect, daemon=True).start()
        else:
            self.signals.status_update.emit("Waiting for incoming P2P connection...")

    def _attempt_outgoing_connect(self):
        """Try to connect to peer; if succeed, set p2p_conn and start recv loop."""
        try:
            cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli.settimeout(6.0)
            cli.connect((self.peer_ip, int(self.peer_port)))
            cli.settimeout(None)
            with self.p2p_lock:
                if self.p2p_conn:
                    # someone else already connected us
                    cli.close()
                    return
                self.p2p_conn = cli
            self.signals.status_update.emit("Connected (outgoing)!")
            self.signals.connection_established.emit()
            self._p2p_recv_loop(cli, incoming=False)
        except Exception as e:
            self.signals.status_update.emit("Outgoing connect failed: " + str(e))

    def _p2p_recv_loop(self, conn, incoming):
        """Loop receiving messages from an established P2P conn."""
        try:
            while self.running:
                data = conn.recv(4096)
                if not data:
                    break
                # display with peer name if available
                who = getattr(self, "peer_name", "Peer") or "Peer"
                self.signals.message_received.emit(f"{who}: {data.decode()}")
        except Exception:
            pass
        finally:
            # cleanup p2p connection on close
            self._close_p2p_conn()
            self.signals.status_update.emit("Connection closed")

    def _close_p2p_conn(self):
        with self.p2p_lock:
            if self.p2p_conn:
                try:
                    self.p2p_conn.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    self.p2p_conn.close()
                except:
                    pass
                self.p2p_conn = None

    def _cleanup_mgmt(self):
        if self.mgmt_sock:
            try:
                self.mgmt_sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.mgmt_sock.close()
            except:
                pass
            self.mgmt_sock = None

    def _cleanup_all(self):
        # close p2p conn and listener and mgmt socket
        self._close_p2p_conn()
        if self.p2p_listener:
            try:
                self.p2p_listener.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.p2p_listener.close()
            except:
                pass
            self.p2p_listener = None
        self._cleanup_mgmt()

    def closeEvent(self, ev):
        self.running = False
        self._cleanup_all()
        ev.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = P2PChatGUI()
    window.show()
    sys.exit(app.exec_())
