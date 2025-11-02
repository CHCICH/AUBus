# c2atp Protocol — Documentation

## Overview
c2atp is a TCP-based application protocol used to unify static and dynamic request handling for the platform. It routes all static requests through a c2atp gateway and handles asynchronous or user-interaction-dependent requests via a c2atp live server. Messages are transmitted as stringified JSON over TCP.

Goals:
- Unify WebSocket-like live interactions and API-gateway style static requests.
- Keep transport simple (text JSON) and compatible with TCP-based servers.

## High-level architecture
- Client ↔ Gateway: all static requests and initial routing pass through the gateway.
- Gateway ↔ Live Server: forwards dynamic/asynchronous interactions to the process managing them.
- Live Server ↔ Client: long-lived interactions and push messages are handled by the live server.
- Underlying transport: TCP sockets (use TLS in production).

## Message format
Every message is a JSON object encoded as UTF-8 text. Minimum recommended fields:
- req_URL (string): logical request path and action (e.g., "auth|login", "chat|send").
- data_body (object): payload specific to the functionality.
- meta (optional object): e.g., request_id, timestamp, auth_token, correlation_id.

Example:
```
{
    "req_URL": "auth|login",
    "data_body": {
        "username": "alice",
        "password": "••••"
    },
    "meta": {
        "request_id": "req-1234",
        "timestamp": "2025-11-02T12:00:00Z"
    }
}
```

## Framing (important)
TCP is a stream; you must define message boundaries. Two common options:
- Newline-delimited JSON (NDJSON): send each JSON followed by '\n'. Easy, but JSON must not contain raw newlines in top-level.
- Length-prefixed: prepend 4-byte big-endian length, then JSON bytes. Safer for arbitrary content.

Recommendation: use length-prefixed framing for robustness.

## Connection lifecycle
1. TCP connect (optionally TLS).
2. Optional handshake: client sends auth token / client metadata.
3. Server responds with acceptance or error.
4. Client sends requests; server replies or pushes events.
5. Heartbeat/keepalive: periodic ping/pong or empty heartbeat messages.
6. Graceful shutdown: send a close message and then close socket.

## Request types & routing
- Static request: handled entirely by gateway — short-lived, blocking.
- Dynamic/asynchronous: routed to live server — may involve correlation_id and pub/sub semantics.
- Push notifications: live server can send unsolicited messages to client.

## Error handling
Include an error object in responses:
```
{
    "req_URL": "auth|login",
    "error": {
        "code": "AUTH_FAILED",
        "message": "Invalid credentials"
    },
    "meta": { "request_id": "req-1234" }
}
```
Define a small set of codes (e.g., BAD_REQUEST, AUTH_FAILED, NOT_FOUND, SERVER_ERROR, TIMEOUT).

## Security
- Use TLS (TLS over TCP) in production.
- Authenticate at connection or per-request via tokens in meta.
- Validate and sanitize all inputs on server side.
- Rate-limit and quota per connection/client.
- Avoid sending secrets in logs.

## Implementation notes
- Parse framing before JSON decode.
- Keep message processing idempotent when possible (use request_id).
- Use correlation_id to track asynchronous workflows across gateway and live server.
- Implement exponential backoff for reconnects.
- Provide server-side diagnostics and monitoring for dropped connections, latency, and message errors.

## Minimal examples
Client (NDJSON):
{"req_URL":"chat|send","data_body":{"room":"r1","text":"hello"}}
Server response:
{"req_URL":"chat|send:response","data_body":{"status":"ok"},"meta":{"request_id":"req-1"}}

Length-prefixed example (pseudocode):
[0x00 0x00 0x00 0x45]{"req_URL":"auth|status","data_body":{"token":"t"}} 
