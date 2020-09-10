# coding: utf-8
import typing
import json
import asyncio
import queue
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket
from . import JsPyBackground

class JsPyError(Exception):
    """Exception class for JsPyTextSocket

    This class is used to propagate exceptions from the client.

    Attributes
    ----------
    message() -> str
        Explanation of the cause of the exception.
    report() -> str
        Detailed explanation of the cause of the exception.
    get_socket_id() -> int
        Get socket ID of the place where the exception occurred.
    """
    def __init__(self, msg: str, protocol: str,
                 key: str, id: int, socket_id: int):
        """Initial

        Parameters
        ----------
        msg: str
            The message of exception.
        protocol: str
        key: str
        id: int
            Internal information of websocket communication.
        socket_id: int
            This is the socket ID that has propagated the exception.
            The socket ID is a unique number that is assigned to the client
            by the server when websocket communication is established.
            Socket ID 0 means server.
        """
        self._protocol = protocol
        self._key = key
        self._id = id
        self._socket_id = socket_id
        self._msg = msg
        super().__init__(self.report())

    def __repr__(self):
        return self._msg

    def message(self) -> str:
        """Explanation of the cause of the exception"""
        return self._msg

    def report(self) -> str:
        """Detailed explanation of the cause of the exception """
        return(self._msg+' in {protocol: '+self._protocol+', key: '+self._key+
               ', id: '+str(self._id)+', socket_id: '+str(self._socket_id)+'}')

    def get_socket_id(self) -> int:
        """Get socket ID of the place where the exception occurred

        Returns
        ----------
        int
            This is the socket ID that has propagated the exception.
            The socket ID is a unique number that is assigned to the client
            by the server when websocket communication is established.
            This is an identification number uniquely assigned to the
            connected client. Assigned from 1 in connection order.
            Socket ID 0 means server.
        """
        return self._socket_id

    class JSONEncoder(json.JSONEncoder):
        """JSON encoder for exception instances

        When JsPyError() instance or Exception() instance is JSON encoded,
        it is replaced with a character string.

        Examples
        ----------
        import json
        from JsMeetsStarlette import JsPyError

        json_str = json.dumps(some_obj, cls=JsPyError.JSONEncoder)
        """
        def default(self, obj):
            if isinstance(obj, JsPyError):
                return '<'+obj.__class__.__name__+'>: '+obj.report()
            elif isinstance(obj, Exception):
                return '<'+obj.__class__.__name__+'>: '+str(obj.args)
            else:
                return json.JSONEncoder.default(self, obj)

