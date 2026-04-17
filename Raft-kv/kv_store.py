class KVStore:
    def __init__(self):
        self.key_store = {}
    def set_command(self, key, value):
        self.key_store[key] = value

    def get_command(self, key):
        return self.key_store.get(key, None)
        

    def del_command(self, key):
        if key in self.key_store:
            del self.key_store[key]
            return "Ok\n"
        return None