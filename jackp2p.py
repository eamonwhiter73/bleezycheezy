from pyp2p.net import *
import time
import urllib.request
import json
import requests
from pprint import pprint

#Setup jack's p2p node.
jack = Net(passive_bind="192.168.1.131", passive_port=44446, interface="en0", node_type="passive", debug=1, type="direct")
jack.start()
jack.bootstrap()
jack.advertise()

#Event loop.
boolean = False
while 1:
    #time.sleep(100) #neccessary to make sure no connections?
    if boolean or not jack.inbound:
        response = urllib.request.urlopen("http://0.0.0.0:5000/mine")
        res = response.read()
    for con in jack:
        if not boolean:
            r = requests.get("http://0.0.0.0:5000/previous")
            pprint("\n ////self_previous_hash:\n" + r.text + "\n")
            #jsonData3 = json.loads(r.text)
            r2 = requests.get("http://" + con.addr + ":5000/give_chain", params = {'previous':r.text})
            jsonData2 = json.loads(r2.text)
            
            pprint("\n ////chain_returned:")
            pprint(jsonData2)
            pprint("\n")

            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            r3 = requests.post('http://0.0.0.0:5000/add_chain', json=jsonData2, headers=headers)
            pprint("\n ////self_new_chain_length:\n" + r3.text + "\n")
            boolean = True
        else:
            print("Connection address:")
            pprint(con.addr)
            print(res)
            jsonData = json.loads(res)
            my_node = jsonData['node']
            r8 = requests.get("http://0.0.0.0:5000/chain_length")
            print(r8.text)

            string = ''
            for index, item in enumerate(res.decode()):
            	string = string + item
                #string = string + item.decode()
            
            string = string.replace("'", "")
            print(string)

            j = json.loads(r8.text)
            dat = {
                'length': j['length'],
                'res': json.dumps(json.loads(string))
            }

            pprint(res)
            print("THIS IS THE 222")
            print("THIS IS THE 222")
            print("THIS IS THE 222")

            pprint(dat)
            print("THIS IS THE DUMPS")
            print("THIS IS THE DUMPS")
            print("THIS IS THE DUMPS")

            con.send_line(json.dumps(dat))
            for reply in con:
                jsonData5 = json.loads(json.dumps(reply))
                pprint(jsonData5)
            
                jsonData5 = jsonData5.replace("'", "")
                jsonData5 = jsonData5.replace("/", "")

                print(jsonData5)

                string1 = ''
                for index, item in enumerate(res.decode()):
            	    string1 = string1 + item
                    #string = string + item.decode()
            
                string1 = string.replace("'", "")
                string1 = string.replace("/", "")

                print(string1)
                jsonData6 = json.loads(string1)
                jsonData8 = json.loads(jsonData5)
                if my_node == jsonData6['node']:
                    r9 = requests.get("http://0.0.0.0:5000/chain_length")
                    print(r9.text)
                    jsonData7 = json.loads(r9.text)
                    pprint(jsonData8['length'])
                    print("jsonData5 length")
                    print("jsonData5 length")
                    print("jsonData5 length")
                    if jsonData8['length'] > jsonData7['length']:
                        print(reply + "   ************    MY NODE WAS RETURNED TO ME *********  I AM WRONG **********")
                        r4 = requests.get("http://" + con.addr + ":5000/give_chain", params = {'previous':jsonData['previous_hash']})
                        print(r4.text)
                        print('this is from give_chain to be added &&&&&&&&&&')
                        print('this is from give_chain to be added &&&&&&&&&&')
                        print('this is from give_chain to be added &&&&&&&&&&')

                        print(r4.text)
                        jsonData2 = json.loads(r4.text)
                        pprint(jsonData2)
                        pprint('jsonData2')
                        pprint('jsonData2')
                        pprint('jsonData2')
                        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                        r5 = requests.post('http://0.0.0.0:5000/add_chain', json = jsonData2, headers=headers)
                        print(r5.text + ": new chain length /////////////")
                else:
                    print(reply)
                    print('this is reply on line 63')
                    print('this is reply on line 63')
                    print('this is reply on line 63')

                    sender_node = my_node
                    r6 = requests.get('http://0.0.0.0:5000/validate', params=jsonData5['res'])
                    print(r6.text)
                    jsonData4 = json.loads(r6.text)
                    if jsonData4['add']:
                        r7 = requests.post('http://0.0.0.0:5000/add_validated_block', json = jsonData5['res'], headers=headers)
                        print(r7.text)
                    else:
                        con.send_line(sender_node)

    time.sleep(1)