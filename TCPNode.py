import threading
import struct
import sys
import readline
import socket


class TCPNode:
    HEADER_SIZE = 2
    TRIPLET_SIZE = 8

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.connections = {}
        self.reachability_table = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("[PseudoBGP Node]")
        print("Address:", ip)
        print("Port:", port)

    def start_node(self):
        """ Create two new threads
        one to handle console commands and
        another to listen to incoming connections. """
        print("START EXECUTED")
        connection_handler_thread =\
            threading.Thread(target=self.handle_incoming_connections)
        connection_handler_thread.start()
        self.handle_console_commands()

    @staticmethod
    def receive_and_decode_message(connection):
        # Header is the first 2 bytes, it contains the length
        header = connection.recv(2)
        length = struct.unpack('!H', header)[0]
        print(f"RECEIVED A MESSAGE WITH {length} TRIPLETS:")

        for _ in range(0, length):
            # Read each triplet
            message = connection.recv(TCPNode.TRIPLET_SIZE)
            triplet = struct.unpack('!BBBBBBBB', message)

            ip = triplet[:4]
            mask = triplet[4]
            cost = int.from_bytes(triplet[5:], byteorder='big', signed=False)

            print(f"ADDRESS: {ip[0]}.{ip[1]}.{ip[2]}.{ip[3]}",
                  f", SUBNET MASK: {mask}, COST: {cost}")

    @staticmethod
    def listen_to_connection(connection):
        while True:
            try:
                TCPNode.receive_and_decode_message(connection)
            except Exception:
                # A socket disconnection may throw a non defined exception
                # this will catch all exceptions and blame it in a
                # socket disconnecting abruptly
                connection.close()
                print("A connection was closed")
                return  # stop the thread not-so gracefully

    def handle_incoming_connections(self):
        print("LISTENING TO INCOMING CONNECTIONS")
        self.sock.bind((self.ip, self.port))
        self.sock.listen(self.port)

        while True:
            conn, addr = self.sock.accept()
            print(f"CONNECTED WITH {addr}")
            connection_listener = \
                threading.Thread(
                    target=self.listen_to_connection,
                    args=(conn,))
            connection_listener.start()

    def send_message(self, ip, port, message):
        print(f"SENDING {len(message)} BYTES TO {ip}:{port}")
        address = (ip, port)
        if address in self.connections:
            host_socket = self.connections[address]
        else:
            host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host_socket.connect(address)
            self.connections[address] = host_socket

        try:
            host_socket.sendall(message)
        except BrokenPipeError:
            self.connections[address].close()
            del self.connections[address]
            print(f"Conection with {address} closed")

    def handle_console_commands(self):
        while True:
            command = input("Enter your command...\n> ")
            command = command.strip().split(" ")

            if len(command) != 3:
                print("Unrecognized command, try again.")
                continue

            if command[0] == "sendMessage":
                message = self.read_message()
                self.send_message(ip=command[1],
                                  port=int(command[2]),
                                  message=message)
            elif command[0] == "exit":
                sys.exit(1)

    def stop_node(self):
        # Close all open connections and terminate all threads
        pass

    def read_message(self):
        length = int(input("Enter the length of your message...\n"))
        message = bytearray(2 + length*self.TRIPLET_SIZE)
        # First encode 2 bytes that represents the message length
        struct.pack_into("!H", message, 0, length)

        offset = 2
        for _ in range(0, length):
            current_message = \
                input("Type the message to be sent as follows:\n" +
                      "<IP address> <subnet mask> <cost>\n")
            current_message = current_message.strip().split(' ')
            address = current_message[0].strip().split('.')

            # Each triplet is encoded with the following 8-byte format:
            # BBBB (4 bytes) network address
            # B    (1 byte)  subnet mask
            # I    (4 bytes) cost.
            #      The cost should only be 3 bytes, this is handled below.
            struct.pack_into('!BBBBB', message, offset,
                             int(address[0]), int(address[1]),
                             int(address[2]), int(address[3]),
                             int(current_message[1]))

            # Pack the cost into a 4 byte buffer
            cost = struct.pack('!I', int(current_message[2]))

            # Write the cost into the message buffer, copying only 3 bytes
            # The least significant byte is the one dropped because its encoded
            # as big endian
            message[offset+5:offset+8] = cost[1:]

            # Move the offset to write the next triplet
            offset += self.TRIPLET_SIZE

        return message


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(sys.argv)
        print(len(sys.argv))
        print("Incorrect arg number")
        sys.exit(1)

    node = TCPNode(sys.argv[1], int(sys.argv[2]))
    node.start_node()
