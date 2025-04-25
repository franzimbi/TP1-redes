import socket

BUFFER = 1024

# __MAIN__
skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


skt.connect(('localhost', 8080))
skt.sendall(b'Hola, servidor!')
data = skt.recv(BUFFER)
print(f"Recibido: {data.decode('utf-8')}")