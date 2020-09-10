# coding: utf-8
import typing
import json
import asyncio
import queue
from starlette import status
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket
from . import JsPyBackground

class JsPyBinarySocket():
    """Websocket endpoint class that works in the background

    Controls WebSocket communication in binary format.
    It is an extension class registered in JsMeetsPy.add_socket().

    It is not compatible with multi-process, and operation
    on the main thread is recommended.

    Attributes for general users
    ----------
    set_connection_limit(limit: int=0) -> None
        Set socket quantity limit.
    number_of_connections() -> int
        Get the number of currently connected sockets.
    get_socket_id() -> tuple
        Get a tuple of currently connected socket ID.
    close_socket(socket_id: int) -> bool
        Disconnects the websocket with the specified socket ID.
    set_message_handler(callback: typing.Callable) -> None
        Register a callback function called when data arrives from client.
    reservecast(data: bytes, socket: typing.Union[
                None, int, typing.List[int],
                typing.Tuple[int], typing.Set[int]]=None) -> None
        Reserve to send bytes data to the specified sockets.
    broadcast(data: bytes) -> list
        Send bytes data to the currently connected sockets.
    multicast(data: bytes, socket: typing.Union[
              None, int, typing.List[int],
              typing.Tuple[int], typing.Set[int]]=None) -> list
        Send bytes data to the specified sockets.
    add_socket_event(func: typing.Callable) -> None
        Register the callback functions called by websocket event.
    clear_socket_event() -> None
        Clear all callback functions called by Websocket event.

    Examples
    ----------
    from starlette.websockets import WebSocket
    from JsMeetsStarlette import JsMeetsPy, JsPyBinarySocket

    app = JsMeetsPy()    # Create an application instance.

    # Callback function with three arguments
    async def echo(ws: WebSocket, socket_id: int, data: bytes):
        print('From socket ID {}, data: {}'.format(socket_id, str(data)))
        await ws.send_bytes(data)

    # Instantiate a websocket endpoint for binary communication.
    bs = JsPyBinarySocket('/socket/pipe1')
    # Register the callback function called when data is received.
    bs.set_message_handler(echo)
    # Register the endpoint with the application instance.
    app.add_socket(bs)
    # Then start accepting websockets automatically.

    async def some_event():
        ...
        # Send bytes data to the currently connected sockets.
        await bs.broadcast(b'Good morning')
        ...

    Example in client side
    ----------
    // You need to load 'JsPyBinarySocket.js' in advance.
    function print_log(ws, data){
        console.log('Received '+data.byteLength+' bytes of data.');
    }
    // The websocket connection will be started automatically.
    bs = new JsPyBinarySocket('/socket/pipe1');
    // Register the callback function called when data is received.
    bs.set_message_handler(print_log);

    function some_event(){
        let msg = new ArrayBuffer(10);
        ...
        bs.send(msg);    # Send to the server 10bytes
        ...
    }
    """
    # encoding = 'bytes'
    SERIAL_MAX = 0XFFFFFFFF

    def __init__(self, url_path: str='/jsmeetspy/binarysocket') -> None:
        """Initialize

        Creates a websocket endpoint with the specified URL path.
        When instantiated and registered with JsMeetsPy.add_socket(),
        a websocket will be opened.

        Parameters
        ----------
        url_path: str
            URL pathname
        """
        self._url_path = url_path        # URL path name
        self._connected = 0              # Number of connected sockets
        self._connection_limit = 0       # Socket connection limit
        self._socket_serial = 0          # ID management assigned to sockets

        # key:   socket ID currently connected
        # value: starlette.websockets.WebSocket instance
        self._socket_pool = {}

        # Callback functions called at websocket connect and disconnect.
        # Normal function or async function.
        # Function has two argument.
        # The first argument is the socket ID where the event occurred.
        # The second argument is the event name 'connect' or 'disconnect'.
        self._socket_events = set()

        self._message_handler = lambda a,b,c: None

    # --------------------
    # The following four method are required for extended websockets.
    def url_path(self) -> str:
        """Returns the websocket URL pathname"""
        return self._url_path

    # Not implemented
    # async def startup_handler(self) -> None
    # async def shutdown_handler(self) -> None

    def endpoint(self):
        """Return websocket endpoint"""
        return self.socket_handler
    # --------------------

    def set_connection_limit(self, limit: int=0) -> None:
        """Set socket quantity limit.

        If you set a value smaller than the number of
        already connected, the number of connections will
        temporarily exceed. However, new connections will
        not be accepted and will be reduced naturally.

        Parameters
        ----------
        limit: int, default 0 (unlimited)
            Number of sockets allowed to connect.
            0 means unlimited.
        """
        self._connection_limit = limit if limit >= 0 else 0

    def number_of_connections(self) -> int:
        """Get the number of currently connected sockets."""
        return self._connected

    def get_socket_id(self) -> tuple:
        """Get a tuple of currently connected socket ID.

        The socket ID is a unique number that is assigned to the socket
        by the server when websocket communication is established.
        This is an identification number uniquely assigned to the
        connected socket. Assigned from 1 in connection order.
        Multiple sockets may be connected from one client.

        It is different from the socket ID of sister library JsPyTextSocket.

        Returns
        ----------
        tuple
            (socket ID1, socket ID2, ...)
            An empty tuple if there are no connected socket.
        """
        return tuple(self._socket_pool.keys())

    def close_socket(self, socket_id: int) -> bool:
        """Disconnects the websocket with the specified socket ID.

        Parameters
        ----------
        socket_id: int
            socket ID to close.
            The socket ID is a unique number that is assigned to the socket
            by the server when websocket communication is established.
            Multiple sockets may be connected from one client.

            It is different from the socket ID of sister library JsPyTextSocket.

        Returns
        ----------
        bool
            If True, success to close.
            If False, the socket ID specified in the argument
            is not currently connected.
        """
        if socket_id in self._socket_pool:
            JsPyBackground.register_function(
                self._socket_pool[socket_id].close, [])
            return(True)
        else:
            return(False)

    def add_socket_event(self, func: typing.Callable) -> None:
        """Register the callback function called by websocket event.

        When websocket communication is connect and disconnect,
        the registration functions are called.

        Parameters
        ----------
        func: Callable
            Callbak function has two argument.
            The first is the socket ID where the event occurred.
            The second is the event name 'connect' or 'disconnect'.

        See Also
        ----------
        clear_socket_event()
        """
        self._socket_events.add(func)

    def clear_socket_event(self) -> None:
        """Clear all callback functions called by websocket event.

        See Also
        ----------
        add_socket_event()
        """
        self._socket_events.clear()

    def set_message_handler(self, callback: typing.Callable) -> None:
        """Register a callback function called when data arrives from client.

        Register a callback function when a websocket is received.
        Only one callback function is registered.
        Even if you set it multiple times, it will be overwritten.

        Parameters
        ----------
        callback: typing.Callable
            Called to be received from the client.
            Callbak function has three arguments.

            The first argument is the starlette.websockets.WebSocket class
            instance that suggests the websocket to communicate with.

            The second argument is the source socket ID.

            The third argument is bytes data.
        """
        self._message_handler = callback

    def reservecast(self, data: bytes, socket: typing.Union[
                    None, int, typing.List[int],
                    typing.Tuple[int], typing.Set[int]]=None) -> None:
        """Reserve to send bytes data to the specified sockets.

        This can be used on other than the main thread.
        Reserved for data transmission and processed later.
        Execution result and exception cannot be caught.

        Parameters
        ----------
        data: bytes
        socket: None or int or list or tuple or set, default None
            socket ID to send. If None, same as broadcast()
            The socket ID is a unique number that is assigned to the socket
            by the server when websocket communication is established.
            Multiple sockets may be connected from one client.

            It is different from the socket ID of sister library JsPyTextSocket.
        """
        JsPyBackground.register_function(self.multicast, (data, socket))

    def broadcast(self, data: bytes) -> typing.Awaitable:
        """Send bytes data to the currently connected sockets.

        Call on the main thread where the event loop is running.

        If Add the await keyword, it will wait until the transmission
        is completed. No exception occurs even if transmission fails.

        If you do not add the await keyword, the transmission is reserved
        and will be executed later.

        Parameters
        ----------
        data: bytes

        Returns
        ----------
        asyncio.gather instance with return_exceptions=True
        """
        cor_list = []
        for socket_id in self._socket_pool:
            cor_list.append(self._socket_pool[socket_id].send_bytes(data))
        return asyncio.gather(*cor_list, return_exceptions=True)

    def multicast(self, data: bytes, socket: typing.Union[
                  None, int, typing.List[int],
                  typing.Tuple[int], typing.Set[int]]=None) -> typing.Awaitable:
        """Send bytes data to the specified sockets.

        Call on the main thread where the event loop is running.

        If Add the await keyword, it will wait until the transmission
        is completed. No exception occurs even if transmission fails.

        If you do not add the await keyword, the transmission is reserved
        and will be executed later.

        Parameters
        ----------
        data: bytes
        socket: None or int or list or tuple or set, default None
            socket ID to send. If None, same as broadcast()
            The socket ID is a unique number that is assigned to the socket
            by the server when websocket communication is established.
            Multiple sockets may be connected from one client.

            It is different from the socket ID of sister library JsPyTextSocket.

        Returns
        ----------
        asyncio.gather instance with return_exceptions=True
        """
        cor_list = []
        if socket is None:
            return self.broadcast(data)
        elif isinstance(socket, int):
            if socket in self._socket_pool:
                cor_list.append(self._socket_pool[socket].send_bytes(data))
        elif isinstance(socket, (tuple, list, set)):
            for i in socket:
                if i in self._socket_pool:
                    cor_list.append(self._socket_pool[i].send_bytes(data))
        return asyncio.gather(*cor_list, return_exceptions=True)

    def _append_socket(self, ws: WebSocket) -> int:
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
        self._socket_serial += 1
        if self._socket_serial > JsPyBinarySocket.SERIAL_MAX:
            self._socket_serial = 1
        while self._socket_serial in self._socket_pool:
            self._socket_serial += 1
            if self._socket_serial > JsPyBinarySocket.SERIAL_MAX:
                self._socket_serial = 1
        self._socket_pool[self._socket_serial] = ws
        return(self._socket_serial)

    def _delete_socket(self, socket_id: int) -> None:
        """websocket unregistration

        Disable websocket of specified socket ID.

        Parameters
        ----------
        socket_id: int
            The socket ID is a unique number that is assigned to the socket
            by the server when websocket communication is established.
            Multiple sockets may be connected from one client.

            It is different from the socket ID of sister library JsPyTextSocket.
        """
        if socket_id in self._socket_pool:
            del self._socket_pool[socket_id]

    async def socket_handler(self, ws: WebSocket):
        """Processing when websocket is newly established

        When the websocket is connected from the client,
        the socket ID is assigned and the websocket is registered.
        """
        self._connected += 1
        await ws.accept()
        _socket_id = self._append_socket(ws)
        if self._connection_limit > 0 and\
           self._connected > self._connection_limit:
            await ws.close()
        else:
            for callback in self._socket_events:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(_socket_id, 'connect'))
                    else:
                        callback(_socket_id, 'connect')
                except:
                    pass
            try:
                while True:
                    message = await ws.receive()
                    if message["type"] == "websocket.receive":
                        if 'bytes' not in message:
                            await ws.close(code=status.WS_1003_UNSUPPORTED_DATA)
                            break
                        data = message['bytes']
                        try:
                            if not self._message_handler:
                                pass
                            elif(asyncio.iscoroutinefunction(self._message_handler)):
                                asyncio.create_task(
                                    self._message_handler(ws, _socket_id, data))
                            else:
                                self._message_handler(ws, _socket_id, data)
                        except:
                            pass
                    elif message["type"] == "websocket.disconnect":
                        break
            except:
                pass
        self._delete_socket(_socket_id)
        self._connected -= 1
        for callback in self._socket_events:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(
                        callback(_socket_id, 'disconnect'))
                else:
                    callback(_socket_id, 'disconnect')
            except:
                pass
