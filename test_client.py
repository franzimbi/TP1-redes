import time
from common.socket_rdt_sw_copy import SocketRDT_SW

def run_client():
    rdt = SocketRDT_SW()
    server_addr = ('10.0.0.2', 12345)
    try:
        rdt.connect(server_addr)
    except Exception as e:
        print(f"[CLIENT] Error al conectar al servidor: {e}")
        return
    
    print("[CLIENT] Enviando archivo...")

    start = time.time()
    with open("cliente/storage_client/rio.jpg", "rb") as f:
        data = f.read()
        rdt.sendall(data)

    # Señal de fin de archivo
    rdt.sendall(b'__END__')
    end = time.time()
    print("[CLIENT] Archivo enviado.")
    print(f"La función tardó {end - start:.4f} segundos")
    rdt.close()

if __name__ == "__main__":
    run_client()
