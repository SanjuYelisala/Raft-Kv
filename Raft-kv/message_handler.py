
class MessageHandler:
    def __init__(self, r_node):
        self.r_node = r_node
    

    def handle(self, message):
        if message["message_type"] == "request_vote":
            self.handle_request_vote(message)
        elif message["message_type"] == "append_entries":
            self.handle_append_entries(message)
        elif message["message_type"] == "vote_response":
            self.handle_vote_response(message)
        elif message["message_type"] == "append_response":
            self.handle_append_response(message)

    def handle_request_vote(self, message):
        if (message["term"] >= self.r_node.current_term) and (self.r_node.voted_for == None or self.r_node.voted_for == message["candidate_id"] ):
            voted = True
            self.r_node.voted_for = message["candidate_id"]
        else:
            voted = False
        requestVote_response = {
                "message_type": "vote_response",
                "term" : self.r_node.current_term,
                "voted": voted

            }
        host, port = message["candidate_id"].split(":")
        self.r_node.server.send(host, int(port), requestVot_response)
        

    def handle_vote_response(self, response):
        if response["voted"] == True:
            self.r_node.votes_received += 1
            total_nodes = len(self.r_node.peers) + 1
            majority = (total_nodes//2) + 1
            if self.r_node.votes_received >= majority:
                self.r_node.role = "leader"
                print(f"{self.r_node.node_id} is now the LEADER for term {self.r_node.current_term}")

    
    def handle_append_entries(self, message):
        self.r_node.last_heartbeat = time.time()
        if message["term"] >= self.r_node.current_term:
            self.r_node.current_term = message["term"]
            self.r_node.role = "follower"
            success = True
        else:
            success = False
        acknowledgement = {
                "message_type": "append_response",
                "term": current_term,
                "success": success
                }
        host, port = message["leader_id"].split(":")
        self.r_node.server.send(host, int(port), acknowledgement)


    def handle_append_response(self, message):
        print(f"Acknowledgement received with success field as {message["success"]}")