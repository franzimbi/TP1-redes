import queue
import random
import socket
import threading  # si, lo vamos a usar
import time


from common.package import Package
from common.logger import LOW_VERBOSITY, HIGH_VERBOSITY

# TIMEOUT = 0.005 # segundos
MAX_PACKAGE_SIZE = 1035
HEADER_SIZE = 13  # confirmar esto
TOTAL_RETRIES = 5
WINDOW_SIZE = 5
MAX_SEQ_NUM = 2**16 - 1

# HAY Q HACER UN TIMEOUT SI NO RECIBE MAS MENSAJES DESP DE
# CIERTO TIEMPO PARA QUE CORTE LA CONEXION Y SE DESPIDA
# si el cleinte falla el client tengo q catchear la excpcion y cerrar el
# socket | mjuli no tiene fe de q arregle esto


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
        self.recv_queue = (
            queue.Queue()
        )  # queue con get() bloqueante para que el hilo no sea un busyloop
        self.SYN_queue = queue.Queue()
        self.acks_queue = queue.Queue()

        self.keep_running = True
        self.process_pack_thread = None  # se asigna desp
        # queue para los datos recibidos y procesados para sacarlos de a bytes
        self.data_queue = (queue.Queue())

        self._estimated_rtt = None
        self._dev_rtt = 0
        self._timeout = 0.05  # Valor inicial
        self._alpha = 0.125
        self._beta = 0.25
        self.send_times = {}

        self.process_pack_thread = None

    def __del__(self):
        self.keep_running = False
        if self.process_pack_thread is not None:
            self.process_pack_thread.join()


    def bind(self):
        self.socket.bind(self.adress)
        self.logger.log(f"[sr-bind] Escuchando en {self.adress}", LOW_VERBOSITY)


    def close_server(self):
        self.keep_running = False
        self.socket.close()
        print("[SR.SERVIDOR] Socket cerrado correctamente")

    # def _mod_seq(self, num):
    #     return num % MAX_SEQ_NUM

    # def get_adress(self):
    #     return self.adress

    # def close_client(self, adress):
    #     if adress in self.connections:
    #         del self.connections[adress]
    #         print(
    #             f"[SR.SERVIDOR] Socket cliente {adress} cerrado correctamente"
    #         )
    #     else:
    #         print(f"[SR.SERVIDOR] Socket cliente {adress} no encontrado")

    def listen(self, n_connections):
        self.logger.log( "[sr-listen] Escuchando conexiones", LOW_VERBOSITY)
       

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
        # eliminar conexiones muertas
        for addr, conn in list(self.connections.items()):
            if not conn._is_connected:
                del self.connections[addr]
            # else:
            #     print(f"[SR.SERVIDOR] Conexión con {addr} activa")

    def accept(self):
        while self.keep_running:
            self.logger.log("[sr-accept] Esperando conexiones", LOW_VERBOSITY)
            self.reap_dead_connections()

            data_syn, addr_syn = (
                self.SYN_queue.get()
            )  # bloqueante, evita busyloop

            pack_syn = Package()
            pack_syn.decode_to_package(data_syn)

            if pack_syn.want_SYN():  # si es syn le mando mi SN y el ack
                self.logger.log(
                    f"[sr-accept] Paquete SYN recibido de {addr_syn}",HIGH_VERBOSITY)
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
                )  # solo referencia, NO se crea otro
                new_socket.logger = self.logger
                new_socket.adress = addr_syn  # dirección del cliente asociado
                new_socket._is_connected = True

                new_socket.sequence_number = (
                    self.sequence_number + 1
                ) % MAX_SEQ_NUM
                # antes estaba en 0, dep d q ande pruebo esto->
                # (pack_syn.get_sequence_number() + 1) % MAX_SEQ_NUM
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

                new_socket._estimated_rtt = None
                new_socket._dev_rtt = 0
                new_socket._timeout = 0.05  # Valor inicial
                new_socket._alpha = 0.125
                new_socket._beta = 0.25
                new_socket.send_times = {}
                self.connections[addr_syn] = new_socket

                # enviar SYN+ACK y esperar ACK final
                self.__send_and_wait_syn(answer_syn, TOTAL_RETRIES, addr_syn)
                self.logger.log(
                    f"[sr-accept] Nueva conexión aceptada de {addr_syn}", LOW_VERBOSITY)
                new_socket.process_pack_thread.start()
                return new_socket, addr_syn
            # del self.connections[addr_syn]
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
                f"[sr-connect] Recibido SYN+ACK de {self.adress}", HIGH_VERBOSITY)
            final_ack = Package()
            final_ack.set_ACK(self.ack_number)
            final_ack.set_ACK_FLAG()
            final_ack.set_sequence_number(
                (self.sequence_number + 1) % MAX_SEQ_NUM
            )
           
            self.socket.sendto(final_ack.packaging(), self.adress)
            self._is_connected = True

            #Inicializar correctamente para el envío de datos
            
            self.send_base = (self.sequence_number + 1) % MAX_SEQ_NUM
            self.recv_base = (
                answer_connect.get_sequence_number() + 1
            ) % MAX_SEQ_NUM

            self.next_seq_number = self.send_base
            self.logger.log("[sr-connect] Enviando base de ventana: {self.send_base}", LOW_VERBOSITY)

        if answer_connect is None:
            self.logger.log("[sr-connect] Timeout esperando SYN+ACK", HIGH_VERBOSITY)
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

    def sendall(self, data):
        if not self._is_connected:
            raise Exception("Socket no conectado")

        total_size = len(data)
        offset = 0
        chunk_size = 1024
        window_chunk_size = chunk_size * WINDOW_SIZE

        while offset < total_size:
            if (
                self.send_base
                <= self.next_seq_number + chunk_size
                < self.send_base + window_chunk_size
            ):
                data_chunk = data[offset: offset + chunk_size]

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

        # FIX: Corrección de aumento de sequence number
        self.next_seq_number = (self.next_seq_number + len(data)) % MAX_SEQ_NUM

        self.send_times[self.next_seq_number] = (
            time.time()
        )  # me guardo el time de envio
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

        # guardar hilo en diccionario de hilos
        self.thrds[self.next_seq_number] = thrd

    def _check_ACKs(self):
        pack = self.acks_queue.get()
        pack_ack = pack.get_ack_number()
        if pack_ack in self.thrds:
            sample_rtt = time.time() - self.send_times[pack_ack]
            self._update_timeout(sample_rtt)

            # parar el hilo especifico
            self.stop_events[pack_ack].set()
            self.thrds[pack_ack].join()

            len_pack_thrd = self.shared_lenghts[pack_ack][0]
            self._delete_thrd(pack_ack)
            numerito = (pack_ack - len_pack_thrd + MAX_SEQ_NUM) % MAX_SEQ_NUM
            self.packages_acked[numerito] = len_pack_thrd

            while self.send_base in self.packages_acked:
                lenght = self.packages_acked[self.send_base]

                del self.packages_acked[self.send_base]
                # FIX: Avanzar la base con modulo
                self.send_base = (self.send_base + lenght) % MAX_SEQ_NUM

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
        # reenviar el paquete
        self.socket.sendto(paquete.packaging(), self.adress)


    def recv_all(self):

        if not self._is_connected:
            #self.logger.log("[SR.RECV] Socket no conectado", LOW_VERBOSITY)
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
            self.logger.log("[sr-recv_all] Paquete SYN recibido", HIGH_VERBOSITY)
            self.SYN_queue.put((recived_bytes, sender_adress))
        # else:
        #     print(
        #         f"[SR.RECV] Ignoro el paquete con seq_number {pack.get_sequence_number()} y con el flag de SYN {pack.want_SYN()}"   # noqa: E501
        #     )
        return None

    def process_package(self):

        while self._is_connected:
            try:
                pack = self.recv_queue.get(timeout=2)  # espera 2 segundos
                seq_num = pack.get_sequence_number()
                data = pack.get_data()
            except queue.Empty:
                continue  # volver a chequear self.keep_running

            # verificar si el paquete es FIN
            if pack.want_FIN():
                self.logger.log("[sr-recv_all] Paquete FIN recibido", LOW_VERBOSITY)
                self.ack_number = (
                    pack.get_sequence_number() + 1
                ) % MAX_SEQ_NUM
                self.__end_connection()
                return None

            # si el paquete esta dentro de la ventana de recepcion
            if self.in_window(self.recv_base, seq_num, WINDOW_SIZE * 1024):
                # almacenar el paquete en el buffer si esta dentro de la
                # ventana
                self.recv_buffer[seq_num] = data

                # enviar ACK para el siguiente paquete esperado
                ack_seq = (
                    seq_num + len(data)
                ) % MAX_SEQ_NUM  # el siguiente paquete esperado
                answer = Package()
                answer.set_ACK(ack_seq)
                answer.set_ACK_FLAG()
                answer.set_sequence_number(self.sequence_number % MAX_SEQ_NUM)
                # esto es thread safe, no hay problema que todos le hablen a la
                # misma isntancia de socketUDP
                self.socket.sendto(answer.packaging(), self.adress)
                # procesar paquetes en orden (si estan disponibles)
                while self.recv_base in self.recv_buffer:
                    # aca se puede procesar el paquete
                    data = self.recv_buffer[self.recv_base]

                    # guardar el paquete en la cola de datos
                    for b in data:
                        self.data_queue.put(b)
                    # eliminar del buffer
                    del self.recv_buffer[self.recv_base]

                    # avanzar la ventana
                    # print("recv base antes: ", self.recv_base)
                    self.recv_base = (self.recv_base + len(data)) % MAX_SEQ_NUM
                    # print(
                    #     f"[SR.PROCESS_PACK] Avanzo la ventana a {self.recv_base}"  # noqa: E501
                    # )
            # si me llego un seq_num menor, reenvio el ACK pq quizas el otro no
            # recibio mi ACK anterior
            else:
                # Reenviar ACK
                ack_seq = (
                    seq_num + len(data)
                ) % MAX_SEQ_NUM  # el próximo paquete que esperás
                answer = Package()
                answer.set_ACK(ack_seq)
                answer.set_ACK_FLAG()
                answer.set_sequence_number(self.sequence_number % MAX_SEQ_NUM)
                # esto es thread safe, no hay problema que todos le hablen a la
                # misma isntancia de socketUDP
                self.socket.sendto(answer.packaging(), self.adress)
                # print(
                #     f"[SR.PROCESS_PACK] Reenviando ACK para seq {ack_seq} (paquete duplicado con seq {seq_num})"  # noqa: E501
                # )
            # ignorar el paquete si esta afuera de la ventana

    @staticmethod
    def in_window(base, seq, window_size):
        # FIX: Comparación modular
        return (seq - base) % MAX_SEQ_NUM < window_size

    def recv(self, n_bytes):
        result = bytearray()
        # print(f"[SR.RECV de fran] Recibiendo {n_bytes} bytes")
        for _ in range(n_bytes):
            byte = self.data_queue.get()  # bloquea hasta que haya un byte
            result.append(byte)
        return bytes(result)

    def close(self):
        # print("[close()] Esperando que terminen los hilos de retransmisión...")
        while self.thrds:
            try:
                self._check_ACKs()
            except queue.Empty:
                pass
        self.logger.log("[sr-close] Todos los hilos terminaron. Procediendo con el cierre", LOW_VERBOSITY)

        # vaciar recv_queue de ACKs redundantes
        while True:
            try:
                self.acks_queue.get_nowait()
            except queue.Empty:
                break

        fin = Package()
        fin.set_FIN()
        # print("[close()]---self.sequence_number---", self.sequence_number)
        fin.set_sequence_number(self.sequence_number)
        # print("[close()]---FIN con seq---", fin.get_sequence_number())

        ack_answer = self._client_send_and_wait_syn(
            fin, TOTAL_RETRIES, self.adress
        )
        if ack_answer is not None:
            # print("[close()] espero el FIN del server")
            if not ack_answer.want_FIN():
                final_pack = self.acks_queue.get()
            else:
                final_pack = ack_answer
            if final_pack.want_FIN():
                print(
                    "[close()]---FIN del server--- SEQ: ",
                    final_pack.get_sequence_number(),
                )
                print(
                    "[close()]---FIN del server--- ACK: ", final_pack.get_ACK()
                )
                answer = Package()
                self.ack_number = (self.ack_number + 1) % MAX_SEQ_NUM
                answer.set_ACK(self.ack_number + 1)
                answer.set_sequence_number(self.sequence_number % MAX_SEQ_NUM)
                print(
                    "[close()]---ANSWER al FIN con seq---",
                    answer.get_sequence_number(),
                )
                print("[close()]---ANSWER al FIN con ack---", answer.get_ACK())
                self.socket.sendto(answer.packaging(), self.adress)
                self._is_connected = False
                self.socket.close()
                # print("[close()] Socket cerrado correctamente")
                self.process_pack_thread.join() 
                self.logger.log("[sr-close] Socket cerrado correctamente", HIGH_VERBOSITY)
                return True

    def __end_connection(self):

        print("[close()] Esperando que terminen los hilos de retransmisión...")
        while self.thrds:
            try:
                self._check_ACKs()
            except queue.Empty:
                pass
        print(
            "[close()] Todos los hilos terminaron. Procediendo con el cierre."
        )

        while True:
            try:
                self.acks_queue.get_nowait()
            except queue.Empty:
                break

        print("[SERVER.END CONEXION] Entre a terminar la conexion")
        ack_fin = Package()
        ack_fin.set_ACK(self.ack_number)
        ack_fin.set_ACK_FLAG()
        ack_fin.set_sequence_number(self.sequence_number)
        self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
        data = ack_fin.packaging()
        self.socket.sendto(data, self.adress)
        print(
            "[SERVER.END CONEXION] Mande package con ACK "
            + str(ack_fin.get_ACK())
        )

        # mando el fin ahora
        self._is_connected = True
        retries = 0
        fin = Package()
        fin.set_FIN()
        fin.set_ACK_FLAG()

        fin.set_sequence_number(self.sequence_number)
        self.sequence_number = (self.sequence_number + 1) % MAX_SEQ_NUM
        data = fin.packaging()

        while self._is_connected and retries < TOTAL_RETRIES:
            print(
                "[SERVER.END CONEXION] Envie fin con SEQ NUMBER "
                + str(self.sequence_number)
            )
            self.socket.sendto(data, self.adress)
            try:
                # espera de ACK en el buffer personal, no en el socket
                print("[SR.END_CONN] INTENTO RECIBIR ACK FINAL")
                # bloqueante con timeout ojo aca ahora no estaria recibiendo el
                # fin en esta acksqueue
                final_ack = self.acks_queue.get(timeout=1)
                if final_ack.get_ACK() == self.sequence_number:
                    self._is_connected = False
                    print("[SR.END_CONN] ACK final recibido correctamente")
                elif final_ack.want_FIN():
                    self.socket.sendto(data, self.adress)
                    print(
                        "[SERVER.END CONEXION] Mande package con ACK "
                        + str(ack_fin.get_ACK())
                    )
                else:
                    self._is_connected = False
                    # print(
                    #     "[SERVER.END_CONN] ACK inválido en cierre de conexión SEQ: "  # noqa: E501
                    #     + str(final_ack.get_sequence_number())
                    #     + " ACK: "
                    #     + str(final_ack.get_ACK())
                    # )
            except queue.Empty:
                retries += 1
                print(
                    "[SR.END_CONN] Timeout esperando el ACK final del FIN, reintentando...... " +  # noqa: E501
                    str(retries))

        self._is_connected = False
        print("[SERVER.END CONEXION] Termino el cierre de la conexion")
        # OJO, ver si aca o en otro lado tengo q cerrar threads q controlan el
        # timeout d paquetes

    def __send_and_wait_syn(self, package, total_retries, address):
        # print("[SEND_AND_WAIT_SYN] ")
        data = package.packaging()
        retries = 0
        while retries < total_retries:
            self.socket.sendto(data, address)
            try:
                # print(
                #     "[SR_SENWAIT] INTENTO RECIBIR EL ACK = "
                #     + str((self.sequence_number + 1) % MAX_SEQ_NUM)
                # )
                answer = self.acks_queue.get(
                    timeout=1
                )  # espera máximo 2 segundos
                # print(
                #     "[SR_SENWAIT] RECIBO ACK con sequence number "
                #     + str(answer.get_sequence_number())
                # )
                # print(
                #     "[SR_SENWAIT] RECIBO ACK con numero "
                #     + str(answer.get_ACK())
                # )
                if (
                    answer.get_ACK()
                    == (self.sequence_number + 1) % MAX_SEQ_NUM
                ):
                    # print(
                    #     f"[SR_SENWAIT] Recibi ACK con numero {answer.get_ACK()}"  # noqa: E501
                    # )
                    return answer
            except queue.Empty:
                retries += 1
                if not self.connections[address].recv_queue.empty():
                    break
                # si sale de aca, se jodio todo, me olvido d el lo borro del
                # diccionario asi se concectra mas tarde
                # print(
                #     f"[SR_SENDWAIT] Timeout esperando ACK , reintentando... {retries}"  # noqa: E501
                # )
        return None

    def _client_send_and_wait_syn(self, package, total_retries, address):
        # print("[CLIENT_SEND_AND_WAIT_SYN] ")
        data = package.packaging()
        self.socket.settimeout(1.0)
        retries = 0
        while retries < total_retries:
            # print(
            #     "[CLIENT_SEND_AND_WAIT_SYN] INTENTO ENVIAR SYN CON SEQUENCE_NUM "  # noqa: E501
            #     + str(package.get_sequence_number())
            # )
            self.socket.sendto(data, address)
            # print("[CLIENT_SEND_AND_WAIT_SYN] ENVIE EL SYN")
            try:
                # print(
                #     "[CLIENT_SEND_AND_WAIT_SYN] INTENTO RECIBIR ACK "
                #     + str((self.sequence_number + 1) % MAX_SEQ_NUM)
                # )
                answer = self.acks_queue.get(timeout=1)
                # print(
                #     "[CLIENT_SEND_AND_WAIT_SYN] RECIBO EL ACK: "
                #     + str(answer.get_ACK())
                # )
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
                # print(
                #     f"[SR_CLIENTSENDANDWAIT] Timeout esperando ACK , reintentando... {retries}"  # noqa: E501
                # )

        self.socket.settimeout(None)
        return None

    def is_closed(self):
        if not self._is_connected:
            return True
        return False
