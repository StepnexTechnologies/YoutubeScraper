class ScraperRuntimeError(Exception):
    def __init__(self, message, channel=None):
        super().__init__(message)
        self.channel = channel
