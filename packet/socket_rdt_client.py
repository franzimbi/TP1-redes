import socket
from packet.package import Package
import random
import numpy as np

MAX_PACKAGE_SIZE = 1037
HEADER_SIZE = 13



class SocketRDTClient:

    def __init__(self, host, port):
        self.port = port
        self.host = host
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_sequence_number = random.randint(0, 2**16 - 1)
        self.server_sequence_number = 0
        self._is_connected = False
        
    def connect(self):
        print(f"[Cliente] Conectando a {self.host}:{self.port}...")
        init_connection_pack = Package()
        init_connection_pack.set_SYN()
        init_connection_pack.set_sequence_number(self.client_sequence_number)
        lenght, data = init_connection_pack.packaging()
        self.socket.sendto(data, (self.host, self.port))
        print(f"[Cliente] Enviado PAQUETE CON SYN Y SEQ NUMBER={init_connection_pack}")
        data, adress = self.socket.recvfrom(HEADER_SIZE)
        package_recv = Package()
        package_recv.decode_to_package(data)
        print(f"[Cliente] Recibido SYN-ACK con {package_recv}")
        if package_recv.want_SYN():
            self.server_sequence_number = package_recv.get_sequence_number()
            answer = Package()
            ack_number = self.server_sequence_number + 1
            answer.set_ACK(ack_number)
            self.client_sequence_number += 1
            answer.set_sequence_number(self.client_sequence_number)
            len, data = answer.packaging()
            self.socket.sendto(data, (self.host, self.port))
            print(f"[Cliente] Enviado ACK final con ACK={answer}")

            print("[Cliente] Conexión establecida")
            self._is_connected = True


    def recv(self):
        if not self._is_connected:
            raise Exception("Socket no conectado")
               
        
        recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)

        pack = Package()
        pack.decode_to_package(recived_bytes)

        if pack.want_ACK_FLAG():
            return

        print(f"[Client] PRE DECODE: ACK : {self.server_sequence_number} y SecNum {self.client_sequence_number}")

        if self.client_sequence_number != pack.get_ACK():
            raise Exception("El ACK recibido no corresponde al ultimo envio realizado")

        self.server_sequence_number = pack.get_sequence_number() + pack.get_data_length()
        self.client_sequence_number += 1

        print(f"[Client] POST DECODE: ACK : {self.server_sequence_number} y SecNum {self.client_sequence_number}")
        
        answer = Package()
        answer.set_ACK(self.server_sequence_number)
        answer.set_sequence_number(self.client_sequence_number)
        answer.set_ACK_FLAG()
        len, data = answer.packaging()
        self.socket.sendto(data, address)
        print(f"[Server] Envio ACK: {answer}")
        
        return pack.get_data()

    def send(self, data):
        if not self._is_connected:
            raise Exception("Socket no conectado")
        
        total_size = len(data)
        offset = 0
        self.socket.settimeout(1.0)

        while offset < total_size:
            data_chunk = data[offset:offset + 1024]
            pack = Package()
            pack.set_data(data_chunk)
            pack.set_sequence_number(self.client_sequence_number)
            pack.set_ACK(self.server_sequence_number)
            tam, data_bytes = pack.packaging()
            print(f"[Cliente] Enviando paquete {pack}")
            
            retries = 0
            ack_received = False
            while not ack_received and retries < 5:
                self.socket.sendto(data_bytes, (self.host, self.port))
                try:
                    data_r, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                    ack_pack = Package()
                    ack_pack.decode_to_package(data_r)
                    print(f"[Cliente] Recibido ACK con {ack_pack}")
                    if ack_pack.get_ACK() == self.client_sequence_number + len(data_chunk):
                        print(f"[Cliente] ACK recibido: {ack_pack.get_ACK()}")
                        ack_received = True
                    else:
                        print(f"[Cliente] ACK no esperado: {ack_pack.get_ACK()}")
                        retries += 1
                except socket.timeout:
                    print(f"[Cliente] Timeout esperando ACK, reintentando... {retries}")
                    retries += 1

            if not ack_received:

                raise Exception("Se alcanzó el número máximo de reintentos para enviar el paquete")
            
            self.client_sequence_number += len(data_chunk)
            offset += len(data_chunk)
            
            
    def end_connection(self):
        #primero le envio FIN
        end_connection_pack = Package()
        end_connection_pack.set_FIN()
        len, data = end_connection_pack.packaging()
        self.socket.sendto(data, (self.host, self.port))
        print(f"[Cliente] Envio FIN {end_connection_pack}")
        #espero a recibir el ACK
        data, address = self.socket.recvfrom(HEADER_SIZE)
        package_recv = Package()
        package_recv.decode_to_package(data)
        print(f"[Cliente] Recibo ACK del server {package_recv}")
        #espero a recibir el FIN
        data, address = self.socket.recvfrom(HEADER_SIZE)
        package_recv = Package()
        package_recv.decode_to_package(data)
        print(f"[Cliente] Recibo FIN del server {package_recv}")
        #si recibi FIN le respondo ACK
        if package_recv.want_FIN():
            answer = Package()
            answer.set_ACK_FLAG()
            len, data = answer.packaging()
            self.socket.sendto(data, (self.host, self.port))
            print(f"[Cliente] Envio ACK {answer}")
        

            