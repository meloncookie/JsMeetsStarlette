/*
JsPyQueue.js

Overview
----------
A library that extends JsPyTextSocket.js. Load JsPyTextSocket.js before loading this library.
Any data can be sent and received between the cloud and server in the mutual queue.

License
----------
This software is released under the MIT License.
Copyright (c) 2020 meloncookie

Version
----------
0.0.0   2020.09.09

Requirements
----------
ES2017

Public functions
----------
JsPyQueue
    push_nowait(key)(data)
        Send data to the queue of the server.
        There is no guarantee performed.
    push(key, timeout=0)(data)
        Send data to the queue of the server.
        Guarantees the arrival of transmitted data.
    pop(key, default_value=undefined)
        Remove and return an element from the right side of the queue.(LIFO).
    shift(key, default_value=undefined)
        Remove and return an element from the left side of the queue.(FIFO).
    add_callback(func)
        Register a callback function when data arrives in the client queue.
    clear_callback()
        Clear all callback functions when data arrives in the client queue.
    is_empty(key)
        Whether data is empty in the queue with the key name.
    get_keys()
        Get an array of all key names that exist in the client queue.
    has(key)
        Whether a client queue with the specified key name exists.
    clear(key)
        Clear the inventory data of the client queue with the specified key name.
    clear_all()
        Clear the inventory data of the all client queue.
    remove(key)
        Delete client queue with the specified key name.
    remove_all()
        Delete all client queue.
*/
JsPyQueue = {};
// constants ***************************
JsPyQueue.VERSION = '0.0.0';
// valiable ****************************
JsPyQueue._queue_id = 0;
JsPyQueue._queue_stack = new Map();
JsPyQueue._queue_memory = new Map();
JsPyQueue._queue_callbacks = [];
// function ****************************
/**
 * Send data to the queue of the server.
 *     There is no guarantee arrival.
 * @param {string} key The key name that identifies the server side queue.
 * @returns {Function} Function that takes the data to be sent to the server queue as an argument.
 *     The data can be converted to a JSON format.
 *     An Error() exception is raised only if it could not be sent to the server.
 */
JsPyQueue.push_nowait = (key) => {
    function inner(data){
        JsPyQueue._queue_id += 1;
        if(JsPyQueue._queue_id > JsPyTextSocket._MAX_ID){
            JsPyQueue._queue_id = 1;
        }
        let this_id = JsPyQueue._queue_id;
        send_obj = {'protocol': 'queue', 'key': key, 'id': this_id,
                    'data': data, 'exception': null};
        if(! JsPyTextSocket.send_json(send_obj)){
            throw new Error("Could not send to server @javascript")
        }
    }
    return(inner);
};
/**
 * Send data to the queue of the server.
 *     Guarantees the arrival of transmitted data.
 * @param {string} key The key name that identifies the server side queue.
 * @param {number|null} [timeout=0] Maximum time to wait for acknowledgment from server.
 * @returns {async function} Takes the value passed to the queue as an argument.
 *     The data can be converted to a JSON format.
 *     Returns true if there is a receipt notification from the server. Otherwise false.
 */
JsPyQueue.push = (key, timeout=0) => {
    async function inner(data){
        JsPyQueue._queue_id += 1;
        if(JsPyQueue._queue_id > JsPyTextSocket._MAX_ID){
            JsPyQueue._queue_id = 1;
        }
        let this_id = JsPyQueue._queue_id;
        let send_obj = {'protocol': 'queue_call', 'key': key, 'id': this_id,
                        'data': data, 'exception': null};
        let call_promise = new Promise((resolve, reject) => {
            JsPyQueue._queue_memory.set(this_id, [resolve, reject]);
            if(! JsPyTextSocket.send_json(send_obj)){
                reject("Unable to communicate with the server @javascript");
            }
        });
        try{
            if(timeout === null || timeout <= 0){
                await call_promise;
            }
            else{
                await Promise.race([call_promise, JsPyTextSocket._time_raise(timeout)]);
            }
        }
        catch(error){
            return(false);
        }
        finally{
            JsPyQueue._queue_memory.delete(this_id);
        }
        return(true);
    }
    return(inner);
};
/**
 * Remove and return an element from the right side of the queue.(LIFO)
 * @param {string} key The key name that identifies the client side queue.
 * @param {any} [default_value=undefined] Return value when there is no valid queue data.
 * @returns {any} Queue value. If there is no data in the specified key queue, default_value is returned.
 */
