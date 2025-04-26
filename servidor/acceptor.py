import sys
import client
class Acceptor():
    
    def __init__(self, skt):
        super().__init__()
        self.skt = skt
        self.clients = []
        self._keep_running = True
        self.start()
        #self.skt_hanlder = None

    def run(self,ip,port,mode):
        try:
            while self._keep_running:
                peer = self.skt.accept()
                client = Client(peer)
                client.start()
                self.clients.append(client)
              #skt_hanlder  self.reap_dead()
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
        if self.clients_v:
            for client in self.clients_v:
                client.stop()
                client.join()