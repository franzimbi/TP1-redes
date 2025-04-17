import socket
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from packet.package import Package


BUFFER_SIZE = 4096
PORT_DESTINO = 8086

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pack = Package()

pack.set_data("Hola, soy el cliente")
pack.sequence_number = 23
size, content = pack.packaging()

sock.sendto(content, ('localhost', PORT_DESTINO)) #esto hay q ver si cambia el localhost por otra cosa cuando usemos mininet
data, address = sock.recvfrom(BUFFER_SIZE)
print(f"Recibido {data.decode()} desde {address}")
    
