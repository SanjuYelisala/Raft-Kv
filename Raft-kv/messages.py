class RaftMessage:
    def __init__(self, node_id, current_term, last_log_index, last_log_term):
        self.node_id = node_id
        self.current_term = current_term
        self.last_log_index = last_log_index
        self.last_log_term = last_log_term

    def requestVote_message(self):
        request_message = {
            "message_type" : "request_vote",
            "candidate_id" : self.node_id,
            "term" : self.current_term,
            "last_log_index" : self.last_log_index,
            "last_log_term" : self.last_log_term
        }
        return request_message
