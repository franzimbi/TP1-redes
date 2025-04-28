from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel

class SimpleTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        self.addLink(h1, h2, cls=TCLink, loss=10, delay='50ms')

def run():
    topo = SimpleTopo()
    net = Mininet(topo=topo, switch=OVSKernelSwitch, link=TCLink, controller=None)
    net.start()
    print("Red inicializada")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
