import time
from common.socket_rdt_sw_copy import SocketRDT_SW

def run_client():
    rdt = SocketRDT_SW()
    server_addr = ('localhost', 12345)
    rdt.adress = server_addr  # importante: necesitás setear `adress` antes de enviar
    rdt.connect(server_addr)

    print("[CLIENT] Enviando archivo...")

    with open("cliente/storage_client/rio.jpg", "rb") as f:
        data = f.read()
        rdt.sendall(data)

    # Señal de fin de archivo
    rdt.sendall(b'__END__')
    print("[CLIENT] Archivo enviado.")
    rdt.close()

if __name__ == "__main__":
    run_client()
