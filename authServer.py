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

def handle_login(data):
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
        return {"status": "200", "message": "Authenticated", "email": user[3]}
    else:
        return {"status": "401", "message": "Invalid credentials please try again and check your password or username"}


def handle_sign_up(data):
    username = data.get("userName")
    password = data.get("password")
    email = data.get("email")
    isDriver = data.get("isDriver", False)
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
        conn.commit()
        conn.close()
        return {"status": "201", "message": "User created successfully", "data":{"username": username, "email": email, "isDriver": isDriver, "aubID": aubID, "userID": userID}}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}
