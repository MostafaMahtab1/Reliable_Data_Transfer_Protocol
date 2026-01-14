                            M Transport Protocol (MTP)
                        ===================================

Overview:

M Transport Protocol (MTP) is a custom reliable file transfer protocol built on top of UDP.
It provides reliable, ordered, and corruption-free delivery of data over an unreliable network by implementing TCP-inspired mechanisms at the application layer.

MTP is designed for educational and experimental purposes and demonstrates core transport-layer concepts such as sequencing, acknowledgments, retransmissions, sliding windows, and congestion handling.


Design Goals:

1. Reliable delivery over an unreliable channel

2. In-order data reconstruction

3. Detection and recovery from packet loss and corruption

4. Support for out-of-order delivery

5. Simple and extensible protocol design


Packet Format:

All MTP packets share a fixed-size header followed by an optional payload.

Header Structure (16 bytes total)

Field	         Size (bytes)	   Description

packet_type	         4	           Packet type identifier
sequence_number	   4	           Packet sequence number
payload_length	      4	           Length of payload in bytes
checksum	            4	           CRC32 checksum


Header fields are encoded in network byte order (big-endian).


Packet Types:

Type	   Value	   Description

DATA	     0	       Data packet carrying file content
ACK	     1	       Acknowledgment packet


DATA Packets:

DATA packets carry a contiguous chunk of the file being transferred.

Structure:

| Header (16 bytes) | Payload (variable) |

sequence_number uniquely identifies the packet

payload_length specifies the number of data bytes

checksum covers the header (with checksum field set to 0) and payload


DATA packets may arrive:

a) Out of order

b) Duplicated

c) Corrupted

d) Lost


ACK Packets:

ACK packets are used by the receiver to confirm successful receipt of data.

Structure:

| Header (16 bytes) |


No payload

sequence_number represents the highest contiguous DATA packet received

Implements cumulative acknowledgments

Example:

ACK seqNum = 5 means packets [0…5] have been received correctly


                             ### Reliability Mechanisms: ###

Sequencing:

Each DATA packet is assigned a monotonically increasing sequence number

Enables reordering and duplicate detection


Checksum Verification:

CRC32 checksum is used to detect corruption

Corrupted packets are discarded

Receiver responds with a duplicate ACK for the last valid sequence number


Sliding Window Protocol:

Sender maintains a configurable sliding window

Tracks:

base: lowest unacknowledged sequence number

next_seq: next sequence number to send

Allows multiple in-flight packets


Acknowledgment Strategy:

Receiver sends cumulative ACKs

Duplicate ACKs are sent when:

* Corrupt packets are received

* Out-of-order packets create gaps

* Duplicate packets are detected


Retransmission Policy:

The sender retransmits packets under two conditions:

1. Timeout-based retransmission:

If an ACK is not received within a fixed timeout interval

2. Fast retransmit: 

Triggered after receiving three duplicate ACKs for the same sequence number


Out-of-Order Handling:

Receiver buffers out-of-order packets

Buffered packets are delivered to the output file only when all preceding packets have been received

Prevents data loss and preserves ordering.


### Network Fault Simulation ###


MTP is tested using a simulated unreliable channel that can introduce:

a -> Packet loss

b -> Packet corruption

This allows evaluation of protocol behavior under adverse network conditions.



Connection Termination: 

The transfer completes when all DATA packets have been successfully acknowledged

Receiver reconstructs the file by writing buffered data in sequence order

Graceful shutdown enhancements (e.g., FIN handshake) are planned for future versions



Limitations:

No encryption or authentication

Single sender–receiver connection

Fixed timeout values

No advanced congestion control (e.g., TCP Reno/Cubic)


Summary

MTP demonstrates how reliable data transfer can be built over UDP using fundamental transport-layer concepts.
The protocol emphasizes clarity, correctness, and extensibility while remaining simple enough for experimentation and learning the core ideas of data transfer in computer networking.