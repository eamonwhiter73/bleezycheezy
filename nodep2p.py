from pyp2p.net import *
import time
import grequests
import requests
from pprint import pprint
import json

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
first_time = True
i_need_the_chain = False
my_chain_length = 0
mining = True
mined_block = ''
previous_block = ''
did_mine_block = False
#fully_validated_count = 0
replies = []

def exception_handler(request, exception):
    print("Request failed")

def chain_length_check(ip, in_port):
    reqs = [
        grequests.get('http://' + ip + ':' + in_port + '/chain_length'),
        grequests.get('http://0.0.0.0:' + port + '/chain_length')
    ]

    results = grequests.map(reqs, exception_handler=exception_handler)
    return results

def put_chains_together(prev_hash):
    reqs = []
    above_previous = 0
    for index, item in enumerate(connections):
        reqs.append(grequests.get("http://" + item['ip'] + ":" + item['port'] + "/give_chain", params = {'previous': prev_hash, 'start_at_index':above_previous, 'increment_by':int(my_chain_length / len(connections))}))
        above_previous += int(my_chain_length / len(connections))

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

def mine():
    if len(connections) == 0 or (not first_time and mining):

        reqs = [
            grequests.get('http://0.0.0.0:'+port+'/previous'),
            grequests.get('http://0.0.0.0:'+port+'/mine')
        ]

        results = grequests.map(reqs, exception_handler=exception_handler)
        print('\n //// results from previous and mine\n')
        print(results.__class__)
        pprint(results)

        print('\n //// last block mined\n')

        mined_block = results[1].content.decode()
        previous_block = results[0].content.decode()

        print('\n //// last block mined\n')
        print(mined_block)
        print('\n //// previous block to last block\n')
        print(previous_block)
        #send block out to be validated
        did_mine_block = True

    

while 1:

    mine()

    if len(connections) > 0 and i_need_the_chain:
        
        prev_hash = json.loads(previous_block)['previous_hash']
        all_chains = put_chains_together(prev_hash)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        r = requests.post('http://0.0.0.0:'+port+'/add_chain', json = {'chain': all_chains}, headers=headers)
        print("\n ////new_chain_length\n")
        print(r.text) 

        i_need_the_chain = False

    for con in node:
        con.send_line(port)

        mine()

        if len(connections) > 0 and i_need_the_chain:
            
            prev_hash = json.loads(previous_block)['previous_hash']
            all_chains = put_chains_together(prev_hash)

            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            r = requests.post('http://0.0.0.0:'+port+'/add_chain', json = {'chain': all_chains}, headers=headers)
            print("\n ////new_chain_length\n")
            print(r.text) 

            i_need_the_chain = False

        if did_mine_block:
            con.send_line(mined_block+';'+previous_block)
            mining = False
            did_mine_block = False

        for reply in con:
            print('\n //// GOT REPLY\n')
            print(reply)
            is_digit = False

            if reply.isdigit():
                found = False
                is_digit = True
                for index, item in enumerate(connections):
                    if item['ip'] == con.addr:
                        item['port'] = reply
                        found = True

                if not found:
                    print('\n //// Adding connection to connections\n')
                    connections.append({'ip': con.addr, 'port': reply})
                    con.send_line(port)

                if first_time:
                    results = chain_length_check(con.addr, reply)

                    print('\n //// response in responses\n')
                    len_array = []
                    for result in results:
                        len_array.append(json.loads(result.content.decode())['length'])

                    if len_array[0] > len_array[1]:
                        i_need_the_chain = True
                        my_chain_length = len_array[0]
                        print('\n //// my chain length after check\n')
                        print(str(my_chain_length))

                    first_time = False

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
                print('\n //// I have an invalid block ////\n')
                r = requests.get('http://0.0.0.0:'+port+'/subtract_block')
                if json.loads(r.text)['result'] == 'block removed':
                    mined_block = ''
                    print('\n //// block removed\n')
                    mining = True

            else:
                if ';' in reply:
                    blocks = reply.split(';')
                    print('\n //// blocks 0')
                    pprint(json.loads(blocks[0]))
                    if json.loads(blocks[0])['message'] == 'New Block Forged':
                        #validate block
                        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                        r = requests.post('http://0.0.0.0:'+port+'/validate', json = {'last_block': blocks[1], 'this_block': blocks[0]}, headers=headers)
                        print('\n //// response from validate:\n')
                        print(r.text)
                        if json.loads(r.text)['add']:
                            print('\n //// sending out that the block is valid')
                            con.send_line(port)
                            con.send_line('validated'+json.loads(blocks[0])['node'])
                        else:
                            print('\n //// sending out that the block is invalid')
                            con.send_line(port)
                            con.send_line('invalid'+json.loads(blocks[0])['node'])

    time.sleep(1)