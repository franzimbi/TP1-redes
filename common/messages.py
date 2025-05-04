class MessageInit:
    def __init__(self, type, path, file_name):
        self.type = type
        self.path = path
        self.file_name = file_name

    def encode(self):
        bytes = b""
        bytes += self.type.encode()  # si es upload o download el mensaje
        bytes += len(self.path).to_bytes(32, byteorder="big")
        bytes += self.path.encode()
        bytes += len(self.file_name).to_bytes(32, byteorder="big")
        bytes += self.file_name.encode()
        return bytes

    def decode(self, bytes):
        self.type = bytes[0:1].decode()
        self.path = bytes[1:33].decode()
        self.file_name = bytes[33:65].decode()


class MessageData:

    def encode_data(self, data):
        bytes = b""
        bytes += len(data).to_bytes(64, byteorder="big")
        bytes += data
        return bytes

    def encode_file(self, path):
        # to do: leer el archivo y codificarlo
        return

    def decode(self, bytes):
        return
