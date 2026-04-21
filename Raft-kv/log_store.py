class Log:
    def __init__(self):
        self.logs = []

    def append_log(self, log):
        self.logs.append(log)
        return log["index"]

    def get_log(self, index):
        if 0 <= index < len(self.logs):
            return self.logs[index]
        return None

    def get_entries_from(self, index):
        entries = self.logs[index:]
        return entries

    
    def last_index_log(self):
        if self.logs:
            return len(self.logs)
        return 0

    def last_term_log(self):
        if self.logs:
            return self.logs[-1]["term"]
