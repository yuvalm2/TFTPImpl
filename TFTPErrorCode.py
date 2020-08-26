from enum import Enum

class TFTPErrorCode(Enum):
    Undefined = 0
    FileNotFound = 1
    AccessViolation = 2
    DiskFullOrAllocationExceeded = 3
    IllegalTFTPOperation = 4
    UnknownTransferID = 5
    FileAlreadyExists = 6
    NoSuchUser = 7
