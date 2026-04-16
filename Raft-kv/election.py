from messages import RaftMessage

class RaftElection:
    def __init__(self, node_id, role, current_term,last_log_index, last_log_term, peers, server):
        self.node_id = node_id
        self.role = role
        self.current_term = current_term
        self.last_log_index = last_log_index
        self.last_log_term = last_log_term
        self.peers = peers
        self.server = server

        self.raft_message = RaftMessage(self.node_id, self.current_term, self.last_log_index, self.last_log_term)
        self.message = self.raft_message.requestVote_message()
        self.request_votes(self.peers,self.message)

    def request_votes(self, peers, message):
        for peer in peers:
            host, port = peer.split(":")
            self.server.send(host, int(port), message)
    
