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
            elif parsed["message_type"] == "install_snapshot":
                self.handle_install_snapshot(parsed)
            elif parsed["message_type"] == "snapshot_response":
                self.handle_snapshot_response(parsed)
        except json.JSONDecodeError:
            # handle as client command
            print(f"This is a client command")
            commands = message.split(" ")
            
            if not commands:
                print(f"Empty commands received")
                return
            command = commands[0].upper()
            key = commands[1] if len(commands) > 1 else None
            value = " ".join(commands[2:]) if len(commands) > 2 else None
            if self.r_node.role != "leader" and command == 'SET':
                leader = self.r_node.current_leader
                if leader:
                    sock.sendall(f"Not the leader. Try {leader}\n".encode())
                else:
                    sock.sendall("Not the leader. No leader known yet\n".encode())
                return
            if command == 'SET':
                log_entry = {
                    "index": self.r_node.snapshot_index + self.r_node.r_log.last_index_log() + 1,
                    "term" : self.r_node.current_term,
                    "command" : {"action": "set", "key": key, "value": value}

                }
                self.r_node.r_log.append_log(log_entry)
                self.r_node.storage.append_entry(log_entry)
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
            elif command == "STATUS":
                status = {
                    "node_id": self.r_node.node_id,
                    "role": self.r_node.role,
                    "term": self.r_node.current_term,
                    "commit_index": self.r_node.commit_index,
                    "log_size": len(self.r_node.r_log.logs),
                    "snapshot_index": self.r_node.snapshot_index,
                    "leader": self.r_node.current_leader
                }
                sock.sendall((str(status) + "\n").encode())
            else:
                print(f"Command Not Recognized")
            
        
    def handle_request_vote(self, message):
        # step down if we see higher term
        if message["term"] > self.r_node.current_term:
            self.r_node.current_term = message["term"]
            self.r_node.role = "follower"
            self.r_node.voted_for = None
            self.r_node.storage.save_state(self.r_node.current_term, self.r_node.voted_for, self.r_node.commit_index)

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
        self.r_node.current_leader = message["leader_id"]
        self.r_node.last_heartbeat = time.time()
        if message["term"] >= self.r_node.current_term:
            self.r_node.current_term = message["term"]
            self.r_node.role = "follower"
            success = True
            self.r_node.storage.save_state(self.r_node.current_term, self.r_node.voted_for, self.r_node.commit_index)

            # Consistency Check
            if message["entries"] and message["last_log_index"] > 0:
                adjusted = message["last_log_index"] - self.r_node.snapshot_index - 1
                existing_entry = self.r_node.r_log.get_log(adjusted)
                if existing_entry and existing_entry["term"] != message["last_log_term"]:
                    success = False
        else:
            success = False

        # handle log entries if present
        log_index = None
        if success and message["entries"]:
            for entry in message["entries"]:
                log_index = self.r_node.r_log.append_log(entry)
                self.r_node.storage.append_entry(entry)
        self.r_node.last_log_index = self.r_node.r_log.last_index_log()
        acknowledgement = {
            "message_type": "append_response",
            "term": self.r_node.current_term,
            "success": success,
            "log_index": log_index,
            "node_id": self.r_node.node_id,
            "reason": "consistency_check" if not success else None
        }
        host, port = message["leader_id"].split(":")
        self.r_node.server.send(host, int(port), acknowledgement)

        # apply any newly committed entries to KV store
        if message["commit_index"] > self.r_node.commit_index:
            for i in range(self.r_node.commit_index, message["commit_index"]):
                adjusted = i - self.r_node.snapshot_index
                entry = self.r_node.r_log.get_log(adjusted)
                if entry:
                    command = entry["command"]
                    print(f"Applying entry to KV: {entry}")
                    self.r_node.r_kvstore.set_command(command["key"], command["value"])
            self.r_node.commit_index = message["commit_index"]


    def handle_append_response(self, message):
        
        if not message["success"]:
            if message.get("reason") == "consistency_check":
                if message["node_id"] in self.r_node.next_index:
                    self.r_node.next_index[message["node_id"]] -= 1
            return
        
        log_index = message["log_index"]
        if log_index is None:  # heartbeat response, nothing to commit
            return
        else:
            if message["success"] == True:
                new_next = log_index + 1
                if new_next > self.r_node.next_index.get(message["node_id"], 0):
                    self.r_node.next_index[message["node_id"]] = new_next
            else:
                if message["log_index"] is None and message["node_id"] in self.r_node.next_index:
                    self.r_node.next_index[message["node_id"]] -= 1
                return
        # increment confirmation count for this log index
        if log_index not in self.r_node.log_confirmations:
            self.r_node.log_confirmations[log_index] = 1  # leader already counts as 1

        self.r_node.log_confirmations[log_index] += 1
        
        total_nodes = len(self.r_node.peers) + 1
        majority = (total_nodes // 2) + 1
        print(f"log_confirmations={self.r_node.log_confirmations}, log_index={log_index}, majority={majority}")
        if self.r_node.log_confirmations[log_index] >= majority:
            if log_index > self.r_node.commit_index:
                adjusted_index = log_index - self.r_node.snapshot_index - 1
                log_entry = self.r_node.r_log.get_log(adjusted_index)
                if log_entry:
                    command = log_entry["command"]
                    self.r_node.r_kvstore.set_command(command["key"], command["value"])
                    self.r_node.commit_index = log_index
                    self.r_node.maybe_snapshot()
                    self.r_node.storage.save_state(self.r_node.current_term, self.r_node.voted_for,self.r_node.commit_index)
                    sock = self.r_node.pending_clients.pop(log_index, None)
                    if sock:
                        sock.sendall(f"{command['key']} committed successfully\n".encode())
                # always delete confirmations regardless
                del self.r_node.log_confirmations[log_index]

    def handle_install_snapshot(self, snap):
        if snap["term"] > self.r_node.current_term:
            self.r_node.current_term = snap["term"]
        self.r_node.r_kvstore.key_store = snap["kv_data"]
        self.r_node.snapshot_index = snap["snapshot_index"]
        self.r_node.snapshot_term = snap["snapshot_term"]
        self.r_node.commit_index = snap["snapshot_index"]
        self.r_node.r_log.logs = []
        self.r_node.last_heartbeat = time.time()
        self.r_node.storage.save_state(self.r_node.current_term, self.r_node.voted_for, self.r_node.commit_index)
        self.r_node.storage.save_snapshot(
            snap["snapshot_index"],
            snap["snapshot_term"],
            snap["kv_data"]
        )
        response = {
        "message_type": "snapshot_response",
        "term": self.r_node.current_term,
        "node_id": self.r_node.node_id,
        "snapshot_index": snap["snapshot_index"]
        }
        host, port = snap["leader_id"].split(":")
        self.r_node.server.send(host, int(port), response)

    def handle_snapshot_response(self, snap_response):
        print(f"snapshot_response: setting next_index[{snap_response['node_id']}] = {self.r_node.snapshot_index + 1}")
        self.r_node.next_index[snap_response["node_id"]] = self.r_node.snapshot_index + 1

