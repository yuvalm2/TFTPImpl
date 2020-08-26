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
    HOST_ADDRESS = "127.0.0.1"
    HOST_PORT = 69
    REMOTE_FILENAME = "RemoteFile.txt"

    """Todo - one line null check + assignment"""
    def __init__(self, local_filename, remote_filename=None, host=None, port=None):
        if local_filename is None:
            raise Exception("Filename was not supplied to TFTPWriteClient constructor")
        if host is None:
            self.host = TFTPWriteClient.HOST_ADDRESS
        if port is None:
            self.port = TFTPWriteClient.HOST_PORT

        self.local_filename = local_filename
        if remote_filename is None:
            self.remote_filename = TFTPWriteClient.REMOTE_FILENAME
        else:
            self.remote_filename = remote_filename

        # UDP / IP
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.settimeout(TFTPWriteClient.TIMEOUT_IN_SECONDS)

        # A number chosen (presumably close to) uniformly at random
        # making the chance of two instances colliding relatively low (Though not 0)
        self.assign_source_tid()

        self.init_transfer_state()

    def assign_source_tid(self):
        self.source_tid = random.randint(0, 2 ** 16 - 1)

        # TODO - identify (low probability) collisions
        # Assign new TID until one with no collisions is found (Perhaps give up at some point)

    def init_transfer_state(self):
        self.last_chunk_acked = -1

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
            self.socket.sendto(packet.to_bytes(), (self.host, self.port))
        except TimeoutError:
            print("Request timed out... aborting")
            raise

        received_ack = False
        while not received_ack:
            received_ack = self.handle_request_write_ack()

    def handle_common_ack(self, request_opcode):
        try:
            response, address = self.socket.recvfrom(1024)  # Todo - Is the choice of buffer size critical?
        except TimeoutError:
            print(f"Request of type {request_opcode} response timed out... aborting")
            raise

        # Validate the host generating the response
        host, port = address
        if host != self.host:
            return None

        # Check response_opcode
        response_opcode = struct.unpack("!H", response[0:2])
        if response_opcode[0] == Opcode.Error.value:
            error_code = struct.unpack("!H", response[2:4])
            tftp_error = TFTPErrorCode(error_code[0])
            error_message = response[4:-2]
            raise ErrorResponseToPacketException(request_opcode, tftp_error, error_message)
        if response_opcode[0] != Opcode.Ack.value:
            raise UnexpectedOpcodeException(request_opcode, response_opcode)

        return response

    def handle_request_write_ack(self):
        """
        Awaits for an acknowledgement to the write request sent previously.

        Returns:
            False if an irrelevant packet is received (and dropped)
            True if a suitable ack was received.

        Raises:
            TimeoutError: if timed out while awaiting response to the write request.
            ErrorResponseToPacketException: if the opcode received from the TFTP server was Error.
            UnexpectedOpcodeException: if the opcode received from the TFTP server was neither Error nor Ack.
        """
        if self.handle_common_ack(Opcode.WriteRequest) is not None:
            self.last_chunk_acked = 0
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
        response = self.handle_common_ack(Opcode.Data)
        if response is None:
            return False

        # Verify block number
        block_num = struct.unpack("!H", response[2:4])
        if block_num != self.last_chunk_acked + 1:
            print(f"block_num {block_num} received. Expected {self.last_chunk_acked + 1}")
            return False

        self.last_chunk_acked += 1

        return True

    def write(self):
        # Request and set up a connection
        self.init_transfer_state()

        # TODO - Verify that the filename is in netascii and is terminated by a zero byte
        self.request_write(self.remote_filename, OperationMode.NETASCII)

        self.transfer_data()

    def transfer_data(self):
        for block_number, data_chunk in enumerate(
                self.iterate_file_chunks(chunk_size=DataPacket.MAX_DATA_LENGTH_IN_BYTES), start=1):
            packet = DataPacket(block_number=block_number, data_chunk=data_chunk)
            print(f"Generated packet number {block_number}")

            # Send packet
            try:
                self.socket.sendto(packet.to_bytes(),
                                   (TFTPWriteClient.HOST_ADDRESS, TFTPWriteClient.HOST_PORT))
            except TimeoutError:
                print("Request timed out... aborting")
                raise
            print(f"Successfully sent packet number {block_number}")

            # Await acknowledgement before moving the the next packet
            received_ack = False
            while not received_ack:
                # Todo - Verify that  the case that I keep getting bad still results in timeout? Hit a stopwatch and check it after every bad packet
                received_ack = self.handle_data_ack()

            print(f"Packet number {block_number} was acknowledged")

        print(f"Transmission complete")

    # Make sure the last chunk is smaller than chunk size (Possibly of length 0)
    def iterate_file_chunks(self, chunk_size):
        assert chunk_size > 0

        # This could raise exceptions if the file cannot be read or does not exist
        # But since there isn't any way to handle such exceptions, there is not point to catch them
        with open(self.local_filename, "rb") as file_obj:
            while True:
                chunk = file_obj.read(chunk_size)
                if len(chunk) > 0:
                    yield chunk

                # The last chunk read was the last
                if len(chunk) < chunk_size:
                    break


# Tests - the iteration mechanism
# Add a required tests list

if __name__ == "__main__":
    client = TFTPWriteClient(local_filename="C:\TFTP-Root\Remote.txt", remote_filename="target.txt")
    client.write()
