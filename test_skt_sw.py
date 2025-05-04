import threading
import time

from common.socket_rdt_sw import SocketRDT_SW

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5005

# Estados compartidos
server_connected = threading.Event()
client_connected = threading.Event()


def run_server():
    server = SocketRDT_SW()
    server.bind((SERVER_HOST, SERVER_PORT))
    server.accept()
    connected_clients = [
        client for client in server.clients.values() if client == True
    ]

    if len(connected_clients) == 1:
        server_connected.set()


def run_client():
    time.sleep(1)  # Esperamos al servidor
    client = SocketRDT_SW()
    client.connect((SERVER_HOST, SERVER_PORT))
    if client._is_connected:
        client_connected.set()


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    client_thread = threading.Thread(target=run_client)

    server_thread.start()
    client_thread.start()

    server_thread.join()
    client_thread.join()

    assert (
        server_connected.is_set() and client_connected.is_set()
    ), "La conexión no se estableció correctamente"
    print("✅ Test de conexión exitoso")
