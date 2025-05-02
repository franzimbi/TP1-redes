import socket
from common.package import Package
import random
import numpy as np

MAX_PACKAGE_SIZE = 1035
MAX_DATA_SIZE = 1024
HEADER_SIZE = 13
TOTAL_RETRIES = 10
MAX_SEQ_NUM = 2**16 - 1
DEFAULT_LISTENERS = 5


class SocketRDT_SW:
    
    def __init__(self):
        self.sequence_number = random.randint(0, MAX_SEQ_NUM - 1)
        self.ack_number = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._is_connected = False
        self.sockets = []
        self.socket_max = DEFAULT_LISTENERS

    #Para Servidor
    def bind(self, adress):
        self.socket.bind(adress)

    def listen(self, n_connections):
        self.socket_max = n_connections
        print(f"[SERVER] Escuchando")

    def _reap_dead_sockets(self):
        for sock in self.sockets:
            if not sock._is_connected:
                self.sockets.remove(sock)

    def _close_sockets(self):
        for sock in self.sockets:
            sock.close()
        
    def accept(self):
        print("[SERVER] Esperando SYN...")
        data, client_address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
        self._reap_dead_sockets()
        packet = Package()
        packet.decode_to_package(data)
        self.socket.settimeout(1)  # Timeout de 1 segundo
        if packet.want_SYN():
            if len(self.sockets) >= self.socket_max:
                print(f"[SERVER] Se supero el maximo de {self.socket_max} conexiones")
                return (None, None)
            seq_num = (packet.get_sequence_number() + 1) % MAX_SEQ_NUM
            print("[SERVER] Recibido SYN, enviando SYN-ACK")
            print(f"[SERVER] Enviando SYN-ACK a {client_address}")
            new_socket, new_port = self._create_client_handler(client_address, seq_num)
            server_syn_pack = Package()
            server_syn_pack.set_SYN()
            server_syn_pack.set_data(new_port.to_bytes(2, byteorder='big'))
            server_syn_pack.set_sequence_number(self.sequence_number)
            
            client_ack_pack = Package()
            
            counter = 0
            while not client_ack_pack.want_ACK_FLAG() and counter < TOTAL_RETRIES:
                self.socket.sendto(server_syn_pack.packaging(), client_address)
                try:
                    ack_data, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                    client_ack_pack.decode_to_package(ack_data)
                except socket.timeout:
                    print("[SERVER] Timeout esperando ACK, reintentando...") 
                    counter += 1
                    continue

            if client_ack_pack.want_ACK_FLAG():
                print("[SERVER] Conexión establecida")
                self.socket.settimeout(None)
                new_socket._is_connected = True
                self.sockets.append(new_socket)
                return new_socket, client_address
                
                
        print("[SERVER] No se recibió SYN, cerrando conexión, ¿quien chota sos?")
        return (None, None)


    def _create_client_handler(self, client_address, seq_num):
        new_socket = SocketRDT_SW()
        new_socket.bind((self.socket.getsockname()[0], 0))
        new_socket._connect_to_peer(client_address)
        new_socket.ack_number = seq_num
        new_socket.sequence_number = self.sequence_number
        return new_socket, new_socket.socket.getsockname()[1]

    def _connect_to_peer(self, client_address):
        self.socket.connect(client_address)
    
    #Para Cliente
    def connect(self, adress):
        print("[CLIENT] Enviando SYN")
        client_syn_pack = Package()
        client_syn_pack.set_SYN()
        client_syn_pack.set_sequence_number(self.sequence_number)
        self.socket.settimeout(1)  # Timeout de 1 segundo
        server_syn_ack = Package()
        
        counter = 0
        while not server_syn_ack.want_SYN() and counter < TOTAL_RETRIES:
            print("[CLIENT] Enviando SYN en el while")
            print(f"[CLIENT] server_syn_ack: {server_syn_ack.want_SYN()}")
            self.socket.sendto(client_syn_pack.packaging(), adress)
            try:
                data, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                server_syn_ack.decode_to_package(data)
            except socket.timeout:
                print("[CLIENT] Timeout esperando SYN-ACK, reintentando...")
                counter += 1
                continue

        if counter == TOTAL_RETRIES:
            raise Exception("[CLIENT] Timeout esperando SYN-ACK, se agotaron los reintentos")
            
        if server_syn_ack.want_SYN():
            self.ack_number = (server_syn_ack.get_sequence_number() + 1) % MAX_SEQ_NUM
            print(f"[CLIENT] Recibido SYN-ACK, enviando ACK {self.ack_number}")
            print("[CLIENT] Recibido SYN-ACK, enviando ACK")
            client_ack_pack = Package()
            client_ack_pack.set_ACK_FLAG()
            self.socket.sendto(client_ack_pack.packaging(), adress)
            self._is_connected = True
            self.socket.connect((adress[0], int.from_bytes(server_syn_ack.get_data(), byteorder='big')))
            print("[CLIENT] Conexión establecida")

    def recv(self, n_bytes):
        self.socket.settimeout(None)
        while True:
            received_bytes, address = self.socket.recvfrom(n_bytes+HEADER_SIZE)
            pack = Package()
            pack.decode_to_package(received_bytes)
            seq_num = pack.get_sequence_number()

            if seq_num == self.ack_number:
                # Paquete válido y esperado
                data = pack.get_data()
                self.ack_number = (self.ack_number + 1) % MAX_SEQ_NUM

                ack_pack = Package()
                ack_pack.set_ACK_FLAG()
                ack_pack.set_sequence_number(self.ack_number)
                ack_pack.set_ACK(self.ack_number)
                print(f"[RECV] Envio ack con numero {self.ack_number}")
                self.socket.send(ack_pack.packaging())
                return data
            else:
                # Paquete duplicado o fuera de orden → reenviamos último ACK
                print(f"[RECV] Secuencia inesperada: {seq_num}, esperaba: {self.ack_number}. Reenviando ACK.")
                ack_pack = Package()
                ack_pack.set_ACK_FLAG()
                ack_pack.set_sequence_number(self.ack_number)
                ack_pack.set_ACK(self.ack_number)
                self.socket.send(ack_pack.packaging())

    
    def sendall(self, data):
        print(f"[SEND] Enviando {len(data)} bytes")
        chunks = [data[i:i + MAX_DATA_SIZE] for i in range(0, len(data), MAX_DATA_SIZE)]

        for chunk in chunks:
            retries = 0
            ack_received = False
            while not ack_received and retries < TOTAL_RETRIES:
                print(f"[SEND] Enviando paquete, reintentos: {retries}")
                self._send(chunk, (retries != 0))
                # packet = Package()
                # packet.set_data(chunk)
                # self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
                # packet.set_sequence_number(self.sequence_number)
                # self.socket.sendto(packet.packaging(), self.adress)

                try:
                    self.socket.settimeout(0.05)
                    ack_data, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                    ack_packet = Package()
                    ack_packet.decode_to_package(ack_data)
                    # Verificar si el ACK es correcto
                    print(f"[SEND] Recibido ACK: {ack_packet.get_ack_number()}")
                    print(f"[SEND] Secuencia esperada: {(self.sequence_number + 1) % MAX_SEQ_NUM}")
                    print(f"[SEND] ACK esperado: {ack_packet.want_ACK_FLAG()}")
                    if ack_packet.want_ACK_FLAG() and ack_packet.get_ack_number() == ((self.sequence_number + 1) % MAX_SEQ_NUM):
                        print(f"[SEND] ACK correcto, secuencia: {ack_packet.get_ack_number()}")
                        ack_received = True
                        #self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
                    else:
                        retries += 1
                except socket.timeout:
                    print(f"[SEND] Timeout esperando ACK, reintentando {retries + 1} seq_num: {self.sequence_number}" )
                    retries += 1
                    continue

            if not ack_received:

                    raise Exception("[SEND] Fallo en el envío, se agotaron los reintentos")
    
    def _send(self,chunk, resend):
        seq_num = (self.sequence_number + 1) % MAX_SEQ_NUM
        if resend:
            seq_num = self.sequence_number
        
        packet = Package()
        packet.set_data(chunk)
        self.sequence_number = seq_num
        packet.set_sequence_number(self.sequence_number)
        print(f"[SEND] Enviando pack con seq num: {self.sequence_number}")

        self.socket.send(packet.packaging())
        
    def close(self):
        self._close_sockets()
        self._reap_dead_sockets()
        self.socket.close()
        self._is_connected = False
