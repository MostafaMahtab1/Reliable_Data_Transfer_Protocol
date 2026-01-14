import sys
import socket
import threading
import time
import zlib
import struct
from unreliable_channel import send_packet, recv_packet

# Constants
DATA_TYPE = 0
ACK_TYPE = 1
HEADER_FORMAT = "!IIII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_PACKET_SIZE = 1472
DATA_SIZE = MAX_PACKET_SIZE - HEADER_SIZE
TIMEOUT = 0.5

# Global state
lock = threading.Lock()
base = 0
next_seq = 0
window = []
unacked_packets = {}
dup_ack_count = {}
acknowledged = set()
finished = False
sender_socket = None
receiver_address = None
log_file = None
file_chunks = []

# Helper Functions

def calculate_checksum(packet_type, seq_num, length, data):
    temp_header = struct.pack(HEADER_FORMAT, packet_type, seq_num, length, 0)
    return zlib.crc32(temp_header + data) & 0xffffffff

def log(message):
    print(message)
    log_file.write(message + '\n')
    log_file.flush()

def create_packet(packet_type, seq_num, data=b''):
    length = len(data)
    checksum = calculate_checksum(packet_type, seq_num, length, data)
    full_header = struct.pack(HEADER_FORMAT, packet_type, seq_num, length, checksum)
    return full_header + data, checksum

def extract_packet_info(packet):
    header = packet[:HEADER_SIZE]
    data = packet[HEADER_SIZE:]
    packet_type, seq_num, length, checksum = struct.unpack(HEADER_FORMAT, header)
    calc_checksum = calculate_checksum(packet_type, seq_num, length, data)
    return packet_type, seq_num, length, checksum, calc_checksum, data

def resent_packet(seq_num):
    if seq_num in unacked_packets:
        packet, _ = unacked_packets[seq_num]
        send_packet(sender_socket, packet, receiver_address)
        unacked_packets[seq_num] = (packet, time.time())
        log(f"Retransmitting packet seqNum = {seq_num} due to timeout or triple duplicate ACK.")

# ACK Listener

def ack_listener():
    global base, finished
    while not finished:
        try:
            raw_packet, _ = recv_packet(sender_socket)
            pkt_type, seq_num, length, pkt_checksum, calc_checksum, _ = extract_packet_info(raw_packet)

            if pkt_type != ACK_TYPE:
                continue

            if pkt_checksum != calc_checksum:
                log(f"Packet received; type=ACK, seqNum={seq_num}; length={length};"
                    f"checksum_in_packet={hex(pkt_checksum)}; cheksum_calculated={hex(calc_checksum)}; status = CORRUPT")
                continue

            log(f"Packet received; type=ACK, seqNum={seq_num}; length={length}; checksum={hex(pkt_checksum)}; status = NOT_CORRUPT")

            with lock:
                if seq_num >= base:
                    base = seq_num + 1
                    log(f"Window moved to base= {base}")
                    dup_ack_count.clear()
                else:
                    dup_ack_count[seq_num] = dup_ack_count.get(seq_num, 0) + 1
                    if dup_ack_count[seq_num] == 3:
                        resent_packet(seq_num)

        except Exception:
            continue

# Timer

def timer():
    global base
    while not finished:
        time.sleep(0.05)
        with lock:
            current_time = time.time()
            for seq_num in list(unacked_packets.keys()):
                _, sent_time = unacked_packets[seq_num]
                if current_time - sent_time > TIMEOUT:
                    resent_packet(seq_num)

# Main

def main():
    global sender_socket, receiver_address, log_file, next_seq, base, file_chunks, finished

    if len(sys.argv) != 6:
        print("Usage: ./MTPSender <receiver-IP> <receiver-port> <window-size> <input-file> <sender-log-file>")
        sys.exit(1)

    receiver_ip = sys.argv[1]
    receiver_port = int(sys.argv[2])
    window_size = int(sys.argv[3])
    input_file = sys.argv[4]
    log_filename = sys.argv[5]

    receiver_address = (receiver_ip, receiver_port)
    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender_socket.bind(('', 0))
    log_file = open(log_filename, "w")

    with open(input_file, "rb") as f:
        while True:
            chunk = f.read(DATA_SIZE)
            if not chunk:
                break
            file_chunks.append(chunk)

    total_packets = len(file_chunks)
    log(f"Total number of packets = {total_packets}")

    threading.Thread(target=ack_listener, daemon=True).start()
    threading.Thread(target=timer, daemon=True).start()

    while base < total_packets:
        with lock:
            while next_seq < base + window_size and next_seq < total_packets:
                data = file_chunks[next_seq]
                packet, checksum = create_packet(DATA_TYPE, next_seq, data)
                send_packet(sender_socket, packet, receiver_address)
                log(f"Packet sent; type=DATA, seqNum={next_seq}; length={len(data)}; checksum={hex(checksum)}")

                unacked_packets[next_seq] = (packet, time.time())
                next_seq += 1

            window_status = ', '.join(f"{seq}({int(seq >= next_seq)})" for seq in range(base, base + window_size))
            log(f"Window status: [{window_status}]")

        time.sleep(0.05)

    while base < total_packets:
        time.sleep(0.1)

    finished = True
    log("All packets sent and acknowledged. Sender finished...")
    log_file.close()
    sender_socket.close()

if __name__ == "__main__":
    main()
