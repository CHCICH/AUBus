import socket
import threading
import json
from datetime import datetime

HOST='0.0.0.0'
PORT=9000
users={}           #USERNAMES={password,name,email,area,is_driver,p2p_port,ip}
rides={}           #USERNAMES (FOR DRIVERS) list of ride entries 
pending_requests={} #REQEUEST_ID ={passenger,time,area,min_rating,status}
lock=threading.Lock()
request_counter=0
TIME_TOLERANCE_MIN = 15 


def parse_time_to_minutes(tstr): ####take hours:minutes
    h,m=map(int, tstr.split(':'))
    return h*60+m


def time_match(t1,t2,tol=TIME_TOLERANCE_MIN):
    return abs(parse_time_to_minutes(t1) - parse_time_to_minutes(t2)) <= tol


def send_json(conn, obj):
    data=json.dumps(obj).encode()
    conn.sendall(len(data).to_bytes(4, 'big') + data)


def recv_json(conn):
    raw_len=conn.recv(4)
    if not raw_len:
        return None
    length=int.from_bytes(raw_len, 'big')
    data =b''
    while len(data) < length:
        more = conn.recv(length - len(data))
        if not more:
            return None
        data += more
    return json.loads(data.decode())


def handle_add_ride(payload, client_addr):
    """
    payload: {
      "username": "...",
      "area": "Hamra",
      "to_aub_time": "08:15",
      "from_aub_time": "16:00",
      "days": ["Mon","Tue"],   # optional
      "p2p_port": 50001
    }
    """
    username=payload['username']
    with lock:
        rides.setdefault(username, []).append({
            'area': payload['area'],
            'to_aub_time': payload.get('to_aub_time'),
            'from_aub_time': payload.get('from_aub_time'),
            'days': payload.get('days', []),
            'p2p_port': payload.get('p2p_port'),
            'ip': client_addr[0],
        })
    return{'status':'OK','message':'Ride added'}


def handle_request_ride(payload):
    """
    payload: {
      'request_id' (optional),
      'passenger': username,
      'area':'Hamra',
      'time':'08:10',
      'direction': 'to_aub' or 'from_aub',
      'min_rating': 0
    }
    """
    global request_counter
    passenger=payload['passenger']
    area = payload['area']
    time = payload['time']
    direction = payload.get('direction', 'to_aub')

    with lock:
        request_counter += 1
        req_id = f"r{request_counter}"
        pending_requests[req_id] = {
            'passenger': passenger,
            'area': area,
            'time': time,
            'direction': direction,
            'status': 'pending',
            'candidates': []
        }
    candidates=[]
    with lock:
        for driver, driver_rides in rides.items():
            for r in driver_rides:
                if r['area'].lower() != area.lower():
                    continue
                driver_time=r.get('to_aub_time') if direction == 'to_aub' else r.get('from_aub_time')
                if not driver_time:
                    continue
                if time_match(driver_time, time):
                    candidates.append({
                        'driver': driver,
                        'ip': r['ip'],
                        'p2p_port': r.get('p2p_port'),
                        'to_aub_time': r.get('to_aub_time'),
                        'from_aub_time': r.get('from_aub_time'),
                    })
                    pending_requests[req_id]['candidates'].append(driver)

    # forward request to candidate drivers -- in production we'd open new connections or use persistent sessions
    # Here we'll simulate by storing the candidates and returning them so the client can contact the server to poll/accept
    return {'status': 'OK', 'request_id': req_id, 'candidates': candidates, 'message': f'{len(candidates)} drivers found'}


def handle_accept_ride(payload):
    """
    payload: {
      'request_id': 'r1',
      'driver': 'driver_username'
    }
    """
    req_id = payload['request_id']
    driver = payload['driver']
    with lock:
        req = pending_requests.get(req_id)
        if not req:
            return {'status': 'ERROR', 'message': 'Request not found'}
        if req['status'] != 'pending':
            return {'status': 'ERROR', 'message': 'Request already handled'}
        if driver not in req['candidates']:
            return {'status': 'ERROR', 'message': 'Driver not a candidate'}

        # Mark accepted
        req['status'] = 'accepted'
        req['accepted_driver'] = driver

        # Find driver's p2p info
        drv_entries = rides.get(driver, [])
        p2p_info = None
        if drv_entries:
            # pick most recent entry
            e = drv_entries[-1]
            p2p_info = {'ip': e['ip'], 'p2p_port': e.get('p2p_port')}

        # In a real implementation: notify passenger via an open socket / push.
        # Here we return the accepted driver details so the caller can forward to passenger.
        return {'status': 'OK', 'driver': driver, 'p2p_info': p2p_info}


def client_thread(conn, addr):
    try:
        while True:
            msg = recv_json(conn)
            if msg is None:
                print("Client disconnected", addr)
                break
            typ = msg.get('type')
            payload = msg.get('payload', {})
            print("Received", typ, "from", addr, payload.get('username') or payload.get('passenger'))

            if typ == 'ADD_RIDE':
                res = handle_add_ride(payload, addr)
                send_json(conn, {'type': 'ADD_RIDE_RESPONSE', 'payload': res})
            elif typ == 'REQUEST_RIDE':
                res = handle_request_ride(payload)
                send_json(conn, {'type': 'REQUEST_RIDE_RESPONSE', 'payload': res})
            elif typ == 'ACCEPT_RIDE':
                res = handle_accept_ride(payload)
                send_json(conn, {'type': 'ACCEPT_RIDE_RESPONSE', 'payload': res})
            else:
                send_json(conn, {'type': 'ERROR', 'payload': {'message': 'Unknown command'}})
    except Exception as e:
        print("Client thread error:", e)
    finally:
        conn.close()


def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(10)
    print("Server listening on", HOST, PORT)
    while True:
        conn, addr = s.accept()
        print("New connection from", addr)
        t = threading.Thread(target=client_thread, args=(conn, addr), daemon=True)
        t.start()


if __name__ == '__main__':
    start_server()
