import protocol_server

class Client:
    def __init__(self, skt):
        self.skt = skt  
        self.is_alive = True
        self.protocol = None
        self.thread = None

    def start(self):
        self.protocol = ProtocolServer(self.skt)
        self.thread = t.Thread(target=self._start_connection)
        self.thread.start() 

    def stop(self):
        self.is_alive = False
        self.protocol.close()
    
    def join(self):
        self.thread.join()

    def is_dead(self):
        if not self.is_alive:
            return True
        return False