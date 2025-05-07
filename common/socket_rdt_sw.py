import random
import socket
import time
from common.package import Package
from common.logger import HIGH_VERBOSITY, LOW_VERBOSITY

MAX_PACKAGE_SIZE = 1035
MAX_DATA_SIZE = 1024
HEADER_SIZE = 11
TOTAL_RETRIES = 10
MAX_SEQ_NUM = 2**16 - 1
DEFAULT_LISTENERS = 5


class SocketRDT_SW:

    def __init__(self, logger):
        self.sequence_number = random.randint(0, MAX_SEQ_NUM)
        self.ack_number = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._is_connected = False
        self.sockets = []
        self.socket_max = DEFAULT_LISTENERS
        self._recv_buffer = b""
        self.logger = logger
        #rtt
        self.estimated_rtt = 0.1
        self.dev_rtt = 0.05
        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt

    def _update_rtt(self, sample_rtt):
        alpha = 0.125
        beta = 0.25
        self.estimated_rtt = (1 - alpha) * self.estimated_rtt + alpha * sample_rtt
        self.dev_rtt = (1 - beta) * self.dev_rtt + beta * abs(sample_rtt - self.estimated_rtt)
        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt


    # Para Servidor
    def bind(self, adress):
        self.socket.bind(adress)

    def listen(self, n_connections):
        self.socket_max = n_connections
        self.logger.log("[SW-listen] escuchando conexiones", LOW_VERBOSITY)

    def _reap_dead_sockets(self):
        for sock in self.sockets:
            if not sock._is_connected:
                self.sockets.remove(sock)

    def _close_sockets(self):
        for sock in self.sockets:
            sock.close()

    def accept(self):
        self.logger.log("[SW-accept] aceptando con 3 way handshake", LOW_VERBOSITY)
        data, client_address = self.socket.recvfrom(MAX_PACKAGE_SIZE)
        self._reap_dead_sockets()
        packet = Package()
        packet.decode_to_package(data)

        self.socket.settimeout(self.timeout_interval)  # usar RTT estimado

        if packet.want_SYN():
            if len(self.sockets) >= self.socket_max:
                self.logger.log(
                    "[SW-accept] No se pueden aceptar más conexiones por limite",
                    LOW_VERBOSITY)
                self.socket.settimeout(None)
                return (None, None)
            seq_num = (packet.get_sequence_number() + 1) % MAX_SEQ_NUM
            self.logger.log(
                f"[SW-accept] Recibido SYN, de {client_address}",
                HIGH_VERBOSITY)
            new_socket, new_port = self._create_client_handler(
                client_address, seq_num
            )
            server_syn_pack = Package()
            server_syn_pack.set_SYN()
            server_syn_pack.set_data(new_port.to_bytes(2, byteorder="big"))
            server_syn_pack.set_sequence_number(self.sequence_number)

            client_ack_pack = Package()

            counter = 0
            while (
                not client_ack_pack.want_ACK_FLAG() and counter < TOTAL_RETRIES
            ):
                self.socket.sendto(server_syn_pack.packaging(), client_address)
                try:
                    ack_data, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                    client_ack_pack.decode_to_package(ack_data)

                    # Calcular sample_rtt y actualizar timeout_interval
                    sample_rtt = self.timeout_interval
                    self._update_rtt(sample_rtt)
                    counter += 1

                except socket.timeout:
                    self.logger.log(
                        "[SW-accept] Timeout esperando ACK, reintentando...",
                        HIGH_VERBOSITY)
                    counter += 1
                    continue


            if client_ack_pack.want_ACK_FLAG():
                self.logger.log(
                    f"[SW-accept] conexion establecida con {self.ack_number}",
                    LOW_VERBOSITY)
                self.socket.settimeout(None)
                new_socket._is_connected = True
                self.sockets.append(new_socket)
                return new_socket, client_address
        self.socket.settimeout(None)
        return (None, None)

    def _create_client_handler(self, client_address, seq_num):
        new_socket = SocketRDT_SW(self.logger)
        new_socket.bind((self.socket.getsockname()[0], 0))
        new_socket._connect_to_peer(client_address)
        new_socket.ack_number = seq_num
        new_socket.sequence_number = self.sequence_number
        new_socket._is_connected = True
        return new_socket, new_socket.socket.getsockname()[1]

    def _connect_to_peer(self, client_address):
        self.socket.connect(client_address)

    # Para Cliente
    def connect(self, adress):
        self.logger.log("[sw-connect] Conectando...", LOW_VERBOSITY)
        client_syn_pack = Package()
        client_syn_pack.set_SYN()
        client_syn_pack.set_sequence_number(self.sequence_number)
        self.socket.settimeout(1)  # Timeout de 1 segundo
        server_syn_ack = Package()

        counter = 0
        while not server_syn_ack.want_SYN() and counter < TOTAL_RETRIES:
            self.logger.log("[sw-connect] Enviando SYN, esperando SYN-ACK", HIGH_VERBOSITY)
            self.socket.sendto(client_syn_pack.packaging(), adress)
            try:
                data, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                server_syn_ack.decode_to_package(data)
            except socket.timeout:
                self.logger.log(
                    "[sw-connect] Timeout esperando SYN-ACK, reintentando...", HIGH_VERBOSITY)
                counter += 1
                continue

        if counter == TOTAL_RETRIES:
            raise Exception(
                "[sw-connect] Timeout esperando SYN-ACK, se agotaron los reintentos"   # noqa: E501
            )

        if server_syn_ack.want_SYN():
            self.ack_number = (
                server_syn_ack.get_sequence_number() + 1
            ) % MAX_SEQ_NUM
            client_ack_pack = Package()
            client_ack_pack.set_ACK_FLAG()
            self.socket.sendto(client_ack_pack.packaging(), adress)
            self._is_connected = True
            self.socket.connect(
                (
                    adress[0],
                    int.from_bytes(server_syn_ack.get_data(), byteorder="big"),
                )
            )
            self.logger.log(
                f"[sw-connect] Conexión establecida con {self.socket.getsockname()}",
                LOW_VERBOSITY)

    def recv(self, n_bytes):
        self.socket.settimeout(None)
        while True:
            try:
                received_bytes, address = self.socket.recvfrom(
                    n_bytes + HEADER_SIZE
                )
                pack = Package()
                pack.decode_to_package(received_bytes)
                seq_num = pack.get_sequence_number()
            except socket.timeout:
                self.logger.log("[sw-recv] Timeout esperando paquete", LOW_VERBOSITY)
                break

            if seq_num == self.ack_number:
                data = pack.get_data()
                self.ack_number = (self.ack_number + 1) % MAX_SEQ_NUM

                ack_pack = Package()
                ack_pack.set_ACK_FLAG()
                ack_pack.set_sequence_number(self.ack_number)
                ack_pack.set_ACK(self.ack_number)
                self.socket.send(ack_pack.packaging())
                return data
            else:
                ack_pack = Package()
                ack_pack.set_ACK_FLAG()
                ack_pack.set_sequence_number(self.ack_number)
                ack_pack.set_ACK(self.ack_number)
                self.socket.send(ack_pack.packaging())

        self.close()

    def sendall(self, data):
        chunks = [
            data[i:i + MAX_DATA_SIZE]
            for i in range(0, len(data), MAX_DATA_SIZE)
        ]

        for chunk in chunks:
            retries = 0
            ack_received = False
            while not ack_received and retries < TOTAL_RETRIES:
                start_time = time.time()
                self._send(chunk, (retries != 0))

                try:
                    self.socket.settimeout(self.timeout_interval)
                    ack_data, _ = self.socket.recvfrom(MAX_PACKAGE_SIZE)
                    end_time = time.time()
                    sample_rtt = end_time - start_time
                    ack_packet = Package()
                    ack_packet.decode_to_package(ack_data)

                    if (
                        ack_packet.want_ACK_FLAG()
                        and ack_packet.get_ack_number()
                        == ((self.sequence_number + 1) % MAX_SEQ_NUM)
                    ):
                        self._update_rtt(sample_rtt)
                        ack_received = True
                    else:
                        retries += 1
                except socket.timeout:
                    self.logger.log("[sw-sendall] Timeout esperando ACK", LOW_VERBOSITY)
                    retries += 1
                    continue

            if not ack_received:

                raise Exception(
                    "[SEND] Fallo en el envío, se agotaron los reintentos"
                )

    def _send(self, chunk, resend):
        seq_num = (self.sequence_number + 1) % MAX_SEQ_NUM
        if resend:
            seq_num = self.sequence_number

        packet = Package()
        packet.set_data(chunk)
        self.sequence_number = seq_num
        packet.set_sequence_number(self.sequence_number)

        self.socket.send(packet.packaging())

    def close(self):
        self.logger.log("[sw-close] Cerrando socket", LOW_VERBOSITY)
        self._is_connected = False
        self._close_sockets()
        self._reap_dead_sockets()
        self.socket.close()
        
