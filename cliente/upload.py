from protocol_client import ProtocolClient
import socket
# from common.socket_rdt_sw import SocketRDT_SW

#__main__
skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# skt = socket.socket('localhost', 8080)
skt.connect(("localhost", 8080))

protocol = ProtocolClient('U', skt)

protocol.send_start_message()
protocol.send_file("./archivo_prueba.txt")

skt.close()
print("Fin del cliente upload")
