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
        self.last_heartbeat_sent = time.time()
        self.last_log_term = 0
        self.last_log_index = 0
        self.commit_index = 0
        self.votes_received = 0

        self.r_kvstore = KVStore()
        self.r_log = Log()
        
        self.pending_clients = {}
        self.log_confirmations = {}  # {log_index: count}
        self.next_index = {}

        
    def start(self):
        self.server.start()

    def check_election_timeout(self):
        
        if self.role == "leader":
            if time.time() - self.last_heartbeat_sent > 0.5:
                self.send_heartbeat()
                self.last_heartbeat_sent = time.time()
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
        print(f"Leader log: {self.r_log.logs}")
        print(f"Sending heartbeat to peers: {self.peers}")
        r_message = RaftMessage(self.node_id, self.current_term, self.last_log_index, self.last_log_term)


        for peer in self.peers:
            print(f"peer={peer}, next_index={self.next_index.get(peer)}, last_log={self.r_log.last_index_log()}")
            if peer not in self.next_index:
                self.next_index[peer] = 1  # new peer, send from beginning
            host, port = peer.split(":")
            if self.next_index[peer] < self.r_log.last_index_log() + 1:
                if self.next_index[peer] > 0:
                    message = r_message.append_entries(self.current_term, self.node_id, self.last_log_index, self.commit_index, self.r_log.get_entries_from(self.next_index[peer] - 1))
                
            else:
                message = r_message.append_entries(self.current_term, self.node_id, self.last_log_index, self.commit_index, [])
            self.server.send(host, int(port), message)
        
            

    def replicate_log(self, log_entry):
        self.last_log_index = self.r_log.last_index_log()
        print(f"Replicating log to peers: {self.peers}")
        r_message = RaftMessage(self.node_id, self.current_term, self.last_log_index, self.last_log_term)
        message = r_message.append_entries(self.current_term, self.node_id, self.last_log_index, self.commit_index, [log_entry])
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
