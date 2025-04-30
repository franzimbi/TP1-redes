import time
from common.socket_rdt_sw_copy import SocketRDT_SW

def run_server():
    rdt = SocketRDT_SW()
    rdt.bind(('localhost', 12345))
    rdt.accept()

    print("[SERVER] Esperando archivo...")

    file_data = b''
    while True:
        try:
            data = rdt.recv(1035)
            if data == b'__END__':
                break
            file_data += data
        except Exception as e:
            print(f"[SERVER] Error al recibir: {e}")
            break

    with open("archivo_recibido.txt", "wb") as f:
        f.write(file_data)

    print("[SERVER] Archivo recibido y guardado.")
    rdt.close()

if __name__ == "__main__":
    run_server()
