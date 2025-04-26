from protocol_server import ProtocolServer
import threading as t


class Client:
    def __init__(self, skt):
        self.skt = skt  
        self.is_alive = True
        self.protocol = None
        self.thread = None

    def start(self):
        print("[client.py]: starting client thread")
        self.thread = t.Thread(target=self.start_connection)
        self.thread.daemon = True
        self.thread.start() 


    def start_connection(self):
        print("[client.py]: entra al thread")
        self.protocol = ProtocolServer(self.skt)
        print("[client.py]: protocol server creado")
        while self.is_alive:            
            data = self.protocol.recv_service_option()
            if data is None:
                print("[SERVIDOR] Conexión finalizada.")
                break


    def stop(self):
        print("[client.py]: stopping client thread")
        self.is_alive = False
        self.protocol.close()
    
    def join(self):
        self.thread.join()

    def is_dead(self):
        if not self.is_alive:
            return True
        return False