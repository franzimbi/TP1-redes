from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import OVSController
from mininet.log import setLogLevel
from mininet.cli import CLI
import subprocess

class LinealTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        self.addLink(h1, s1)
        self.addLink(s1, s2)
        self.addLink(s2, s3)
        self.addLink(s3, h2)

def run():
    topo = LinealTopo()
    net = Mininet(topo=topo, controller=OVSController, link=TCLink)
    net.start()

    h1, h2 = net.get('h1', 'h2')

    print("[+] Asignando IPs IPv4...")
    h1.setIP('10.0.0.1/24')
    h2.setIP('10.0.0.2/24')

    print("[+] Desactivando IPv6 en h1 y h2...")
    for h in [h1, h2]:
        h.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1')
        h.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1')


    print("[+] Bajando MTU de s2-eth2 a 500 bytes...")
    s2 = net.get('s2')
    s2.cmd('ifconfig s2-eth2 mtu 500')

    print("[+] Configurando pérdida del 10% en s3-eth2...")
    s3 = net.get('s3')
    s3.cmd('tc qdisc add dev s3-eth2 root netem loss 10%')

    print("[+] Iniciando tcpdump en h2...")
    h2.cmd('tcpdump -i h2-eth0 -w captura_h2.pcap &')

    subprocess.Popen(['wireshark'])
    input("Wireshark abierto. Elegí la interfaz (ej: h2-eth0) y empezá a capturar. Presioná Enter para continuar...")

    print("[+] Iniciando servidor UDP en h2 con iperf...")
    h2.cmd('iperf -s -u > iperf_server.txt &')

    print("[+] Ejecutando cliente UDP en h1 (paquetes de 1400 bytes)...")
    h1.cmd('iperf -c 10.0.0.2 -u -l 1400 -t 10 > iperf_client.txt')

    print("[+] Esperando a que termine la captura...")
    h2.cmd('sleep 2')
    h2.cmd('pkill tcpdump')
    h2.cmd('pkill iperf')

    print("[+] Archivos generados:")
    print(" - iperf_client.txt")
    print(" - iperf_server.txt")
    print(" - captura_h2.pcap")

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
