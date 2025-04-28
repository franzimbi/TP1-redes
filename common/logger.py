class Logger:

    def __init__(self, prefix, log_level=0):
        self.prefix = prefix
        self.log_level = log_level

    def log(self, message, level):
        if level <= self.log_level:
            print(f"{self.prefix}: {message}")

    def set_log_level(self, level):
        self.log_level = level
