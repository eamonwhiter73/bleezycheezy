from pyp2p.net import *
import time
import grequests
import requests
from pprint import pprint
import json
import math

#Setup node's p2p node.
#node = Net(passive_bind='192.168.1.129', passive_port=44447, node_type='passive', debug=1)
node = Net(passive_bind='192.168.1.149', passive_port=44446, node_type='passive', debug=1)
#node = Net(passive_bind='192.168.1.131', passive_port=44445, node_type='passive', debug=1)
node.start()
node.bootstrap()
node.advertise()

connections = []
mining = True
i_need_the_chain = False
mined_block = ''
previous_block = ''
valid_replies = []
invalid_replies = []
first_time = True

def exception_handler(request, exception):
    print("Request failed")

def get_connections():
    return connections

def set_connections(array):
    connections = array[:]

def by_connection_length_key(connection):
    return connection['length']

def show_json(result):
    print('\n //// status_code of a give_chain result or didnt work')
    print(result.status_code)
    return json.loads(result.content.decode())

def by_index_key(block):
    return block['index']

def search_for_connection(addr, length):
    temp_connections = get_connections()
    found = False

    for c in temp_connections:
        if c['addr'] == addr:
            c['length'] = length
            found = True

    if not found:
        temp_connections.append({ 'addr': addr, 'length': length})

    set_connections(temp_connections)

def gather_chain(prev, chain_length):
    temp_connections = get_connections()
    reqs = []
    increment = 0
    start_at = 0

    temp_connections = sorted(temp_connections, key = by_connection_length_key)

    if len(temp_connections) > 0:
        increment = math.ceil(temp_connections[-1]['length'] / len(temp_connections))

    increments = []
    start_ats = [0]
    for index, item in enumerate(temp_connections):
        if increment + start_at > item['length']:
            new_increment = increment - (increment + start_at - item['length'])
            increments.append(new_increment)
        else:
            increments.append(increment)

        if index > 0:
            start_at += increments[index]
            start_ats.append(start_at)

    if sum(increments) > chain_length:
        for index, inc in enumerate(increments):
            reqs.append(grequests.get("http://" + temp_connections[index]['addr'] + ":5000/give_chain", params = {'previous': json.loads(prev)['previous_hash'], 'start_at_index':start_ats[index], 'increment_by':inc}))
        
        request_chain_results = grequests.map(reqs, exception_handler=exception_handler)

        chains_to_add = [show_json(result) for result in request_chain_results]
        
        all_chains = []
        for i, chain in enumerate(chains_to_add):
            prev = {}
            for index, ch in enumerate(chain['chain']):
                #pprint(ch)
                deleted = False
                if index > 0 and ch['index'] == prev['index']:
                    if ch['timestamp'] < prev['timestamp']:
                        del chain['chain'][index - 1]
                    else:
                        del chain['chain'][index]
                    
                    deleted = True

                if not deleted: 
                    all_chains.append(ch)

                prev = ch

        all_chains = sorted(all_chains, key = by_index_key)

        return all_chains

    else:
        return []

while 1:

    for con in node:
        length_req = requests.get('http://0.0.0.0:5000/chain_length')
        length = json.loads(length_req.text)
        con.send_line(str(length['length']))
        print('chain length: '+str(length['length']))

        for reply in con:
            if reply.isdigit():
                search_for_connection(con.addr, int(reply))

                if int(reply) + 1 > length['length'] or first_time:
                    i_need_the_chain = True

            if ';' in reply:
                incoming_block = reply.split(';')[0]
                incoming_prev_block = reply.split(';')[1]

                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                r = requests.post('http://0.0.0.0:5000/validate', json = {'this_block': incoming_block, 'last_block': incoming_prev_block}, headers=headers)
                print('\n //// response from validate:\n')
                print(r.text)

                if json.loads(r.text)['add']:
                    print('\n //// sending out that the block is valid')
                    con.send_line('validated'+json.loads(incoming_block)['node'])
                    print(str(i_need_the_chain))
                else:
                    print('\n //// sending out that the block is invalid')
                    con.send_line('invalid'+json.loads(incoming_block)['node'])
                    mining = True

                if json.loads(incoming_block)['index'] > length['length']:
                    length['length'] = json.loads(incoming_block)['index']
                    i_need_the_chain = True

            elif mined_block != '' and json.loads(mined_block)['message'] != 'miner off':
                if ('validated'+json.loads(mined_block)['node']) in reply:
                    valid_replies.append(reply)
                    print('\n //// received validated message\n')
                    print(str(len(valid_replies)) + ': replies\n')
                    print(str(len(connections)) + ': connections\n')

                    if len(valid_replies) > int(len(connections) * .5):
                        valid_replies = []

                        array = []
                        for index, item in enumerate(connections):
                            array.append(grequests.get('http://'+item['addr']+':5000/set_close_cycle'))

                        results = grequests.map(array, exception_handler=exception_handler)

                        mining = True

                        print('\n //// I am fully validated ////\n')
                    else:
                        print('\n //// still not there - waiting for validations to come in\n')

                elif ('invalid'+json.loads(mined_block)['node']) in reply:
                    invalid_replies.append(reply)

                    if len(invalid_replies) > int(len(connections) * .5):
                        invalid_replies = []
                        print('\n //// I have an invalid block ////\n')
                        r = requests.get('http://0.0.0.0:5000/subtract_block')
                        if json.loads(r.text)['result'] == 'block removed':
                            print('\n //// block removed\n')
                            mining = True

                            array = []
                            for index, item in enumerate(connections):
                                array.append(grequests.get('http://'+item['addr']+':5000/set_close_cycle'))

                            results = grequests.map(array, exception_handler=exception_handler)  

            if i_need_the_chain:
                result = gather_chain(previous_block, length['length'])
                if len(result) > 0:
                    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                    r = requests.post('http://0.0.0.0:5000/add_chain', json = {'chain': result}, headers=headers)
                    print("\n ////new_chain_length_and_chain\n")
                    pprint(result)
                    first_time = False
                    mining = True
                    i_need_the_chain = False

        if len(node.inbound) < len(connections):
            connections = []             

    if mining or len(connections) == 0:
        reqs = [
            grequests.get('http://0.0.0.0:5000/previous'),
            grequests.get('http://0.0.0.0:5000/mine')
        ]

        results = grequests.map(reqs, exception_handler=exception_handler)

        previous_block = results[0].content.decode()
        mined_block = results[1].content.decode()

        if json.loads(mined_block)['message'] != 'miner off':
            print('\n //// next to last block mined\n')
            print(previous_block)
            print('\n //// last block mined\n')
            print(mined_block)

            array = []
            for index, item in enumerate(connections):
                array.append(grequests.get('http://'+item['addr']+':5000/set_break_cycle'))

            results = grequests.map(array, exception_handler=exception_handler)

            for c in node:
                c.send_line(mined_block+';'+previous_block)

            mining = False

    time.sleep(1) 