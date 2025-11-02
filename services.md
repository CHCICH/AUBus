# DB schema 

```DaC
user[icon:user,color:yellow]{
  username  string
  email string
  password string
  aubID int
  userID int pk
  isDriver bool 
}

Ride[icon:rails, color: lightblue]{
  ownerID string fk
  rideID string pk
  carId string
  source string
  destination string
  startTime DATE
  endTime DATE
  scheduleID string fk
}

Car[icon:car, color:pink]{
  carId string pk
  cartype string
  carPlate string
  capacity string
  ownerID string fk
}


Rider[icon:interconnect, color:green]{
  userID string fk
  rideID string fk
}

schedule[icon:data, color:orange]{
  userID string fk
  scheduleID string pk
}

Request[icon:bell, color:purple]{
  requestID string pk
  riderID string fk
  rideID string fk
  status string
  requestTime DATE
}


user.userID < Car.ownerID
user.userID < Ride.ownerID
Ride.rideID < Request.rideID
user.userID - schedule.userID
schedule.scheduleID < Ride.scheduleID
user.userID < Rider.userID
Ride.rideID < Rider.rideID
user.userID < Request.riderID


```

