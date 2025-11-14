import socket
import threading

IP = socket.gethostbyname(socket.gethostname())

otherClient_ServerPort = 9000
serverPORT = 9001


def handle_client():
    #Start a new thread for the server
    t2 = threading.Thread(target=serverSide,args=()) 
    t2.start()
    print("Client 2's Device: ")
    option = input("Would you like to send a message? y/n\n")
    if option == 'y':
        t1 = threading.Thread(target=clientSide,args=())
        t1.start()
        t1.join()
   
    
    
def serverSide():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((IP,serverPORT))
    
    server.listen()
    while True:
        connection, address = server.accept()
        message = connection.recv(1024).decode('utf-8')
        print(message)

        # Receive the file data
       
        
        #Signal successfully received data
        connection.sendall("0".encode('utf-8'))
       
        connection.close()
        break
    server.close()
        
def success():
    print("SUCCESS!")
        
# Send to server of secondClient
def clientSide():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((IP,otherClient_ServerPort))
    
    message = input(" What message would you like to send to Client 1? ")
    client.sendall(message.encode('utf-8'))
   

   
    
    if int(client.recv(1024).decode('utf-8')) == 0: success()
    else: print("An error occured.")
    

    client.close()
    
    
    
handle_client()

