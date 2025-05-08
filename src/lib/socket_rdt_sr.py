import queue
import random
import socket
import threading
import time


from lib.package import Package
from lib.logger import LOW_VERBOSITY, HIGH_VERBOSITY

MAX_PACKAGE_SIZE = 1035
HEADER_SIZE = 13
TOTAL_RETRIES = 5
WINDOW_SIZE = 20
MAX_SEQ_NUM = 2**16 - 1


class SocketRDT_SR:
    def __init__(self, host, port, logger):
        self.sequence_number = random.randint(0, MAX_SEQ_NUM)
        self.ack_number = 0
        self._is_connected = True
        self.logger = logger
        # para la instancia original aca se guarda la ip y el puerto del host,
        # para las instancias creadas por el accept(), se guarda la ip y el
        # puerto del cliente
        self.adress = (host, port, )
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(None)
        # emisor
        self.send_base = (
            self.sequence_number
        )  # Primer número de secuencia aún no ACKeado (emisor)
        self.next_seq_number = (
            self.sequence_number
        )  # Próximo número de secuencia a usar para enviar (emisor)
        self.thrds = {}  # diccionario de thrds
        self.packages_acked = {}  # diccionario de acked
        self.stop_events = {}  # diccionario de stop events
        self.shared_lenghts = {}  # diccionario de variables compartidas
        # receptor
        self.recv_base = 0  # Primer número de secuencia esperada (receptor)
        self.recv_buffer = {}  # clave: número de secuencia, valor: datos
        self.connections = {}  # diccionario de conexiones activas
        self.recv_queue = queue.Queue()
        self.SYN_queue = queue.Queue()
        self.acks_queue = queue.Queue()

        self.keep_running = True
        self.process_pack_thread = None
        # queue para los datos recibidos y procesados para sacarlos de a bytes
        self.data_queue = (queue.Queue())

        self._estimated_rtt = 0.125
        self._dev_rtt = 0
        self._timeout = 0.05
        self._alpha = 0.125
        self._beta = 0.25
        self.send_times = {}
        self.is_sending = True

        self.process_pack_thread = None

    def __del__(self):
        self.keep_running = False
        if self.process_pack_thread is not None:
            self.process_pack_thread.join()

    def bind(self):
        self.socket.bind(self.adress)
        self.logger.log(f"[sr-bind] Escuchando en {self.adress}",
                        LOW_VERBOSITY)

    def close_server(self):
        self.keep_running = False
        self.socket.close()

    def listen(self, n_connections):
        self.logger.log("[sr-listen] Escuchando conexiones", LOW_VERBOSITY)

    def _update_timeout(self, sample_rtt):
        if self._estimated_rtt is None:
            self._estimated_rtt = sample_rtt
            self._dev_rtt = sample_rtt / 2
        else:
            self._estimated_rtt = (
                1 - self._alpha
            ) * self._estimated_rtt + self._alpha * sample_rtt
            self._dev_rtt = (
                1 - self._beta
            ) * self._dev_rtt + self._beta * abs(
                sample_rtt - self._estimated_rtt
            )

        self._timeout = self._estimated_rtt + 4 * self._dev_rtt
        return self._timeout

    def reap_dead_connections(self):
        for addr, conn in list(self.connections.items()):
            if not conn._is_connected:
                del self.connections[addr]

    def accept(self):
        while self.keep_running:
            self.logger.log("[sr-accept] Esperando conexiones", LOW_VERBOSITY)
            self.reap_dead_connections()

            data_syn, addr_syn = (
                self.SYN_queue.get()
            )

            pack_syn = Package()
            pack_syn.decode_to_package(data_syn)

            if pack_syn.want_SYN():
                self.logger.log(
                    f"[sr-accept] Paquete SYN recibido de {addr_syn}",
                    HIGH_VERBOSITY)
                # responder con SYN+ACK
                answer_syn = Package()
                answer_syn.set_SYN()
                self.ack_number = (
                    pack_syn.get_sequence_number() + 1
                ) % MAX_SEQ_NUM
                answer_syn.set_ACK(self.ack_number)
                answer_syn.set_ACK_FLAG()
                answer_syn.set_sequence_number(self.sequence_number)

                # handshake exitoso: crear socket nuevo para este cliente
                new_socket = SocketRDT_SR.__new__(SocketRDT_SR)
                new_socket.socket = (
                    self.socket
                )
                new_socket.logger = self.logger
                new_socket.adress = addr_syn
                new_socket._is_connected = True

                new_socket.sequence_number = (
                    self.sequence_number + 1
                ) % MAX_SEQ_NUM

                new_socket.ack_number = 0

                new_socket.send_base = new_socket.sequence_number
                new_socket.next_seq_number = new_socket.sequence_number

                new_socket.thrds = {}
                new_socket.packages_acked = {}
                new_socket.stop_events = {}
                new_socket.shared_lenghts = {}

                new_socket.recv_base = (
                    pack_syn.get_sequence_number() + 1
                ) % MAX_SEQ_NUM
                new_socket.recv_buffer = {}
                new_socket.recv_queue = queue.Queue()
                new_socket.acks_queue = queue.Queue()
                new_socket.process_pack_thread = threading.Thread(
                    target=new_socket.process_package
                )
                new_socket.process_pack_thread.daemon = True
                new_socket.data_queue = queue.Queue()
                new_socket.keep_running = True

                new_socket._estimated_rtt = 0.125
                new_socket._dev_rtt = 0
                new_socket._timeout = 0.05
                new_socket._alpha = 0.125
                new_socket._beta = 0.25
                new_socket.send_times = {}
                self.connections[addr_syn] = new_socket

                # enviar SYN+ACK y esperar ACK final
                self.__send_and_wait_syn(answer_syn, TOTAL_RETRIES, addr_syn)
                self.logger.log(
                    f"[sr-accept] Nueva conexión aceptada de {addr_syn}",
                    LOW_VERBOSITY)
                new_socket.process_pack_thread.start()
                return new_socket, addr_syn
        return None

    def connect(self):
        syn = Package()
        syn.set_SYN()
        syn.set_sequence_number(self.sequence_number)
        self.logger.log(
            f"[sr-connect] Enviando SYN a {self.adress}", HIGH_VERBOSITY)
        answer_connect = self._client_send_and_wait_syn(
            syn, TOTAL_RETRIES, self.adress
        )
        if answer_connect is not None and answer_connect.want_SYN():
            self.ack_number = (
                answer_connect.get_sequence_number() + 1
            ) % MAX_SEQ_NUM
            self.logger.log(
                f"[sr-connect] Recibido SYN+ACK de {self.adress}",
                HIGH_VERBOSITY)
            final_ack = Package()
            final_ack.set_ACK(self.ack_number)
            final_ack.set_ACK_FLAG()
            final_ack.set_sequence_number(
                (self.sequence_number + 1) % MAX_SEQ_NUM
            )
            self.socket.sendto(final_ack.packaging(), self.adress)
            self._is_connected = True
            self.send_base = (self.sequence_number + 1) % MAX_SEQ_NUM
            self.recv_base = (
                answer_connect.get_sequence_number() + 1
            ) % MAX_SEQ_NUM

            self.next_seq_number = self.send_base
            self.logger.log("[sr-connect] Enviando base de ventana: {self.send_base}", LOW_VERBOSITY)  # noqa: E501

        if answer_connect is None:
            self.logger.log("[sr-connect] Timeout esperando SYN+ACK",
                            HIGH_VERBOSITY)
            self._is_connected = False
            return False
        self.connections[self.adress] = self
        self.logger.log("[sr-connect] Conexión establecida", LOW_VERBOSITY)

        self.process_pack_thread = threading.Thread(
            target=self.process_package
        )
        self.process_pack_thread.daemon = True
        self.process_pack_thread.start()
        return True

    def _ack_listener(self):
        while self.is_sending:
            self._check_ACKs()

    def sendall(self, data):
        if not self._is_connected:
            raise Exception("Socket no conectado")

        total_size = len(data)
        offset = 0
        chunk_size = 1024
        window_chunk_size = chunk_size * WINDOW_SIZE

        self.is_sending = True
        ack_thread = threading.Thread(target=self._ack_listener)
        ack_thread.start()
        while offset < total_size:
            if (
                self.send_base
                <= self.next_seq_number + chunk_size
                < self.send_base + window_chunk_size
            ):
                data_chunk = data[offset: offset + chunk_size]

                self._send_data(data_chunk)

                offset += len(data_chunk)

        self.is_sending = False
        ack_thread.join()

        while self.thrds:
            try:
                self._check_ACKs()
            except queue.Empty:
                pass

        while True:
            try:
                self.acks_queue.get_nowait()
            except queue.Empty:
                break

    def _send_data(self, data):
        pack = Package()
        pack.set_data(data)
        pack.set_sequence_number(self.next_seq_number)
        self.socket.sendto(pack.packaging(), self.adress)

        self.next_seq_number = (self.next_seq_number + len(data)) % MAX_SEQ_NUM
        self.send_times[self.next_seq_number] = (
            time.time()
        )
        self._create_thrd(pack)  # crear hilo para controlar el timeout

    def _create_thrd(self, pack):
        self.shared_lenghts[self.next_seq_number] = [0]
        self.stop_events[self.next_seq_number] = threading.Event()

        thrd = threading.Thread(
            target=self._controlar_timeout,
            args=(
                pack,
                self.shared_lenghts[self.next_seq_number],
                self.stop_events[self.next_seq_number],
            ),
        )
        thrd.start()

        self.thrds[self.next_seq_number] = thrd

    def _check_ACKs(self):
        try:
            pack = self.acks_queue.get()
            pack_ack = pack.get_ack_number()
            if pack_ack in self.thrds:
                sample_rtt = time.time() - self.send_times[pack_ack]
                self._update_timeout(sample_rtt)

                self.stop_events[pack_ack].set()
                self.thrds[pack_ack].join()

                len_pack_thrd = self.shared_lenghts[pack_ack][0]
                self._delete_thrd(pack_ack)
                numerito = (pack_ack - len_pack_thrd + MAX_SEQ_NUM) % MAX_SEQ_NUM  # noqa: E501
                self.packages_acked[numerito] = len_pack_thrd

                while self.send_base in self.packages_acked:
                    lenght = self.packages_acked[self.send_base]

                    del self.packages_acked[self.send_base]
                    self.send_base = (self.send_base + lenght) % MAX_SEQ_NUM
        except queue.Empty:
            pass

    def _delete_thrd(self, pack_ack):
        del self.thrds[pack_ack]
        del self.stop_events[pack_ack]
        del self.shared_lenghts[pack_ack]

    def _controlar_timeout(self, pack, variable_compartida, stop_event):
        while not stop_event.is_set():

            if stop_event.wait(self._estimated_rtt):
                break

            self._retransmit(pack)

        variable_compartida[0] = pack.get_data_length()

    def _retransmit(self, paquete):
        self.socket.sendto(paquete.packaging(), self.adress)

    def recv_all(self):

        if not self._is_connected:

            return None

        self.socket.settimeout(2)
        try:
            recived_bytes, sender_adress = self.socket.recvfrom(
                MAX_PACKAGE_SIZE
            )
        except (socket.timeout, OSError):
            return None
        pack = Package()
        pack.decode_to_package(recived_bytes)

        if pack.want_ACK_FLAG():

            if sender_adress in self.connections:
                self.connections[sender_adress].acks_queue.put(pack)
            else:
                self.acks_queue.put(pack)
            return None

        if sender_adress in self.connections:
            self.connections[sender_adress].recv_queue.put(pack)
            return None

        if pack.want_SYN():
            self.logger.log("[sr-recv_all] Paquete SYN recibido",
                            HIGH_VERBOSITY)
            self.SYN_queue.put((recived_bytes, sender_adress))
        return None

    def process_package(self):

        while self._is_connected:
            try:
                pack = self.recv_queue.get(timeout=2)
                seq_num = pack.get_sequence_number()
                data = pack.get_data()
            except queue.Empty:
                continue

            # verificar si el paquete es FIN
            if pack.want_FIN():
                self.logger.log("[sr-recv_all] Paquete FIN recibido",
                                LOW_VERBOSITY)
                self.ack_number = (
                    pack.get_sequence_number() + 1
                ) % MAX_SEQ_NUM
                self.__end_connection()
                return None

            # si el paquete esta dentro de la ventana de recepcion
            if self.in_window(self.recv_base, seq_num, WINDOW_SIZE * 1024):
                # almacenar el paquete en el buffer si esta dentro de la ventana  # noqa: E501
                self.recv_buffer[seq_num] = data

                # enviar ACK para el siguiente paquete esperado
                ack_seq = (
                    seq_num + len(data)
                ) % MAX_SEQ_NUM
                answer = Package()
                answer.set_ACK(ack_seq)
                answer.set_ACK_FLAG()
                answer.set_sequence_number(self.sequence_number % MAX_SEQ_NUM)

                self.socket.sendto(answer.packaging(), self.adress)
                # procesar paquetes en orden (si estan disponibles)
                while self.recv_base in self.recv_buffer:
                    data = self.recv_buffer[self.recv_base]

                    # guardar el paquete en la cola de datos
                    for b in data:
                        self.data_queue.put(b)
                    # eliminar del buffer
                    del self.recv_buffer[self.recv_base]

                    # avanzar la ventana
                    self.recv_base = (self.recv_base + len(data)) % MAX_SEQ_NUM

            else:
                ack_seq = (
                    seq_num + len(data)
                ) % MAX_SEQ_NUM
                answer = Package()
                answer.set_ACK(ack_seq)
                answer.set_ACK_FLAG()
                answer.set_sequence_number(self.sequence_number % MAX_SEQ_NUM)

                self.socket.sendto(answer.packaging(), self.adress)

    @staticmethod
    def in_window(base, seq, window_size):
        return (seq - base) % MAX_SEQ_NUM < window_size

    def recv(self, n_bytes):
        result = bytearray()
        for _ in range(n_bytes):
            byte = self.data_queue.get()
            result.append(byte)
        return bytes(result)

    def close(self):
        fin = Package()
        fin.set_FIN()
        fin.set_sequence_number(self.sequence_number)

        ack_answer = self._client_send_and_wait_syn(
            fin, TOTAL_RETRIES, self.adress
        )
        if ack_answer is not None:
            if not ack_answer.want_FIN():
                final_pack = self.acks_queue.get()
            else:
                final_pack = ack_answer
            if final_pack.want_FIN():
                answer = Package()
                self.ack_number = (self.ack_number + 1) % MAX_SEQ_NUM
                answer.set_ACK(self.ack_number + 1)
                answer.set_sequence_number(self.sequence_number % MAX_SEQ_NUM)
                self.socket.sendto(answer.packaging(), self.adress)
                self._is_connected = False
                self.socket.close()
                self.process_pack_thread.join()
                self.logger.log("[sr-close] Socket cerrado correctamente",
                                HIGH_VERBOSITY)
                return True

    def __end_connection(self):

        ack_fin = Package()
        ack_fin.set_ACK(self.ack_number)
        ack_fin.set_ACK_FLAG()
        ack_fin.set_sequence_number(self.sequence_number)
        self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
        data = ack_fin.packaging()
        self.socket.sendto(data, self.adress)

        self._is_connected = True
        retries = 0
        fin = Package()
        fin.set_FIN()
        fin.set_ACK_FLAG()

        fin.set_sequence_number(self.sequence_number)
        self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
        data = fin.packaging()

        while self._is_connected and retries < TOTAL_RETRIES:
            self.socket.sendto(data, self.adress)
            try:
                final_ack = self.acks_queue.get(timeout=1)
                if final_ack.get_ACK() == self.sequence_number:
                    self._is_connected = False
                elif final_ack.want_FIN():
                    self.socket.sendto(data, self.adress)
                else:
                    self._is_connected = False

            except queue.Empty:
                retries += 1

        self._is_connected = False

    def __send_and_wait_syn(self, package, total_retries, address):
        data = package.packaging()
        retries = 0
        while retries < total_retries:
            self.socket.sendto(data, address)
            try:

                answer = self.acks_queue.get(
                    timeout=1
                )
                if (
                    answer.get_ACK()
                    == (self.sequence_number + 1) % MAX_SEQ_NUM
                ):

                    return answer
            except queue.Empty:
                retries += 1
                if not self.connections[address].recv_queue.empty():
                    break

        return None

    def _client_send_and_wait_syn(self, package, total_retries, address):
        data = package.packaging()
        self.socket.settimeout(1.0)
        retries = 0
        while retries < total_retries:
            self.socket.sendto(data, address)
            try:
                answer = self.acks_queue.get(timeout=1)
                if (
                    answer.get_ACK()
                    == (self.sequence_number + 1) % MAX_SEQ_NUM
                ):
                    self.socket.settimeout(None)
                    return answer
                    retries += 1
                if answer.want_FIN():
                    self.socket.settimeout(None)
                    return answer
            except queue.Empty:
                retries += 1

        self.socket.settimeout(None)
        return None

    def is_closed(self):
        if not self._is_connected:
            return True
        return False
