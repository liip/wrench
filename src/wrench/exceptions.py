from requests import Response


class InputValidationError(Exception):
    ...


class HttpRequestError(Exception):
    def __init__(self, response: Response) -> None:
        self.response = response
