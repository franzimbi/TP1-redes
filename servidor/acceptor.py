import sys
from client import Client
class Acceptor():
    
    def __init__(self, skt):
        self.skt = skt
        self.clients = []
        self._keep_running = True

    def run(self):
        try:
            while self._keep_running:
                peer = self.skt.accept()
                print(f"[acceptor.py]: Accepted connection from peer")
                client = Client(peer)
                print ("[acceptor.py]: client fue creado")
                client.start()
                print ("[acceptor.py]: client fue iniciado")
                self.clients.append(client)
                print ("[acceptor.py]: client fue agregado a la lista")
                self.reap_dead()
        except Exception as e:
            print ("[acceptor.py]: Error en el acceptor")
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
        self.skt.close_server()

    def __del__(self):
        if self.clients:
            i = 0
            for client in self.clients:
                print ("[acceptor.py]: cerrando cliente numero: ", i)
                i += 1
                client.stop()
                client.join()