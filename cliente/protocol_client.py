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

    def send_file(self, path_file):
        file = os.path.basename(path_file)
        # mando path name
        self.connection.sendall(len(file).to_bytes(32, byteorder='big'))
        self.connection.sendall(file.encode('utf-8'))
        # mando size del archivo
        size_file = os.path.getsize(path_file).to_bytes(32, byteorder='big')
        self.connection.send(size_file)
        # mando el archivo
        with open(path_file, 'rb') as f:
            while True:
                print(f"enviando chunk de archivo")
                chunk = f.read(1024)
                if not chunk:
                    break
                self.connection.sendall(chunk)
        # close the file
        f.close()
        print(f"archivo entero mandado: {path_file}")

    def recv_file(self):
        # recibo el path name
        path_size = self.connection.recv(32)
        path_size = int.from_bytes(path_size, byteorder='big')
        path_str = self.connection.recv(path_size).decode('utf-8')
        # recibo el tamanio del archivo
        data_bytes = self.connection.recv(32)
        size_file = int.from_bytes(data_bytes, byteorder='big')
        # recibo el archivo
        with open(path_str, 'wb') as f:
            for _ in range(int(size_file)):
                print(f"recibiendo chunk de archivo")
                chunk = self.connection.recv(1024)
                if not chunk:
                    break
                f.write(chunk)
        f.close()
        print(f"archivo entero recibido: {path_str}")
