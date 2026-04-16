import time
import sys
import random
import json

from node import NodeServer
from messages import RaftMessage
from election import RaftElection
from message_handler import MessageHandler

class RaftNode:
    def __init__(self, host, port, peers):
        self.node_id = f"{host}:{port}"
        self.host = host
        self.port = port
        self.role = "follower"
        self.peers = peers

        self.current_term = 0
        self.voted_for = None

        self.message_handler = MessageHandler(self)
        self.server = NodeServer(host, port, self.check_election_timeout, self.message_handler.handle)
        self.election_timeout = random.uniform(1.0, 3.0)

        self.last_heartbeat = time.time()
        self.last_log_term = 0
        self.last_log_index = 0
        
        
        
    def start(self):
        self.server.start()

    def check_election_timeout(self):
        
        if self.role == "leader":
            return
        if time.time() - self.last_heartbeat > self.election_timeout:
            print("Election timeout fired!")
            self.role = "candidate"
            self.current_term += 1
            self.voted_for = self.node_id
            self.last_heartbeat = time.time()
            self.election_timeout = random.uniform(1.0, 3.0)
            r_elect = RaftElection(self.node_id, self.role, self.current_term, self.last_log_index,
                                             self.last_log_term, self.peers,self.server)
        

def main():
    host = sys.argv[1]
    port = int(sys.argv[2])

    with open("config/peers.json") as f:
        config = json.load(f)
    peers = []
    for peer in config["nodes"]:
        if peer["port"] != str(port):
            peers.append(f"{peer['host']}:{peer['port']}")

    r_node = RaftNode(host, port, peers)
    r_node.start()
    

if __name__ == "__main__":
    main()
