import socket
from packet.package import Package
import random

class SocketRDTServer:
    

    def __init__(self, host, port):
        self.port = port
        self.host = host
        self.other_address = ("", "")
        self.my_sequence_number = 0
        self.other_sequence_number = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def bind(self):
        self.socket.bind((self.host, self.port))

        while True:
            data, address = self.socket.recvfrom(12)
            package = Package()
            package.decode_to_package(data)
            print(f"SERVER: package con syn 1?: {package}")
            if package.want_SYN():
                answer = Package()
                answer.set_SYN()
                self.other_sequence_number = package.get_sequence_number() + 1
                answer.set_ACK(self.other_sequence_number)
                self.my_sequence_number = random.randint(0, 2**16 - 1)
                answer.set_sequence_number(self.my_sequence_number)
                len, data = answer.packaging()
                print(f"SERVER: package respuesta con syc, ack y sq number: {answer}")
                self.socket.sendto(data, address)
                # recibe el ack?
                data, address = self.socket.recvfrom(12)
                package.decode_to_package(data)
                print(f"SERVER: ack final recibido: {package}") 
                if package.get_ACK() == self.my_sequence_number + 1:
                    self.my_sequence_number += 1
                    self.other_address = address
                    return True


