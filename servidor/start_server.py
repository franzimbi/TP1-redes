import socket
from protocol_server import ProtocolServer
# from common.socket_rdt_sw import SocketRDT_SW

BUFFER = 1024

# __MAIN__
skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# skt = socket.socket("localhost", 8081)
skt.bind(("localhost", 8080))

skt.listen(5)
conn, addr = skt.accept()

proto = ProtocolServer(conn)

option = proto.recv_service_option()
if option == 'U':
    print("Option U selected")
    proto.recv_file()
elif option == 'D':
    proto.send_file("./archivo_prueba.txt")
else:
    print("Invalid option received.")
conn.close()
skt.close()