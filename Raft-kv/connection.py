class Connection:
    def __init__(self):
        self.buffer = b""
    def feed(self, message):
        self.buffer += message
        output = self.buffer.split(b"\n")
        final_list = output[:-1]
        self.buffer = output[-1]   
        return final_list

        