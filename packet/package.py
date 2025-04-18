from dataclasses import dataclass
import numpy as np
import struct

@dataclass
class Package:
    sequence_number = np.uint16(0)
    ack_number = np.uint16(0)
    header_length = np.uint16(0)
    SYN = np.uint8(0)
    FIN = np.uint8(0)
    data_length = np.uint32(0)
    data = ""

    def set_data(self, data):
        self.data = data
        self.data_length = np.uint32(len(data))

    def get_data(self):
        return self.data
    
    def packaging(self):
        header = struct.pack('>HHHBBI',  # formato
                            self.sequence_number,
                            self.ack_number,
                            self.header_length,
                            self.SYN,
                            self.FIN,
                            self.data_length)
        payload = self.data.encode('utf-8')  # <-- esto convierte el str en bytes
        return len(header + payload), header + payload
    
    def decode_to_package(self, data):
        # package = Package()
        self.sequence_number = int.from_bytes(data[0:2], byteorder='big')
        self.ack_number = int.from_bytes(data[2:4], byteorder='big')
        self.header_length = int.from_bytes(data[4:6], byteorder='big')
        self.SYN = int.from_bytes(data[6:7], byteorder='big')
        self.FIN = int.from_bytes(data[7:8], byteorder='big')
        self.data_length = int.from_bytes(data[8:12], byteorder='big')
        self.data = data[12:12 + self.data_length].decode('utf-8')


    def set_SYN(self):
        self.SYN = np.uint8(1)

    def want_SYN(self):
        return self.SYN == 1

    def set_ACK(self, ack_number):
        self.ack_number = ack_number

    def set_sequence_number(self, sequence_number):
        self.sequence_number = sequence_number

    def get_ACK(self):
        return self.ack_number

    def get_sequence_number(self):
        return self.sequence_number

    def get_ack_number(self):
        return self.ack_number

    def __str__(self):
        return (
            "----- HEADER CONTENT -----\n"
            f"Sequence Number: {self.sequence_number}\n"
            f"Ack Number:      {self.ack_number}\n"
            f"Header Length:   {self.header_length}\n"
            f"SYN Flag:        {self.SYN}\n"
            f"FIN Flag:        {self.FIN}\n"
            f"Data Length:     {self.data_length}\n"
            f"Data:            {self.data}\n"
            "--------------------------"
        )


# header udp
# header nuestro
# data