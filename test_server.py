import time
import threading
from common.socket_rdt_sw import SocketRDT_SW

# Contador global de conexiones
connection_counter = 0
connection_lock = threading.Lock()

def handle_client(skt, client_address, thread_id):
    print(f"[THREAD-{thread_id}] Esperando archivo de {client_address}...")

    file_data = b''
    while True:
        try:
            data = skt.recv(1035)
            if data == b'__END__':
                break
            file_data += data
        except Exception as e:
            print(f"[THREAD-{thread_id}] Error al recibir: {e}")
            break

    filename = f"archivo_recibido_{thread_id}.jpg"
    with open(filename, "wb") as f:
        f.write(file_data)

    print(f"[THREAD-{thread_id}] Archivo recibido y guardado en {filename}")
    skt.close()

def run_server():
    global connection_counter
    rdt = SocketRDT_SW()
    rdt.bind(('10.0.0.2', 12345))
    rdt.listen(5)

    print("[SERVER] Esperando conexiones...")

    while True:
        skt, address = rdt.accept()

        if skt is None:
            print("[SERVER] Error al aceptar conexión.")
            continue

        # Asignar ID de thread único
        with connection_lock:
            connection_counter += 1
            thread_id = connection_counter

        client_thread = threading.Thread(target=handle_client, args=(skt, address, thread_id))
        client_thread.start()

if __name__ == "__main__":
    run_server()
