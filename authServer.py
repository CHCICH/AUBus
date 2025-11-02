import json

"""
data is transimitted in this format to authenticate we send a stringified json message that needs to be parsed
in this message the format looks like that

{
    "code_req":101, // this indicates that it is a auth connection
    "data_req":{
        "type_of_connection" : "login" | "signUp",
        "userName",
        "password",
        "email",
    }

}
"""

def handle_login(data):
    username = data.get("userName")
    password = data.get("password")
    


def handle_sign_up(data):
    username = data.get("userName")
    password = data.get("password")
    email = data.get("email")


def handle_auth(connection):
    try:
        while True:
            msg = connection.recv(1024)
            if not msg:
                break
            user_data = msg.decode("utf-8")
            user_data = json.loads(user_data)

            if user_data.get("code_req") == 101:
                data = user_data.get("data_req", {})
                if data.get("type_of_connection") == "login":
                    handle_login(data)
                elif data.get("type_of_connection") == "signUp":
                    handle_sign_up(data)

    except (ConnectionAbortedError, ConnectionResetError):
        print("Connection terminated by client.")
    finally:
        connection.close()
        print("closing connection")


