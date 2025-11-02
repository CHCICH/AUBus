# AUBus backend auth documentation

## request code

Authentication: 101
PersonalInfoRequest: 110


## Auth

data is transimitted in this format to authenticate we send a stringified json message that needs to be parsed
in this message the format looks like that



```json
{
    "code_req":101, // this indicates that it is a auth connection
    "data_req":{
        "type_of_connection" : "login" | "signUp",
        "userName":"username",
        "password":"password",
        "email":"email"
    }

}
```