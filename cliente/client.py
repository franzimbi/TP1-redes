# import socket
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# from packet.package import Package
from packet.socket_rdt_sw import SocketRDT


# BUFFER_SIZE = 4096
# PORT_DESTINO = 8086

#client = SocketRDT("localhost", 8081)
client = SocketRDT("10.0.0.2", 8081)

client.connect()

client.send("Hola, soy el cliente")
client.send("Juli aprende python")
client.send("Caro vas a hacer el tpp con nosotros? o no?")
client.close()

#pack = Package()

#pack.set_data("Hola, soy el cliente")
#pack.sequence_number = 23
#size, content = pack.packaging()

#sock.sendto(content, ('localhost', PORT_DESTINO)) #esto hay q ver si cambia el localhost por otra cosa cuando usemos mininet
#data, address = sock.recvfrom(BUFFER_SIZE)
#print(f"Recibido {data.decode()} desde {address}")
    