/*
JsPyTextSocket.js

Overview
----------
Used in combination with Python library 'JsMeetsStarlette'.
'JsMeetsStarlette' is a web server framework.

'JsPyTextSocket.js' is the basic library that communicates with the server on the browser side.
Various functions are realized by this basic library and the following extension libraries.
Therefore, there are few opportunities to directly operate 'JsPyTextSocket.js'.
These extension libraries are loaded after 'JsPyTextSocket.js'.

1. JsPyFunction.js
You can call the server side python function like a javascript function and get the return value.
Also, expose the javascript function that can be called from the server.

2. JsPyQueue.js
Any data can be sent and received between the cloud and server in the mutual queue.

3. JsPubsub.js
Any data can be exchanged using a PUB-SUB model such as MQTT.

License
----------
This software is released under the MIT License.
Copyright (c) 2020 T.Katoh

Version
----------
0.0.0   2020.09.10

Requirements
----------
ES2017

Public functions
----------
JsPyTextSocket
    init()
        Establish communication with the server.
        The user does not need to call it because it is called automatically.
    ready()
        Check that websocket connection with the server is established.
    send_json(send_obj)
        Send JSON data to the server.
    get_socket_id()
        Get the socket ID of my own client.
*/
let JsPyTextSocket = {};
// constants ***************************
JsPyTextSocket.VERSION = '0.0.0';
JsPyTextSocket._URL_PATH = '/jsmeetspy/textsocket';
JsPyTextSocket._MAX_ID = 0XFFFFFFFF;
// valiable ****************************
JsPyTextSocket._protocol_table = new Map();
JsPyTextSocket._socket_events = new Array();
JsPyTextSocket._socket_id = null;
JsPyTextSocket._disconnect_reason = 'It has not been initialized yet.';
JsPyTextSocket._websocket = null;
JsPyTextSocket._url = null;
// function ****************************
/**
* Reconnect after disconnecting the websocket.
* @returns {boolean} true: success, false: failure
*/
JsPyTextSocket.reconnect = (url) => {
    if(JsPyTextSocket._websocket !== null && JsPyTextSocket._websocket.readyState !== WebSocket.CLOSED){
        return(false);
    }
    try{
        JsPyTextSocket._websocket = new WebSocket(url);
    }
    catch(e){
        JsPyTextSocket._websocket = null;
        JsPyTextSocket._socket_id = null;
        JsPyTextSocket._disconnect_reason = 'It has not been initialized yet.';
        return(false);
    }
    JsPyTextSocket._websocket.onmessage = (event) => {
        try{
            let msg_obj = JSON.parse(event.data);
            if('protocol' in msg_obj && 'key' in msg_obj && 'id' in msg_obj &&
                'data' in msg_obj && 'exception' in msg_obj && JsPyTextSocket._protocol_table.has(msg_obj['protocol'])){
                JsPyTextSocket._protocol_table.get(msg_obj['protocol'])(msg_obj);
            }
        }
        catch(e){
            // Do nothing
        }
    };
    JsPyTextSocket._websocket.onclose = (event) => {
        for(let fn of JsPyTextSocket._socket_events){
            try{
                fn();
            }
            catch(e){
                // Do nothing
            }
        }
        JsPyTextSocket._socket_id = null;
    };
    return(true);
};
/**
 * Establish communication with the server.
 * @returns {boolean} true: success, false: failure
 */
JsPyTextSocket.init = JsPyTextSocket.reconnect;
/**
 * Close the websocket, if the websocket is open.
 * @returns {boolean} true: success, false: failure
 */
JsPyTextSocket.close = () => {
    if(JsPyTextSocket._websocket !== null && JsPyTextSocket._websocket.readyState === WebSocket.OPEN){
        JsPyTextSocket._websocket.close();
        return(true);
    }
    else{
        return(false);
    }
}
/**
 * Check that websocket connection with the server is opened.
 * @returns {boolean} true: opened, false: not opened
 */
JsPyTextSocket.ready = () => {
    return(JsPyTextSocket._websocket !== null && JsPyTextSocket._websocket.readyState === WebSocket.OPEN);
};
/**
 * Send JSON data to the server.
 * @param {Object} send_obj Object that can be converted to JSON format.
 * @returns {boolean} true: success, false: failure
 */
JsPyTextSocket.send_json = (send_obj) => {
    if(JsPyTextSocket._websocket !== null && JsPyTextSocket._websocket.readyState === WebSocket.OPEN){
        try{
            JsPyTextSocket._websocket.send(JSON.stringify(send_obj));
            return(true);
        }
        catch(e){
            return(false);
        }
    }
    else{
        return(false);
    }
};
/**
 * Get the socket ID of my own client.
 * @returns {number} Socket ID (If null, connection with the server has not been established yet.)
 */
JsPyTextSocket.get_socket_id = () => {
    return(JsPyTextSocket._socket_id);
};
/**
 * Register websocket reception process.
 * @param {string} protocol protocol name.
 * @param {Function} func Processing function with one argument according to protocol name.
 *     The argument is the object that has the following five keys. (protocol, key, id, data, exception).
 */
JsPyTextSocket._add_protocol = (protocol, func) => {
    JsPyTextSocket._protocol_table.set(protocol, func);
};
/**
 * Register a callback function that will be called when the socket is closed.
 * @param {Function} func Callback function with no argument.
 */
JsPyTextSocket.add_close_event = (func) => {
    JsPyTextSocket._socket_events.push(func);
};
/**
 * Clear all callback functions that will be called when the socket is closed.
 */
JsPyTextSocket.clear_close_event = () => {
    JsPyTextSocket._socket_events.length = 0;
};
// Processes data with protocol 'system'
JsPyTextSocket._add_protocol('system', (obj_data) => {
    if(obj_data['key'] === 'connect'){
        let data = obj_data['data'];
        let except = obj_data['exception'];
        if(except){
            JsPyTextSocket._socket_id = null;
            JsPyTextSocket._disconnect_reason = except;
        }
        else{
            JsPyTextSocket._socket_id = data;
            JsPyTextSocket._disconnect_reason = '';
        }
    }
});
/**
 * Exception timer
 * @param {number} wake_sec Wakeup time [second].
 * @returns {Promise} Promise instance that will be rejected after a specified time.
 */
JsPyTextSocket._time_raise = (wake_sec) => {
    return(new Promise((resolve, reject) => {
           setTimeout(() => {reject("A timeout has occurred @javascript");}, Math.floor(wake_sec*1000));
    }));
};

// Initial settings
if(window.location.protocol === 'http:'){
    JsPyTextSocket._url = 'ws://'+window.location.host+JsPyTextSocket._URL_PATH;
    JsPyTextSocket.init(JsPyTextSocket._url);
}
else if(window.location.protocol === 'https:'){
    JsPyTextSocket._url = 'wss://'+window.location.host+JsPyTextSocket._URL_PATH;
    JsPyTextSocket.init(JsPyTextSocket._url);
}
else{
    JsPyTextSocket._url = null;
}
