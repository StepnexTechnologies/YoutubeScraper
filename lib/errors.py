class ScraperRuntimeError(Exception):
    def __init__(self, message, channel=None):
        super().__init__(message)
        self.channel = channel


class EmptyStringException(Exception):
    def __init__(self, message, content):
        super().__init__(message)
        self.content = content
