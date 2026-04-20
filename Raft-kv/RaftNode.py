import time
import sys
import random
import json

from node import NodeServer
from messages import RaftMessage
from election import RaftElection
from message_handler import MessageHandler
from kv_store import KVStore
from log_store import Log

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
        self.commit_index = 0
        self.votes_received = 0

        self.r_kvstore = KVStore()
        self.r_log = Log()
        
        
    def start(self):
        self.server.start()

    def check_election_timeout(self):
        
        if self.role == "leader":
            self.send_heartbeat()
            return
        if time.time() - self.last_heartbeat > self.election_timeout:
            print("Election timeout fired!")
            self.role = "candidate"
            self.current_term += 1
            self.votes_received = 1
            self.voted_for = self.node_id
            self.last_heartbeat = time.time()
            self.election_timeout = random.uniform(1.0, 5.0)
            r_elect = RaftElection(self.node_id, self.role, self.current_term, self.last_log_index,
                                             self.last_log_term, self.peers,self.server)
    
    def send_heartbeat(self):
        print(f"Sending heartbeat to peers: {self.peers}")
        r_message = RaftMessage(self.node_id, self.current_term, self.last_log_index, self.last_log_term)
        message = r_message.append_entries(self.current_term, self.node_id, self.last_log_index, self.commit_index, [])
        for peer in self.peers:
            host, port = peer.split(":")
            self.server.send(host, int(port), message)



def main():
    host = sys.argv[1]
    port = int(sys.argv[2])

    with open("config/peers.json") as f:
        config = json.load(f)
    peers = []
    for peer in config["nodes"]:
        if peer["port"] != port:
            peers.append(f"{peer['host']}:{peer['port']}")

    r_node = RaftNode(host, port, peers)
    r_node.start()
    

if __name__ == "__main__":
    main()
