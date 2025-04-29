import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.messages import MessageInit
from common.messages import MessageData

CHUNK_SIZE = 1024


class ProtocolClient:
    def __init__(self, type, connection):
        self.connection = connection
        self.type = type

    
    def send_start_message(self):
        self.connection.sendall(self.type.encode())

    def send_file(self, path, file):
        # mando name
        self.connection.sendall(len(file).to_bytes(32, byteorder='big'))
        self.connection.sendall(file.encode('utf-8'))
        # mando size del archivo
        file_complete = os.path.join(path, file)
        if not os.path.isfile(file_complete):
            print(f"archivo {file_complete} no encontrado")
            return
        size_file = os.path.getsize(file_complete).to_bytes(32, byteorder='big')
        self.connection.send(size_file)
        # mando el archivo
        with open(file_complete, 'rb') as f:
            while True:
                print(f"enviando chunk de archivo")
                chunk = f.read(1024)
                if not chunk:
                    break
                self.connection.sendall(chunk)
        # close the file
        f.close()
        print(f"archivo entero mandado: {file_complete}")

    def recv_file(self, path, file):
        # envio el file name
        self.connection.sendall(len(file).to_bytes(32, byteorder='big'))
        self.connection.sendall(file.encode('utf-8'))
        # recibo el tamanio del archivo
        data_bytes = self.connection.recv(32)
        size_file = int.from_bytes(data_bytes, byteorder='big')
        # recibo el archivo
        file_complete = os.path.join(path, file)
        if not os.path.exists(path):
            print(f"directorio {path} no encontrado")
            return
        with open(file_complete, 'wb') as f:
            for _ in range(int(size_file)):
                print(f"recibiendo chunk de archivo")
                chunk = self.connection.recv(1024)
                if not chunk:
                    break
                f.write(chunk)
        f.close()
        print(f"archivo entero recibido: {file_complete}")