class JsPyTextSocket(WebSocketEndpoint):
    """Websocket endpoint class that works in the background

    Controls WebSocket communication in text format.
    It is an extension class registered in JsMeetsPy.add_socket().
    Based on this class, the following modules implement various functions.
        JsPyFunction, JsPyQueue, JsPyPubsub
    Therefore, there are few opportunities to directly operate this class.

    It is not compatible with multi-process, and operation
    on the main thread is recommended.

    Attributes for general users < All functions are classmethods. >
    ----------
    set_connection_limit(limit: int=0) -> None
        Set socket quantity limit.
    number_of_connections() -> int
        Get the number of currently connected sockets.
    get_socket_id() -> tuple
        Get a tuple of currently connected socket ID.
    close_socket(socket_id: int) -> bool
        Disconnects the websocket with the specified socket ID.

    Attributes for developers < All functions are classmethods. >
    ----------
    add_protocol(protocol: str, func: typing.Callable) -> None
        Register websocket reception callback functions.
    add_socket_event(func: typing.Callable) -> None
        Register the callback function called by websocket event.
    clear_socket_event() -> None
        Clear all callback functions called by Websocket event.
    reservecast(data, socket: typing.Union[
                None, int, typing.List[int],
                typing.Tuple[int], typing.Set[int]]=None) -> None
        Reserve to send data in JSON format to the specified sockets.
    broadcast(data) -> list
        Send data in JSON format to the currently connected clients.
    multicast(data, socket: typing.Union[
              None, int, typing.List[int],
              typing.Tuple[int], typing.Set[int]]=None) -> list
        Send data in JSON format to the specified sockets.

    Notes
    ----------
    The data format of websocket is a JSON format string.
    It has the following five keys.
        key:   "protocol"
        value: "system",
               "function_call", "function_return", "function",
               "queue", "queue_call", "queue_return",
               "pub_call", "pub_return", "sub_call", "sub_return", "pub"

        key:   "key"
        value: str

        key:   "id"
        value: int

        key:   "data"
        value: Any

        key:   "exception"
        value: Any (almost None or str)
    """
    encoding = 'text'
    _SOCKET_PATH = '/jsmeetspy/textsocket'

    _connected = 0              # Number of connected clients
    _connection_limit = 0       # Client connection limit
    _protocol_table = {}        # Function corresponding to protocol name

    _socket_serial = 0          # ID management assigned to clients
    SERIAL_MAX = 0XFFFFFFFF     # Maximum number of socket ID

    # key:   socket ID currently connected
    # value: starlette.websockets.WebSocket instance
    _socket_pool = {}

    # Callback functions called at websocket connect and disconnect.
    # Normal function or async function.
    # Function has two argument.
    # The first argument is the client socket ID where the event occurred.
    # The second argument is the event name 'connect' or 'disconnect'.
    _socket_events = set()

    # --------------------
    # The following four classmethod are required for extended websockets.
    @classmethod
    def url_path(cls) -> str:
        """Returns the websocket URL pathname"""
        return cls._SOCKET_PATH

    # Not implemented
    # async def startup_handler(self) -> None
    # async def shutdown_handler(self) -> None

    @classmethod
    def endpoint(cls):
        """Return websocket endpoint"""
        return cls
    # --------------------

    @classmethod
    def set_connection_limit(cls, limit: int=0) -> None:
        """Set socket quantity limit.

        If you set a value smaller than the number of
        already connected, the number of connections will
        temporarily exceed.However, new connections will
        not be accepted and will be reduced naturally.

        Parameters
        ----------
        limit: int, default 0 (unlimited)
            Number of clients allowed to connect.
            0 means unlimited.
        """
        cls._connection_limit = limit if limit >= 0 else 0

    @classmethod
    def number_of_connections(cls) -> int:
        """Get the number of currently connected sockets."""
        return cls._connected

    @classmethod
    def get_socket_id(cls) -> tuple:
        """Get a tuple of currently connected socket ID.

        The socket ID is a unique number that is assigned to the socket
        by the server when websocket communication is established.
        This is an identification number uniquely assigned to the
        connected socket. Assigned from 1 in connection order.

        Returns
        ----------
        tuple
            (socket ID1, socket ID2, ...)
            An empty tuple if there are no socket.
        """
        return tuple(cls._socket_pool.keys())

    @classmethod
    def close_socket(cls, socket_id: int) -> bool:
        """Disconnects the websocket with the specified socket ID.

        Parameters
        ----------
        socket_id: int
            socket ID to close.
            The socket ID is a unique number that is assigned to the socket
            by the server when websocket communication is established.

        Returns
        ----------
        bool
            If True, success to close.
            If False, the socket ID specified in the argument
            is not currently connected.
        """
        if socket_id in cls._socket_pool:
            JsPyBackground.register_function(
                cls._socket_pool[socket_id].close, [])
            # on_disconnect() is called immediately by close()
            return(True)
        else:
            return(False)

    @classmethod
    def add_protocol(cls, protocol: str, func: typing.Callable) -> None:
        """Register websocket reception callback functions.

        Register the processing function of the data sent from the client.
        The data is in JSON format, and a processing function is registered
        for each protocol name.

        Parameters
        ----------
        protocol: str
            protocol name.
        func: Callable
            Processing function according to protocol name.
            Normal function or async function with three arguments.

            The first argument is the starlette.websockets.WebSocket class
            instance that suggests the websocket to communicate with.

            The second argument is the source websocket ID.

            The third argument is the dictionary type data sent from the client.
            The dictionary data has the following five keys.
            (protocol, key, id, data, exception)
        """
        cls._protocol_table[protocol] = func

    @classmethod
    def add_socket_event(cls, func: typing.Callable) -> None:
        """Register the callback function called by websocket event.

        When websocket communication is connected and disconnected,
        the registration functions are called.

        Parameters
        ----------
        func: Callable
            Callbak function has two arguments.
            The first is the client socket ID where the event occurred.
            The second is the event name 'connect' or 'disconnect'.

        See Also
        ----------
        clear_socket_event()
        """
        cls._socket_events.add(func)

    @classmethod
    def clear_socket_event(cls) -> None:
        """Clear all callback functions called by websocket event.

        See Also
        ----------
        add_socket_event()
        """
        cls._socket_events.clear()

    @classmethod
    def reservecast(cls, data, socket: typing.Union[
                    None, int, typing.List[int],
                    typing.Tuple[int], typing.Set[int]]=None) -> None:
        """Reserve to send data in JSON format to the specified sockets.

        This can be used on other than the main thread.
        Reserved for data transmission and processed later.
        Execution result and exception cannot be caught.

        Parameters
        ----------
        data: Any
            Data that can be converted to JSON format.
            Specifiable types:
                int, float, str, None, True, False,
                list, dict, tuple(convert to list)
        socket: None or int or list or tuple or set, default None
            socket ID to send. If None, same as broadcast()
            The socket ID is a unique number that is assigned to the client
            by the server when websocket communication is established.
        """
        JsPyBackground.register_function(cls.multicast, (data, socket))

    @classmethod
    def broadcast(cls, data) -> typing.Awaitable:
        """Send data in JSON format to the currently connected clients.

        Call on the main thread where the event loop is running.

        If Add the await keyword, it will wait until the transmission
        is completed. No exception occurs even if transmission fails.

        If you do not add the await keyword, the transmission is reserved
        and will be executed later.

        Parameters
        ----------
        data: Any
            Data that can be converted to JSON format.
            Specifiable types:
                int, float, str, None, True, False,
                list, dict, tuple(convert to list)

        Returns
        ----------
        asyncio.gather instance with return_exceptions=True

        Raises
        ----------
        TypeError
            Argument data cannot be converted to JSON format.
        """
        text_data = json.dumps(data)
        cor_list = []
        for socket_id in cls._socket_pool:
            cor_list.append(cls._socket_pool[socket_id].send_text(text_data))
        return asyncio.gather(*cor_list, return_exceptions=True)

    @classmethod
    def multicast(cls, data, socket: typing.Union[
                  None, int, typing.List[int],
                  typing.Tuple[int], typing.Set[int]]=None) -> typing.Awaitable:
        """Send data in JSON format to the specified sockets.

        Call on the main thread where the event loop is running.

        If Add the await keyword, it will wait until the transmission
        is completed. No exception occurs even if transmission fails.

        If you do not add the await keyword, the transmission is reserved
        and will be executed later.

        Parameters
        ----------
        data: Any
            Data that can be converted to JSON format.
            Specifiable types:
                int, float, str, None, True, False,
                list, dict, tuple(convert to list)
        socket: None or int or list or tuple or set, default None
            socket ID to send. If None, same as broadcast_json()
            The socket ID is a unique number that is assigned to the client
            by the server when websocket communication is established.

        Returns
        ----------
        asyncio.gather instance with return_exceptions=True

        Raises
        ----------
        TypeError
            Argument data cannot be converted to JSON format.
        """
        cor_list = []
        text_data = json.dumps(data)
        if socket is None:
            return cls.broadcast(data)
        elif isinstance(socket, int):
            if socket in cls._socket_pool:
                cor_list.append(cls._socket_pool[socket].send_text(text_data))
        elif isinstance(socket, (tuple, list, set)):
            for i in socket:
                if i in cls._socket_pool:
                    cor_list.append(
                        cls._socket_pool[i].send_text(text_data))
        return asyncio.gather(*cor_list, return_exceptions=True)

    @classmethod
    def _append_socket(cls, ws: WebSocket) -> int:
        """websocket registration

        Registers a newly connected websocket and returns an socket ID.

        Parameters
        ----------
        ws: WebSocket
            newly connected WebSocket instance.

        Returns
        ----------
        int
            The assigned socket ID. Unique number assigned from 1.
            Increment by 1 in connection order.
        """
        cls._socket_serial += 1
        if cls._socket_serial > cls.SERIAL_MAX:
            cls._socket_serial = 1
        while cls._socket_serial in cls._socket_pool:
            cls._socket_serial += 1
            if cls._socket_serial > cls.SERIAL_MAX:
                cls._socket_serial = 1
        cls._socket_pool[cls._socket_serial] = ws
        return(cls._socket_serial)

    @classmethod
    def _delete_socket(cls, socket_id: int) -> None:
        """websocket unregistration

        Disable websocket of specified socket ID.

        Parameters
        ----------
        socket_id: int
            The socket ID is a unique number that is assigned to the client
            by the server when websocket communication is established.
        """
        if socket_id in cls._socket_pool:
            del cls._socket_pool[socket_id]

    async def on_connect(self, ws: WebSocket):
        """Processing when websocket is newly established

        When the websocket is connected from the client,
        the socket ID is assigned and the websocket is registered.

        Next, depending on the limit on the number of client connections,
        there are two types of correspondence.

        1. When the number of connections exceeds the limit.
            Send the following JSON string to the client.
            -----
            {'protocol': 'system', 'key': 'connect', 'id': 0,
             'data': None, 'exception':
             'Connection refused due to connection limit @python'}

        2. Others
            Send the following JSON string to the client.
            XXX means the assigned socket ID.( >= 1)
            -----
            {'protocol': 'system', 'key': 'connect', 'id': 0,
             'data': XXX, 'exception': None}
        """
        JsPyTextSocket._connected += 1
        await ws.accept()
        self._socket_id = JsPyTextSocket._append_socket(ws)
        if JsPyTextSocket._connection_limit > 0 and\
           JsPyTextSocket._connected > JsPyTextSocket._connection_limit:
            send_dict = {'protocol': 'system', 'key': 'connect', 'id': 0,
                         'data': None, 'exception':
                         'Connection refused due to connection limit @python'}
            await ws.send_json(send_dict)
            await ws.close()
            # on_disconnect() is called immediately by ws.close().
        else:
            send_dict = {'protocol': 'system', 'key': 'connect', 'id': 0,
                         'data': self._socket_id, 'exception': None}
            await ws.send_json(send_dict)
        for callback in JsPyTextSocket._socket_events:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self._socket_id, 'connect'))
                else:
                    callback(self._socket_id, 'connect')
            except:
                pass

    async def on_receive(self, ws: WebSocket, data: str):
        """Processing when data is received"""
        try:
            dict_data = json.loads(data)
            if('protocol' in dict_data and 'key' in dict_data and
               'id' in dict_data and 'data' in dict_data and
               'exception' in dict_data):
                call_func = JsPyTextSocket._protocol_table[dict_data['protocol']]
                if(asyncio.iscoroutinefunction(call_func)):
                    asyncio.create_task(call_func(ws, self._socket_id, dict_data))
                else:
                    call_func(ws, self._socket_id, dict_data)
        except:
            pass

    async def on_disconnect(self, ws: WebSocket, close_code: int):
        """Processing when websocket is disconnected"""
        JsPyTextSocket._delete_socket(self._socket_id)
        JsPyTextSocket._connected -= 1
        for callback in JsPyTextSocket._socket_events:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self._socket_id, 'disconnect'))
                else:
                    callback(self._socket_id, 'disconnect')
            except:
                pass
