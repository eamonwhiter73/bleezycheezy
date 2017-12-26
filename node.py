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
did_send_out_block = False

def exception_handler(request, exception):
    print("Request failed")

def chain_length_check():
    reqs = [
        grequests.get('http://0.0.0.0:' + port + '/chain_length'),
    ]

    for index, item in enumerate(connections):
        reqs.append(grequests.get("http://" + item['ip'] + ":" + item['port'] + "/chain_length"))

    results = grequests.map(reqs, exception_handler=exception_handler)
    
    for index, result in enumerate(results):
        if index > 0:
            connections[index - 1]['length'] = json.loads(result.content.decode())['length']

    my_length = results.pop(0)
    sorted_chain_lengths = sorted(results, key = by_length_key)
    sorted_chain_lengths.append(my_length)

    return sorted_chain_lengths

def put_chains_together(sorted_lengths):
    reqs = []
    increment = 0
    holder = 0

    print('\n //// Previous hash in put_chains_together')
    print(json.loads(previous_block)['previous_hash'])

    sorted_con_lengths = sorted(connections, key = by_connection_length_key)
    if len(sorted_lengths) > 1:

        longest_chain = json.loads(sorted_lengths[len(sorted_lengths) - 2].content.decode())['length']
        increment = math.ceil((longest_chain - json.loads(previous_block)['index']) / len(sorted_con_lengths))

    adjusted = False
    start_at = 0
    slack = 0
    for index, item in enumerate(sorted_con_lengths):
        #if index == len(sorted_con_lengths) - 1:
            #xincrement -= holder

        if adjusted:
            slack = old_increment - sorted_con_lengths[index - 1]['length']
            increment += slack
            adjusted = False

        if sorted_con_lengths[index]['length'] < (increment + slack) and not adjusted:
            increment = increment - (increment + slack - sorted_con_lengths[index]['length'])
            adjusted = True

        reqs.append(grequests.get("http://" + item['ip'] + ":" + item['port'] + "/give_chain", params = {'previous': json.loads(previous_block)['previous_hash'], 'start_at_index':start_at, 'increment_by':increment}))
        start_at += increment
        old_increment = increment

    request_chain_results = grequests.map(reqs, exception_handler=exception_handler)

    chains_to_add = [show_json(result) for result in request_chain_results]
    
    all_chains = []
    for chain in chains_to_add:
        print('\n //// chain in chains_to_add')
        pprint(chain)
        for ch in chain['chain']:
            all_chains.append(ch)

    return all_chains

def show_json(result):
    print('\n //// status_code of a give_chain result or didnt work')
    print(result.status_code)
    return json.loads(result.content.decode())

def by_length_key(result):
    return json.loads(result.content.decode())['length']

def by_connection_length_key(connection):
    return connection['length']

while 1:
    sorted_lengths = []

    if len(connections) > 0:
        connection = connections[0]
        sorted_lengths = chain_length_check()

        if len(sorted_lengths) > 1:
            if json.loads(sorted_lengths[len(sorted_lengths) - 1].content.decode())['length'] < json.loads(sorted_lengths[len(sorted_lengths) - 2].content.decode())['length']:
                i_need_the_chain = True
            else:
                i_need_the_chain = False

    if i_need_the_chain:
        r = requests.get('http://0.0.0.0:'+port+'/previous')
        previous_block = r.text
        all_chains = put_chains_together(sorted_lengths)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        r = requests.post('http://0.0.0.0:'+port+'/add_chain', json = {'chain': all_chains}, headers=headers)
        print("\n ////new_chain_length_and_chain\n")
        print(r.text)

        i_need_the_chain = False
        mining = True

    if (mining and not i_need_the_chain) or not (len(node.inbound) > len(connections)):
            #grequests.get('http://0.0.0.0:'+port+'/previous'),
        
        r = requests.get('http://0.0.0.0:'+port+'/previous')
        previous_block = r.text
        r1 = requests.get('http://0.0.0.0:'+port+'/mine')
        mined_block = r1.text
        #previous_block = results[0].content.decode()
        

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
            for c in node:
                c.send_line(mined_block+';'+previous_block+';'+port)
            did_mine_block = False
            mining = False
        else:
            mining = True

        for reply in con:
            if reply.isdigit():
                found = False
                for index, item in enumerate(connections):
                    if item['ip'] == con.addr:
                        item['port'] = reply
                        found = True
                        print('\n //// Found ip in my connections!\n')

                if not found:
                    print('\n //// Adding connection to connections\n')
                    connections.append({'ip': con.addr, 'port': reply})
                    #con.send_line(port)

                mining = True

            elif ';' in reply:
                blocks = reply.split(';')
                print('\n //// blocks 0')
                pprint(json.loads(blocks[0]))

                r = requests.get('http://0.0.0.0:' + port + '/chain_length')
                my_chain_length = json.loads(r.text)['length']

                if json.loads(blocks[0])['index'] > my_chain_length + 1:
                    my_chain_length = json.loads(blocks[0])['index']
                    i_need_the_chain = True

                else:
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

                    mining = True

            elif ('validated'+json.loads(mined_block)['node']) in reply:
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
                port_of = reply.split(':')[0]
                obj = chain_length_check()

                if len(obj) > 1:
                    if json.loads(obj[len(obj) - 1].content.decode())['length'] - json.loads(obj[len(obj) - 2].content.decode())['length'] == 1:
                        print('\n //// I have an invalid block ////\n')
                        r = requests.get('http://0.0.0.0:'+port+'/subtract_block')
                        if json.loads(r.text)['result'] == 'block removed':
                            print('\n //// block removed\n')
                            mining = True

                    elif json.loads(obj[len(obj) - 1].content.decode())['length'] < json.loads(obj[len(obj) - 2].content.decode())['length']:
                        i_need_the_chain = True
                        print('\n //// doing check in invalid my array is shorter than checked array\n')    

                    elif json.loads(obj[len(obj) - 1].content.decode())['length'] > json.loads(obj[len(obj) - 2].content.decode())['length']:
                        mining = True
                else:
                    print('\n //// length of obj is less than 1')            

    time.sleep(1)