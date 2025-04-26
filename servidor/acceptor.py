import sys
from client import Client
class Acceptor():
    
    def __init__(self, skt):
        self.skt = skt
        self.clients = []
        self._keep_running = True

    def run(self,ip,port,mode):
        try:
            while self._keep_running:
                peer = self.skt.accept()
                print(f"[acceptor.py]: Accepted connection from peer")
                client = Client(peer)
                print ("[acceptor.py]: client fue creado")
                client.start()
                print ("[acceptor.py]: client fue iniciado")
                self.clients.append(client)
                self.reap_dead()
        except Exception as e:
            print(str(e), file=sys.stderr)

    def reap_dead(self):
        alive_clients = []
        for client in self.clients:
            if client.is_dead():
                client.stop()
                client.join()
            else:
                alive_clients.append(client)
        self.clients = alive_clients

    def shutdown(self):
        self._keep_running = False
        self.skt.close()

    def __del__(self):
        if self.clients:
            for client in self.clients:
                client.stop()
                client.join()