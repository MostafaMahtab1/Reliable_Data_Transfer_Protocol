import socket
import random

probability = 0.95  # 5% packet loss or corruption.

def recv_packet(socket):
    received_data, recv_addr = socket.recvfrom(1472)
    #corrupt the packet
    if random.random()>probability:
        #Flipping one random byte to simulate corruption
        corrupt_index = random.randint(0,len(received_data)-1)
        corrupted_byte = (received_data[corrupt_index] ^ 0xFF).to_bytes(1,'big')

        received_data = received_data[:corrupt_index] + corrupted_byte + received_data[corrupt_index+1:]
    return received_data, recv_addr
def send_packet(socket,packet,recv_addr):
    #drop the packet 5% of the time
    if random.random()<probability:
        socket.sendto(packet,recv_addr)
