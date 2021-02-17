from http import HTTPStatus
from typing import List, Callable, Awaitable

from macrobase_driver.endpoint import Endpoint
from macrobase_driver.logging import get_request_id, set_request_id
from .exceptions import get_exception_handler

from sanic.request import Request
from sanic.response import BaseHTTPResponse, text as TextResponse, json as JsonResponse, file as FileResponse, raw as RawResponse


class SanicEndpoint(Endpoint):

    @staticmethod
    def params_from_dictparams(params: dict):
        args = {}

        for key in params:
            value = params[key]

            if isinstance(value, list) and len(value) == 1:
                value = value[0]

            args[key] = value

        return args

    @staticmethod
    def import_body_match_info(request: Request) -> dict:
        if request.match_info is not None:
            return dict(request.match_info)

        return {}

    @staticmethod
    def import_body_json(request: Request) -> dict:
        if 'application/json' in request.content_type and request.json is not None:
            return dict(request.json)

        return {}

    @staticmethod
    def import_body_args(request: Request) -> dict:
        if request.method != 'POST' and request.args is not None and len(request.args) > 0:
            args = SanicEndpoint.params_from_dictparams(request.args)

            return dict(args)

        return {}

    @staticmethod
    def import_body_files(request: Request) -> dict:
        if request.files is not None and len(request.files) > 0:
            files = {}

            for key in request.files:
                if isinstance(request.files[key], list):
                    files[key] = [{'type': file.type, 'body': file.body, 'name': file.name} for file in
                                  request.files[key]]
                else:
                    files[key] = request.files

            return files

        return {}

    @staticmethod
    def import_body_form(request: Request) -> dict:
        if request.form is not None and len(request.form) > 0:
            args = request.form

            if 'multipart/form-data' in request.content_type:
                args = SanicEndpoint.params_from_dictparams(args)

            return dict(args)

        return {}

    @staticmethod
    def import_body_headers(request: Request) -> dict:
        headers = {}

        for header in request.headers:
            if header[:2].lower() == 'x-':
                headers[header] = request.headers[header]

        return headers

    @staticmethod
    async def make_response_raw(
            raw_str: str,
            code: int = 200,
            headers: dict = None,
            content_type: str = "application/octet-stream"
    ) -> BaseHTTPResponse:
        headers = headers or {}
        headers['x-cross-request-id'] = get_request_id()
        return RawResponse(str.encode(raw_str), status=code, headers=headers, content_type=content_type)

    @staticmethod
    async def make_response_text(
            text: str,
            code: int = 200,
            headers: dict = None,
            content_type: str = "text/plain; charset=utf-8"
    ) -> BaseHTTPResponse:
        headers = headers or {}
        headers['x-cross-request-id'] = get_request_id()
        return TextResponse(text, status=code, headers=headers, content_type=content_type)

    @staticmethod
    async def make_response_json(
            code: int = 200,
            message: str = None,
            data: dict = None,
            error_code: int = None,
            headers: dict = None,
    ) -> BaseHTTPResponse:

        headers = headers or {}
        headers['x-cross-request-id'] = get_request_id()

        if data is not None:
            return JsonResponse(data, status=code,  headers=headers)

        if message is None:
            message = HTTPStatus(code).phrase

        if error_code is None:
            error_code = code

        data = {
            'code': error_code,
            'message': message
        }

        return JsonResponse(data, status=code, headers=headers)

    @staticmethod
    async def make_response_file(filepath: str, headers: dict = None) -> BaseHTTPResponse:
        headers = headers or {}
        headers['x-cross-request-id'] = get_request_id()

        return await FileResponse(filepath, headers=headers)

    async def handle(self, request: Request, auth: dict = None, *args, **kwargs) -> BaseHTTPResponse:
        body = {}

        # aggregate data from all inputs
        body.update(self.import_body_match_info(request))
        body.update(self.import_body_json(request))
        body.update(self.import_body_args(request))
        body.update(self.import_body_files(request))
        body.update(self.import_body_form(request))
        body.update(self.import_body_headers(request))

        body['auth'] = auth

        return await self._method(request, body, *args, **kwargs)

    def _get_before_methods(self) -> List[Callable[..., Awaitable[None]]]:
        return []

    def _get_after_methods(self) -> List[Callable[..., Awaitable[None]]]:
        return []

    async def _before_method(self, request: Request, body: dict, *args, **kwargs):
        for func in self._get_before_methods():
            await func(request, body, *args, **kwargs)

    async def _after_method(self, *args, **kwargs):
        for func in self._get_after_methods():
            await func(*args, **kwargs)

    async def _handle_method_exceptions(self, exception: Exception, *args, **kwargs) -> BaseHTTPResponse:
        handler = get_exception_handler(exception)
        code = 500
        data = None
        message = str(exception)

        if handler:
            code, message, data = handler(exception)

        return await self.make_response_json(code=code, message=message, data=data)

    async def _method(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        set_request_id()
        method = request.method.lower()
        func_name = f'method_{method}'

        if hasattr(self, func_name):
            func = getattr(self, func_name)

            try:
                await self._before_method(request, body, *args, **kwargs)
                return await func(request, body, *args, **kwargs)
            except Exception as e:
                return await self._handle_method_exceptions(e, *args, **kwargs)
            finally:
                await self._after_method(*args, **kwargs)
        else:
            return await self.make_response_json(code=405, message='Method Not Allowed')

    async def method_get(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')

    async def method_head(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')

    async def method_post(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')

    async def method_put(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')

    async def method_delete(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')

    async def method_connect(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')

    async def method_options(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')

    async def method_trace(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')

    async def method_patch(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_json(code=500, message=f'{request.method} Not Impl')


class HealthEndpoint(SanicEndpoint):

    async def method_get(self, request: Request, body: dict, *args, **kwargs) -> BaseHTTPResponse:
        return await self.make_response_raw('Health')
