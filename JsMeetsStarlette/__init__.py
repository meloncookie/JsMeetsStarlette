# coding: utf-8
import asyncio
import queue
from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.endpoints import WebSocketEndpoint
from .JsPyTextSocket import JsPyError, JsPyTextSocket
from . import JsPyBackground

__copyright__ = 'Copyright (c) 2020 meloncookie'
__version__ = '0.0.0'
__license__ = 'MIT'

"""
This software is released under the MIT License.
Copyright (c) 2020 meloncookie

Version
----------
0.0.0   2020.09.09

Requirements
----------
Python 3.7+

Overview
----------
Python is the most popular programming language today.
It is used for a wide range of purposes from scientific
calculation to hobby.

On the other hand, in the user interface,
the influence of the browser is increasing.
Javascript is indispensable for dynamic expression in the browser.

This is a library that bridges server-side python and browser-side javascript.
1. You can call python functions from javascript in a natural way.
   The reverse is also true.
2. You can send arbitrary data from javascript to the queue on the python side.
   The reverse is also true.
3. Like MQTT, arbitrary data can be published/subscribed via the topic.

Let's enjoy programming creation.
"""

class JsMeetsPy(Starlette):
    """Application class that replaces Starlette class.

    Since JsMeetsPy inherites Starlette, the usage is the same as Starlette.
    In addition, it is a base class that adds the websocket.

    Attributes
    ----------
    add_socket(endpoint) -> None
        Add websocket endpoint.
    templates: Jinja2Templates
        Jinja2 template instance.

    Directory
    ----------
    some directory
        |--- main.py        (main module written by user)
        |--- templates *1   (for jinja2 template engine)
        |       |--- index.html
        |       |--- etc... File to which the template is applied
        |--- static *2      (for static files)
                |--- .js / .css / .ico / image file
                |--- etc... Files to distribute statically

    *1: When templates parameter is set to "templates"
        in the constructor of function JsMeetsPy.
    *2: When static parameter is set to "static"
        in the constructor of function JsMeetsPy.

    Examples
    ----------
    from JsMeetsStarlette import JsMeetsPy

    app = JsMeetsPy(debug=True, static='static',
                    templates='templates')

    @app.route('/', ['GET'])
    async def page_root(request):
        ...
        # use jinja2 template engine
        return app.templates.TemplateResponse('index.html', {'name': 'Mike'})

    Constructor
    ----------
    Conforms to the constructor of starlette.applications.Starlette .
        debug, routes, middleware, exception_handlers, on_startup, on_shutdown

    In addition to them, the following special keyword parameters can be set.
        static: str, templates: str
    """

    def __init__(self, *args, **kwargs):
        """Constructor

        Parameters
        ----------
        Conforms to the constructor of starlette.applications.Starlette.
        debug, routes, middleware, exception_handlers, on_startup, on_shutdown

        In addition, the following special keyword parameters can be set.
        static: str, templates: str

        static: str
            Serve files in a given directory. The specified directory
            corresponds to the '/static' URL path.
            For example, if you specify directory "stat", ./stat/favicon.ico
            file can be accessed with URL 'http://.../static/favicon.ico'  *1

            In the "jinja2" template engine, you can access static files by
            writing as follows.

            <link href="{{ url_for('static', path='/favicon.ico') }}"
             rel="icon" type="image/vnd.microsoft.icon" />    *2

            *1: The URL path name is fixed at '/static'.
                (not the directory name)
            *2: The first parameter of url_for is fixed to 'static'.

        templates: str
            You can use a "jinja2" template engine. If you specify a directory,
            the files under it will be decorated by the template engine.

        Examples
        ----------
        from JsMeetsStarlette import JsMeetsPy

        app = JsMeetsPy(debug=True, templates='templates')

        @app.route('/', ['GET'])
        async def page_root(request):
            ...
            # Use jinja2 template engine.
            # app.templates is equal to
            # starlette.templating.Jinja2Templates instance.
            temp_value = {'name': 'Mike', 'age': 22}
            return app.templates.TemplateResponse('index.html', temp_value)
        """
        self._static_dir = None
        self._templates_dir = None
        if 'static' in kwargs:
            self._static_dir = kwargs['static']
            del kwargs['static']
        if 'templates' in kwargs:
            self._templates_dir = kwargs['templates']
            del kwargs['templates']
        # Hidden keyword for developers
        # List of extended websocket endpoints (Refer to add_socket())
        if 'extended_sockets' in kwargs:
            extended_sockets = kwargs['extended_sockets']
            if not extended_sockets:
                extended_sockets = []
            del kwargs['extended_sockets']
        else:
            # If 'extended_sockets' is not specified in kwargs,
            # Set standard expansion websocket.
            extended_sockets = [JsPyTextSocket]

        super().__init__(*args, **kwargs)
        for i in extended_sockets:
            self.add_socket(i)
        self.add_event_handler('startup', JsPyBackground.startup_handler)
        self.add_event_handler('shutdown', JsPyBackground.shutdown_handler)

        if self._static_dir:
            self.mount('/static',
                       StaticFiles(directory=self._static_dir),
                       'static')
        if self._templates_dir:
            self.templates = Jinja2Templates(directory=self._templates_dir)

    def add_socket(self, endpoint) -> None:
        """Add websocket endpoint

        The Extended WebSockets endpoint accepts two types.
            1. Inherited class of starlette.endpoints.WebSocketEndpoint.
            2. Normal class instance with event handler function.

        Parameters
        ----------
        endpoint
            1. Inherited class of starlette.endpoints.WebSocketEndpoint. Not instance.
               The following two classmethod must be provided in this class.
                    def url_path() -> str
                        Returns the websocket URL pathname you want to connect to.
                    def endpoint()
                        Return websocket endpoint.

               The following two methods are defined as needed.
               Not implemented when not needed.
                    async def startup_handler() -> None
                        Startup processing at server startup.
                    async def shutdown_handler() -> None
                        Shutdown processing when the server is shutdown.

            2. Normal class instance with event handler function.
               It has the above 4 methods(not classmethod).

        Examples
        ----------
        from starlette.endpoints import WebSocketEndpoint
        from starlette.websockets import WebSocket

        # Case 1.
        class Ext1Socket(WebSocketEndpoint):
            encoding = 'bytes'   # or 'text'
            @classmethod
            def url_path(cls):
                return '/socket_url1'
            # Defined if necessary
            # async def startup_handler(cls), async def shutdown_handler(cls) ...
            @classmethod
            def endpoint(cls):
                return cls
            async def on_connect(self, ws: WebSocket):
                ...
            async def on_receive(self, ws: WebSocket, data: bytes):
                ...
            async def on_disconnect(self, ws: WebSocket, close_code: int):
                ...

        # Case 2.
        class Ext2Socket():
            def __init__(self, path: str):
                self._path = path
            def url_path(self):
                return self._path
            # Defined if necessary
            # async def startup_handler(self), async def shutdown_handler(self) ...
            def endpoint(self):
                return self.socket_handler

            async def socket_handler(self, ws: WebSocket):
                await ws.accept()
                await ws.send_text('Hello')
                await ws.close()
            ...

        app = JsMeetsPy()

        # Case 1.
        app.add_socket(Ext1Socket)

        # Case 2.
        ws_endpoint1 = Ext2Socket('/new_url1')
        ws_endpoint2 = Ext2Socket('/new_url2')
        app.add_socket(ws_endpoint1)
        app.add_socket(ws_endpoint2)
        """
        self.add_websocket_route(endpoint.url_path(), endpoint.endpoint())
        if hasattr(endpoint, 'startup_handler'):
            self.add_event_handler('startup', endpoint.startup_handler)
        if hasattr(endpoint, 'shutdown_handler'):
            self.add_event_handler('shutdown', endpoint.shutdown_handler)
