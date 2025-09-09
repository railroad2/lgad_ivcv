import sys
import asyncio
import json
import websockets

class WSComm:
    def __init__(self, uri=None):
        self.uri = uri

    def send_data(self, data):
        cmd, ch = data.split()

        if cmd.lower() == "on":
            data1 = {'cmd':'set', 'ch':int(ch), "val":True}
        elif cmd.lower() == "off":
            data1 = {'cmd':'set', 'ch':int(ch), "val":False}
        elif cmd.lower() == "pinstat":
            data1 = {'cmd':'get'}
        else:
            print (f'Invalid command {data}', file=sys.stderr)
            return

        if data1['cmd'] == 'get':
            response = asyncio.run(self.send_data_once(data1))
            responsed = json.loads(response)

            if 'pins' in responsed.keys():
                return self._conv_pinstat(responsed['pins'])
            else:
                return response
        else:
            return  

    async def send_data_once(self, data, timeout=3, reply=None):
        if isinstance(data, dict):
            text = json.dumps(data)
            if reply is None:
                reply = (str(data.get("cmd", "")).lower() == "get")
        else:
            text = data
            if reply is None:
                reply = ("get" in text.lower())

        async with websockets.connect(self.uri, ping_interval=None, open_timeout=timeout) as ws:
            try:
                await asyncio.wait_for(ws.send(text), timeout=timeout)
                if reply:
                    response = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    return response
                return None
            except asyncio.TimeoutError:
                return "Timeout: no response from the websocket"



    def _conv_pinstat(self, datain):
        pinstat = [str(int(i)) for i in datain]
        return ' '.join(pinstat)

