import struct
import random
from socket import socket, AF_INET, SOCK_DGRAM

from Exceptions.ErrorResponseToPacketException import ErrorResponseToPacketException
from Exceptions.UnexpectedOpcodeException import UnexpectedOpcodeException
from Opcode import Opcode
from OperationMode import OperationMode
from PacketTypes.DataPacket import DataPacket
from PacketTypes.WRQPacket import WRQPacket

# TODO Didn't read termination yet
from TFTPErrorCode import TFTPErrorCode


class TFTPWriteClient():
    PACKET_SIZE = 512
    TIMEOUT_IN_SECONDS = 5
    DEFAULT_HOST_IP = "127.0.0.1"
    INITIAL_DEST_PORT = 69
    REMOTE_FILENAME = "Target.txt"

    """Todo - one line null check + assignment"""
    def __init__(self, local_filename, remote_filename=None, host=None):
        if local_filename is None:
            raise Exception("Filename was not supplied to TFTPWriteClient constructor")
        self.local_filename = local_filename

        if remote_filename is None:
            self.remote_filename = TFTPWriteClient.REMOTE_FILENAME
        else:
            self.remote_filename = remote_filename

        if host is None:
            self.host = TFTPWriteClient.DEFAULT_HOST_IP
        else:
            self.host = host

        self.data_dest_port = None

    def pick_data_source_port(self):
        self.data_source_port = random.randint(0, 2 ** 16 - 1)

        # TODO - identify (low probability) collisions
        # Assign new TID until one with no collisions is found (Perhaps give up at some point)

    def init_transfer_state(self):
        # Initially no block is acked.
        # I treat the WRQ as block 1
        self.last_block_acked = -1

        # A number chosen (presumably close to) uniformly at random
        # making the chance of two instances colliding relatively low
        self.pick_data_source_port()

    def request_write(self, remote_filename, mode):
        """
        Sends a write request, and awaits acknowledgement. (Or terminate upon error)

        :param remote_filename: The name of the file whose write is requested.
        :param mode: one of those defined in OperationMode enum.

        Returns:
            None

        Raises:
            TimeoutError: if timed out while sending the write request to the server or while awaiting for an
            acknowledgement for it to arrive.
            ErrorResponseToPacketException: if the opcode received from the TFTP server was Error.
            UnexpectedOpcodeException: if the opcode received from the TFTP server was neither Error nor Ack.
        """
        packet = WRQPacket(filename=remote_filename, mode=mode.name)

        try:
            self.socket.sendto(packet.to_bytes(), (self.host, TFTPWriteClient.INITIAL_DEST_PORT))
        except TimeoutError:
            print("Request timed out... Aborting")
            raise

        received_ack = False
        while not received_ack:
            received_ack = self.handle_request_write_ack()

    def receive_next_packet(self, request_opcode):
        try:
            return self.socket.recvfrom(1024)  # Todo - What should be the buffer size?
        except TimeoutError:
            print(f"Request of type {request_opcode} response timed out... Aborting")
            raise

    def handle_request_write_ack(self):
        """
        Awaits for acknowledgement to a previously sent write request .

        Returns:
            False if an irrelevant packet is received (and dropped)
            True if a suitable ack was received.

        Raises:
            TimeoutError: if timed out while awaiting response to the write request.
            ErrorResponseToPacketException: if the opcode received from the TFTP server was Error.
            UnexpectedOpcodeException: if the opcode received from the TFTP server was neither Error nor Ack.
        """
        """
        Verify an ack is received for the request_opcode with the suitable block number. (0 for WRQ, and for each data
        packet, the corresponding block number which is >=1)
        :param request_opcode: Which request type are we waiting for an ack for (used just for logging)
        :return: The response
        """
        try:
            response, address = self.receive_next_packet(Opcode.WriteRequest)
        except TimeoutError:
            print(f"Request of type {Opcode.WriteRequest} response timed out... Aborting")
            raise

        # Validate the host generating the response
        # Ignore responses originating from unexpected hosts
        if address[0] != self.host:
            return False

        # Use the port in the packet for future data messages (TODO - verify it only happens in WRQ)
        if self.data_dest_port is None:
           self.data_dest_port = address[1]

        # Verify an ack was received (And raise an exception otherwise)
        response_opcode = struct.unpack("!H", response[0:2])
        if Opcode(response_opcode[0]) == Opcode.Error:
            error_code = struct.unpack("!H", response[2:4])
            tftp_error = TFTPErrorCode(error_code[0])
            error_message = response[4:-2]
            raise ErrorResponseToPacketException(Opcode.WriteRequest, tftp_error, error_message)
        if Opcode(response_opcode[0]) != Opcode.Ack:
            raise UnexpectedOpcodeException(Opcode.WriteRequest, response_opcode)

        self.last_block_acked = 0

        return True

    def handle_data_ack(self):
        """
        Awaits an acknowledgement to the last sent data packet. (By block ID)

        Returns:
            False if an irrelevant packet is received (and dropped)
            True if received a suitable ack.

        Raises:
            TimeoutError: if timed out while awaiting response to the write request.
            ErrorResponseToWRQException: if the opcode received from the TFTP server was Error.
            UnexpectedOpcodeException: if the opcode received from the TFTP server was neither Error nor the expected Ack.
        """
        try:
            response, address = self.receive_next_packet(Opcode.Data)
        except TimeoutError:
            print(f"Request of type {Opcode.Data} response timed out... aborting")
            raise

        # Validate the host generating the response
        # Ignore responses originating from unexpected hosts
        host, port = address
        if host != self.host:
            return None

        assert port == self.data_dest_port

        # Verify an ack was received (And raise an exception otherwise)
        response_opcode = struct.unpack("!H", response[0:2])
        if Opcode(response_opcode[0]) == Opcode.Error:
            error_code = struct.unpack("!H", response[2:4])
            tftp_error = TFTPErrorCode(error_code[0])
            error_message = response[4:-2]
            raise ErrorResponseToPacketException(Opcode.Data, tftp_error, error_message)
        if Opcode(response_opcode[0]) != Opcode.Ack:
            raise UnexpectedOpcodeException(Opcode.Data, response_opcode)

        # Verify block number
        block_num = struct.unpack("!H", response[2:4])
        if block_num[0] != self.last_block_acked + 1:
            print(f"block_num {block_num[0]} acknowledged. Expected {self.last_block_acked + 1}")
            return False

        self.last_block_acked += 1

        return True

    def write(self):
        # Request and set up a connection
        self.init_transfer_state()

        # UDP / IP
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.settimeout(TFTPWriteClient.TIMEOUT_IN_SECONDS)

        try:
            self.request_write(self.remote_filename, OperationMode.NETASCII)

            self.transfer_data()
        finally:
            self.socket.close()
            self.socket = None

    def transfer_data(self):
        for block_number, data_chunk in enumerate(
                self.iterate_file_chunks(chunk_size=DataPacket.MAX_DATA_LENGTH_IN_BYTES), start=1):
            packet = DataPacket(block_number=block_number, data_chunk=data_chunk)
            print(f"Generated data packet number {block_number}")

            # Send packet
            try:
                self.socket.sendto(packet.to_bytes(),
                                   (self.host, self.data_dest_port))
            except TimeoutError:
                print("Request timed out... aborting")
                raise
            print(f"Successfully sent packet number {block_number}")
            print(f"Packet {block_number} contents - {repr(packet)}")

            # Await acknowledgement before moving the the next packet
            received_ack = False
            while not received_ack:
                received_ack = self.handle_data_ack()

            print(f"Packet number {block_number} was acknowledged")

        print(f"Transmission complete")

    # Make sure the last chunk is smaller than chunk size (Possibly of length 0)
    def iterate_file_chunks(self, chunk_size):
        assert chunk_size > 0

        # This could raise exceptions if the file cannot be read or does not exist
        # But since there isn't much to do about that, there is not point in catch such exceptions
        with open(self.local_filename, "rb") as file_obj:
            while True:
                chunk = file_obj.read(chunk_size)
                print("Chunk length - " + str(len(chunk)))
                if len(chunk) >= 0:
                    yield chunk

                # The last chunk read was the last
                if len(chunk) < chunk_size:
                    break

# Todo - add tests:
# 1) The block iteration mechanism (For both files which are and those which are not of length which is a multiple of the block size)
# Add a required tests list
### Verify that if I keep getting bad packages, I would still timeout? How? Perhaps hit a stopwatch and check it after every bad packet?

if __name__ == "__main__":
    #local_filename = "C:\\TFTP-Root\\Regular.txt"
    #local_filename = "C:\\TFTP-Root\\SingleBlockInput.txt"
    local_filename = "C:\\TFTP-Root\\TwoBlockInput.txt"
    client = TFTPWriteClient(local_filename=local_filename, remote_filename=TFTPWriteClient.REMOTE_FILENAME)
    client.write()
