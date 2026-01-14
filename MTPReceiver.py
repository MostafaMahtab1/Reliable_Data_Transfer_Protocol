import sys
import socket
import struct
import zlib
import time
from unreliable_channel import send_packet, recv_packet

# Constants
DATA_TYPE = 0
ACK_TYPE = 1
HEADER_FORMAT = "!IIII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_PACKET_SIZE = 1472
TIMEOUT = 0.5

# State
expected_seq_num = 0
received_data = {}
log_file = None
receiver_socket = None
client_addr = None

#Helper Functions

def calculate_checksum(packet_type, seq_num, length, data):
    temp_header = struct.pack(HEADER_FORMAT, packet_type, seq_num, length, 0)
    return zlib.crc32(temp_header + data) & 0xffffffff

def log(message):
    print(message)
    log_file.write(message + "\n")
    log_file.flush()

def create_packet(packet_type, seq_num, data=b''):
    length = len(data)
    checksum = calculate_checksum(packet_type, seq_num, length, data)
    full_header = struct.pack(HEADER_FORMAT, packet_type, seq_num, length, checksum)
    return full_header + data

def extract_packet_info(packet):
    header = packet[:HEADER_SIZE]
    data = packet[HEADER_SIZE:]
    packet_type, seq_num, length, checksum = struct.unpack(HEADER_FORMAT, header)
    calc_checksum = calculate_checksum(packet_type, seq_num, length, data)
    return packet_type, seq_num, length, checksum, calc_checksum, data

# Main 

def main():
    global log_file, receiver_socket, client_addr, expected_seq_num

    if len(sys.argv) != 4:
        print("Usage: ./MTPReceiver <receiver-port> <output-file> <receiver-log-file>")
        sys.exit(1)

    receiver_port = int(sys.argv[1])
    output_file_path = sys.argv[2]
    log_file_path = sys.argv[3]

    log_file = open(log_file_path, "w")
    output_file = open(output_file_path, "wb")

    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket.bind(('', receiver_port))
    receiver_socket.settimeout(TIMEOUT)

    ack_pending = False
    last_ack_sent_time = 0

    while True:
        try:
            raw_packet, addr = recv_packet(receiver_socket)
            client_addr = addr

            pkt_type, seq_num, length, pkt_checksum, calc_checksum, data = extract_packet_info(raw_packet)

            if pkt_type != DATA_TYPE:
                continue

            status = "NOT_CORRUPT" if pkt_checksum == calc_checksum else "CORRUPT"
            log(f"Packet received; type=DATA; seqNum={seq_num}; length={length}; "
                f"checksum_in_packet={hex(pkt_checksum)}; checksum_calculated={hex(calc_checksum)}; status={status}")

            if pkt_checksum != calc_checksum:
                safe_seq = max(0, expected_seq_num - 1)
                ack_packet = create_packet(ACK_TYPE, safe_seq)
                send_packet(receiver_socket, ack_packet, client_addr)
                log(f"Sent DUP ACK for seqNum={safe_seq} (corrupt packet)")
                continue

            if seq_num == expected_seq_num:
                received_data[seq_num] = data
                expected_seq_num += 1
                ack_pending = True
                last_ack_sent_time = time.time()

                # Handle buffered in-order packets
                while expected_seq_num in received_data:
                    expected_seq_num += 1

                safe_seq = max(0, expected_seq_num - 1)
                ack_packet = create_packet(ACK_TYPE, safe_seq)
                send_packet(receiver_socket, ack_packet, client_addr)
                log(f"Sent CUMULATIVE ACK for seqNum={safe_seq}")

            elif seq_num > expected_seq_num:
                if seq_num not in received_data:
                    received_data[seq_num] = data
                    log(f"Packet received; type=DATA; seqNum={seq_num}; length={length}; "
                    f"checksum_in_packet={hex(pkt_checksum)}; checksum_calculated={hex(calc_checksum)}; "
                    f"status=OUT_OF_ORDER_PACKET")
                safe_seq = max(0, expected_seq_num - 1)
                ack_packet = create_packet(ACK_TYPE, safe_seq)
                send_packet(receiver_socket, ack_packet, client_addr)
                log(f"Sent DUP ACK for seqNum={safe_seq} (gap detected)")


            else:
                # Duplicate packet -> resend ACK for already ACKed packet
                safe_seq = max(0, seq_num)
                ack_packet = create_packet(ACK_TYPE, safe_seq)
                send_packet(receiver_socket, ack_packet, client_addr)
                log(f"Duplicate packet; resent ACK for seqNum={safe_seq}")

        except socket.timeout:
            if ack_pending:
                safe_seq = max(0, expected_seq_num - 1)
                ack_packet = create_packet(ACK_TYPE, safe_seq)
                send_packet(receiver_socket, ack_packet, client_addr)
                log(f"Timeout: Sent delayed ACK for seqNum={safe_seq}")
                ack_pending = False

        except KeyboardInterrupt:
            break

    # Write received data to output
    for seq in sorted(received_data):
        output_file.write(received_data[seq])

    log_file.close()
    output_file.close()
    receiver_socket.close()

if __name__ == "__main__":
    main()
