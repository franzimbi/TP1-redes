from common.logger import NORMAL_VERBOSITY, HIGH_VERBOSITY
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

CHUNK_SIZE = 1024


class ProtocolClient:
    def __init__(self, type, connection, logger):
        self.connection = connection
        self.type = type
        self.logger = logger

    def send_start_message(self):
        if self.type == "U":
            self.logger.log(
                "[PROTOCOL_CLIENT] enviando mensaje de upload al servidor",
                HIGH_VERBOSITY,
            )
        elif self.type == "D":
            self.logger.log(
                "[PROTOCOL_CLIENT] enviando mensaje de download al servidor",
                HIGH_VERBOSITY,
            )
        else:
            self.logger.log(
                f"[PROTOCOL_CLIENT] tipo de mensaje {self.type} no valido",
                HIGH_VERBOSITY,
            )
        self.connection.sendall(self.type.encode())

    def send_file(self, path, file):
        # mando name
        self.connection.sendall(len(file).to_bytes(32, byteorder="big"))
        self.connection.sendall(file.encode("utf-8"))
        self.logger.log(
            f"[PROTOCOL_CLIENT] mande nombre {file}", HIGH_VERBOSITY
        )
        # mando size del archivo
        file_complete = os.path.join(path, file)
        if not os.path.isfile(file_complete):
            self.logger.log(
                f"[PROTOCOL_CLIENT] archivo {file_complete} no encontrado",
                NORMAL_VERBOSITY,
            )
            return
        size_file = os.path.getsize(file_complete)
        self.logger.log(
            f"[PROTOCOL_CLIENT] archivo {file_complete} tiene tamanio {size_file}",  # noqa: E501
            HIGH_VERBOSITY,
        )
        size = size_file
        size_file = size_file.to_bytes(32, byteorder="big")
        self.connection.sendall(size_file)

        # mando el archivo
        with open(file_complete, "rb") as f:
            self.logger.log("[PROTOCOL_CLIENT] mando archivo", HIGH_VERBOSITY)

            if ((size / 1024) % 2) == 0:
                size = int(size / 1024)
            else:
                size = int(size / 1024) + 1
            print(f"enviando archivo {size}")

            for j in range(size):
                print(f"enviando chunk {j}")
                chunk = f.read(1024)
                self.connection.sendall(chunk)
        # close the file
        f.close()
        self.logger.log(
            f"[PROTOCOL_CLIENT] archivo entero mandado: {file_complete}",
            HIGH_VERBOSITY,
        )

    def recv_file(self, path, file):
        # envio el file name
        self.connection.sendall(len(file).to_bytes(32, byteorder="big"))
        self.connection.sendall(file.encode("utf-8"))
        self.logger.log(
            f"[PROTOCOL_CLIENT] mando nombre {file}", HIGH_VERBOSITY
        )
        # recibo el tamanio del archivo
        data_bytes = self.connection.recv(32)
        size_file = int.from_bytes(data_bytes, byteorder="big")
        self.logger.log(
            f"[PROTOCOL_CLIENT] recibo tamanio de {file} que es {size_file}",
            HIGH_VERBOSITY,
        )
        # recibo el archivo
        file_complete = os.path.join(path, file)
        if not os.path.exists(path):
            self.logger.log(
                f"[PROTOCOL_CLIENT] directorio {path} no encontrado",
                NORMAL_VERBOSITY,
            )
            return
        with open(file_complete, "wb") as f:
            self.logger.log(
                "[PROTOCOL_CLIENT] recibiendo archivo", HIGH_VERBOSITY
            )
            size = 0
            if (size_file / 1024) % 2 == 0:
                size = int(size_file / 1024)
            else:
                size = int(size_file / 1024) + 1
            print(f"enviando archivo {size}")

            for j in range(size):
                chunk = self.connection.recv(1024)
                f.write(chunk)
        f.close()
        self.logger.log(
            f"[PROTOCOL_CLIENT] archivo {file_complete} recibido",
            HIGH_VERBOSITY,
        )
