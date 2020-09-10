/*
JsPyBinarySocket.js

Overview
----------
Used in combination with Python library 'JsMeetsStarlette'.
'JsMeetsStarlette' is a web server framework.

'JsPyBinarySocket.js' is the basic library that communicates with the server on the browser side.
Controls sending and receiving of binary data on websocket.

License
----------
This software is released under the MIT License.
Copyright (c) 2020 meloncookie

Version
----------
0.0.0   2020.09.10

Requirements
----------
ES2017
*/
class JsPyBinarySocket{
    /**
     * Create and connect to a websocket entry point.
     * @param {string} [url_path='/jsmeetspy/binarysocket'] URL pathname.
     * @memberof JsPyBinarySocket
     */
    constructor(url_path='/jsmeetspy/binarysocket'){
        this.VERSION = '0.0.0;';
        this._url = null;
        this._websocket = null;
        this._message_handler = (socket, data) => {};
        this._socket_events = new Array();
        this.reconnect(url_path);
    }
    /**
     * Reconnect after disconnecting the websocket.
     * @param {string} [url_path='/jsmeetspy/binarysocket']
     * @returns {boolean} true: success, false: failure
     * @memberof JsPyBinarySocket
     */
    reconnect(url_path='/jsmeetspy/binarysocket'){
        if(this._websocket !== null && this._websocket.readyState !== WebSocket.CLOSED){
            return(false);
        }
        try{
            if(window.location.protocol === 'http:'){
                this._url = 'ws://'+window.location.host+url_path;
            }
            else if(window.location.protocol === 'https:'){
                this._url = 'wss://'+window.location.host+url_path;
            }
            else{
                this._url = null;
                this._websocket = null;
                return(false);
            }
            this._websocket = new WebSocket(this._url);
            this._websocket.binaryType = 'arraybuffer';
        }
        catch(e){
            this._url = null;
            this._websocket = null;
            return(false);
        }
        this._websocket.onmessage = (event) => {
            this._message_handler(this._websocket, event.data);
        };
        this._websocket.onclose = (event) => {
            for(let fn of this._socket_events){
                try{
                    fn();
                }
                catch(e){
                    // Do nothing
                }
            }
            this._websocket = null;
        };
        return(true);
    }
    /**
     * Close the websocket, if the websocket is open.
     * @returns {boolean} true: success, false: failure
     * @memberof JsPyBinarySocket
     */
    close(){
        if(this._websocket !== null && this._websocket.readyState === WebSocket.OPEN){
            this._websocket.close();
            return(true);
        }
        else{
            return(false);
        }
    }
    /**
     * Check that websocket connection with the server is established.
     * @returns {boolean} true: opened, false: not opened
     * @memberof JsPyBinarySocket
     */
    ready(){
        return(this._websocket !== null && this._websocket.readyState === WebSocket.OPEN);
    }
    /**
     * Send binary data (ArrayBuffer) to the server.
     * @param {ArrayBuffer} data
     * @returns {boolean} true: success, false: failure
     * @memberof JsPyBinarySocket
     */
    send(data){
        if(this._websocket !== null && this._websocket.readyState === WebSocket.OPEN){
            try{
                this._websocket.send(data);
                return(true);
            }
            catch(e){
                return(false);
            }
        }
        else{
            return(false);
        }
    }
    /**
     * Register a callback function that will be called when the socket is closed.
     * @param {Function} func Callback function with no argument.
     * @memberof JsPyBinarySocket
     */
    add_close_event(func){
        this._socket_events.push(func);
    }
    /**
     * Clear all callback functions that will be called when the socket is closed.
     * @memberof JsPyBinarySocket
     */
    clear_close_event(){
        this._socket_events.length = 0;
    }
    /**
     * Register a callback function called when data arrives from the server.
     *     The callback function has two arguments.
     *     The first argument is a Websocket instance.
     *     The second argument is a ArrayBuffer data.
     * @param {*} func Callback function with two arguments.
     * @memberof JsPyBinarySocket
     */
    set_message_handler(func){
        this._message_handler = func;
    }
}
