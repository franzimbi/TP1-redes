import socket
from protocol_server import ProtocolServer
from common.socket_rdt_sw import SocketRDT_SW

BUFFER = 1024

# __MAIN__
skt = SocketRDT_SW("localhost", 8081)
skt.bind()

skt.listen(1)
conn, addr = skt.accept()
print(f"Conexión establecida con {addr}")

proto = ProtocolServer(conn)
proto.recv_file("archivo.txt")