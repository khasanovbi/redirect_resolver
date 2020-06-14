class ResolverError(Exception):
    pass


class MaxRedirectsLimitError(ResolverError):
    def __init__(self):
        super().__init__("the maximum number of redirects has been reached")


class CyclicRedirectsError(ResolverError):
    def __init__(self, history):
        self.history = history

    def __str__(self):
        return f"cyclic redirects has been found, history: {self.history}"


class MaxBodySizeLimitError(ResolverError):
    def __init__(self, url):
        super().__init__("the maximum body size has been reached")
        self.url = url


class LocationHeaderMissedError(ResolverError):
    def __init__(self):
        super().__init__("Location header missed")