JsPyQueue.pop = (key, default_value=undefined) => {
    if(JsPyQueue._queue_stack.has(key)){
        let key_array = JsPyQueue._queue_stack.get(key);
        if(key_array.length == 0){
            return(default_value);
        }
        else{
            return(key_array.pop());
        }
    }
    else{
        return(default_value);
    }
};
/**
 * Remove and return an element from the left side of the queue.(FIFO)
 * @param {string} key The key name that identifies the client side queue.
 * @param {any} [default_value=undefined] Return value when there is no valid queue data.
 * @returns {any} Queue value. If there is no data in the specified key queue, default_value is returned.
 */
JsPyQueue.shift = (key, default_value=undefined) => {
    if(JsPyQueue._queue_stack.has(key)){
        let key_array = JsPyQueue._queue_stack.get(key);
        if(key_array.length == 0){
            return(default_value);
        }
        else{
            return(key_array.shift());
        }
    }
    else{
        return(default_value);
    }
};
/**
 * Register a callback function when data arrives in the client queue.
 * @param {Function} func Function have one argument. It is the queue key name of the destination.
 */
JsPyQueue.add_callback = (func) => {
    JsPyQueue._queue_callbacks.push(func);
};
/**
 * Clear all callback functions when data arrives in the client queue.
 */
JsPyQueue.clear_callback = () => {
    JsPyQueue._queue_callbacks.length = 0;
};
/**
 * Whether data is empty in the queue with the key name.
 * @param {string} key The key name that identifies the client side queue.
 * @returns {boolean} True(not exit key name or empty), False(not empty)
 */
JsPyQueue.is_empty = (key) => {
    if(JsPyQueue._queue_stack.has(key)){
        return(JsPyQueue._queue_stack.get(key).length == 0);
    }
    else{
        return(true);
    }
};
/**
 * Get an array of all key names that exist in the client queue.
 * @returns {Array} Array of all key names.
 */
JsPyQueue.get_keys = () => {
    return(Array.from(JsPyQueue._queue_stack.keys()));
};
/**
 * Whether a client queue with the specified key name exists.
 * @param {string} key The key name that identifies the client side queue.
 * @returns {boolean} true: exist, false:not exist.
 */
JsPyQueue.has = (key) => {
    return(JsPyQueue._queue_stack.has(key));
};
/**
 * Clear the inventory data of the client queue with the key name.
 * @param {string} key The key name that identifies the server side queue.
 */
JsPyQueue.clear = (key) => {
    if(JsPyQueue._queue_stack.has(key)){
        JsPyQueue._queue_stack.get(key).length = 0;
    }
};
/**
 * Clear the inventory data of the all client queue.
 */
JsPyQueue.clear_all = () => {
    for(let key of JsPyQueue._queue_stack.keys()){
        JsPyQueue._queue_stack.get(key).length = 0;
    }
};
/**
 * Delete client queue with the specified key name.
 * @param {string} key Specified key name is deleted on the client.
 */
JsPyQueue.remove = (key) => {
    JsPyQueue._queue_stack.delete(key);
};
/**
 * Delete all client queue.
 */
JsPyQueue.remove_all = () => {
    JsPyQueue._queue_stack.clear();
};
/**
 * Processes data with protocol 'queue', 'queue_call'
 */
JsPyQueue._queue = (obj_data) => {
    if(JsPyQueue._queue_stack.has(obj_data['key'])){
        JsPyQueue._queue_stack.get(obj_data['key']).push(obj_data['data']);
    }
    else{
        JsPyQueue._queue_stack.set(obj_data['key'], [obj_data['data']]);
    }
    if(obj_data['protocol'] === 'queue_call'){
        send_obj = {'protocol': 'queue_return', 'key': obj_data['key'],
                    'id': obj_data['id'], 'data': null, 'exception': null};
        JsPyTextSocket.send_json(send_obj);
    }
    for(let callback of JsPyQueue._queue_callbacks){
        try{
            callback(obj_data['key']);
        }
        catch(e){
            // Do nothing
        }
    }
};
/**
 * Processes data with protocol 'queue_return'
 */
JsPyQueue._queue_return = (obj_data) => {
    let id = obj_data['id'];
    let success = (obj_data['exception'] === null);
    if(JsPyQueue._queue_memory.has(id)){
        if(success){
            // resolve(true);
            JsPyQueue._queue_memory.get(id)[0](true);
        }
        else{
            // reject("error message...")
            JsPyQueue._queue_memory.get(id)[1](obj_data['exception']);
        }
    }
};

JsPyTextSocket._add_protocol('queue', JsPyQueue._queue);
JsPyTextSocket._add_protocol('queue_call', JsPyQueue._queue);
JsPyTextSocket._add_protocol('queue_return', JsPyQueue._queue_return);
