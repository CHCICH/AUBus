# authenticate(data_string) — Input / Output contract

The backend exposes a single entry point function `authenticate` that expects a JSON-encoded payload and returns a JSON-compatible dictionary describing the result.

General notes
- The backend expects a JSON object (application/json). If the payload is not valid JSON the response will be a 400 error.
- The JSON object must include a top-level key `type_of_connection` with one of the supported values:
    - "login"
    - "signUp"
- Response payloads use string codes in the `status` field (e.g. "200", "201", "400", "401") and a human-readable `message`. On success some responses include additional fields (see below).

1) Login
- Request (JSON)
    {
        "type_of_connection": "login",
        "userName": "<string>",
        "password": "<string>"
    }

- Successful response (authenticated)
    {
        "status": "200",
        "message": "Authenticated",
        "email": "<user email stored in DB>"
    }

- Failed authentication (wrong username/password)
    {
        "status": "401",
        "message": "Invalid credentials please try again and check your password or username"
    }

- Service/DB error
    {
        "status": "400",
        "message": "an unexpected error occurred: it seems that the service is down"
    }

2) Sign up
- Request (JSON)
    {
        "type_of_connection": "signUp",
        "userName": "<string>",
        "password": "<string>",
        "email": "<string>",       
        "isDriver": <boolean>,     
        "aubID": "<string|null>"   
    }

- Email validation rules
    - Email must contain exactly one '@'.
    - Local part (before '@') must be non-empty and at most 6 characters.
    - Domain must be exactly "aub.edu.lb" or "mail.aub.edu".

- Successful response (user created)
    {
        "status": "201",
        "message": "User created successfully",
        "data": {
            "username": "<string>",
            "email": "<string>",
            "isDriver": <boolean>,
            "aubID": "<string|null>",
            "userID": "<string>"   // generated user identifier
        }
    }

- Possible sign-up error responses
    - Username or email already exists:
        {
            "status": "400",
            "message": "Username or email already exists"
        }
    - Invalid email:
        {
            "status": "400",
            "message": "Email is not valid please provide a valid email"
        }
    - Service/DB error:
        {
            "status": "400",
            "message": "an unexpected error occurred: it seems that the service is down"
        }

3) Invalid request type
- If `type_of_connection` is missing or not one of the supported values:
    {
        "status": "400",
        "message": "Invalid type_of_connection value"
    }

4) Invalid JSON
- If the request body is not valid JSON:
    {
        "status": "400",
        "message": "Invalid JSON format"
    }

Examples
- Login example request body:
    {"type_of_connection":"login","userName":"alice","password":"s3cr3t"}

- Sign-up example request body:
    {"type_of_connection":"signUp","userName":"bob","password":"p@ss","email":"bob@aub.edu.lb","isDriver":false,"aubID":null}

Use these request/response shapes to integrate the frontend with the backend entrypoint.