import socket

class ProtocolServer:
    def __init__(self, conection):
        self.socket = conection

    def recv_service_option(self):
        
        data = self.socket.recv(1024)
        

    def stop(self):
        print("Stopping server")