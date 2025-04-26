from protocol_client import ProtocolClient
# import socket
from common.socket_rdt_sw import SocketRDT_SW

#__main__
skt = SocketRDT_SW('localhost', 8080)
skt.connect()

protocol = ProtocolClient('U', skt)
protocol.send_data_message("./archivo_prueba.txt")
