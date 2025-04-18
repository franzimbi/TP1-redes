import socket
from packet.package import Package
import random
import numpy as np


class SocketRDTClient:

    def __init__(self, host, port):
        self.port = port
        self.host = host
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.my_sequence_number = random.randint(0, 2**16 - 1)
        self.other_sequence_number = 0
        
    def connect(self):
        print(f"[Cliente] Conectando a {self.host}:{self.port}...")
        init_connection_pack = Package()
        init_connection_pack.set_SYN()
        init_connection_pack.set_sequence_number(self.my_sequence_number)
        lenght, data = init_connection_pack.packaging()
        self.socket.sendto(data, (self.host, self.port))
        print(f"[Cliente] Enviado PAQUETE CON SYN Y SEQ NUMBER={init_connection_pack}")
        data, adress = self.socket.recvfrom(1024)
        package_recv = Package()
        package_recv.decode_to_package(data)
        print(f"[Cliente] Recibido SYN-ACK con {package_recv}")
        if package_recv.want_SYN():
            self.other_sequence_number = package_recv.get_sequence_number()
            answer = Package()
            ack_number = self.other_sequence_number + 1
            answer.set_ACK(ack_number)
            self.my_sequence_number += 1
            answer.set_sequence_number(self.my_sequence_number)
            len, data = answer.packaging()
            self.socket.sendto(data, (self.host, self.port))
            print(f"[Cliente] Enviado ACK final con ACK={answer}")

            print("[Cliente] Conexión establecida")
            


