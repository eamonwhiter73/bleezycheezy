from pyp2p.net import *
import time
import grequests
import requests
from pprint import pprint
import json
import math

#Setup node's p2p node.
node = Net(passive_bind='192.168.1.129', passive_port=44447, node_type='passive', debug=1)
#node = Net(passive_bind='192.168.1.149', passive_port=44446, node_type='passive', debug=1)
#node = Net(passive_bind='192.168.1.131', passive_port=44445, node_type='passive', debug=1)
node.start()
node.bootstrap()
node.advertise()

#Event loop.
port = "5000"
connections = []
mining = True
mined_block = ''
previous_block = ''
i_need_the_chain = True
#first_time = True
replies = []
my_chain_length = 0
invalid_replies = []

def set_my_chain_length(length):
    my_chain_length = length

def get_my_chain_length():
    return my_chain_length

def get_connections():
    return connections

def exception_handler(request, exception):
    print("Request failed")

def chain_length_check(array):
    reqs = [
        grequests.get('http://0.0.0.0:' + port + '/chain_length'),
    ]

    for index, item in enumerate(array):
        print('\n //// chain_length_check showing values in array')
        print(item)
        reqs.append(grequests.get(item))

    results = grequests.map(reqs, exception_handler=exception_handler)

    if len(reqs) - 1 == len(connections):
        for index, result in enumerate(results):
            if index > 0:
                connections[index - 1]['length'] = json.loads(result.content.decode())['length']
    
    return results

def put_chains_together(prev):
    reqs = []
    increment = 0
    start_at = 0
    connections = get_connections()
    my_length = get_my_chain_length()

    #array = []
    #for index, item in enumerate(connections):
    #    array.append('http://'+item['ip']+':'+item['port']+'/chain_length')

    #chain_length_check(array)

    connections = sorted(connections, key = by_connection_length_key)

    if len(connections) > 0:
        increment = math.ceil(connections[-1]['length'] / len(connections))

        if increment != 0:
            increments = []
            start_ats = [0]
            for index, item in enumerate(connections):
                if increment + start_at > item['length']:
                    new_increment = increment - (increment + start_at - item['length'])
                    increments.append(new_increment)
                else:
                    increments.append(increment)

                if index > 0:
                    start_at += increments[index]
                    start_ats.append(start_at)

            for index, inc in enumerate(increments):
                reqs.append(grequests.get("http://" + connections[index]['ip'] + ":" + connections[index]['port'] + "/give_chain", params = {'previous': json.loads(prev)['previous_hash'], 'start_at_index':start_ats[index], 'increment_by':inc}))
                
            request_chain_results = grequests.map(reqs, exception_handler=exception_handler)

            chains_to_add = [show_json(result) for result in request_chain_results]
            
            all_chains = []
            for i, chain in enumerate(chains_to_add):
                for index, ch in enumerate(chain['chain']):
                    my_length += 1
                    all_chains.append(ch)

            all_chains = sorted(all_chains, key = by_index_key)

            set_my_chain_length(my_length)

            return all_chains

        else:
            return []
    else:
        return []

def show_json(result):
    print('\n //// status_code of a give_chain result or didnt work')
    print(result.status_code)
    return json.loads(result.content.decode())

def by_index_key(block):
    return block['index']

def by_length_key(result):
    return json.loads(result.content.decode())['length']

def by_connection_length_key(connection):
    return connection['length']

def search_for_connection(port_in, length, address):
    found = False
    for index, item in enumerate(connections):
        if item['ip'] == address:
            item['port'] = port
            item['length'] = int(length)
            found = True
            print('\n //// Found ip in my connections!\n')

    if not found:
        print('\n //// Adding connection to connections\n')
        connections.append({'ip': con.addr, 'port': port_in, 'length': int(length)})

    print('\n //// connections')
    pprint(connections)

while 1:
    for con in node:
        print('\n //// being sent out')
        con.send_line(port+"--"+str(my_chain_length))
        print(port+"--"+str(my_chain_length))
        
        for reply in con:
            if '--' in reply:
                data = reply.split('--')
                search_for_connection(data[0], data[1], con.addr)

            elif '::' in reply:
                #r = requests.get('http://0.0.0.0:' + port + '/set_break_cycle')

                blocks = reply.split('::')
                print('\n //// blocks 0')
                pprint(json.loads(blocks[0]))

                if json.loads(blocks[0])['index'] > my_chain_length:
                    my_chain_length = json.loads(blocks[0])['index']
                    i_need_the_chain = True
                    mining = False

                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                r = requests.post('http://0.0.0.0:'+port+'/validate', json = {'this_block': blocks[0], 'last_block': blocks[1]}, headers=headers)
                print('\n //// response from validate:\n')
                print(r.text)

                #if json.loads(blocks[0])['message'] != 'miner off':
                if json.loads(r.text)['add']:
                    if json.loads(r.text)['to_chain']:
                        my_chain_length += 1

                    print('\n //// sending out that the block is valid')
                    con.send_line('validated'+json.loads(blocks[0])['node'])

                    r = requests.get('http://0.0.0.0:'+port+'/set_break_cycle')

                else:
                    print('\n //// sending out that the block is invalid')
                    con.send_line('invalid'+json.loads(blocks[0])['node'])

            elif mined_block != '' and json.loads(mined_block)['message'] != 'miner off':
                if ('validated'+json.loads(mined_block)['node']) in reply:
                    replies.append(reply)
                    print('\n //// received validated message\n')
                    print(str(len(replies)) + ': replies\n')
                    print(str(len(connections)) + ': connections\n')

                    if len(replies) > int(len(connections) * .5):
                        mining = True
                        replies = []
                        my_chain_length += 1

                        array = []
                        for index, item in enumerate(connections):
                            array.append(grequests.get('http://'+item['ip']+':'+item['port']+'/set_close_cycle'))

                        results = grequests.map(array, exception_handler=exception_handler)

                        print('\n //// I am fully validated ////\n')
                    else:
                        print('\n //// still not there - waiting for validations to come in\n')

                elif ('invalid'+json.loads(mined_block)['node']) in reply:
                    invalid_replies.append(reply)

                    if len(invalid_replies) > int(len(connections) * .5):
                        invalid_replies = []
                        print('\n //// I have an invalid block ////\n')
                        r = requests.get('http://0.0.0.0:'+port+'/subtract_block')
                        if json.loads(r.text)['result'] == 'block removed':
                            print('\n //// block removed\n')
                            mining = True
                            my_chain_length -= 1

        if len(node.inbound) < len(connections):
            connections = []

        if i_need_the_chain and len(connections) > 0:
            print('\n //// in i need the chain')
            print(str(connections[-1]['length']))
            print(str(my_chain_length))

            if connections[-1]['length'] > my_chain_length:
                r = requests.get('http://0.0.0.0:'+port+'/previous')
                prev = r.text
                result = put_chains_together(prev)

                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                r = requests.post('http://0.0.0.0:'+port+'/add_chain', json = {'chain': result}, headers=headers)
                print("\n ////new_chain_length_and_chain\n")
                pprint(result)

                i_need_the_chain = False
                mining = True

    if mining or (len(node.inbound) <= len(connections)):
        reqs = [
            grequests.get('http://0.0.0.0:'+port+'/previous'),
            grequests.get('http://0.0.0.0:'+port+'/mine')
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
                array.append(grequests.get('http://'+item['ip']+':'+item['port']+'/set_break_cycle'))

            results = grequests.map(array, exception_handler=exception_handler)

            for c in node:
                c.send_line(mined_block+'::'+previous_block)

            mining = False

        else:
            my_chain_length += 1

    time.sleep(1) 
