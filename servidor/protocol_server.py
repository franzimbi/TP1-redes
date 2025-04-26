import socket
import protocol_server

class ProtocolServer:
    def __init__(self, conection):
        self.socket = conection

    def recv_service_option(self):
        
        data = self.socket.recv(1024)
        
    def recv_file(self, file):
        data_bytes = self.socket.recv_all()
        size_file = int.from_bytes(data_bytes[:32], byteorder='big')
        print(f"File size: {size_file} bytes")
        with open(file, 'wb') as f:
            for _ in range(int(size_file)):
                data = self.socket.recv(1024)
                if not data:
                    break
                f.write(data)
        print(f"File {file} received successfully.")


    def close(self):
        if not self.socket.is_closed():
            self.socket.close()