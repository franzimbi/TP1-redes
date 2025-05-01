from protocol_client import ProtocolClient
import socket
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.logger import *
import argparse
from common.socket_rdt_sw_copy import SocketRDT_SW

def parse_args():
    parser = argparse.ArgumentParser(
        description="Servidor de almacenamiento y descarga de archivos."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="count", default=NORMAL_VERBOSITY, help="full output verbosity")
    group.add_argument("-q", "--quiet", action="store_true", help="no verbosity")
    
    parser.add_argument("-H", "--host", type=str, default="localhost", help="server IP address")
    parser.add_argument("-p", "--port", type=int, default=8080, help="server port")
    parser.add_argument("-d", "--dst", type=str, required=True, help="destination file path")
    parser.add_argument("-n", "--name", type=str, required=True, help="file name")
    parser.add_argument("-r", "--protocol", type=str, choices=["sw", "sr"], default="sw", help="error recovery protocol")

    return parser.parse_args()


#__main__
args = parse_args()
logger = Logger("[DOWNLOAD]")
if args.verbose > NORMAL_VERBOSITY:
    logger.set_log_level(HIGH_VERBOSITY)
if args.quiet:
    logger.set_log_level(LOW_VERBOSITY)

skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
skt.connect((args.host, args.port))
logger.log(f"Arrancando cliente en: ({args.host}:{args.port})", HIGH_VERBOSITY)

protocol = ProtocolClient('D', skt, logger)

protocol.send_start_message()
protocol.recv_file(args.dst, args.name)

skt.close()
logger.log(f"Arrancando cliente en: ({args.host}:{args.port})", NORMAL_VERBOSITY)