import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.socket_rdt_sw import SocketRDT_SW
from common.socket_rdt_sr import SocketRDT_SR
import threading as t
import socket
from protocol_server import ProtocolServer 
from acceptor import Acceptor

BUFFER = 1024

# __MAIN__
def recv_loop(socket_principal):
    while True:
        socket_principal.recv()

def main():
    skt = SocketRDT_SR("localhost", 8082)
    skt.bind()
    acceptor = Acceptor(skt)

    accepter = t.Thread(target=acceptor.run)
    accepter.daemon = True
    accepter.start()

    
    recv_thread = t.Thread(target=recv_loop, args=(skt,))
    recv_thread.daemon = True
    recv_thread.start()

    while True:
        user_input = input().rstrip()
        if user_input == 'q':
            print("Shutting down server...")
            break

    print("1")
    acceptor.shutdown()
    print("2")
    accepter.join()
    print("3")
    recv_thread.join() 
    print("cerre")


if __name__ == "__main__":
    main()





# BUFFER_SIZE = 4096
# PORT_SERVER = 8086

# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # AF_INET hace q sea IPv4 y SOCK_DGRAM lo ha UDP

# sock.bind(('localhost', PORT_SERVER)) #bind es para asignar una ip y un puerto al socket

# i = 0

# while True:
#     data, address = sock.recvfrom(BUFFER_SIZE)

#     print(f"Recibido {data.decode()} desde {address}")
#     package = Package.decode_to_package(data)
#     print(package)
#     response = "ACK" + str(i) + ": recibido campeon"
#     i += 1
#     sock.sendto(response.encode(), address)

#skt = SocketRDT_SR("localhost", 8081)
#skt = SocketRDT_SW("localhost", 8081)
#skt = SocketRDT_SW("10.0.0.2", 8081)

#skt.bind()
#i = 0
#while True:
    #data = skt.recv_all()
    #data = skt.recv()
    #if data is None:
        #print("[SERVIDOR] Conexión finalizada.")
        #break
    # print(f"Recibido {i}: {data.decode('utf-8')}")
    #i+=1


