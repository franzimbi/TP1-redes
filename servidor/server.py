# import socket
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from packet.socket_rdt_sw import SocketRDT_SW
from packet.socket_rdt_sr import SocketRDT_SR



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

skt = SocketRDT_SR("localhost", 8081)
#skt = SocketRDT_SW("localhost", 8081)
#skt = SocketRDT_SW("10.0.0.2", 8081)

skt.bind()
i = 0
while True:
    #data = skt.recv_all()
    data = skt.recv()
    # print(f"Recibido {i}: {data.decode('utf-8')}")
    i+=1

