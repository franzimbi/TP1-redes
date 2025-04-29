import socket
import threading
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.logger import *
from protocol_server import ProtocolServer
import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description="Servidor de almacenamiento y descarga de archivos."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="count", default=NORMAL_VERBOSITY, help="full output verbosity")
    group.add_argument("-q", "--quiet", action="store_true", help="no verbosity")
    
    parser.add_argument('-H', '--host', type=str, default="localhost", help='service IP address')
    parser.add_argument('-p', '--port', type=int, default=8080, help='service port')
    parser.add_argument('-s', '--storage', type=str, default="/", help='storage dir path')
    parser.add_argument('-r', '--protocol', type=str, choices=["sw", "sr"], default="", help='error recovery protocol')

    return parser.parse_args()

BUFFER = 1024
shutdown_event = threading.Event()

def handle_client(conn, addr, args, logger):
    proto = ProtocolServer(conn, logger)
    try:
        option = proto.recv_option()
        if option == 'U':
            logger.log(f"[{addr}] Opcion Upload detectada", HIGH_VERBOSITY)
            proto.recv_file(args.storage)
        elif option == 'D':
            logger.log(f"[{addr}] Opcion Download detectada", HIGH_VERBOSITY)
            proto.send_file(args.storage)
        else:
            logger.log(f"[{addr}] Opcion invalida recibida", NORMAL_VERBOSITY)
    except Exception as e:
        logger.log(f"[{addr}] Error: {e}", NORMAL_VERBOSITY)
    finally:
        conn.close()
        logger.log(f"[{addr}] Conexion cerrada", HIGH_VERBOSITY)

# __MAIN__
args = parse_args()
logger = Logger("[SERVER]")
if args.verbose > 0:
    logger.set_log_level(HIGH_VERBOSITY)
if args.quiet:
    logger.set_log_level(LOW_VERBOSITY)
skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
logger.log(f"Arrancando server en: ({args.host}:{args.port})", HIGH_VERBOSITY)
skt.bind((args.host, args.port))
skt.listen(5)

while True:
    conn, addr = skt.accept()
    logger.log(f"conexion aceptada de {addr}", HIGH_VERBOSITY)
    thread = threading.Thread(target=handle_client, args=(conn, addr, args, logger))
    thread.start()
