import math
import socket
import time
from common.package import Package
import random
import numpy as np

MAX_PACKAGE_SIZE = 1035
MAX_DATA_SIZE = 1024
HEADER_SIZE = 13
TOTAL_RETRIES = 5
MAX_SEQ_NUM = 2**16 - 1


class SocketRDT_SW:
    
    def __init__(self, host, port):
        self.sequence_number = random.randint(0, MAX_SEQ_NUM - 1)
        self.ack_number = 0
        self.adress = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clients = {} #diccionario tupla (ip,port),state
        self._is_connected = False
        

        #Lado Servidor
        def accept(self):
            self.socket.bind(self.adress)
            print("[SERVER] Esperando SYN...")
            data, client_address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
            packet = Package()
            packet.decode_to_package(data)

            if packet.want_SYN():
                self.ack_number = (int(packet.get_sequence_number()) + 1) % MAX_SEQ_NUM
                print("[SERVER] Recibido SYN, enviando SYN-ACK")
                server_syn_pack = Package()
                server_syn_pack.set_SYN()
                self.socket.sendto(server_syn_pack.packaging(), client_address)

                ack_data, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                client_ack_pack = Package()
                client_ack_pack.decode_to_package(ack_data)
                if client_ack_pack.want_ACK_FLAG():
                    self.clients[client_address] = True
                    print("[SERVER] Conexión establecida")
        
        #Lado Cliente
        def connect(self, host, port):
            print("[CLIENT] Enviando SYN")
            client_syn_pack = Package()
            client_syn_pack.set_SYN()
            self.socket.sendto(client_syn_pack.packaging(), (host, port))

            data, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
            server_syn_ack = Package()
            server_syn_ack.decode_to_package(data)

            if server_syn_ack.want_SYN():
                self.ack_number = (int(server_syn_ack.get_sequence_number()) + 1) % MAX_SEQ_NUM
                print("[CLIENT] Recibido SYN-ACK, enviando ACK")
                client_ack_pack = Package()
                client_ack_pack.set_ACK_FLAG()
                self.socket.sendto(client_ack_pack.packaging(), self.adress)
                self._is_connected = True
                print("[CLIENT] Conexión establecida")


        def recv(self, bytes):

        #def send_all(self, bytes):
        
        #def close(self):

        

    # def bind(self):
    #     self.socket.bind(self.adress)
    #     while True:
    #         # recibir el primer syn
    #         data_syn, add_syn = self.socket.recvfrom(HEADER_SIZE)
    #         pack_syn = Package()
    #         pack_syn.decode_to_package(data_syn)
    #         if pack_syn.want_SYN(): #si es syn le mando mi SN y el ack

    #             answer_syn = Package()
    #             answer_syn.set_SYN()
    #             self.ack_number = (pack_syn.get_sequence_number() + 1) % MAX_SEQ_NUM
    #             answer_syn.set_ACK(self.ack_number)
    #             answer_syn.set_sequence_number(self.sequence_number)
    #             pack_ack_syn = self.__send_and_wait_syn(answer_syn, TOTAL_RETRIES, add_syn)
    #             if pack_ack_syn is not None and pack_ack_syn.get_ACK() == (self.sequence_number + 1) % MAX_SEQ_NUM:
    #                 self.sequence_number = (self.sequence_number+ 1) % MAX_SEQ_NUM
    #                 self.adress = add_syn
    #                 self._is_connected = True
    #                 return True

    # def connect(self):
    #     syn = Package()
    #     syn.set_SYN()
    #     syn.set_sequence_number(self.sequence_number)
    #     answer_connect = self.__send_and_wait_syn(syn, TOTAL_RETRIES, self.adress)
    #     if answer_connect is not None and answer_connect.want_SYN():
    #         self.ack_number = (answer_connect.get_sequence_number() + 1) % MAX_SEQ_NUM
    #         final_ack = Package()
    #         final_ack.set_ACK(self.ack_number)
    #         self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
    #         final_ack.set_sequence_number(self.sequence_number)
    #         self.socket.sendto(final_ack.packaging(), self.adress)
    #         self._is_connected = True


    # def _send(self, data):
    #     if not self._is_connected:
    #         raise Exception("Socket no conectado")
        
    #     total_size = len(data)
    #     offset = 0
    #     while offset < total_size:
    #         data_chunk = data[offset:offset + MAX_DATA_SIZE]
    #         pack = Package()
    #         pack.set_data(data_chunk)
    #         pack.set_sequence_number(self.sequence_number)

    #         try:
    #             self.__send_and_wait(pack, TOTAL_RETRIES, self.adress)
    #         except Exception as e:
    #             raise e
    #         self.sequence_number = (self.sequence_number + len(data_chunk)) % MAX_SEQ_NUM
    #         offset += len(data_chunk)

    # def send_all(self, data):
    #     if not self._is_connected:
    #         raise Exception("Socket no conectado")
        
    #     size = math.ceil(len(data) / MAX_DATA_SIZE)
    #     self._send(str(size).encode('utf-8'))
    #     self._send(data)

    # def __is_seq_less(self, a, b):
    #    return ((b - a + MAX_SEQ_NUM) % MAX_SEQ_NUM) < (MAX_SEQ_NUM // 2)

    
    # def _recv(self):
    #     if not self._is_connected:
    #         raise Exception("[SERVER]Socket no conectado")
        
    #     recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
    #     pack = Package()
    #     pack.decode_to_package(recived_bytes)

    #     if pack.want_FIN():
    #         self._is_connected = False
    #         return self.__end_connection()

    #     if pack.get_sequence_number() == self.ack_number:
    #         self.ack_number = (self.ack_number + pack.get_data_length()) % MAX_SEQ_NUM
    #         answer = Package()
    #         answer.set_ACK(self.ack_number)
    #         answer.set_sequence_number(self.sequence_number)
    #         data = answer.packaging()
    #         self.socket.sendto(data, address)

    #     elif self.__is_seq_less(pack.get_sequence_number(), self.ack_number):
    #         print("[Servidor] Duplicado detectado, reenviando ACK.")
    #         return None

    #     return pack.get_data()

    # def recv(self):
    #     if not self._is_connected:
    #         raise Exception("[SERVER]Socket no conectado")
        
    #     size = None
    #     while size is None:
    #         size = self._recv()
    #     size = int(size.decode('utf-8'))
    #     buffer = b''
    #     received_packages = 0
    #     while received_packages < size:
    #         data = self._recv()
    #         if data is not None:
    #             buffer += data
    #             received_packages += 1
    #     return buffer


    # def close(self):
    #     fin = Package()
    #     fin.set_FIN()
    #     fin.set_sequence_number(self.sequence_number)

    #     ack_answer = self.__send_and_wait_syn(fin, TOTAL_RETRIES, self.adress)
    #     if ack_answer is not None:
    #         data, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
    #         final_pack = Package()
    #         final_pack.decode_to_package(data)
    #         if final_pack.want_FIN():
    #             answer = Package()
    #             self.ack_number = (self.ack_number + 1) % MAX_SEQ_NUM
    #             answer.set_ACK((self.ack_number + 1) % MAX_SEQ_NUM)
    #             answer.set_sequence_number(self.sequence_number)
    #             self.socket.sendto(answer.packaging(), self.adress)
    #             self._is_connected = False
    #             self.socket.close()
    #             print("[INFO] Socket cerrado correctamente")
    #             return True


    # def __end_connection(self):
    #     ack_fin = Package()
    #     self.ack_number = (self.ack_number + 1) % MAX_SEQ_NUM
    #     ack_fin.set_ACK(self.ack_number)
    #     ack_fin.set_sequence_number(self.sequence_number)
    #     self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
    #     data = ack_fin.packaging()
    #     self.socket.sendto(data, self.adress)
    #     # mando el fin ahora
    #     fin = Package()
    #     fin.set_FIN()
    #     fin.set_sequence_number(self.sequence_number)
    #     self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
    #     data = fin.packaging()
    #     self.socket.sendto(data, self.adress)
    #     # espero el ack
    #     self.socket.settimeout(2.0)
    #     try:
    #         data, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
    #         final_ack = Package()
    #         final_ack.decode_to_package(data)
    #         if final_ack.get_ACK() == self.sequence_number:
    #             self.socket.settimeout(None)
    #             self.socket.close()
    #             return
    #     except socket.timeout:
    #         self.socket.settimeout(None)
    #         self.socket.close()
    #         raise Exception("[ERROR] Timeout al esperar el ACK del FIN")


    # def __send_and_wait(self, package, total_retries, address):
    #     data = package.packaging()
    #     self.socket.settimeout(1.0)
    #     retries = 0
    #     while retries < total_retries:
    #         self.socket.sendto(data, address)
    #         try:
    #             data_rcv, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
    #             answer = Package()
    #             answer.decode_to_package(data_rcv)
    #             if answer.get_ACK() == (self.sequence_number + package.get_data_length()) % MAX_SEQ_NUM:
    #                 self.socket.settimeout(None)
    #                 return answer
    #         except socket.timeout:
    #             print(f"[Cliente] Timeout esperando ACK , reintentando... {retries}")
    #             retries += 1

    #     self.socket.settimeout(None)
    #     return None


    # def __send_and_wait_syn(self, package, total_retries, address):
    #     data = package.packaging()
    #     self.socket.settimeout(1.0)
    #     retries = 0
    #     while retries < total_retries:
    #         self.socket.sendto(data, address)
    #         try:
    #             data_rcv, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
    #             answer = Package()
    #             answer.decode_to_package(data_rcv)
    #             if answer.get_ACK() == (self.sequence_number + 1) % MAX_SEQ_NUM:
    #                 self.socket.settimeout(None)
    #                 return answer
    #         except socket.timeout:
    #             retries += 1
    #             print(f"[Cliente] Timeout esperando ACK , reintentando... {retries}")

    #     self.socket.settimeout(None)
    #     return None



    # def is_closed(self):
    #     if not self._is_connected:
    #         return True    
    #     return False