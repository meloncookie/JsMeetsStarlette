/*
JsPyFunction.js

Overview
----------
A library that extends JsPyTextSocket.js. Load JsPyTextSocket.js before loading this library.
Mutual functions can be called naturally between the cloud and the server.

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
JsPyFunction
    expose(key, func, exclusive=false)
        Expose javascript function to the server by specified key name.
    clear(key)
        Clear functions exposed to the server.
    is_running(key)
        Get execution status of javascript function with specified key name.
    get_keys()
        Get an array of key name exposed to the server.
    has(key)
        Verification of key name of javascript function exposed to the server.
    call_nowait(key)(...args)
        Execute the python function exposed by the server side key name.
        The return value or exception from the client is ignored. Reaching the server is not guaranteed.
    call(key, timeout=0)(...args)
        Execute the python function exposed by the server side key name.
        Wait for the return value from the server.
*/
JsPyFunction = {};
// constants ***************************
JsPyFunction.VERSION = '0.0.0';
// valiable ****************************
JsPyFunction._exposed_function = new Map();
JsPyFunction._call_id = 0;
JsPyFunction._call_memory = new Map();
// function ****************************
/**
 * Expose javascript function to the server by specified key name.
 * @param {string} key Key name exposing to server.
 * @param {Function} func Function called by specifying key name.(Normal or async function).
 * @param {boolean} [exclusive=false] Whether to run exclusively.
 * @returns {boolean} Successful(true) or unsuccessful(false) to expose.
 */
JsPyFunction.expose = (key, func, exclusive=false) => {
    if(JsPyFunction._exposed_function.has(key) && JsPyFunction._exposed_function.get(key)[2]){
        return(false);
    }
    JsPyFunction._exposed_function.set(key, [func, func.constructor.name === "AsyncFunction", false, exclusive ? []: null]);
    return(true);
};
/**
 * Clear functions exposed to the server.
 * @param {string} key Key name exposing to the server.
 * @returns {boolean} Successful(true) or unsuccessful(false).
 */
JsPyFunction.clear = (key) => {
    if(JsPyFunction._exposed_function.has(key) && ! JsPyFunction._exposed_function.get(key)[2]){
        JsPyFunction._exposed_function.delete(key);
        return(true);
    }
    return(false);
};
/**
 * Get execution status of javascript function with specified key name.
 * @param {string} key Key name exposing to the server.
 * @returns {boolean} Now running in the background(true) or not(false).
 */
JsPyFunction.is_running = (key) => {
    if(JsPyFunction._exposed_function.has(key)){
        return(JsPyFunction._exposed_function.get(key)[2]);
    }
    return(false);
};
/**
 * Get an array of key name exposed to the server.
 * @returns {Array} Array of key name.
 */
JsPyFunction.get_keys = () => {
    return(Array.from(JsPyFunction._exposed_function.keys()));
};
/**
 * Verification of key name of javascript function exposed to the server.
 * @param {string} key Key name exposing to the server.
 * @returns {boolean} The key name exists(true) or not(false)
 */
JsPyFunction.has = (key) => {
    return(JsPyFunction._exposed_function.has(key));
};
/**
 * Execute the python function exposed by the server side key name.
 *     The return value or exception from the client is ignored. Reaching the server is not guaranteed.
 * @param {string} key The key name of the function exposed by the server.
 * @returns {Function} Function with argument to python function exposed on server.
 *     The arguments must be positional argument that can be converted to JSON format.
 *     There is no return value or exception notification from the server.
 *     An Error() exception is raised only if there is an error in the server route.
 */
