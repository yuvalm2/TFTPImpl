class ErrorResponseToPacketException(Exception):
    def __init__(self, request_opcode, received_error_code, error_message):
        self.request_opcode = request_opcode
        self.received_error_code = received_error_code
        self.error_message = error_message

    def __str__(self):
        return f"Received error code {self.received_error_code} in response to a request with opcode {self.request_opcode}. Error message was {self.error_message}"
