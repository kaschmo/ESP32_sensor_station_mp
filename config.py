import os
import ujson

class Config:

    # loads a configuration from the specified file,
    # and initializes an instance of Config
    def __init__(self, config_filename):
        self.filename = config_filename
        self.values = self.load_config(config_filename)

    # returns a value of the specified parameter if the parameter exists
    # otherwise, returns an empty string
    def get(self, name):
        if name in self.values:
            return self.values[name]
        return ''

    # return full json
    def get_json(self):
        return self.values

    # updates the specified parameter
    def set(self, name, value):
        self.values[name] = value

    # stores the configuration to the specified file
    def store(self):
        with open(self.filename, 'w') as f:
            f.write(ujson.dumps(self.values))

    # loads a configuration from the specified file
    @staticmethod
    def load_config(config_filename):
        if config_filename not in os.listdir():
            print('cannot find ' + config_filename)
            return {}
        with open(config_filename) as f:
            return ujson.load(f)