JsPyFunction.call_nowait = (key) => {
    function inner(){
        JsPyFunction._call_id += 1;
        if(JsPyFunction._call_id > JsPyTextSocket._MAX_ID){
            JsPyFunction._call_id = 1;
        }
        let this_id = JsPyFunction._call_id;
        let send_obj = {'protocol': 'function', 'key': key, 'id': this_id,
                        'data': Array.from(arguments), 'exception': null};
        if(! JsPyTextSocket.send_json(send_obj)){
            throw new Error("Could not send to server @javascript");
        }
    }
    return(inner);
};
/**
 * Execute the python function exposed by the server side key name.
 *     Wait for the return value from the server.
 * @param {string} key The key name of the function exposed by the server.
 * @param {number|null} [timeout=0] Maximum time to wait for a response from the server.
 * @returns {async function} Function with arguments to server side python. The arguments must be positional
 *     argument that can be converted to JSON format. There is a return value from a python function.
 *     If an exception occurs in the python function, throw the Error() exception.
 *     If a timeout occurs, an Error() exception will occur.
 */
JsPyFunction.call = (key, timeout=0) => {
    async function inner(){
        JsPyFunction._call_id += 1;
        if(JsPyFunction._call_id > JsPyTextSocket._MAX_ID){
            JsPyFunction._call_id = 1;
        }
        let this_id = JsPyFunction._call_id;
        let send_obj = {'protocol': 'function_call', 'key': key, 'id': this_id,
                        'data': Array.from(arguments), 'exception': null};
        let call_promise = new Promise((resolve, reject) => {
            JsPyFunction._call_memory.set(this_id, [resolve, reject]);
            if(! JsPyTextSocket.send_json(send_obj)){
                reject("Unable to communicate with the server @javascript");
            }
        });

        let return_value;
        try{
            if(timeout === null || timeout <= 0){
                return_value = await call_promise;
            }
            else{
                return_value = await Promise.race([call_promise, JsPyTextSocket._time_raise(timeout)]);
            }
        }
        catch(error){
            throw new Error(error);
        }
        finally{
            JsPyFunction._call_memory.delete(this_id);
        }
        return(return_value);
    }
    return(inner);
};
/**
 * Processes data with protocol 'function_return'
 */
JsPyFunction._return_from_py = (obj_data) => {
    let id = obj_data['id'];
    let data = obj_data['data'];
    let except = obj_data['exception'];
    if(JsPyFunction._call_memory.has(id)){
        if(!except){
            // resolve(data);
            JsPyFunction._call_memory.get(id)[0](data);
        }
        else{
            // reject(except);
            JsPyFunction._call_memory.get(id)[1](except);
        }
    }
};

JsPyTextSocket._add_protocol('function_return', JsPyFunction._return_from_py);
/**
 * Processes data with protocol 'function_call', 'function'
 */
JsPyFunction._call_from_py = async (obj_data) => {
    let key = obj_data['key'];
    let protocol = obj_data['protocol'];
    let send_obj = {'protocol': 'function_return', 'key': key,
                     'id': obj_data['id'], 'data': null, 'exception': null};
    if(! JsPyFunction._exposed_function.has(key)){
        send_obj['exception'] = 'Function key name is not registered @javascript';
    }
    else{
        let functional_set = JsPyFunction._exposed_function.get(key);
        let func = functional_set[0];
        let is_async = functional_set[1];
        let is_running = functional_set[2];
        let exclusive = functional_set[3];
        if(exclusive !== null && is_running){
            await(new Promise((resolve) => {exclusive.push(resolve);}));
        }
        functional_set[2] = true;
        try{
            if(is_async){
                send_obj['data'] = await func(...obj_data['data']);
            }
            else{
                send_obj['data'] = func(...obj_data['data']);
            }
        }
        catch(e){
            send_obj['data'] = null;
            send_obj['exception'] = "Javascript function raised exception @javascript";
        }
        if(exclusive !== null && exclusive.length > 0){
            exclusive.shift()(true);
        }
        else{
            functional_set[2] = false;
        }
    }
    if(protocol === 'function_call'){
        if(! JsPyTextSocket.send_json(send_obj)){
            send_obj['data'] = null;
            send_obj['exception'] = "Javascript function return value does not conform to JSON format @javascript";
            JsPyTextSocket.send_json(send_obj);
        }
    }
};

JsPyTextSocket._add_protocol('function_call', JsPyFunction._call_from_py);
JsPyTextSocket._add_protocol('function', JsPyFunction._call_from_py);
