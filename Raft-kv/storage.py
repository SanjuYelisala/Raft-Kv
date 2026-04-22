import os
import json
os.makedirs("data", exist_ok=True)

class RaftStorage:
    def __init__(self,node_id):
        self.safe_id = node_id.replace(":","_")
        self.state_file = f"data/{self.safe_id}_state.json"
        self.log_file = f"data/{self.safe_id}_log.json"

    def save_state(self, term, voted_for, commit_index):
        state = {
            "current_term" : term,
            "voted_for" : voted_for,
            "commit_index": commit_index
        }

        with open(self.state_file, "w") as f:
            json.dump(state, f)

    def load_state(self):
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)

        except Exception as e:
            return {
                "current_term": 0, 
                "voted_for": None,
                "commit_index": 0
            }

    def append_entry(self, entry):
        logs = self.load_logs()
        logs.append(entry)
        with open(self.log_file, "w") as f:
            json.dump(logs, f)
    
    def load_logs(self):
        try:
            with open(self.log_file, "r") as f:
                return json.load(f)
        except Exception as e:
            return []

        