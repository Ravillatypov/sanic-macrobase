from sanic.exceptions import SanicException
from typing import Callable, Optional, Tuple, Union, Type


class RoutingErrorException(SanicException):

    def __init__(self, message, *args, **kwargs):
        super().__init__(message, status_code=500, *args, **kwargs)


_exception_handlers = {}
ExceptionTyping = Union[Exception, Type[Exception]]
ExceptionHandlerTyping = Callable[[ExceptionTyping], Tuple[int, str, dict]]


def register_exception_handler(*exceptions: Type[Exception]):
    def wrapper(func: ExceptionHandlerTyping):
        for exception in exceptions:
            _exception_handlers[exception] = func
        return func

    return wrapper


def get_exception_handler(exception: ExceptionTyping) -> Optional[ExceptionHandlerTyping]:
    default = None
    exc_cls = exception.__class__

    if exc_cls is type:
        exc_cls = exception

    if exc_cls in _exception_handlers:
        return _exception_handlers.get(exc_cls)

    for key, handler in _exception_handlers.items():
        if isinstance(exception, key):
            return handler

        if default is None and issubclass(exc_cls, key):
            default = handler

    return default


@register_exception_handler(SanicException)
def _sanic_exceptions(exc: ExceptionTyping):
    return exc.status_code, str(exc), None
