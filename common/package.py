from dataclasses import dataclass
import numpy as np
import struct

MAX_SEQ_NUM = 2**16

@dataclass
class Package:

    def __init__(self):
        self.sequence_number = np.uint16(0)
        self.ack_number = np.uint16(0)
        self.SYN = np.uint8(0)
        self.FIN = np.uint8(0)
        self.ACK = np.uint8(0)
        self.data_length = np.uint32(0)
        self.data = b''

    def set_data(self, data):
        if len(data) > 2**32:
            raise ValueError("Data too long")
        self.data = data
        self.data_length = np.uint32(len(data))

    def get_data_length(self):
        return self.data_length
    
    def get_data(self):
        return self.data
    
    def packaging(self):
        header = struct.pack('>HHBBBI',  # formato
                            self.sequence_number ,
                            self.ack_number ,
                            self.SYN,
                            self.FIN,
                            self.ACK,
                            self.data_length)
        payload = self.data
        return header + payload
    
    def decode_to_package(self, data):
        self.sequence_number = int.from_bytes(data[0:2], byteorder='big')
        self.ack_number = int.from_bytes(data[2:4], byteorder='big')
        self.SYN = int.from_bytes(data[4:5], byteorder='big')
        self.FIN = int.from_bytes(data[5:6], byteorder='big')
        self.ACK = int.from_bytes(data[6:7], byteorder='big')
        self.data_length = int.from_bytes(data[7:11], byteorder='big')
        self.data = data[11:11 + self.data_length]

    def set_SYN(self):
        self.SYN = np.uint8(1)

    def want_SYN(self):
        return self.SYN == 1

    def set_ACK(self, ack_number):
        self.ack_number = ack_number

    def get_ACK(self):
        return self.ack_number

    def set_FIN(self):
        self.FIN = np.uint8(1)

    def want_FIN(self):
        return self.FIN == 1

    def set_ACK_FLAG(self):
        self.ACK = np.uint8(1)

    def want_ACK_FLAG(self):
        return self.ACK == 1

    def set_sequence_number(self, sequence_number):
        self.sequence_number = sequence_number

    def get_sequence_number(self):
        return self.sequence_number
    

    def get_ack_number(self):
        return self.ack_number

    def __str__(self):
        return (
            "\n\n----- PACKAGE CONTENT -----\n"
            f"Sequence_n: {self.sequence_number} | Ack_n: {self.ack_number} | SYN: {self.SYN} | FIN: {self.FIN} | ACK: {self.ACK} |\n"          
            f"Data Len: {self.data_length} | Data: {self.data}\n"
            "--------------------------\n\n"
        )


# header udp
# header nuestro
# data