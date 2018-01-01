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

def get_connections():
    return connections

def exception_handler(request, exception):
    print("Request failed")

def chain_length_check(array):
    for index, item in enumerate(array):
        print('\n //// chain_length_check showing values in array')
        print(item)
        r = requests.get(item)
        connections[index]['length'] = json.loads(r.text)['length']

    r = requests.get('http://0.0.0.0:'+port+'/chain_length')

    return json.loads(r.text)['length']
    
def put_chains_together(prev):
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

    print('\n //// ' + prev)

    print('\n //// is this always the same? this is the previous block hash which decides what block to start at for give_chain\n')
    print(json.loads(prev)['previous_hash'])

    for index, inc in enumerate(increments):
        reqs.append(grequests.get("http://" + item['ip'] + ":" + item['port'] + "/give_chain", params = {'previous': json.loads(prev)['previous_hash'], 'start_at_index':start_ats[index] + 1, 'increment_by':inc})) # 1 added to start_at index because looking for previous_to_last_block
        
    request_chain_results = grequests.map(reqs, exception_handler=exception_handler)

    chains_to_add = [show_json(result) for result in request_chain_results]

    if json.loads(prev)['index'] > 1:
        r = requests.get('http://0.0.0.0:'+port+'/subtract_block')  
    
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

        pprint(chain['chain'])

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

        if len(chain['chain']) > 0:
            prev_chain = chain
        else:
            print('chain["chain"] is empty, moving on, saving previous')


    all_chains = sorted(all_chains, key = by_index_key)

    if len(all_chains) > 0:
        previous_block = json.dumps(all_chains[-1])

    return all_chains

def show_json(result):
    if result != None:
        return json.loads(result.content.decode())
    else:
        return json.loads('{"chain": []}')

def by_index_key(block):
    return block['index']

def by_length_key(result):
    return json.loads(result.content.decode())['length']

def by_connection_length_key(connection):
    return connection['length']

def search_for_connection(reply, address):
    found = False
    for index, item in enumerate(connections):
        if item['ip'] == address:
            item['port'] = reply
            found = True
            print('\n //// Found ip in my connections!\n')

    return found

while 1:
    for con in node:
        con.send_line(port)
        
        for reply in con:

            if reply.isdigit():
                found_here = search_for_connection(reply, con.addr)

                if not found_here:
                    print('\n //// Adding connection to connections\n')
                    connections.append({'ip': con.addr, 'port': reply, 'length': 0})

            elif ';' in reply:
                r = requests.get('http://0.0.0.0:' + port + '/set_break_cycle')

                blocks = reply.split(';')
                print('\n //// blocks 0')
                pprint(json.loads(blocks[0]))

                r = requests.get('http://0.0.0.0:' + port + '/chain_length')
                my_chain_length = json.loads(r.text)['length']

                if json.loads(blocks[0])['message'] != 'miner off' and json.loads(blocks[0])['index'] > my_chain_length:
                    my_chain_length = json.loads(blocks[0])['index']
                    i_need_the_chain = True
                    mining = False

                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                r = requests.post('http://0.0.0.0:'+port+'/validate', json = {'this_block': blocks[0], 'last_block': blocks[1]}, headers=headers)
                print('\n //// response from validate:\n')
                print(r.text)

                if json.loads(blocks[0])['message'] != 'miner off':
                    if json.loads(r.text)['add']:
                        print('\n //// sending out that the block is valid')
                        con.send_line(port+':validated'+json.loads(blocks[0])['node'])
                    else:
                        print('\n //// sending out that the block is invalid')
                        con.send_line(port+':invalid'+json.loads(blocks[0])['node'])

            elif mined_block != '' and json.loads(mined_block)['message'] != 'miner off':
                if ('validated'+json.loads(mined_block)['node']) in reply:
                    replies.append(reply)
                    print('\n //// received validated message\n')
                    print(str(len(replies)) + ': replies\n')
                    print(str(len(connections)) + ': connections\n')

                    if len(replies) > int(len(connections) * .5):
                        mining = True
                        replies = []

                        array = []
                        for index, item in enumerate(connections):
                            array.append(grequests.get('http://'+item['ip']+':'+item['port']+'/set_close_cycle'))

                        results = grequests.map(array, exception_handler=exception_handler)

                        print('\n //// I am fully validated ////\n')
                    else:
                        print('\n //// still not there - waiting for validations to come in\n')

                elif ('invalid'+json.loads(mined_block)['node']) in reply:
                    invalid_replies.append(reply)
                    port_of = reply.split(':')[0]

                    if len(invalid_replies) > int(len(connections) * .5):
                        invalid_replies = []
                        print('\n //// I have an invalid block ////\n')
                        r = requests.get('http://0.0.0.0:'+port+'/subtract_block')
                        if json.loads(r.text)['result'] == 'block removed':
                            print('\n //// block removed\n')
                            mining = True
                            i_need_the_chain = True

        if i_need_the_chain:
            r = requests.get('http://0.0.0.0:'+port+'/previous_to_last') #added because previous block gets deleted sometimes
            prev = r.text
            result = put_chains_together(prev)

            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            r = requests.post('http://0.0.0.0:'+port+'/add_chain', json = {'chain': result}, headers=headers)
            print("\n ////new_chain_length_and_chain\n")

            i_need_the_chain = False
            mining = True

        if len(node.inbound) < len(connections):
            connections = []

    #### MINING ####
    if (mining and not i_need_the_chain) or (len(node.inbound) <= len(connections)):

        r = requests.get('http://0.0.0.0:'+port+'/previous')
        previous_block = r.text

        print('\n //// next to last block mined\n')
        print(previous_block)
        if len(connections) > 0:
            array = []
            for index, item in enumerate(connections):
                array.append('http://'+item['ip']+':'+item['port']+'/chain_length')

            my_chain_length = chain_length_check(array)

            connections = sorted(connections, key = by_connection_length_key)

            if connections[-1]['length'] <= my_chain_length:
                r = requests.get('http://0.0.0.0:'+port+'/mine')
                mined_block = r.text

                #arr = []
                #for index, item in enumerate(connections):
                #    arr.append(grequests.get('http://'+item['ip']+':'+item['port']+'/set_break_cycle'))

                #res = grequests.map(arr, exception_handler=exception_handler)
                if json.loads(mined_block)['message'] != 'miner off':

                    for c in node:
                        c.send_line(mined_block+';'+previous_block+';'+port)

                    array = []
                    for index, item in enumerate(connections):
                        array.append(grequests.get('http://'+item['ip']+':'+item['port']+'/set_break_cycle'))

                    results = grequests.map(array, exception_handler=exception_handler)

                    mining = False   

                    print('\n //// last block mined\n')
                    print(mined_block)

            else:
                i_need_the_chain = True

        else:
            r = requests.get('http://0.0.0.0:'+port+'/mine')
            mined_block = r.text

            #arr = []
            #for index, item in enumerate(connections):
            #    arr.append(grequests.get('http://'+item['ip']+':'+item['port']+'/set_break_cycle'))

            #res = grequests.map(arr, exception_handler=exception_handler)
            if json.loads(mined_block)['message'] != 'miner off':

                for c in node:
                    c.send_line(mined_block+';'+previous_block+';'+port)

                array = []
                for index, item in enumerate(connections):
                    array.append(grequests.get('http://'+item['ip']+':'+item['port']+'/set_break_cycle'))

                results = grequests.map(array, exception_handler=exception_handler)

                mining = False   

                print('\n //// last block mined\n')
                print(mined_block)


    time.sleep(1)

