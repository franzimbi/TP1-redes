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
    

    # def __init__(self):
    #     self.sequence_number = np.uint16(0)
    #     self.ack_number = np.uint16(0)
    #     self.header_length = np.uint16(0)
    #     self.SYN = np.uint8(0)  
    #     self.FIN = np.uint8(0) 
    #     self.data_length = np.uint32(0)
    #     # self.window_size = 0
    #     self.data = None

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
    
    def decode_to_package(data):
        package = Package()
        package.sequence_number = int.from_bytes(data[0:2], byteorder='big')
        package.ack_number = int.from_bytes(data[2:4], byteorder='big')
        package.header_length = int.from_bytes(data[4:6], byteorder='big')
        package.SYN = int.from_bytes(data[6:7], byteorder='big')
        package.FIN = int.from_bytes(data[7:8], byteorder='big')
        package.data_length = int.from_bytes(data[8:12], byteorder='big')
        package.data = data[12:12 + package.data_length].decode('utf-8')
        return package

    def __str__(self):
        print("----- HEADER CONTENT -----")
        print(f"Sequence Number: {self.sequence_number}")
        print(f"Ack Number:      {self.ack_number}")
        print(f"Header Length:   {self.header_length}")
        print(f"SYN Flag:        {self.SYN}")
        print(f"FIN Flag:        {self.FIN}")
        print(f"Data Length:     {self.data_length}")
        print(f"Data:            {self.data}")
        print("--------------------------")

# header udp
# header nuestro
# data