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

    
    def send_start_message(self, path, file):
        self.file = file
        start_msg = MessageInit(path, file)
        bytes = start_msg.encode()
        self.connection.send_all(bytes)
        print(f"Sent start message: {start_msg}")

    def send_data_message(self, path_file):
        print(f"PATH recibido: {path_file}")
        print(f"EXISTE? {os.path.exists(path_file)}")
        print(f"TAMAÑO: {os.path.getsize(path_file)}")
        size_file = os.path.getsize(path_file).to_bytes(32, byteorder='big')
        self.connection.send_all(size_file)
        with open(path_file, 'rb') as f:
            while True:
                print(f"enviando chunk de archivo")
                chunk = f.read(1024)
                if not chunk:
                    break
                self.connection.send_all(chunk)

        # with open(path_file, 'rb') as f:
        #     while (chunk := f.read(CHUNK_SIZE)):
        #         self.connection.sendall(chunk)
        f.close()
        print(f"archivo entero mandado: {path_file}")