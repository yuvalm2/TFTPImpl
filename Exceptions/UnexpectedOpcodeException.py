class UnexpectedOpcodeException(Exception):
    def __init__(self, request_opcode, response_opcode):
        self.request_opcode = request_opcode
        self.response_opcode = response_opcode

        super().__init__(f"Received unexpected opcode {self.response_opcode} for request {self.request_opcode}")
