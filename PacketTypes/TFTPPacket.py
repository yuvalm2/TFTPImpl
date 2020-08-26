import struct


class TFTPPacket(object):
    def __init__(self, opcode, payload):
        self.opcode = opcode
        self.payload = payload

    def __str__(self):
        pass

    def __repr__(self):
        pass

    # TODO - UTF-8?
    def to_string(self):
        return struct.pack("!H", int(self.opcode)).decode("utf-8") + self.payload

    def to_bytes(self):
        return str.encode(self.to_string())
