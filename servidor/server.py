# import socket
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from packet.socket_rdt_server import SocketRDTServer


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

skt = SocketRDTServer("localhost", 8081)
skt.bind()
