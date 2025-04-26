import socket

class Hanlder:
    IP_ADDR = "localhost"
    PORT_ADDR = 8081


    def __init__(self, ip= IP_ADDR, port = PORT_ADDR, rdt_protocol= PROTOCOL_SKT):
        self.skt = socket(AF_INET, SOCK_DGRAM)
        self.sckt.bind((ip, port))
        self.ip = ip
        self.port = port
        self.rdt_protocol = rdt_protocol

    def get_socket(self):
        if self.rdt_protocol = "STOP_AND_WAIT"
            return SocketRDT_SW(self.ip, self.port)
        return SocketRDT_SR(self.ip,self.port)
        
        