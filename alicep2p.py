from pyp2p.net import *
import time
import urllib.request
import json
import requests
from pprint import pprint

#Setup alice's p2p node.
alice = Net(passive_bind="192.168.1.149", passive_port=44446, node_type="passive", debug=1)
alice.start()
alice.bootstrap()
alice.advertise()

#Event loop.
boolean = False
port = 5000
push_cons = []
working = True
while 1:
    #time.sleep(100) #neccessary to make sure no connections?
    if boolean or len(alice.inbound) == 0 and working:
        response = urllib.request.urlopen("http://0.0.0.0:5000/mine")
        res = response.read()

    for con in alice:
        con.send_line(str(port))
        if boolean:
            print("Connection address:")
            pprint(con.addr)
            print(res)
            jsonData = json.loads(res)
            my_node = jsonData['node']
            r8 = requests.get("http://0.0.0.0:5000/chain_length")
            print("\n //// chain_length_if_not_first_time_being_sent_out_with_block")
            print(r8.text)

            string = '' 
            for index, item in enumerate(res.decode()):
                string = string + item
                #string = string + item.decode()
            
            string = string.replace("'", "")

            j = json.loads(r8.text)
            dat = {
                'length': j['length'],
                'res': json.dumps(json.loads(string))
            }

            pprint(res)
            print("THIS IS THE BLOCK")
            print("THIS IS THE BLOCK")
            print("THIS IS THE BLOCK")

            pprint(dat)
            print("THIS IS BEING SENT OUT")
            print("THIS IS BEING SENT OUT")
            print("THIS IS BEING SENT OUT")

            con.send_line(json.dumps(dat))
            
            r11 = requests.get('http://0.0.0.0:5000/stop_mine')
            print("\n //// mining_stopped\n")
            print(r11.text)

            working = False
            
        for reply in con:
            is_digit = False
            if reply.isdigit():
                found = False
                is_digit = True
                for index, item in enumerate(push_cons):
                    if item['ip'] == con.addr:
                        item['port'] = int(reply)
                        found = True

                if not found:
                    push_cons.append({'ip': con.addr, 'port': int(reply)})

            if is_digit:
                if not boolean:
                    r = requests.get("http://0.0.0.0:5000/previous")
                    pprint("\n ////self_previous_hash:\n" + r.text + "\n")
                    #jsonData3 = json.loads(r.text)
                    r2 = requests.get("http://" + con.addr + ":" + str(push_cons[0]['port']) + "/give_chain", params = {'previous':r.text})
                    jsonData2 = json.loads(r2.text)
                    
                    pprint("\n ////chain_returned:")
                    pprint(jsonData2)
                    pprint("\n")

                    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                    r3 = requests.post('http://0.0.0.0:5000/add_chain', json=jsonData2, headers=headers)
                    pprint("\n ////self_new_chain_length:\n" + r3.text + "\n")
                    boolean = True
            else:
                #jsonData5 can be two different things
                jsonData5 = json.loads(json.dumps(reply))
                
                print('\n //// jsonData5 at the beginning:\n')
                print(reply)
                print(reply.__class__)

                string2 = ''
                string2 = reply.replace("\\", "")

                print('\n //// string2:\n')
                print(string2)

                string1 = ''
                for index, item in enumerate(res.decode()):
                    string1 = string1 + item
                    #string = string + item.decode()
        
                string1 = string1.replace("'", "")
                string1 = string1.replace("/", "")

                print(string1)
                jsonData6 = json.loads(string1)
                jsonData8 = json.loads(json.loads(reply)['res'])
                jsonData10 = json.loads(json.dumps(reply))
                #res_loaded = jsonData8['res']
                #print('\n //// resloaded\n')
                #print(res_loaded['node'])

                print('\n //// jsonData10[res]\n')
                pprint(jsonData10)
                print('\n //// jsonData5[res]\n')
                pprint(jsonData5)
                print('\n //// jsonData8[res]\n')
                pprint(jsonData8['node'])

                if my_node == jsonData6['node']:
                    r9 = requests.get("http://0.0.0.0:5000/chain_length")
                    print("\n //// chain_length_for_checking_who_is_ahead\n")
                    print(r9.text)
                    jsonData7 = json.loads(r9.text)

                    if jsonData10 > jsonData7['length']:
                        print("\n //// my_node_was_returned_to_me\n")
                        print(reply)
                        r10 = requests.get("http://0.0.0.0:5000/subtract_block")
                        print("\n //// block_subtracted\n")
                        print(r10.text)
                        for index, item in enumerate(push_cons):
                            if item['ip'] == con.addr:
                                r4 = requests.get("http://" + con.addr + ":" + str(item['port']) + "/give_chain", params = {'previous':jsonData['previous_hash']})
                                print(r4.text)
                                print('this is from give_chain to be added &&&&&&&&&&')
                                print('this is from give_chain to be added &&&&&&&&&&')
                                print('this is from give_chain to be added &&&&&&&&&&')

                                jsonData2 = json.loads(r4.text)

                                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                                r5 = requests.post('http://0.0.0.0:5000/add_chain', json = jsonData2, headers=headers)
                                print("\n ////new_chain_length\n")
                                print(r5.text)

                    working = True

                elif ("blockvalidated" in jsonData8['node']) and (my_node in jsonData8['node']):
                    r6 = requests.get('http://0.0.0.0:5000/start_mine')
                    print("\n //// mining_started\n")
                    print(r6.text)

                    working = True

                else:
                    print(reply)
                    print('this is reply on line 63')
                    print('this is reply on line 63')
                    print('this is reply on line 63')

                    sender_node = my_node
                    r6 = requests.get('http://0.0.0.0:5000/validate', params=jsonData8)
                    print("\n //// validated?\n")
                    print(r6.text)
                    jsonData4 = json.loads(r6.text)
                    if jsonData4['add']:
                        r7 = requests.post('http://0.0.0.0:5000/add_validated_block', json = jsonData8, headers=headers)
                        print("\n //// added_validated_block?\n")
                        print(r7.text)
                        con.send_line("blockvalidated:" + jsonData8['node'])
                    else:
                        con.send_line(jsonData8['node'])

                    working = True