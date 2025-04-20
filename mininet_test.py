from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel

class SimpleTopo(Topo):
    def build(self):
        # Dos hosts conectados directamente
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        # Link entre ellos, podés simular pérdida/latencia
        self.addLink(h1, h2, cls=TCLink, loss=0, delay='50ms')

def run():
    topo = SimpleTopo()
    net = Mininet(topo=topo, switch=OVSKernelSwitch, link=TCLink)
    net.start()
    print("Red inicializada")

    # Levanta CLI interactiva de Mininet
    CLI(net)

    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()