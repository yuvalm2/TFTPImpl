from enum import IntEnum


class Opcode(IntEnum):
    ReadRequest = 1
    WriteRequest = 2
    Data = 3
    Ack = 4
    Error = 5


