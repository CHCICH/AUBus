## Update Personal Info — Gateway-level JSON contract

This document describes how to call the "update personal info" functionality over the project's gateway (TCP static gateway). It documents the exact JSON payload that the gateway expects, the transport details, and the JSON responses you will receive from the gateway.

Note: the gateway entrypoint used in this project is `static_gateway.py` listening on port 9999. The gateway routes requests by the top-level `action` field. To invoke update-personal-info behavior send a JSON object with `action: "update_personal_info"` and the rest of the payload described below.

---

Transport
- Protocol: TCP
- Host: machine running `static_gateway.py` (the project binds to the host returned by `socket.gethostname()`)
- Port: 9999
- Encoding: UTF-8
- Payload: a single JSON object as a UTF-8 string (no framing beyond the socket stream; the client should send the encoded JSON and read the gateway response as a JSON string).

Top-level gateway request shape

{
  "action": "update_personal_info",
  "type_of_connection": "<one of: edit_role, edit_name, edit_schdule>",
  ... other fields depending on the type_of_connection ...
}

The gateway will parse the JSON and call the update-personal-info handler with the same object. The handler expects the `type_of_connection` field and further parameters as shown below.

Supported `type_of_connection` values

1) edit_role

- Description: change a user's role (whether they are a driver).
- Required fields:
  - `action`: "update_personal_info"
  - `type_of_connection`: "edit_role"
  - `userID` (integer or string matching the DB userID)
  - `new_role` (string) — expected: "driver" to set driver flag, anything else will clear it

Example request

{
  "action": "update_personal_info",
  "type_of_connection": "edit_role",
  "userID": 12345,
  "new_role": "driver"
}

Example success response (gateway will forward handler response):

{
  "status": "200",
  "message": "Role updated successfully"
}

Possible error responses
- {"status": "400", "message": "an unexpected error occurred: it seems that the service is down"} — returned by the handler if the DB operation fails.
- {"status": "400", "message": "Invalid action"} — returned by the gateway if `action` is missing or wrong.
- {"status": "500", "message": "Server error: <error>"} — returned by the gateway in case of an unhandled exception.

2) edit_name

- Description: update a user's display name / username.
- Required fields:
  - `action`: "update_personal_info"
  - `type_of_connection`: "edit_name"
  - `userID` (integer or string)
  - `new_name` (string)

Example request

{
  "action": "update_personal_info",
  "type_of_connection": "edit_name",
  "userID": 12345,
  "new_name": "Alice A"
}

Example success response

{
  "status": "200",
  "message": "Name updated successfully"
}

Possible error responses are the same as for `edit_role`.

3) edit_schdule (note: current handler is not implemented)

- Description: intended to update a user's schedule. The handler `handle_edit_schedule` is present but not implemented (it currently does nothing). If you need this feature, implement the handler in `update_personal_info.py` and document the exact fields.

Example (placeholder) request

{
  "action": "update_personal_info",
  "type_of_connection": "edit_schdule",
  "userID": 12345,
  "schedule": { /* implement schedule format */ }
}

Expected behaviour today: the gateway will call the handler but it currently returns no response (handler is `pass`). You should implement the schedule logic in `update_personal_info.py` before relying on this route.

General gateway responses and notes
- Successful handler responses are returned by the gateway as JSON strings encoded with UTF-8.
- Handlers use string status codes (e.g. "200", "201", "400", "401"). Check the `message` field for human-readable details.
- The gateway itself will return `{ "status": "400", "message": "Invalid action" }` when `action` is not one of the supported values.
- If the gateway catches an exception it returns `{ "status": "500", "message": "Server error: <error>" }`.

Client implementation tips
- Always send a top-level `action` field. For update-personal-info use `action: "update_personal_info"`.
- Ensure numeric IDs match the DB (they may be stored as integers or strings depending on how users are created).
- Always JSON-encode the payload and send as UTF-8. Read the gateway response and JSON-decode it.
- Keep the socket open to send multiple requests in the same session; send `action: "quit"` when finished to close the connection cleanly.

Example Python client snippet

```python
import socket, json

payload = {
    "action": "update_personal_info",
    "type_of_connection": "edit_name",
    "userID": 12345,
    "new_name": "New Name"
}

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((socket.gethostname(), 9999))
s.send(json.dumps(payload).encode('utf-8'))
resp = s.recv(4096).decode('utf-8')
print('gateway response:', json.loads(resp))
s.send(json.dumps({"action": "quit"}).encode('utf-8'))
s.close()
```

If you want, I can extend this document with a formal JSON Schema for each `type_of_connection`, and a small test client for each route.
