import threading
import argparse
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.socket_rdt_sw import SocketRDT_SW  # noqa: E402
from common.socket_rdt_sr import SocketRDT_SR  # noqa: E402
from common.logger import Logger, NORMAL_VERBOSITY  # noqa: E402
from common.logger import HIGH_VERBOSITY  # noqa: E402
from common.logger import LOW_VERBOSITY  # noqa: E402
from protocol_client import ProtocolClient  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(
        description="Servidor de almacenamiento y descarga de archivos."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=NORMAL_VERBOSITY,
        help="full output verbosity",
    )
    group.add_argument(
        "-q", "--quiet", action="store_true", help="no verbosity"
    )

    parser.add_argument(
        "-H", "--host", type=str, default="127.0.0.1", help="server IP address"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="server port"
    )
    parser.add_argument(
        "-d", "--dst", type=str, required=True, help="destination file path"
    )
    parser.add_argument(
        "-n", "--name", type=str, required=True, help="file name"
    )
    parser.add_argument(
        "-r",
        "--protocol",
        type=str,
        choices=["sw", "sr"],
        required=True,
        help="error recovery protocol",
    )

    return parser.parse_args()


def recv_loop(socket_principal):
    while socket_principal.keep_running:
        socket_principal.recv_all()


# __main__
args = parse_args()
logger = Logger("[DOWNLOAD]")
start = time.time()
if args.verbose > NORMAL_VERBOSITY:
    logger.set_log_level(HIGH_VERBOSITY)
if args.quiet:
    logger.set_log_level(LOW_VERBOSITY)

skt = None
if args.protocol == "sr":
    print("host es: ", args.host)
    print("port es: ", args.port)
    skt = SocketRDT_SR(args.host, args.port, logger)

elif args.protocol == "sw":
    skt = SocketRDT_SW(logger)
try: 
    if args.protocol == "sr":
        recv_thread = threading.Thread(target=recv_loop, args=(skt,))
        recv_thread.start()
        skt.connect()
    else:
        skt.connect((args.host, args.port))
    logger.log(f"Arrancando cliente en: ({args.host}:{args.port})", HIGH_VERBOSITY)
    protocol = ProtocolClient("D", skt, logger)

    protocol.send_start_message()
    protocol.recv_file(args.dst, args.name)
except Exception:
    logger.log(f"Error al conectar", NORMAL_VERBOSITY)
finally:

    skt.close()

    if args.protocol == "sr":
        skt.keep_running = False
        print("hice keep_running = False")
        recv_thread.join()
        print("hice join de recv_thread")

    logger.log("Fin del cliente download", NORMAL_VERBOSITY)
    end = time.time()
    print(f"La función tardó {end - start:.4f} segundos")
