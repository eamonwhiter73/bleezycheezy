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

def exception_handler(request, exception):
    print("Request failed")

while 1:
    for con in node:
        try:
            connections.index(con.addr)
        except ValueError:
            print('adding connection...')
            connections.append(con.addr)
            
        for reply in con:
            print(reply)

    if len(connections) > former_connections_length:
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        r = requests.post('http://0.0.0.0:5000/nodes/register', json = {'nodes': [connections[-1]]}, headers=headers)

    former_connections_length = len(connections)

    if first_time:
        r = requests.get('http://0.0.0.0:5000/nodes/resolve')
        print('\n //// resolve message')
        print(r.text)
        first_time = False

    reqs = [
        grequests.get('http://0.0.0.0:5000/last_block'),
        grequests.get('http://0.0.0.0:5000/mine')
    ]

    results = grequests.map(reqs, exception_handler=exception_handler)

    previous_block = results[0].content.decode()
    mined_block = results[1].content.decode()

    print('\n //// last_block')
    print(results[0].content.decode())
    print('\n //// mined_block')
    print(results[1].content.decode())
    print('\n //// chain')
    r = requests.get('http://0.0.0.0:5000/chain')
    pprint(json.loads(r.text)['chain'])

    reqs = []
    for connection in connections:
        reqs.append(grequests.get("http://"+connection+":5000/valid_chain", params = { 'prev_block': previous_block, 'block': mined_block }))

    results = grequests.map(reqs, exception_handler=exception_handler)

    valid = True
    for result in results:
        print('\n //// result in results')
        print(result.content.decode())
        if not json.loads(result.content.decode())['valid']:
            invalid_replies.append(json.loads(result.content.decode())['valid'])

        if len(invalid_replies) > .5 * len(results):
            print('\n //// block subtracted')
            r = requests.delete('http://0.0.0.0:5000/subtract_block')
            valid = False
            break

    if valid:
        print('\n //// block validated')
    else:
        print('\n //// block invalid')

    time.sleep(1) 