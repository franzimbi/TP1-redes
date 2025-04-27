import socket
import protocol_server
import os

class ProtocolServer:
    def __init__(self, conection):
        self.socket = conection

    def recv_service_option(self):
        print ("[protocol_server.py]: antes del recv")
        data = self.socket.process_package()
        print ("[protocol_server.py]: despues del recv") 
        return data
        
    def recv_file(self):
        #recibo el path name
        path_size = self.socket.recv(32)
        path_size = int.from_bytes(path_size, byteorder='big')
        path_str = self.socket.recv(path_size).decode('utf-8')
        # recibo el tamanio del archivo
        data_bytes = self.socket.recv(32)
        size_file = int.from_bytes(data_bytes, byteorder='big')
        # recibo el archivo
        with open(path_str, 'wb') as f:
            for _ in range(int(size_file)):
                data = self.socket.recv(1024)
                if not data:
                    break
                f.write(data)
        f.close()
        print(f"File {path_str} received successfully.")

    def send_file(self, file_path):
        # TODO: falta poder saber q archivo quiere el download del cliente
        file = os.path.basename(file_path)
        # mando path name
        self.socket.sendall(len(file).to_bytes(32, byteorder='big'))
        self.socket.sendall(file.encode('utf-8'))
        # mando size del archivo
        size_file = os.path.getsize(file).to_bytes(32, byteorder='big')
        self.socket.send(size_file)
        # mando el archivo
        with open(file, 'rb') as f:
            while True:
                print(f"Sending file chunk")
                chunk = f.read(1024)
                if not chunk:
                    break
                self.socket.sendall(chunk)
        f.close()
        

    def close(self):
        if not self.socket.is_closed():
            self.socket.close()
