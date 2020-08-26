from Opcode import Opcode
from OperationMode import OperationMode
from PacketTypes.TFTPPacket import TFTPPacket


class WRQPacket(TFTPPacket):
    # TODO - can I make index uint?
    def __init__(self, filename: bytes, mode: OperationMode) -> object:
        # Format described in figure 5-1 in RFC 1350
        data_chunk = f"{filename}{chr(0)}{str(mode)}{chr(0)}"

        super(WRQPacket, self).__init__(Opcode.WriteRequest, data_chunk)

    def __str__(self):
        pass

    def __repr__(self):
        return f"Write request (WRQ) packet ([Opcode = {Opcode.Data}][Payload={repr(self.payload)}]"
