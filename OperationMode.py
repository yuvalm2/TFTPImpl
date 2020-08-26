from enum import Enum


class OperationMode(Enum):
    # This is ascii as defined in "USA Standard Code for Information Interchange" [1] with the modifications specified in "Telnet Protocol Specification" [3].
    # 8-bit ascii.
    NETASCII = 0
    OCTET = 1
    MAIL = 2  # Obsolete
