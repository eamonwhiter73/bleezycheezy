import json
from pprint import pprint
import filecmp

i = 2
f = open('blockchain.txt')
prev_line = ""
node1 = ''
n1count = 0
n2count = 0
n3count = 0
node2 = ''
node3 = ''
discovered = False
for line in f.readlines():
	if json.loads(line)['index'] > 1:
	    pprint(json.loads(line))
	    if prev_line != '' and json.loads(line)['transactions'][0]['recipient'] != json.loads(prev_line)['transactions'][0]['recipient'] and not discovered:
	    	node1 = json.loads(prev_line)['transactions'][0]['recipient']
	    	node2 = json.loads(line)['transactions'][0]['recipient']
	    	discovered = True

	    if json.loads(line)['transactions'][0]['recipient'] != node1 and json.loads(line)['transactions'][0]['recipient'] != node2 and discovered:
	    	node3 = json.loads(line)['transactions'][0]['recipient']

	    if i != json.loads(line)['index']:
	        print(f'\n //// something is wrong indexes dont match, index: {i}')
	        break

	    if json.loads(line)['transactions'][0]['recipient'] == node1:
	    	n1count+=1

	    if json.loads(line)['transactions'][0]['recipient'] == node2:
	    	n2count+=1

	    if json.loads(line)['transactions'][0]['recipient'] == node3:
	    	n3count+=1

	    #if prev_line != '' and (json.loads(line)['timestamp'] <= json.loads(prev_line)['timestamp']):
	    	#print(f'\n //// something is wrong with the timestamps: {i}')
	    	#break

	    i += 1
	    prev_line = line

print('\n //// node1:\n')
print(node1)
print(str(n1count))
print('\n //// node2:\n')
print(node2)
print(str(n2count))
print('\n //// node3:\n')
print(node3)
print(str(n3count))

x = filecmp.cmp('blockchain.txt', 'blockchain1.txt')
print(str(x))

x = filecmp.cmp('blockchain.txt', 'blockchain2.txt')
print(str(x))

f.close()
