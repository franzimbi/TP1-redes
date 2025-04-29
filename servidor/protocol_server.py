import socket
import protocol_server
import os
from common.logger import Logger

class ProtocolServer:
    def __init__(self, conection, logger):
        self.socket = conection
        self.logger = logger


    def recv_option(self):
        data = self.socket.recv(1).decode('utf-8')
        return data
        
    def recv_file(self, path):
        #recibo el  name
        name_size = self.socket.recv(32)
        name_size = int.from_bytes(name_size, byteorder='big')
        name = self.socket.recv(name_size).decode('utf-8')
        self.logger.log(f"[server_protocol]: recibiendo archivo {name}", 0)
        # recibo el tamanio del archivo
        data_bytes = self.socket.recv(32)
        size_file = int.from_bytes(data_bytes, byteorder='big')
        self.logger.log(f"[server_protocol]: archivo {name} tiene tamanio {size_file}", 1)
        # recibo el archivo
        path_complete = os.path.join(path, name)
        # Verifico si el directorio existe
        if not os.path.exists(path):
            self.logger.log("el path donde guardar no existe", 0)
            return
        self.logger.log(f"[server_protocol]: el path al archivo {name}: {size_file} existe", 1)
        with open(path_complete, 'wb') as f:
            self.logger.log(f"[server_protocol]: creando el archivo {path_complete} y recibiendo", 1)
            for _ in range(int(size_file)):
                data = self.socket.recv(1024)
                if not data:
                    break
                f.write(data)
        f.close()
        self.logger.log(f"[server_protocol]: archivo {name} recibido correctamente", 1)

    def send_file(self, path):
        # recibo el file name
        file_name_size = self.socket.recv(32)
        file_name_size = int.from_bytes(file_name_size, byteorder='big')
        file = self.socket.recv(file_name_size).decode('utf-8')
        self.logger.log(f"[server_protocol]: enviando archivo {file}", 1)

        file = os.path.join(path, file)
        if not os.path.isfile(file):
            self.logger.log(f"[server_protocol]: el archivo {file} no existe", 0)
            return
        # mando size del archivo
        size_file = os.path.getsize(file).to_bytes(32, byteorder='big')
        self.logger.log(f"[server_protocol]: el archivo {file} tiene tamanio {size_file}", 1)
        self.socket.send(size_file)
        # mando el archivo
        self.logger.log(f"[server_protocol]: enviando el archivo {file}", 1)
        with open(file, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.socket.sendall(chunk)
        f.close()
        self.logger.log(f"[server_protocol]: archivo {file} enviado correctamente", 1)
        
    def close(self):
        if not self.socket.is_closed():
            self.logger.log("[server_protocol]: cerrando socket", 1)
            self.socket.close()