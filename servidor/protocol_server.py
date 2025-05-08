import os
from common.logger import NORMAL_VERBOSITY, HIGH_VERBOSITY


class ProtocolServer:
    def __init__(self, conection, logger):
        self.socket = conection
        self.logger = logger

    def recv_option(self):
        data = self.socket.recv(1).decode("utf-8")
        return data

    def recv_file(self, path):
        # recibo el  name
        name_size = self.socket.recv(32)
        name_size = int.from_bytes(name_size, byteorder="big")
        name = self.socket.recv(name_size).decode("utf-8")
        self.logger.log(
            f"[server_protocol]: recibi nombre de archivo {name}",
            HIGH_VERBOSITY,
        )
        # recibo el tamanio del archivo
        data_bytes = self.socket.recv(32)
        size_file = int.from_bytes(data_bytes, byteorder="big")
        self.logger.log(
            f"[server_protocol]: archivo {name} tiene tamanio {size_file}",
            HIGH_VERBOSITY,
        )
        # recibo el archivo
        path_complete = os.path.join(path, name)
        # Verifico si el directorio existe
        if not os.path.exists(path):
            self.logger.log(
                "el path donde guardar no existe", NORMAL_VERBOSITY
            )
            return
        self.logger.log(
            f"[server_protocol]: el path al archivo {name}: {size_file} existe",   # noqa: E501
            HIGH_VERBOSITY,
        )
        with open(path_complete, "wb") as f:
            self.logger.log(
                f"[server_protocol]: creando el archivo {path_complete} y recibiendo",   # noqa: E501
                NORMAL_VERBOSITY,
            )
            size = 0
            if ((size_file / 1024) % 2) == 0:
                size = int(size_file / 1024)
            else:
                size = int(size_file / 1024) + 1
            for j in range(size):
                data = self.socket.recv(1024)
                f.write(data)
        f.close()
        self.logger.log(
            f"[server_protocol]: archivo {name} recibido correctamente",
            NORMAL_VERBOSITY,
        )

    def send_file(self, path):
        # recibo el file name
        file_name_size = self.socket.recv(32)
        file_name_size = int.from_bytes(file_name_size, byteorder="big")
        file = self.socket.recv(file_name_size).decode("utf-8")
        self.logger.log(
            f"[server_protocol]: enviando archivo {file}", HIGH_VERBOSITY
        )

        file = os.path.join(path, file)
        if not os.path.isfile(file):
            self.logger.log(
                f"[server_protocol]: el archivo {file} no existe",
                NORMAL_VERBOSITY,
            )
            return
        # mando size del archivo
        size_file = os.path.getsize(file)
        size = size_file
        self.logger.log(
            f"[server_protocol]: el archivo {file} tiene tamanio {size_file}",
            HIGH_VERBOSITY,
        )
        size_file = size_file.to_bytes(32, byteorder="big")
        self.socket.sendall(size_file)
        # mando el archivo
        self.logger.log(
            f"[server_protocol]: enviando el archivo {file}", NORMAL_VERBOSITY
        )

        with open(file, "rb") as f:
            file_data = f.read()

        self.logger.log("[server_protocol] mando archivo completo", HIGH_VERBOSITY)
        self.socket.sendall(file_data)  # tu protocolo se encarga de fragmentar

        self.logger.log(
            f"[server_protocol]: archivo {file} enviado correctamente",
            NORMAL_VERBOSITY,
        )
    

    def close(self):
        if not self.socket.is_closed():
            self.logger.log(
                "[server_protocol]: cerrando socket", HIGH_VERBOSITY
            )
            self.socket.close()
