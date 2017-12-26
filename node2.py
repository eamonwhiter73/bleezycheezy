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

#Event loop.
port = "5000"
connections = []
mining = True
mined_block = ''
previous_block = ''
did_mine_block = False
i_need_the_chain = True
#first_time = True
replies = []
my_chain_length = 0
invalid_replies = []

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
                print('\n //// mine going in first')
                print(json.loads(result.content.decode())['length'])
    
    return results

def put_chains_together():
    reqs = []
    increment = 0
    start_at = 0
    connections = get_connections()

    array = []
    for index, item in enumerate(connections):
        array.append('http://'+item['ip']+':'+item['port']+'/chain_length')

    chain_length_check(array)

    connections = sorted(connections, key = by_connection_length_key)

    if len(connections) > 0:
        increment = math.ceil(connections[len(connections) - 1]['length'] / len(connections))

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
        reqs.append(grequests.get("http://" + item['ip'] + ":" + item['port'] + "/give_chain", params = {'previous': json.loads(previous_block)['previous_hash'], 'start_at_index':start_ats[index], 'increment_by':inc}))
        
    request_chain_results = grequests.map(reqs, exception_handler=exception_handler)

    chains_to_add = [show_json(result) for result in request_chain_results]
    
    prev_chain = {'chain':[]}
    all_chains = []
    for i, chain in enumerate(chains_to_add):
        if len(prev_chain['chain']) > 0 and len(chain['chain']) > 0:
            print('\n //// last block previous chain, first block current chain - check difference')
            pprint(prev_chain['chain'][-1])
            pprint(chain['chain'][0])
            last_block_prev_chain = prev_chain['chain'][-1]
            first_block_cur_chain = chain['chain'][0]
            if first_block_cur_chain['index'] > last_block_prev_chain['index'] + 1:
                chain_diff = first_block_cur_chain['index'] - last_block_prev_chain['index']
                r = requests.get("http://" + connections[-1]['ip'] + ":" + connections[-1]['port'] + "/give_chain", params = {'previous': last_block_prev_chain['previous_hash'], 'start_at_index':0, 'increment_by':chain_diff})
                missing_chain = json.loads(r.text)['chain']
                print('\n //// this is the missing chain')
                pprint(missing_chain)
                if len(missing_chain) > 0:
                    #del missing_chain[-(chain_diff + 2):-chain_diff]
                    for block in missing_chain[::-1]:
                        chain['chain'].insert(0, block)

        prev = {}
        for index, ch in enumerate(chain['chain']):
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

        if len(chain['chain']) > 0:
            prev_chain = chain
        else:
            print('chain["chain"] is empty, moving on, saving previous')


    all_chains = sorted(all_chains, key = by_index_key)

    return all_chains

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

while 1:

    if i_need_the_chain:
        r = requests.get('http://0.0.0.0:'+port+'/previous')
        previous_block = r.text
        result = put_chains_together()

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        r = requests.post('http://0.0.0.0:'+port+'/add_chain', json = {'chain': result}, headers=headers)
        print("\n ////new_chain_length_and_chain\n")
        print(r.text)

        i_need_the_chain = False
        mining = True

    if (mining and not i_need_the_chain) or not (len(node.inbound) > len(connections)):
        reqs = [
            grequests.get('http://0.0.0.0:'+port+'/previous'),
            grequests.get('http://0.0.0.0:'+port+'/mine')
        ]

        results = grequests.map(reqs, exception_handler=exception_handler)

        previous_block = results[0].content.decode()
        mined_block = results[1].content.decode()

        print('\n //// next to last block mined\n')
        print(previous_block)
        print('\n //// last block mined\n')
        print(mined_block)

        did_mine_block = True
        mining = False

    for con in node:
        con.send_line(port)

        if did_mine_block:
            print('\n //// sending out my block!\n')
            if 'mining stopped by new block' != json.loads(mined_block)['message']:
                con.send_line(mined_block+';'+previous_block+';'+port)
            else:
                print('\n //// mining stopped my new block, proceeding with duties \n')

            mining = False
            did_mine_block = False

        for reply in con:
            # if i send back my port do i ever need to do it again? first ping to network - receive - send back my port
            if reply.isdigit():
                found = False
                for index, item in enumerate(connections):
                    if item['ip'] == con.addr:
                        item['port'] = reply
                        found = True
                        print('\n //// Found ip in my connections!\n')

                if not found:
                    print('\n //// Adding connection to connections\n')
                    connections.append({'ip': con.addr, 'port': reply, 'length': 0})
                    #con.send_line(port)

            elif ';' in reply:
                blocks = reply.split(';')
                print('\n //// blocks 0')
                pprint(json.loads(blocks[0]))

                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                r = requests.post('http://0.0.0.0:'+port+'/validate', json = {'this_block': blocks[0], 'last_block': blocks[1]}, headers=headers)
                print('\n //// response from validate:\n')
                print(r.text)
                if json.loads(r.text)['add']:
                    print('\n //// sending out that the block is valid')
                    con.send_line(port+':validated'+json.loads(blocks[0])['node'])
                else:
                    print('\n //// sending out that the block is invalid')
                    con.send_line(port+':invalid'+json.loads(blocks[0])['node'])

            elif 'mining stopped by new block' != json.loads(mined_block)['message']:
                if ('validated'+json.loads(mined_block)['node']) in reply:
                    replies.append(reply)
                    print('\n //// received validated message\n')
                    print(str(len(replies)) + ': replies\n')
                    print(str(len(connections)) + ': connections\n')

                    if len(replies) == len(connections):
                        mining = True
                        replies = []
                        print('\n //// I am fully validated ////\n')
                    else:
                        print('\n //// still not there - waiting for validations to come in\n')

                elif ('invalid'+json.loads(mined_block)['node']) in reply:
                    invalid_replies.append(reply)
                    port_of = reply.split(':')[0]
                    array = ['http://'+con.addr+':'+port_of+'/chain_length']
                    results = chain_length_check(array)

                    print('\n //// results from invalid chain check\n')
                    print(json.loads(results[1].content.decode())['length'])
                    print(json.loads(results[0].content.decode())['length'])

                    if len(invalid_replies) > int(len(connections) * .5):
                        mining = True
                        invalid_replies = []

                        if json.loads(results[0].content.decode())['length'] - json.loads(results[1].content.decode())['length'] > 0:
                            print('\n //// I have an invalid block ////\n')
                            r = requests.get('http://0.0.0.0:'+port+'/subtract_block')
                            if json.loads(r.text)['result'] == 'block removed':
                                print('\n //// block removed\n')
                                mining = True

                        elif json.loads(results[0].content.decode())['length'] - json.loads(results[1].content.decode())['length'] == 0:
                            print('\n //// I have an invalid block ////\n')
                            r = requests.get('http://0.0.0.0:'+port+'/subtract_block')
                            if json.loads(r.text)['result'] == 'block removed':
                                print('\n //// block removed\n')
                                mining = False
                                i_need_the_chain = True
                        #elif json.loads(results[0].content.decode())['length'] - json.loads(results[1].content.decode())['length']
                        else:
                            i_need_the_chain = True
                            mining = False

    time.sleep(1)