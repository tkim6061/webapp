#!/usr/bin/env python3

import asyncio
import websockets as ws
import time
import multiprocessing as mp
import math
import csv
import json
import functools


async def listener(q_rdy_evt):
    """
    Listening thread:
        ***Originally listened to Pie Sockets websocket for messages.
        Reads provided csv and runs async counter and queues messages
        according to timestamps

    Inputs: 
        Task queue for queueing messages

    Outputs: 
        None
    """
    with open('avida_sample_data.csv', encoding='utf-8-sig') as csvfile:
        data = csv.reader(csvfile)
        timer = 0.0
        msg_num = 1
        for row in data:
            timestamp = row[0]
            while timer < (float(timestamp)):
                await asyncio.sleep(0.001)
                timer += 0.001
            q.put_nowait((msg_num, timer))
            msg_num += 1
            if not q.empty() and not q_rdy_evt.is_set():
                q_rdy_evt.set()

    # async with ws.connect('wss://demo.piesocket.com/v3/channel_1?api_key=VCXCEuvhGcBDP7XhiJJUDvR1e1D3eiVjgZ9VRiaV&notify_self') as websocket:
    #     while True:
    #         await websocket.recv()

async def calc_task(q_rdy_evt, msg_rdy_evt):
    """
    Main calculation task. Pops task from queue
    and calculates metrics and pushes to messaging queue for front end.
    Inputs:
        Task queue and Message queue
    Ouputs:
        None
    """
    last_time = 0
    result = 0
    while True:
        await q_rdy_evt.wait()

        (msg_num, value) = q.get_nowait()
        if last_time == 0:

            last_time = value - last_time
            calc_stats(last_time)
            (count, mean, agg_var) = running_stats
        else:
            result = value - last_time
            last_time = value
            calc_stats(result)
            (count, mean, var, sample_var) = get_stats()
            std_dev = math.sqrt(var)
            data_q.put_nowait((result, msg_num, count, mean, std_dev))
            # print ('msg_num is: ' , msg_num)
            msg_rdy_evt.set()
        if q.empty():
            q_rdy_evt.clear()

def calc_stats(new_val):
    """
    Helper for calc task
    """
    global running_stats
    (count, mean, agg_var) = running_stats
    count += 1
    if count > 1:
        delta = new_val - mean
        mean += delta / count
        delta2 = new_val - mean
        agg_var += delta * delta2
    running_stats = (count, mean, agg_var)

def get_stats():
    """
    Getter for stats
    """
    (count, mean, agg_var) = running_stats
    if count < 2:
        return float("nan")
    else:
        (count, mean, variance, sample_var) = (count, mean, agg_var / count, agg_var / (count - 1))
        return (count, mean, variance, sample_var)

async def handler(websocket, path, msg_rdy_evt):
    """
    Server handler function
    Awaits a connection from front end before starting message
    loop.
    """
    data = await websocket.recv()
    while True:
        await msg_rdy_evt.wait()
        (result, msg_num, count, mean, std_dev) = data_q.get_nowait()
        result = "{:.3f}".format(result)
        mean = "{:.3f}".format(mean)
        std_dev = "{:.3f}".format(std_dev)
        try:
            await websocket.send(json.dumps({
                'msg_num' : str(msg_num),
                'delta' : str(result),
                'count' : str(count),
                'mean' : str(mean),
                'std_dev' : str(std_dev)
            }))
            msg_rdy_evt.clear() 
        except ws.exceptions.ConnectionClosed:
            print('Connection closed')
            

async def my_server(msg_rdy_evt):
    """
    Server start function
    Passes arguments to handler via functools
    """
    start_server = await ws.serve(functools.partial(handler, msg_rdy_evt=msg_rdy_evt), "localhost", 8000)
    await start_server.server.serve_forever() 

async def run_task():
    """
    Main tasks:
        Listener task:
            Separate threads for handling messages received by socket
            When listening to socket, yields until message recieved, 
            When using .csv, yields for 0.001 seconds(smallest time unit
            between messages)
        calc_task:
            Main task that calculates metrics, reads from task queue
            and yields if the queue is empty.
        my_server:
            Server websocket for front end. Sends metrics as they become
            available. Yields if nothing to send.
    """
    q_rdy_evt = asyncio.Event()
    msg_rdy_evt = asyncio.Event()
    task0 = asyncio.create_task(listener(q_rdy_evt))
    task1 = asyncio.create_task(calc_task(q_rdy_evt, msg_rdy_evt))
    task2 = asyncio.create_task(my_server(msg_rdy_evt))
    await task0
    await task1
    await task2

if __name__ == "__main__":
    """"
    Entry point
    """
    q = asyncio.Queue(maxsize=512)
    data_q = asyncio.Queue(maxsize=128)
    running_stats = (0, 0, 0)
    asyncio.run(run_task())
