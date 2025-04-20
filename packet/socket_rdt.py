import socket
import time
from packet.package import Package
import random
import numpy as np

MAX_PACKAGE_SIZE = 1037
HEADER_SIZE = 13
TOTAL_RETRIES = 5


class SocketRDT:
    def __init__(self, host, port):
        self.sequence_number = random.randint(0, 2**16 - 1)
        self.ack_number = 0
        self._is_connected = False
        self.adress = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def bind(self):
        self.socket.bind(self.adress)
        while True:
            # recibir el primer syn
            data_syn, add_syn = self.socket.recvfrom(HEADER_SIZE)
            pack_syn = Package()
            pack_syn.decode_to_package(data_syn)
            if pack_syn.want_SYN(): #si es syn le mando mi SN y el ack

                answer_syn = Package()
                answer_syn.set_SYN()
                self.ack_number = pack_syn.get_sequence_number() + 1
                answer_syn.set_ACK(self.ack_number)
                answer_syn.set_sequence_number(self.sequence_number)
                pack_ack_syn = self.__send_and_wait_syn(answer_syn, TOTAL_RETRIES, add_syn)
                if pack_ack_syn is not None and pack_ack_syn.get_ACK() == self.sequence_number + 1:
                    self.sequence_number += 1
                    self.adress = add_syn
                    self._is_connected = True
                    return True

    def connect(self):
        syn = Package()
        syn.set_SYN()
        syn.set_sequence_number(self.sequence_number)
        answer_connect = self.__send_and_wait_syn(syn, TOTAL_RETRIES, self.adress)
        if answer_connect is not None and answer_connect.want_SYN():
            self.ack_number = answer_connect.get_sequence_number() + 1
            final_ack = Package()
            final_ack.set_ACK(self.ack_number)
            self.sequence_number += 1
            final_ack.set_sequence_number(self.sequence_number)
            self.socket.sendto(final_ack.packaging(), self.adress)
            self._is_connected = True


    def send(self, data):
        if not self._is_connected:
            raise Exception("Socket no conectado")
        
        total_size = len(data)
        offset = 0
        while offset < total_size:
            data_chunk = data[offset:offset + 1024]
            pack = Package()
            pack.set_data(data_chunk)
            pack.set_sequence_number(self.sequence_number)

            try:
                self.__send_and_wait(pack, TOTAL_RETRIES, self.adress)
            except Exception as e:
                raise e
            self.sequence_number += len(data_chunk)
            offset += len(data_chunk)
    
    def recv(self):
        if not self._is_connected:
            raise Exception("[SERVER]Socket no conectado")
        
        recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
        pack = Package()
        pack.decode_to_package(recived_bytes)

        if pack.want_FIN():
            self._is_connected = False
            return self.__end_connection()

        if pack.get_sequence_number() == self.ack_number:
            self.ack_number += pack.get_data_length()
            answer = Package()
            answer.set_ACK(self.ack_number)
            answer.set_sequence_number(self.sequence_number)
            data = answer.packaging()
            self.socket.sendto(data, address)

        return pack.get_data()

    def close(self):
        fin = Package()
        fin.set_FIN()
        fin.set_sequence_number(self.sequence_number)

        ack_answer = self.__send_and_wait_syn(fin, TOTAL_RETRIES, self.adress)
        if ack_answer is not None:
            data, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
            final_pack = Package()
            final_pack.decode_to_package(data)
            if final_pack.want_FIN():
                answer = Package()
                self.ack_number += 1 # no se pq el doble, falta algun +1 en otro lado
                answer.set_ACK(self.ack_number + 1)
                answer.set_sequence_number(self.sequence_number)
                self.socket.sendto(answer.packaging(), self.adress)
                self._is_connected = False
                self.socket.close()
                print("[INFO] Socket cerrado correctamente")
                return True


    def __end_connection(self):
        ack_fin = Package()
        self.ack_number += 1
        ack_fin.set_ACK(self.ack_number)
        ack_fin.set_sequence_number(self.sequence_number)
        self.sequence_number += 1
        data = ack_fin.packaging()
        self.socket.sendto(data, self.adress)
        # mando el fin ahora
        fin = Package()
        fin.set_FIN()
        fin.set_sequence_number(self.sequence_number)
        self.sequence_number += 1
        data = fin.packaging()
        self.socket.sendto(data, self.adress)
        # espero el ack
        self.socket.settimeout(2.0)
        try:
            data, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
            final_ack = Package()
            final_ack.decode_to_package(data)
            if final_ack.get_ACK() == self.sequence_number:
                self.socket.settimeout(None)
                self.socket.close()
                return
        except socket.timeout:
            self.socket.settimeout(None)
            self.socket.close()
            raise Exception("[ERROR] Timeout al esperar el ACK del FIN")


    def __send_and_wait(self, package, total_retries, address):
        data = package.packaging()
        self.socket.settimeout(1.0)
        retries = 0
        while retries < total_retries:
            self.socket.sendto(data, address)
            try:
                data_rcv, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                answer = Package()
                answer.decode_to_package(data_rcv)
                if answer.get_ACK() == self.sequence_number + package.get_data_length():
                    self.socket.settimeout(None)
                    return answer
            except socket.timeout:
                retries += 1

        self.socket.settimeout(None)
        return None


    def __send_and_wait_syn(self, package, total_retries, address):
        data = package.packaging()
        self.socket.settimeout(1.0)
        retries = 0
        while retries < total_retries:
            self.socket.sendto(data, address)
            try:
                data_rcv, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                answer = Package()
                answer.decode_to_package(data_rcv)
                if answer.get_ACK() == self.sequence_number + 1:
                    self.socket.settimeout(None)
                    return answer
            except socket.timeout:
                retries += 1
                print(f"[Cliente] Timeout esperando ACK, reintentando... {retries}")

        self.socket.settimeout(None)
        return None
    
    def __build_package(self, seq, ack=None, syn=False, fin=False, data=b''):
        p = Package()
        if syn: p.set_SYN()
        elif fin: p.set_FIN()
        if ack: p.set_ACK(ack)
        p.set_sequence_number(seq)
        p.set_data(data)
        return p