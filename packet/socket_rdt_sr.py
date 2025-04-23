import socket
import time
from packet.package import Package
import random
import numpy as np
import threading
import time

TIMEOUT = 1.0  # segundos

MAX_PACKAGE_SIZE = 1037
HEADER_SIZE = 13
TOTAL_RETRIES = 5
WINDOW_SIZE = 4
MAX_SEQ_NUM = 2**16 - 1


class SocketRDT_SR:
    def __init__(self, host, port):
        self.sequence_number = random.randint(0, 2**16 - 1)
        self.ack_number = 0
        self._is_connected = False
        self.adress = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #emisor
        self.send_base = self.sequence_number     # Primer número de secuencia aún no ACKeado (emisor)
        self.next_seq = self.sequence_number      # Próximo número de secuencia a usar para enviar (emisor)
        self.sent_buffer = {}   # seq_num -> (Package, timestamp)
        self.acked = set()      # Conjunto de seq_num que fueron ACKeados

        #receptor
        self.recv_base = 0      # Primer número de secuencia esperada (receptor)
        self.recv_buffer = {}    # clave: número de secuencia, valor: datos

        self.timers = {}  # seq_num: start_time
        self.timer_manager_running = False


    self.skt

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
                    self.recv_base = self.ack_number
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
            #inicializo la ventana
            self.send_base = self.sequence_number + 1
            self.next_seq = self.send_base


    def send(self, data):
        if not self._is_connected:
            raise Exception("Socket no conectado")

        total_size = len(data)
        offset = 0
        chunk_size = 1024
        
        while offset < total_size:
            if self.next_seq < self.send_base + chunk_size * WINDOW_SIZE:
                data_chunk = data[offset:offset + chunk_size]
                pack = Package()
                pack.set_data(data_chunk)
                pack.set_sequence_number(self.next_seq)

                # guardar en el buffer de enviados
                self.sent_buffer[self.next_seq] = (pack, time.time())

                # enviar paquete
                self.socket.sendto(pack.packaging(), self.adress)
                print(f"[CLIENTE] Enviado paquete con seq {self.next_seq}")


                self.next_seq += len(data_chunk)
                offset += len(data_chunk)

                # revisar ACKs
            try:
                recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                pack = Package()
                pack.decode_to_package(recived_bytes)
                ack_seq = pack.get_ack_number()
                print(f"[CLIENTE] Enviado paquete con seq {self.next_seq}")
                if ack_seq in self.sent_buffer:
                    self.acked.add(ack_seq)
                    del self.sent_buffer[ack_seq]
                    # avanzar send_base al menor seq no ACKeado
                    while self.send_base in self.acked:
                        self.send_base += 1
                        #me falta eliminar send_base de acked para que no sea infinito
            except TimeoutError:
                pass


            current_time = time.time()
            for seq, send_time in list(self.sent_buffer.items()):
                if current_time - send_time > TIMEOUT:
                    msg = self.sent_buffer[seq]
                    self.socket.sendto(msg[0].packaging(), (self.adress, self.dest_port))
                    self.sent_buffer[seq] = current_time



    
    def recv(self): #hacer q no sea bloqueante, q un thread lo llame a recv y guarde en un buffer los paquetes continuamente
        if not self._is_connected:
            raise Exception("[SERVER]Socket no conectado")
    
        #buffer = []

        # recibir paquete
        recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
        pack = Package()
        pack.decode_to_package(recived_bytes)
        seq_num = pack.get_sequence_number()  
        data = pack.get_data()  

        # verificar si el paquete es FIN
        if pack.want_FIN():
            self._is_connected = False
            return self.__end_connection()

        # si el paquete esta dentro de la ventana de recepcion
        if self.recv_base <= seq_num < self.recv_base + WINDOW_SIZE:
            # almacenar el paquete en el buffer si esta dentro de la ventana
            self.recv_buffer[seq_num] = data
        
            # enviar ACK para el siguiente paquete esperado
            ack_seq = self.recv_base + 1  # el siguiente paquete esperado
            answer = Package()
            answer.set_ACK(ack_seq)
            answer.set_sequence_number(self.sequence_number)
            self.socket.sendto(answer.packaging(), address)
            print(f"[RECEPTOR] Enviado ACK para el paquete con seq {ack_seq}")

            # procesar paquetes en orden (si estan disponibles)
            while self.recv_base in self.recv_buffer:
                # aca se puede procesar el paquete
                data = self.recv_buffer[self.recv_base]
                print(f"[RECEPTOR] Paquete con seq {self.recv_base} procesado")
                print(f"[RECEPTOR] DATA: {data} ")

                # eliminar del buffer
                del self.recv_buffer[self.recv_base]
            
                #avanzar la ventana 
                self.recv_base += 1
        # si me llego un seq_num menor, reenvio el ACK pq quizas el otro no recibio mi ACK anterior
        elif seq_num < self.recv_base:
            # Reenviar ACK
            ack_seq = self.recv_base  # el próximo paquete que esperás
            answer = Package()
            answer.set_ACK(ack_seq)
            answer.set_sequence_number(self.sequence_number)
            self.socket.sendto(answer.packaging(), address)
            print(f"[RECEPTOR] Reenviando ACK para seq {ack_seq} (paquete duplicado con seq {seq_num})")
        # ignorar el paquete si esta afuera de la ventana
        else:
            print(f"[RECEPTOR] Paquete con seq {seq_num} fuera de la ventana de recepción")

        return data

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
                print(f"[Cliente] Timeout esperando ACK , reintentando... {retries}")

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