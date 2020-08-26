import struct


class TFTPPacket(object):
    EXTENDED_ASCII = "cp437"

    def __init__(self, opcode, payload):
        self.opcode = opcode
        self.payload = payload

    def to_string(self):
        return struct.pack("!H", int(self.opcode)).decode(TFTPPacket.EXTENDED_ASCII) + self.payload

    def to_bytes(self):
        return self.to_string().encode(encoding=TFTPPacket.EXTENDED_ASCII)
