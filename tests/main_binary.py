import typing
import asyncio
import json
from starlette.websockets import WebSocket
from JsMeetsStarlette import JsMeetsPy, JsPyBinarySocket
from starlette.responses import PlainTextResponse

async def receiver(ws: WebSocket, socket_id: int, data: bytes) -> None:
    """Callback function when data is received

    Parameters
    ----------
    ws: starlette.websockets.WebSocket
    socket_id: int
        Data source socket ID
    data: bytes
        Received data
    """
    print('From socket ID {}, data: {}'.format(socket_id, str(data)))
    # If you want to send the data back, use the send_bytes method.
    # await ws.send_bytes(b'OK')

def onsocket(id: int, reason: str) -> None:
    """Callback function called for socket connection/disconnection from client

    Parameters
    ----------
    id: int
        Socket ID that generated the event
    reason: str
        "connect" or "disconnect"
    """
    print('Socket ID {} : {}'.format(id, reason))

# Access http://xxx/static/index_binary.html
app = JsMeetsPy(debug=True, static='static',
                templates='templates')

# Make websocket endpoint (URL path '/ws')
bs = JsPyBinarySocket.JsPyBinarySocket('/ws')
bs.set_message_handler(receiver)
bs.set_connection_limit(4)
bs.add_socket_event(onsocket)
# Register websocket endpoint in the app instance.
app.add_socket(bs)

# HTTP
@app.route('/broadcast', ['GET'])
def page_broadcast(request):
    if 'data' in request.query_params:
        bs.reservecast(request.query_params['data'].encode(), None)
    return PlainTextResponse('Broadcast: '+request.query_params['data'])

@app.route('/state', ['GET'])
def page_state(request):
    ids = bs.get_socket_id()
    connect = bs.number_of_connections()
    info = 'Now {} connections: {}'.format(connect, str(ids))
    return PlainTextResponse(info)

@app.route('/disconnect', ['GET'])
def page_disconnect(request):
    ids = bs.get_socket_id()
    if len(ids) >= 1:
        # Disconnect oldest socket
        bs.close_socket(ids[0])
    return PlainTextResponse('OK')
