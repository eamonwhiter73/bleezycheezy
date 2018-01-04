from pyp2p.net import *
import time
import grequests
import requests
from pprint import pprint
import json
import math

#Setup node's p2p node.
#node = Net(passive_bind='192.168.1.129', passive_port=44447, node_type='passive', debug=1)
#node = Net(passive_bind='192.168.1.149', passive_port=44446, node_type='passive', debug=1)
node = Net(passive_bind='192.168.1.131', passive_port=44445, node_type='passive', debug=1)
node.start()
node.bootstrap()
node.advertise()

connections = []
former_connections_length = 0
invalid_replies = []
first_time = True
mined_block = ''
previous_block = ''
allow_mining = False
length = 0
index_in = 0

def exception_handler(request, exception):
    print("Request failed")

while 1:
    r_length = requests.get("http://0.0.0.0:5000/chain_length")
    length = json.loads(r_length.text)['length']

    for con in node:
        try:
            connections.index(con.addr)
        except ValueError:
            print('adding connection...')
            connections.append(con.addr)
        
        for reply in con:
            if reply.isdigit():
                if int(reply) > index_in:
                    index_in = int(reply)

    print('\n //// in reply looking at my length')
    print(str(length))
    print(str(index_in))

    if length <= index_in:
        r = requests.get("http://0.0.0.0:5000/start_mining")
    else:
        r = requests.get("http://0.0.0.0:5000/stop_mining")

    if len(connections) > former_connections_length:
        print('\n //// inside about to register\n')
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        r = requests.post('http://0.0.0.0:5000/nodes/register', json = {'nodes': [connections[-1]]}, headers=headers)

    former_connections_length = len(connections)

    if first_time:
        r = requests.get('http://0.0.0.0:5000/nodes/resolve')
        print('\n //// resolve message')
        print(r.text)
        first_time = False

    print('\n //// mined_block before entering mining zone\n')
    print(mined_block)
    if not mined_block or ('mining stopped' != json.loads(mined_block)['message']) or allow_mining:

        print('\n //// MINE MINE MINE\n')

        reqs = [
            grequests.get('http://0.0.0.0:5000/previous_block'),
            grequests.get('http://0.0.0.0:5000/mine')
        ]

        results_mining = grequests.map(reqs, exception_handler=exception_handler)

        previous_block = results_mining[0].content.decode()
        mined_block = results_mining[1].content.decode()

        print('\n //// last_block')
        print(results_mining[0].content.decode())
        print('\n //// mined_block')
        print(results_mining[1].content.decode())

        arr = []
        for connection in connections:
            arr.append(grequests.get("http://"+connection+":5000/stop_mining"))

        results = grequests.map(arr, exception_handler=exception_handler)

        reqs = []
        for connection in connections:
            reqs.append(grequests.get("http://"+connection+":5000/valid_chain", params = { 'prev_block': previous_block, 'block': mined_block }))

        results = grequests.map(reqs, exception_handler=exception_handler)

        tally = 0
        for result in results:
            print('\n //// result in results')
            if result is not None and json.loads(result.content.decode())['message'] != 'mining stopped':
                print(result.content.decode())
                if json.loads(result.content.decode())['valid'] == 'reject':
                    print('\n //// block_to_add')
                    print(json.loads(result.content.decode())['block_to_add'])
                    if length < json.loads(json.loads(result.content.decode())['block_to_add'])['index']:
                        r = requests.get("http://0.0.0.0:5000/valid_chain", params = { 'prev_block': json.loads(result.content.decode())['prev_block'], 'block': json.loads(result.content.decode())['block_to_add'] })
                        print('\n //// reject in valid')

                    if length == index_in:
                        r = requests.get('http://0.0.0.0:5000/start_mining')
                
                elif not json.loads(result.content.decode())['valid']:
                    tally += 1

                if tally > .5 * len(results):
                    print('\n //// block subtracted')
                    r = requests.delete('http://0.0.0.0:5000/subtract_block')
                    if json.loads(result.content.decode())['block_to_add']:
                        r = requests.get("http://0.0.0.0:5000/valid_chain", params = { 'prev_block': json.loads(result.content.decode())['prev_block'], 'block': json.loads(result.content.decode())['block_to_add'] })
                    #add his block
                    break

            for c in node:
                if json.loads(results_mining[1].content.decode())['message'] != 'mining stopped':
                    c.send_line(str(json.loads(results_mining[1].content.decode())['index']))
                    print('\n //// index of mined block')
                    print(str(json.loads(results_mining[1].content.decode())['index']))
                else:
                    c.send_line(str(length))
                    print('\n //// length of chain instead')
                    print(str(length))
                    print

        #reqs = []
        #for connection in connections:
        #    reqs.append(grequests.get("http://"+connection+":5000/start_mining"))

        #results = grequests.map(reqs, exception_handler=exception_handler)

    else:
        allow_mining = True

    time.sleep(1) 