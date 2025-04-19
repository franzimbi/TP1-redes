import socket
from packet.package import Package
import random

MAX_PACKAGE_SIZE = 1037
HEADER_SIZE = 13

class SocketRDTServer:
    

    def __init__(self, host, port):
        self.port = port
        self.host = host
        self.other_address = ("", "")
        self.server_sequence_number = 0
        self.client_ack_number = 0
        self._is_connected = False
        self.is_alive = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def recv(self):
        if not self._is_connected:
            raise Exception("[SERVER]Socket no conectado")
        print(f"[Server] Espero mensaje del cliente")
        recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)

        pack = Package()
        pack.decode_to_package(recived_bytes)

        if pack.want_ACK_FLAG():
            return

            #si llega FIN
        if pack.want_FIN():
            #contesto ACK
            answer = Package()
            answer.set_ACK_FLAG()
            len, data = answer.packaging()
            self.socket.sendto(data, address)
            #envio mi FIN 
            print(f"[Server] enviando mi FIN {answer}")
            answer = Package()
            answer.set_FIN()
            len, data = answer.packaging()
            self.socket.sendto(data, address)
            #espero a recibir ack
            print(f"[Server] espero el ACK del FIN")
            data, address = self.socket.recvfrom(HEADER_SIZE)
            package = Package()
            package.decode_to_package(data)
            print(f"[Server] recibi el ack de fin {package}")
            if package.want_ACK_FLAG():
                self.socket.close()
                self._is_connected = False
                self.is_alive = False
                print("[INFO] Socket cerrado correctamente")
                return
        

        print(f"[Server] me llego: {pack}")
        print(f"[SERVER] PRE DECODE: ACK : {self.client_ack_number} y SecNum {pack.get_sequence_number()}")

        if pack.get_sequence_number() != self.client_ack_number:
            raise Exception("El ACK recibido no corresponde al ultimo envio realizado")

        self.client_ack_number += pack.get_data_length()
        # self.server_sequence_number += 1

        answer = Package()
        answer.set_ACK(self.client_ack_number)
        answer.set_sequence_number(self.server_sequence_number)
        answer.set_ACK_FLAG()
        len, data = answer.packaging()
        self.socket.sendto(data, address)
        print(f"[Server] Envio ACK: {answer}")
        
        # print(f"[Server] POST DECODE: ACK : {self.client_ack_number} y SecNum {self.server_sequence_number}")

        return pack.get_data()

    def bind(self):
        self.socket.bind((self.host, self.port))

        while True:
            data, address = self.socket.recvfrom(HEADER_SIZE)
            package = Package()
            package.decode_to_package(data)
            print(f"SERVER: package con syn 1?: {package}")
            if package.want_SYN():
                answer = Package()
                answer.set_SYN()
                self.client_ack_number = package.get_sequence_number() + 1
                answer.set_ACK(self.client_ack_number)
                self.server_sequence_number = random.randint(0, 2**16 - 1)
                answer.set_sequence_number(self.server_sequence_number)
                len, data = answer.packaging()
                print(f"SERVER: package respuesta con syc, ack y sq number: {answer}")
                self.socket.sendto(data, address)
                # recibe el ack?
                data, address = self.socket.recvfrom(HEADER_SIZE)
                package.decode_to_package(data)
                print(f"SERVER: ack final recibido: {package}") 
                if package.get_ACK() == self.server_sequence_number + 1:
                    self.server_sequence_number += 1
                    self.other_address = address
                    self._is_connected = True
                    return True

    def _is_alive(self):
        return self.is_alive
        
        


        
                




