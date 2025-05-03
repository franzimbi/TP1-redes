from protocol_client import ProtocolClient
import socket
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.logger import *
import argparse
from common.socket_rdt_sw import SocketRDT_SW
from common.socket_rdt_sr import SocketRDT_SR
import threading

def parse_args():
    parser = argparse.ArgumentParser(
        description="Servidor de almacenamiento y descarga de archivos."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="count", default=NORMAL_VERBOSITY, help="full output verbosity")
    group.add_argument("-q", "--quiet", action="store_true", help="no verbosity")
    
    parser.add_argument('-H', '--host', type=str, default="localhost", help='service IP address')
    parser.add_argument('-p', '--port', type=int, default=8080, help='service port')
    parser.add_argument('-s', '--source', type=str, default="/", help='source file path')
    parser.add_argument('-n', '--name', type=str, default="/", help='file name')
    parser.add_argument('-r', '--protocol', type=str, choices=["sw", "sr"], default="", help='error recovery protocol')

    return parser.parse_args()

def recv_loop(socket_principal):
    while socket_principal.keep_running:
        socket_principal.recv_all()

#__main__
args = parse_args()
logger = Logger("[UPLOAD]")
if args.verbose > NORMAL_VERBOSITY:
    logger.set_log_level(HIGH_VERBOSITY)
if args.quiet:
    logger.set_log_level(LOW_VERBOSITY)

#skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
start = time.time()
skt = None
if args.protocol == "sr":
    skt = SocketRDT_SR(args.host, args.port)

elif args.protocol == "sw":
    skt = SocketRDT_SW()
else:
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

if args.protocol == "sr":
    recv_thread = threading.Thread(target=recv_loop, args=(skt,))
    recv_thread.start()
    skt.connect()
else:
    skt.connect((args.host, args.port))

logger.log(f"Arrancando cliente en: ({args.host}:{args.port})", HIGH_VERBOSITY)

protocol = ProtocolClient('U', skt, logger)

protocol.send_start_message()
protocol.send_file(args.source, args.name)

skt.close()

if args.protocol == "sr":
    skt.keep_running = False
    print ("hice keep_running = False")
    recv_thread.join()
    print ("hice join de recv_thread")

logger.log("Fin del cliente upload", NORMAL_VERBOSITY)
end = time.time()
print(f"La función tardó {end - start:.4f} segundos")
