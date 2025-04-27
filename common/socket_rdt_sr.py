from collections import deque
import socket
import time
from common.package import Package
import random
import numpy as np
import threading
import time
import threading #si, lo vamos a usar
import queue
import select


TIMEOUT = 1.0  # segundos

MAX_PACKAGE_SIZE = 1037
HEADER_SIZE = 13
TOTAL_RETRIES = 5
WINDOW_SIZE = 4
MAX_SEQ_NUM = 2**16 - 1

class SocketRDT_SR:
    def __init__(self, host, port):
        self.sequence_number = 0 #random.randint(0, 2**16 - 1)
        self.ack_number = 0
        self._is_connected = True
        self.adress = (host, port)  # para la instancia original aca se guarda la ip y el puerto del host, para las instancias creadas por el accept(), se guarda la ip y el puerto del cliente
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
        self.connections = {}    # diccionario de conexiones activas
        self.recv_queue = queue.Queue() #queue con get() bloqueante para que el hilo no sea un busyloop
        self.SYN_queue = queue.Queue() 
        self.keep_running = True

    def bind(self):
        self.socket.bind(self.adress)
        print(f"[SR.SERVIDOR] Escuchando en {self.adress}")
    
    def close_server(self):
        self.keep_running = False
        self.socket.close()
        print("[SR.SERVIDOR] Socket cerrado correctamente")
    
    def accept(self):
        while self.keep_running:
            #esperar el primer paquete(SYN)
            # print(f"[SR.SERVIDOR] Esperando conexión...")
            # data_syn, addr_syn = self.socket.recvfrom(HEADER_SIZE)
            # print(f"[SR.SERVIDOR] Paquete recibido de {addr_syn}")

            data_syn, addr_syn = self.SYN_queue.get() #bloqueante, evita busyloop

            pack_syn = Package()
            pack_syn.decode_to_package(data_syn)

            if pack_syn.want_SYN(): #si es syn le mando mi SN y el ack
                print(f"[SR.SERVIDOR] es un SYN")
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
                    new_socket.socket = self.socket  #solo referencia, NO se crea otro
                    
                    new_socket.adress = addr_syn  #dirección del cliente asociado
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
                    new_socket.recv_queue = queue.Queue()
                    self.connections[addr_syn] = new_socket

                    print(f"[SR.SERVIDOR] Nueva conexión aceptada de {addr_syn}")
                    return new_socket
        return None

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
            print(f"[SR_SENDER] FIRST send_base {self.send_base}")


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
        #print(f"[SR_SENDER] Enviado paquete con contenido {pack.get_data()}") #este lo comento pq es muy molesto
        print(f"[SR_SENDER] Enviado paquete con seq {self.next_seq_number}")

        self.next_seq_number += len(data)

        print(f"[SR_SENDER](ACK que espero recibir): {self.next_seq_number}")

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
        print(f"[SR_SENDER] Llego ACK con sequence number {pack_ack}")
        if pack_ack in self.thrds:
            print(f"[CIENTE] Paquete con ack number {pack_ack} dentro de la ventana de recepcion")
            # parar el hilo específico
            self.stop_events[pack_ack].set()

            self.thrds[pack_ack].join() 

            len_pack_thrd = self.shared_lenghts[pack_ack][0] # obtener el len del hilo

            self._delete_thrd(pack_ack)

            self.packages_acked[pack_ack - len_pack_thrd] = len_pack_thrd # guardar el len en el diccionario de acked
            print(f"[SR_SENDER] send base es: {self.send_base  }")
            while self.send_base in self.packages_acked:
                lenght = self.packages_acked[self.send_base]
                print(f"[SR.RECEPTOR] Paquete con seq {self.send_base} procesado")

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
        print(f"[SR_SENDER] thrd con seq {pack.get_sequence_number()} terminado")

    def _retransmit(self, paquete):
        # Reenviar el paquete
        self.socket.sendto(paquete.packaging(), self.adress)
        print(f"[SR_SENDER] Reenviado paquete con seq {paquete.get_sequence_number()}")
    
    def recv(self):
        print(f"[SR.RECEPTOR]hola, entro a la funciona recv")
        if not self._is_connected:
            print("[SR.RECEPTOR] Socket no conectado")
            return None

        print(f"[SR.RECEPTOR] Recibiendo paquete")
        recived_bytes, sender_adress = self.socket.recvfrom(MAX_PACKAGE_SIZE)
        print(f"[SR.RECEPTOR] Recibi paquete")

        pack = Package()
        pack.decode_to_package(recived_bytes)

        if sender_adress in self.connections:
            self.connections[sender_adress].recv_queue.put(pack)
            return None

        self.SYN_queue.put((recived_bytes, sender_adress)) #si no es un cliente conocido, lo guardo en la cola de SYN
        return None

    def process_package(self):
        print("[SR.RECEPTOR] sacando paquete de la cola")
        pack = self.recv_queue.get() #bloqueante, evita busyloop | ojo pq si el cliente NUNCA manda 'FIN', esto se queda esperando pa siempre, ver como solucionarlo
        print("[SR.RECEPTOR] saque algo de la cola")
        seq_num = pack.get_sequence_number()  
        print(f"[SR.RECEPTOR] Recibi paquete con sequence number {seq_num}")
        data = pack.get_data()  

        # verificar si el paquete es FIN
        if pack.want_FIN():
            print(f"[SR.RECEPTOR] Paquete FIN recibido con seq {seq_num}")
            self._is_connected = False
            self.ack_number = pack.get_sequence_number() + 1
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
            self.socket.sendto(answer.packaging(), self.adress) #esto es thread safe, no hay problema que todos le hablen a la misma isntancia de socketUDP
            print(f"[SR.RECEPTOR] Enviado ACK para el paquete con seq {ack_seq}")

            # procesar paquetes en orden (si estan disponibles)
            while self.recv_base in self.recv_buffer:
                # aca se puede procesar el paquete
                data = self.recv_buffer[self.recv_base]
                print(f"[SR.RECEPTOR] Paquete con seq {self.recv_base} procesado")
                # print(f"[SR.RECEPTOR] DATA: {data} ")

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
            self.socket.sendto(answer.packaging(), self.adress) #esto es thread safe, no hay problema que todos le hablen a la misma isntancia de socketUDP #esto es thread safe, no hay problema que todos le hablen a la misma isntancia de socketUDP
            print(f"[SR.RECEPTOR] Reenviando ACK para seq {ack_seq} (paquete duplicado con seq {seq_num})")
        # ignorar el paquete si esta afuera de la ventana
        else:
            print(f"[SR.RECEPTOR] Paquete con seq {seq_num} fuera de la ventana de recepción")

        return data


    def close(self):
        fin = Package()
        fin.set_FIN()
        print("---self.sequence_number---", self.sequence_number)
        fin.set_sequence_number(self.sequence_number)
        print("---FIN con seq---", fin.get_sequence_number())

        ack_answer = self.__send_and_wait_syn(fin, TOTAL_RETRIES, self.adress)
        if ack_answer is not None:
            data, address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
            final_pack = Package()
            final_pack.decode_to_package(data)
            if final_pack.want_FIN():
                answer = Package()
                self.ack_number += 1 # no se pq el doble, falta algun +1 en otro lado
                answer.set_ACK(self.ack_number + 1)
                print("---self.sequence_number---", self.sequence_number)
                answer.set_sequence_number(self.sequence_number)
                print("---ANSWER con seq---", answer.get_sequence_number())
                self.socket.sendto(answer.packaging(), self.adress)
                self._is_connected = False
                self.socket.close()
                print("[INFO] Socket cerrado correctamente")
                return True


    def __end_connection(self):
        ack_fin = Package()
        #self.ack_number += 1
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
        self._handle_timeout()
    
    def _handle_timeout(self):
        timeout = 2.0
        start_time = time.time()

        while True:
            if time.time() - start_time >= timeout:
                print("[SR.END_CONN] Timeout esperando ACK final del FIN")
                break 

            # usamos select para esperar datos sin bloquear el socket global
            ready_to_read, _, _ = select.select([self.socket], [], [], timeout)

            if ready_to_read:
                final_pack  = self.recv_queue.get() # ojo que se bloquea si nunca le responden al FIN

                if final_pack.get_ACK() == self.sequence_number:
                    print("[SR.END_CONN] ACK final recibido correctamente")
                    print(f"[SR.END_CONN] Conexión cerrada correctamente")
                    break  # Sale del loop si el ACK es el esperado
            else:
                print("[SR.END_CONN] Timeout esperando el ACK final del FIN")
                break  

        # try:
        #     #espera de ACK en el buffer personal, no en el socket
        #     final_ack = self.recv_queue.get(timeout=2.0)  # bloqueante con timeout
        #     if final_ack.get_ACK() == self.sequence_number:
        #         print(f"[SR.END_CONN] ACK final recibido correctamente")
        #     else:
        #         raise Exception("[ERROR] ACK inválido en cierre de conexión")
        # except queue.Empty:
        #     print("[SR.END_CONN] Timeout esperando el ACK final del FIN")
        #     raise Exception("[ERROR] Timeout al esperar el ACK del FIN")

        # #marcar como desconectado
        # #OJO, ver si aca o en otro lado tengo q cerrar threads q controlan el timeout d paquetes
        # self._is_connected = False




    def __send_and_wait_syn(self, package, total_retries, address):
        print("[SEND_AND_WAIT_SYN] ")
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
                print(f"[SR_SENDER] Timeout esperando ACK , reintentando... {retries}")

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