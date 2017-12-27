from uuid import uuid4
from blockchain import Blockchain
from pprint import pprint
from flask import Flask, jsonify, request
import json
from time import time
from time import sleep
import atexit

def exit_handler():
    prev_block = {'index': 0}
    with open('blockchain.txt', 'w') as text_file:
        text_file.truncate()
        for index, block in enumerate(blockchain.chain):
            print(json.dumps(block), file=text_file)

atexit.register(exit_handler)

# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

first_time = True
f = open('blockchain.txt')
for line in f.readlines():
    if first_time:
        blockchain.chain = []
        first_time = False
        
    print('loading chain...')
    blockchain.chain.append(json.loads(line))

@app.route('/mine', methods=['GET'])
def mine():
    print('\n //// in mine in mine ... ////')
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    print("\n Last_block:\n")
    pprint(last_block)
    #print("\n whole_chain:\n")
    #pprint(blockchain.chain)

    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    if proof == 'stopped':

        return jsonify({ 'message': 'stopped' }), 200

    else:
        # We must receive a reward for finding the proof.
        # The sender is "0" to signify that this node has mined a new coin.
        blockchain.new_transaction(
            sender="0",
            recipient=node_identifier,
            amount=1,
        )

        # Forge the new Block by adding it to the chain
        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof, previous_hash)

        response = { 'message': "New Block Forged",
            'index': block['index'],
            'transactions': block['transactions'],
            'proof': block['proof'],
            'previous_hash': block['previous_hash'],
            'node': node_identifier,
            'timestamp': time()
        }

        return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/validate', methods=['POST']) # MIGHT MESS SOMETHING UP CHANGED FROM POST
def validate():
    
    print('\n //// request.args\n')
    pprint(request.get_json())
    print('\n //// this_block\n')
    pprint(json.loads(request.get_json()['this_block']))
    print('\n //// last_block\n')
    pprint(json.loads(request.get_json()['last_block']))

    this_block = json.loads(request.get_json()['this_block'])
    last_block = json.loads(request.get_json()['last_block'])

    if blockchain.valid_proof(last_block['proof'], this_block['proof']):
        if this_block['index'] - blockchain.chain[-1]['index'] == 1:
            blockchain.chain.append(this_block)
            response = { 'add': True }

        elif this_block['index'] - blockchain.chain[-1]['index'] > 1:
            response = { 'add': True }

        elif this_block['index'] == blockchain.chain[-1]['index']:
            if this_block['timestamp'] < blockchain.chain[-1]['timestamp']:
                blockchain.subtract_block()
                blockchain.chain.append(this_block)
                response = { 'add': True }
            else:
                response = { 'add': False }
        else:
            response = { 'add': False }
    else:
        response = { 'add': False }

    return jsonify(response), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/chain_length', methods=['GET'])
def chain_length():
    response = {
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/add_chain', methods=['POST'])
def add_chain():
    values = request.get_json()
    print('\n //// values in add chain parameters json\n')
    pprint(values)

    # Check that the required fields are in the POST'ed data
    required = ['chain']
    if not all(k in values for k in required):
        return 'Missing values', 400

    chain = values['chain']

    for index, item in enumerate(chain):
        if item['index'] == 1:
            blockchain.chain = []

        blockchain.chain.append(item)

    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
        'message': 'new length from chain added'
    }

    return jsonify(response), 201

@app.route('/give_chain', methods=['GET'])
def give_chain():

    previous = request.args.get('previous')
    start_at = request.args.get('start_at_index')
    increment_by = request.args.get('increment_by')
    return_arr = []
    previous_found = False

    print('\n //// start_at and increment_by classes\n')
    print(start_at)
    print(increment_by)

    for index, item in enumerate(blockchain.chain):
        if item['previous_hash'] == previous:
            previous_found = True
            return_arr = blockchain.chain[int(start_at) + index + 1:int(increment_by) + int(start_at) + index]
            method = 'partial'

    if not previous_found:
        return_arr = blockchain.chain[int(start_at):int(increment_by) + int(start_at)]
        print('\n //// didnt find a previous hash in my chain, in give chain')
        method = 'partial/first_time'

    print('\n //// return_array from give chain return_arr\n')
    pprint(return_arr)

    response = {
        'chain': return_arr,
        'length': len(return_arr),
        'method': method
    }
    
    return jsonify(response), 200

@app.route('/previous', methods=['GET'])
def previous():

    return jsonify(blockchain.last_block), 200

@app.route('/subtract_block', methods=['GET'])
def subtract_block():

    blockchain.subtract_block()

    response = {
        'result': "block removed"
    }

    return jsonify(response), 200

@app.route('/set_break_cycle', methods=['GET'])
def set_break_cycle():

    blockchain.set_break_cycle()

    response = {
        'message': 'set_break_cycle used'
    }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)