
class KVStore:
    def __init__(self):
        self.key_store = {}

    def set_command(self, key, value):
        try:
            self.key_store[key] = value
            return f"{key} is Successfully stored in KV"
        except Exception as e:

            return f"{key} storing Unsuccessful"
    def get_command(self, key):
        try:
            return self.key_store.get(key, None)
        except Exception as e:
            print(f"Client command received: {key}")
            print(f"Role: {self.r_node.role}")
            return None

    def del_command(self, key):
        if key in self.key_store:
            del self.key_store[key]
            return "Ok\n"
        return None