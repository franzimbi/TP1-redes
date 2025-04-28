import argparse
from protocol_client import ProtocolClient
import socket
import sys

def parse_args():
    parser = argparse.ArgumentParser(
        description="Servidor de almacenamiento y descarga de archivos."
    )
    group = parser.add_mutually_exclusive_group()
    parser.add_argument("-v", "--verbose", action="count", default=0, help="increase output verbosity")
    parser.add_argument("-q", "--quiet", action="store_true", help="decrease output verbosity to none")
    
    parser.add_argument('-H', '--host', type=str, default="localhost", help='service IP address')
    parser.add_argument('-p', '--port', type=int, default=8080, help='service port')
    parser.add_argument('-s', '--storage', type=str, default="/", help='storage dir path')
    parser.add_argument('-r', '--protocol', type=str, choices=["sw", "sr"], default="", help='error recovery protocol')

    return parser.parse_args()


#__main__

if len(sys.argv) != 2:
    print("No se pasó ningún argumento.")

path = str(sys.argv[1])
file = str(sys.argv[2])

skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
skt.connect(("localhost", 8080))

protocol = ProtocolClient('U', skt)

protocol.send_start_message()
protocol.send_file(path, file)

skt.close()
print("Fin del cliente upload")
