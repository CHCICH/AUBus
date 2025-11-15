import json
import sqlite3
import time


def emaiIsCorrect(email):
    splitted_email = email.split('@')
    if len(splitted_email) != 2:
        return False
    username = splitted_email[0]
    domain = splitted_email[1]
    if username != "" and len(username) <= 6 and (domain == "aub.edu.lb" or domain == "mail.aub.edu"):
        return True
    return False

def generate_ID(username):
    return int(time.time())

def handle_login(data, client_socket):
    username = data.get("userName")
    password = data.get("password")
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM "user" WHERE username=? AND password=?', (username, password))
        user = cur.fetchone()
        conn.close()
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}
    if user:
        try:
            conn = sqlite3.connect('aubus.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO IpInfos (userID, userCurrentIP) VALUES (?, ?) ON CONFLICT(userID) DO UPDATE SET userCurrentIP=excluded.userCurrentIP", (0, client_socket.getpeername()[0]))
            conn.close()
        except sqlite3.Error as e:
            error_response = {"status": "500", "message": "Database connection error"}
            client_socket.send(json.dumps(error_response).encode('utf-8'))
        return {"status": "200", "message": "Authenticated", "data": {"username": username, "email": user[3], "isDriver": user[4], "aubID": user[5], "userID": user[6]}}
    else:
        return {"status": "401", "message": "Invalid credentials please try again and check your password or username"}


def handle_sign_up(data, client_socket):
    username = data.get("userName")
    password = data.get("password")
    email = data.get("email")
    isDriver = data.get("isDriver")
    aubID = data.get("aubID", None)
    zone = data.get("zone", None)
    try:
        conn = sqlite3.connect('aubus.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM "user" WHERE username=? OR email=? OR aubID=?', (username, email, aubID))
        existing_user = cur.fetchone()
        if existing_user:
            conn.close()
            return {"status": "400", "message": "Username or email already exists"}
        if not emaiIsCorrect(email):
            return {"status": "400", "message": "Email is not valid please provide a valid email"}
        userID = generate_ID(username)
        cur.execute('INSERT INTO "user" (username, password, email, isDriver, aubID, userID) VALUES (?, ?, ?, ?, ?, ?)', (username, password, email, bool(isDriver), int(aubID), int(userID)))
        cur.execute('INSERT INTO "Zone" (zoneID, zoneName, UserID) VALUES (?, ?, ?)', (generate_ID(zone), zone, int(userID)))
        cur.execute('SELECT * FROM "user" WHERE username=?', (username,))
        new_user = cur.fetchone()
        print(new_user)
        conn.commit()
        conn.close()
        print("here")
        try:
            conn = sqlite3.connect('aubus.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO IpInfos (userID, userCurrentIP) VALUES (?, ?) ON CONFLICT(userID) DO UPDATE SET userCurrentIP=excluded.userCurrentIP", (0, client_socket.getpeername()[0]))
            conn.close()
        except sqlite3.Error as e:
            error_response = {"status": "500", "message": "Database connection error"}
            client_socket.send(json.dumps(error_response).encode('utf-8'))
        return {"status": "201", "message": "User created successfully", "data":{"username": username, "email": email, "isDriver": isDriver, "aubID": aubID, "userID": userID}}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}
