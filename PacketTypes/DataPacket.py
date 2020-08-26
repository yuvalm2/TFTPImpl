import struct

from Opcode import Opcode
from PacketTypes.TFTPPacket import TFTPPacket


class DataPacket(TFTPPacket):
    MAX_DATA_LENGTH_IN_BYTES = 512

    # TODO - can I make block_number uint?
    def __init__(self, block_number: int, data_chunk: str) -> object:
        # Format described in figure 5-2 in RFC 1350
        payload = struct.pack('!H', block_number).decode("utf-8") + data_chunk.decode("utf-8")

        super(DataPacket, self).__init__(Opcode.Data, payload)

    def __repr__(self):
        return f"Data packet ([Opcode = {Opcode.Data}][Payload={repr(self.payload)}]"
