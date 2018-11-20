from requests import Response


class WrenchError(Exception):
    ...


class DecryptionError(WrenchError):
    ...


class ValidationError(WrenchError):
    ...


class HttpRequestError(WrenchError):
    def __init__(self, response: Response) -> None:
        self.response = response


class FingerprintMismatchError(WrenchError):
    ...


class ImportParseError(WrenchError):
    def __init__(self, lineno):
        self.lineno = lineno
