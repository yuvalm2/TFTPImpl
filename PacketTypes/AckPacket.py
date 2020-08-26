import struct

from Opcode import Opcode
from PacketTypes.TFTPPacket import TFTPPacket


class AckPacket(TFTPPacket):
    def __init__(self, block_number: int) -> object:
        # Format described in figure 5-3 in RFC 1350
        data_chunk = struct.pack('!H', block_number)

        super(AckPacket, self).__init__(Opcode.Ack, data_chunk)
