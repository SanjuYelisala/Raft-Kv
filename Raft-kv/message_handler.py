class MessageHandler:
    def __init__(self, r_node):
        self.r_node = r_node
    

    def handle(self, message):
        if message["message_type"] == "request_vote":
            self.handle_request_vote(message)
        elif message["message_type"] == "append_entries":
            self.handle_append_entries(message)

    def handle_request_vote(self, message):
        pass
    
    def handle_append_entries(self, message):
        pass