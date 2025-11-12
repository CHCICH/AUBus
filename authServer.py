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
    return str(int(time.time() * 13* 1000)) + username[:3] + str(int(time.time() * 7 * 1000))

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
        cur.execute('INSERT INTO "user" (username, password, email, isDriver, aubID, userID) VALUES (?, ?, ?, ?, ?, ?)', (username, password, email, isDriver, aubID, generate_ID(username)))
        conn.commit()
        conn.close()
        return {"status": "201", "message": "User created successfully", "data":{"username": username, "email": email, "isDriver": isDriver, "aubID": aubID, "userID": generate_ID(username)}}
    except sqlite3.Error as e:
        return {"status": "400", "message": str("an unexpected error occurred: it seems that the service is down")}

def authenticate(data_string):
    try:
        data = json.loads(data_string)
    except json.JSONDecodeError:
        return {"status": "400", "message": "Invalid JSON format"}
    code_req = data.get("type_of_connection")
    if code_req == "login":
        return handle_login(data)
    elif code_req == "signUp":
        return handle_sign_up(data)
    else:
        return {"status": "400", "message": "Invalid type_of_connection value"}