import json

i = 1
f = open('blockchain.txt')
prev_line = '{"timestamp":0}'
for line in f.readlines():
    print(line)
    if i != json.loads(line)['index']:
        print(f'\n //// something is wrong indexes dont match, index: {i}')
        break
    if json.loads(prev_line)['timestamp'] >= json.loads(line)['timestamp']:
        print(f'\n //// something is wrong the timestamps are out of order at index: {i}')
        break
    i += 1
    prev_line = line