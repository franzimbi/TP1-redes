import socket
from packet.package import Package
import random

MAX_PACKAGE_SIZE = 1036

class SocketRDTServer:
    

    def __init__(self, host, port):
        self.port = port
        self.host = host
        self.other_address = ("", "")
        self.my_sequence_number = 0
        self.other_sequence_number = 0
        self._is_connected = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def recv(self):
        if not self._is_connected:
            raise Exception("[SERVER]Socket no conectado")
               
        recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)

        pack = Package()
        pack.decode_to_package(recived_bytes)

        print(f"[Server] me llego: {pack}")
        print(f"[SERVER] PRE DECODE: ACK : {self.other_sequence_number} y SecNum {self.my_sequence_number}")

        if self.other_sequence_number <= pack.get_sequence_number():
            raise Exception("El ACK recibido no corresponde al ultimo envio realizado")

        self.other_sequence_number += pack.get_data_length()
        # self.my_sequence_number += 1

        answer = Package()
        answer.set_ACK(self.other_sequence_number)
        answer.set_sequence_number(self.my_sequence_number)
        len, data = answer.packaging()
        self.socket.sendto(data, address)
        print(f"[Server] Envio ACK: {answer}")
        
        # print(f"[Server] POST DECODE: ACK : {self.other_sequence_number} y SecNum {self.my_sequence_number}")
        return pack.get_data()

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
                    self._is_connected = True
                    return True
        
        
            #si llega FIN
            #if package.want_FIN():
                #contesto ACK
                #answer = Package()
                #answer.set_ACK()
                #len, data = answer.packaging()
                #self.socket.sendto(data, address)
                #envio mi FIN 
                #answer = Package()
                #answer.set_FIN()
                #self.socket.sendto(data, address)
                #espero a recibir ack
                #data, address = self.socket.recvfrom(12)
                #package = Package()
                #package.decode_to_package(data)
                #if package.get_ACK():
                    #print(f"SERVER: ACK final recibido, conexión cerrada")
                    #break

        
                




