from protocol_server import ProtocolServer
import threading as t


class Client:
    def __init__(self, skt):
        self.skt = skt  
        self.is_alive = True
        self.protocol = None
        self.thread = None

    def start(self):
        self.thread = t.Thread(target=self.start_connection)


    def start_connection(self):
        self.thread.start() 
        self.protocol = ProtocolServer(self.skt)


    def stop(self):
        self.is_alive = False
        self.protocol.close()
    
    def join(self):
        self.thread.join()

    def is_dead(self):
        if not self.is_alive:
            return True
        return False