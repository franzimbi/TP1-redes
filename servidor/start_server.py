import socket

BUFFER = 1024

# __MAIN__
skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
skt.bind(('localhost', 8080))

skt.listen(1)
conn, addr = skt.accept()
print(f"Conexión establecida con {addr}")

data = conn.recv(BUFFER)
print(f"Recibido: {data.decode('utf-8')}")
conn.sendall(b"hola de nuevo, soy el servidor")

conn.close()    