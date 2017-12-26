from uuid import uuid4
from blockchain import Blockchain
from pprint import pprint
from flask import Flask, jsonify, request
import json
from time import time
from time import sleep

# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()
waiting = False

def by_index_key(block):
    return block['index']

@app.route('/mine', methods=['GET'])
def mine():
    print('\n //// in mine in mine ... ////')
    if not waiting:
        # We run the proof of work algorithm to get the next proof...
        if len(blockchain.chain) > 0:
            last_block = blockchain.last_block
            print("\n Last_block:\n")
            pprint(last_block)
            #print("\n whole_chain:\n")
            #pprint(blockchain.chain)

            last_proof = last_block['proof']
            proof = blockchain.proof_of_work(last_proof)

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
        else:
            return jsonify({'message': 'somehow you dont have a blockchain at all'}), 200

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

    last_proof = json.loads(request.get_json()['last_block'])['proof']
    proof = json.loads(request.get_json()['this_block'])['proof']
    print('\n ///// last_proof / this_proof\n')
    print(proof)
    print(last_proof)

    this_block = json.loads(request.get_json()['this_block'])

    if blockchain.valid_proof(last_proof, proof):
        if this_block['index'] == blockchain.last_block['index'] + 1:
            blockchain.chain.append(this_block)
            response = { 'add': True }
        else:
            if this_block['index'] == blockchain.last_block['index']:
                if this_block['timestamp'] > blockchain.last_block['timestamp']:
                    response = { 'add': False }
                else:
                    print('\n //// length of chain before')
                    len(blockchain.chain)
                    blockchain.subtract_block()
                    print('\n //// length of chain before')
                    len(blockchain.chain)
                    blockchain.chain.append(this_block)
                    response = { 'add': True }

            else:
                response = { 'add': False }
    else:
        response = { 'add': False}

    sleep(0.01)

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
            print('\n //// found a previous hash in my chain, in give chain')
            previous_found = True
            if len(blockchain.chain) < (int(increment_by) + index + int(start_at)):
                return_arr = blockchain.chain[(index + int(start_at) + 1):len(blockchain.chain) - 1]

            return_arr = blockchain.chain[(index + int(start_at) + 1):int(increment_by) + index + int(start_at)]
            method = 'partial'

    if not previous_found:
        print('\n //// didnt find a previous hash in my chain, in give chain')
        if len(blockchain.chain) < (int(increment_by) + int(start_at)):
            return_arr = blockchain.chain[int(start_at):len(blockchain.chain) - 1]

        return_arr = blockchain.chain[int(start_at):int(increment_by) + int(start_at)] 
        method = 'partial/first_time'


    print('\n //// return_arr return_arr\n')
    pprint(return_arr)

    response = {
        'chain': return_arr,
        'length': len(return_arr),
        'method': method
    }
    
    return jsonify(response), 200

@app.route('/start_mine', methods=['GET'])
def start_mine():

    waiting = False
    return jsonify({'message': 'mining started'}), 200

@app.route('/stop_mine', methods=['GET'])
def stop_mine():

    waiting = True
    return jsonify({'message': 'mining stopped'}), 200

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

@app.route('/add_block', methods=['POST'])
def add_block():

    block = json.loads(request.get_json()['block'])
    
    blockchain.chain.append(block)

    response = {
        'result': "block added"
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

    chain = sorted(values['chain'], key = by_index_key)

    if len(chain) > 0:
        print('\n //// index of first in the chain')
        print(str(chain[0]['index']))

        if chain[0]['index'] == 1:
            print('\n //// Getting whole chain on server side')
            blockchain.chain = []

        for index, item in enumerate(chain):
            if len(chain) > 0 and len(blockchain.chain) > 0:
                if chain[len(chain) - 1]['index'] < blockchain.chain[len(blockchain.chain) - 1]['index']:
                    print('\n //// block expunged because too small index\n')
                else:
                    blockchain.chain.append(item)
                    
            elif len(blockchain.chain) == 0:
                blockchain.chain.append(item)
                print('\n //// in add chain and apparently one of us doesnt have a chain!\n')

    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
        'message': 'new length from chain added'
    }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)