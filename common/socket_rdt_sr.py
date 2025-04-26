from collections import deque
import socket
import time
from common.package import Package
import random
import numpy as np
import threading
import time
import threading #si, lo vamos a usar

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
        self.next_seq_number = self.sequence_number      # Próximo número de secuencia a usar para enviar (emisor)
        self.thrds = {} # diccionario de thrds
        self.packages_acked = {} # diccionario de acked
        self.stop_events = {} # diccionario de stop events
        self.shared_lenghts = {} # diccionario de variables compartidas
        #receptor
        self.recv_base = 0      # Primer número de secuencia esperada (receptor)
        self.recv_buffer = {}    # clave: número de secuencia, valor: datos

    def bind(self):
        self.socket.bind(self.adress)
        print(f"[SERVIDOR] Escuchando en {self.adress}")
    
    def accept(self):
        self.bind()
        while True:
            #esperar el primer paquete(SYN)
            data_syn, addr_syn = self.socket.recvfrom(HEADER_SIZE)
            pack_syn = Package()
            pack_syn.decode_to_package(data_syn)

            if pack_syn.want_SYN(): #si es syn le mando mi SN y el ack
                #responder con SYN+ACK
                answer_syn = Package()
                answer_syn.set_SYN()
                self.ack_number = (pack_syn.get_sequence_number() + 1) % MAX_SEQ_NUM
                answer_syn.set_ACK(self.ack_number)
                answer_syn.set_sequence_number(self.sequence_number)

                #enviar SYN+ACK y esperar ACK final
                pack_ack_syn = self.__send_and_wait_syn(answer_syn, TOTAL_RETRIES, addr_syn)

                if pack_ack_syn is not None and pack_ack_syn.get_ACK() == (self.sequence_number + 1) % MAX_SEQ_NUM:
                    #handshake exitoso: crear socket nuevo para este cliente
                    new_socket = SocketRDT_SR.__new__(SocketRDT_SR)
                    new_socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    new_socket.socket.bind(("", 0))  #q el sistema operativo elija un puerto libre
                    new_socket.socket.connect(addr_syn)  # conectar el socket nuevo al cliente
                    
                    new_socket.address = addr_syn
                    new_socket._is_connected = True

                   
                    new_socket.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
                    new_socket.ack_number = (pack_ack_syn.get_sequence_number() + 1) % MAX_SEQ_NUM

                    
                    new_socket.send_base = new_socket.sequence_number 
                    new_socket.next_seq_number = new_socket.sequence_number

                    new_socket.thrds = {} 
                    new_socket.packages_acked = {} 
                    new_socket.stop_events = {} 
                    new_socket.shared_lenghts = {}

                    new_socket.recv_base = pack_ack_syn.get_sequence_number()
                    new_socket.recv_buffer = {}

                    print(f"[SERVIDOR] Nueva conexión aceptada de {addr_syn}")
                    return new_socket
                    


    def _handle_new_connection(self, pack_syn, addr_syn):
        # Crear nuevo socket solo para esta conexión
        socket_nuevo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_nuevo.bind(("", 0))  # Que el sistema operativo elija un puerto libre
        nuevo_host, nuevo_port = socket_nuevo.getsockname()  # obtener (host, puerto) asignados

        # Crear nueva conexión confiable usando el host y puerto
        connection = SocketRDT_SR(nuevo_host, nuevo_port)

        # Reemplazar el socket por el que ya habías creado
        connection.socket = socket_nuevo  # sobrescribo el socket interno con el que ya creaste y bindiaste

        # (Opcional) Guardarlo en alguna lista si querés trackear las conexiones abiertas
        self.conexiones.append(connection)

        # Ahora manejás toda la comunicación con ese cliente
        connection.handle_client(pack_syn)


    def connect(self):
        syn = Package()
        syn.set_SYN()
        syn.set_sequence_number(self.sequence_number)
        answer_connect = self.__send_and_wait_syn(syn, TOTAL_RETRIES, self.adress)
        if answer_connect is not None and answer_connect.want_SYN():
            self.ack_number = (answer_connect.get_sequence_number() + 1) % MAX_SEQ_NUM
            final_ack = Package()
            final_ack.set_ACK(self.ack_number)
            self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
            final_ack.set_sequence_number(self.sequence_number)
            self.socket.sendto(final_ack.packaging(), self.adress)
            self._is_connected = True
            #inicializo la ventana
            self.send_base = self.sequence_number
            self.next_seq_number = self.send_base
            print(f"[CLIENTE] FIRST send_base {self.send_base}")


    def send(self, data):
        if not self._is_connected:
            raise Exception("Socket no conectado")

        total_size = len(data)
        offset = 0
        chunk_size = 1024 
        window_chunk_size = chunk_size * WINDOW_SIZE
        
        while offset < total_size:
            if self.send_base <= self.next_seq_number + chunk_size < self.send_base + window_chunk_size:
                data_chunk = data[offset:offset + chunk_size]

                self._send_data(data_chunk)
                
                offset += len(data_chunk)

                # revisar ACKs
            try:
                self._check_ACKs()

            except TimeoutError:
                pass

    def _send_data(self, data):
        pack = Package()
        pack.set_data(data)
        pack.set_sequence_number(self.next_seq_number)

        self.socket.sendto(pack.packaging(), self.adress)
        print(f"[CLIENTE] Enviado paquete con contenido {pack.get_data()}")
        print(f"[CLIENTE] Enviado paquete con seq {self.next_seq_number}")

        self.next_seq_number += len(data)

        print(f"[CLIENTE] Next sequence number {self.next_seq_number}")

        self._create_thrd(pack) # crear el hilo para controlar el timeout

    def _create_thrd(self, pack):
        self.shared_lenghts[self.next_seq_number] = [0]
        self.stop_events[self.next_seq_number] = threading.Event()

        thrd = threading.Thread(target=self._controlar_timeout,args=(pack, self.shared_lenghts[self.next_seq_number], self.stop_events[self.next_seq_number]))
        thrd.daemon = True  # << esto hace que se termine si el main se va
        thrd.start()

        #guardar hilo en diccionario de hilos
        self.thrds[self.next_seq_number] = thrd

    def _check_ACKs(self):
        recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
        pack = Package()
        pack.decode_to_package(recived_bytes)
        pack_ack = pack.get_ack_number()
        print(f"[CLIENTE] Llego ACK con sequence number {pack_ack}")
        if pack_ack in self.thrds:
            print(f"[CIENTE] Paquete con ack number {pack_ack} dentro de la ventana de recepcion")
            # parar el hilo específico
            self.stop_events[pack_ack].set()

            self.thrds[pack_ack].join() 

            len_pack_thrd = self.shared_lenghts[pack_ack][0] # obtener el len del hilo

            self._delete_thrd(pack_ack)

            self.packages_acked[pack_ack - len_pack_thrd] = len_pack_thrd # guardar el len en el diccionario de acked
            print(f"[CLIENTE] send base es: {self.send_base  }")
            while self.send_base in self.packages_acked:
                lenght = self.packages_acked[self.send_base]
                print(f"[RECEPTOR] Paquete con seq {self.send_base} procesado")

                # eliminar del acked
                del self.packages_acked[self.send_base]
            
                #avanzar la ventana 
                self.send_base += lenght


    def _delete_thrd(self, pack_ack):
        del self.thrds[pack_ack] 
        del self.stop_events[pack_ack]
        del self.shared_lenghts[pack_ack]

    def _controlar_timeout(self, pack, variable_compartida, stop_event):
        while not stop_event.is_set():

            if stop_event.wait(TIMEOUT): 
                break
            
            self._retransmit(pack)

        variable_compartida[0] = pack.get_data_length()
        print(f"[CLIENTE] thrd con seq {pack.get_sequence_number()} terminado")

    def _retransmit(self, paquete):
        # Reenviar el paquete
        self.socket.sendto(paquete.packaging(), self.adress)
        print(f"[CLIENTE] Reenviado paquete con seq {paquete.get_sequence_number()}")
    
    def recv(self): #hacer q no sea bloqueante, q un thread lo llame a recv y guarde en un buffer los paquetes continuamente
        if not self._is_connected:
            return None
    
        #buffer = []

        # recibir paquete
        recived_bytes, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
        pack = Package()
        pack.decode_to_package(recived_bytes)
        seq_num = pack.get_sequence_number()  
        print(f"[RECEPTOR] Recibi paquete con sequence number {seq_num}")
        data = pack.get_data()  

        # verificar si el paquete es FIN
        if pack.want_FIN():
            self._is_connected = False
            self.__end_connection()
            return None

        # si el paquete esta dentro de la ventana de recepcion
        if self.recv_base <= seq_num < self.recv_base + WINDOW_SIZE:
            # almacenar el paquete en el buffer si esta dentro de la ventana
            self.recv_buffer[seq_num] = data
        
            # enviar ACK para el siguiente paquete esperado
            ack_seq = self.recv_base + len(data)  # el siguiente paquete esperado
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
                # print(f"[RECEPTOR] DATA: {data} ")

                # eliminar del buffer
                del self.recv_buffer[self.recv_base]
            
                #avanzar la ventana 
                self.recv_base += + len(data)
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
        self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
        data = ack_fin.packaging()
        self.socket.sendto(data, self.adress)
        # mando el fin ahora
        fin = Package()
        fin.set_FIN()
        fin.set_sequence_number(self.sequence_number)
        self.sequence_number  = (self.sequence_number + 1) % MAX_SEQ_NUM
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
                if answer.get_ACK() == (self.sequence_number + 1) % MAX_SEQ_NUM:
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


    def is_closed(self):
        if not self._is_connected:
            return True    
        return False