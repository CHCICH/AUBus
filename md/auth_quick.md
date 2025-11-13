# Auth — Quick frontend guide

A short, practical guide for frontend developers describing how to call authentication flows through the project's gateway (`static_gateway.py`). Keep it minimal — just what you need to wire up UI interactions.

Transport & entry
- TCP gateway: host running `static_gateway.py`, port 9999.
- Send a single JSON object encoded as UTF-8 over the socket. The gateway looks at the top-level `action` field and forwards the JSON to the auth handlers.

Supported gateway actions (quick)
- Login
  - action: "login"
  - payload: { "action": "login", "userName": "<string>", "password": "<string>" }
  - success: { "status": "200", "message": "Authenticated", "email": "<user email>" }
  - failure: { "status": "401", "message": "Invalid credentials..." }

- Sign up
  - action: "sign_up"
  - payload: { "action": "sign_up", "userName": "<string>", "password": "<string>", "email": "<string>", "isDriver": <bool>, "aubID": <string|null> }
  - success: { "status": "201", "message": "User created successfully", "data": { ... } }
  - possible failures: duplicate user/email ("400"), invalid email ("400"), service/DB error ("400").

General UI guidance
- Show a loading indicator while waiting for the gateway response.
- On success:
  - Login: proceed to authenticated UI, you can use the returned `email` for display.
  - Sign-up: inspect `response["data"]` for created user details (username, email, isDriver, aubID, userID) and then route user to login or auto-login flow.
- On error: show the `message` string to the user in a visible notification. For status "400" or "500" suggest retry or contact support.
- For invalid credentials (status "401") show a clear message and avoid leaking sensitive details.

Implementation tips
- Reuse the same TCP connection for multiple requests during a session. Send {"action":"quit"} when finished to close the socket cleanly.
- Always JSON-decode the gateway response and check `status` before using returned fields.
- Keep the UI resilient: the backend returns string codes ("200","201","400","401"). Treat any non-"200"/"201" as an error.

Example minimal login client (Python)

```python
import socket, json

payload = {"action": "login", "userName": "alice", "password": "s3cr3t"}
s = socket.socket()
s.connect((socket.gethostname(), 9999))
s.send(json.dumps(payload).encode('utf-8'))
resp = json.loads(s.recv(4096).decode('utf-8'))
if resp.get('status') == '200':
    # success -> resp['email'] available
    pass
else:
    # show resp['message'] to user
    pass
s.send(json.dumps({"action": "quit"}).encode('utf-8'))
s.close()
```

If you want a compact JSON Schema or a small JS fetch-style example for your GUI (WebSocket or TCP client library), tell me which target (React, plain JS, Electron) and I'll add one.
