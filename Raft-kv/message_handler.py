import time
import json
import random

from kv_store import KVStore

class MessageHandler:
    def __init__(self, r_node):
        self.r_node = r_node
    

    def handle(self, message, sock):
        if not message.strip():
            return
        try:
            print(f"Client command received: {message}")
            print(f"Role: {self.r_node.role}")
            parsed = json.loads(message)
            print("this is a raft command")
            # route to Raft handlers
            if parsed["message_type"] == "request_vote":
                self.handle_request_vote(parsed)
            elif parsed["message_type"] == "append_entries":
                self.handle_append_entries(parsed)
            elif parsed["message_type"] == "vote_response":
                self.handle_vote_response(parsed)
            elif parsed["message_type"] == "append_response":
                self.handle_append_response(parsed)
        except json.JSONDecodeError:
            # handle as client command
            print(f"This is a client command")
            commands = message.split(" ")
            
            if not commands:
                print(f"Empty commands received")
                return
            command = commands[0].upper()
            key = commands[1]
            value = " ".join(commands[2:])
            if self.r_node.role != "leader" and command == 'SET':
                sock.sendall("Not the leader\n".encode())
                return
            if command == 'SET':
                log_entry = {
                    "index" : self.r_node.r_log.last_index_log() + 1,
                    "term" : self.r_node.current_term,
                    "command" : {"action": "set", "key": key, "value": value}

                }
                self.r_node.r_log.append_log(log_entry)
                self.r_node.pending_clients[log_entry["index"]] = sock
                self.r_node.replicate_log(log_entry)
                
                
                
                '''response = self.r_node.r_kvstore.set_command(key, value)
                print(f"Sending response: {response}")
                sock.sendall((response + "\n").encode())'''
            elif command == "GET":
                response = self.r_node.r_kvstore.get_command(key)
                if response is None:
                    response =  "NOT FOUND"
                print(f"Sending response: {response}")
                sock.sendall((response + "\n").encode())
            elif command == "DEL":
                response = self.r_node.r_kvstore.del_command(key)
                if response is None:
                    response =  "NOT FOUND"
                sock.sendall((response + "\n").encode())
            else:
                print(f"Command Not Recognized")
            
        
    def handle_request_vote(self, message):
        # step down if we see higher term
        if message["term"] > self.r_node.current_term:
            self.r_node.current_term = message["term"]
            self.r_node.role = "follower"
            self.r_node.voted_for = None

        # grant vote if term is valid and we haven't voted for someone else
        if (message["term"] >= self.r_node.current_term and
            (self.r_node.voted_for is None or 
            self.r_node.voted_for == message["candidate_id"])):
            voted = True
            self.r_node.voted_for = message["candidate_id"]
        else:
            voted = False

        response = {
            "message_type": "vote_response",
            "term": self.r_node.current_term,
            "voted": voted
        }
        print(f"Vote request from {message['candidate_id']} term={message['term']}, voting={voted}")
        host, port = message["candidate_id"].split(":")
        self.r_node.server.send(host, int(port), response)

    def handle_vote_response(self, response):
        print(f"Processing vote response, my role={self.r_node.role}, voted={response['voted']}")
        if self.r_node.role != "candidate":
            return
        if response["voted"] == True:
            self.r_node.votes_received += 1
            total_nodes = len(self.r_node.peers) + 1
            majority = (total_nodes//2) + 1
            print(f"votes_received={self.r_node.votes_received}, total_nodes={total_nodes}, majority={majority}")
            if self.r_node.votes_received >= majority:
                print(f"Vote received! Total votes: {self.r_node.votes_received}, need: {majority}")
                self.r_node.role = "leader"
                for peer in self.r_node.peers:
                    self.r_node.next_index[peer] = self.r_node.r_log.last_index_log() + 1
                print(f"{self.r_node.node_id} is now the LEADER for term {self.r_node.current_term}")

    
    def handle_append_entries(self, message):

        # always reset heartbeat and update term
        print(f"Received entries: {message['entries']}, commit_index: {message['commit_index']}")
        self.r_node.last_heartbeat = time.time()
        if message["term"] >= self.r_node.current_term:
            self.r_node.current_term = message["term"]
            self.r_node.role = "follower"
            success = True
        else:
            success = False

        # handle log entries if present
        log_index = None
        if message["entries"]:
            for entry in message["entries"]:
                log_index = self.r_node.r_log.append_log(entry)
        self.r_node.last_log_index = self.r_node.r_log.last_index_log()
        acknowledgement = {
            "message_type": "append_response",
            "term": self.r_node.current_term,
            "success": success,
            "log_index": log_index,
            "node_id": self.r_node.node_id
        }
        host, port = message["leader_id"].split(":")
        self.r_node.server.send(host, int(port), acknowledgement)

        # apply any newly committed entries to KV store
        if message["commit_index"] > self.r_node.commit_index:
            for i in range(self.r_node.commit_index, message["commit_index"]):
                entry = self.r_node.r_log.get_log(i)
                if entry:
                    command = entry["command"]
                    print(f"Applying entry to KV: {entry}")
                    self.r_node.r_kvstore.set_command(command["key"], command["value"])
            self.r_node.commit_index = message["commit_index"]


    def handle_append_response(self, message):
        
        if not message["success"]:
            return
        
        log_index = message["log_index"]
        if log_index is None:  # heartbeat response, nothing to commit
            return
        else:
            if message["success"] == True:
                self.r_node.next_index[message["node_id"]] = log_index + 1 
        # increment confirmation count for this log index
        if log_index not in self.r_node.log_confirmations:
            self.r_node.log_confirmations[log_index] = 1  # leader already counts as 1
        self.r_node.log_confirmations[log_index] += 1

        total_nodes = len(self.r_node.peers) + 1
        majority = (total_nodes // 2) + 1

        if self.r_node.log_confirmations[log_index] >= majority:
            # commit — apply to KV store
            if log_index > self.r_node.commit_index:  # only commit once
                log_entry = self.r_node.r_log.get_log(log_index - 1)  # log is 0-indexed
                print(f"Committing log entry: {log_entry}")
                if log_entry:
                    command = log_entry["command"]
                    self.r_node.r_kvstore.set_command(command["key"], command["value"])
                    self.r_node.commit_index = log_index
                    print(f"Committing log entry: {log_entry}")
                    # respond to waiting client
                    sock = self.r_node.pending_clients.pop(log_index, None)
                    if sock:
                        sock.sendall(f"{command['key']} committed successfully\n".encode())


