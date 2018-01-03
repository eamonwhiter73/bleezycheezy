import hashlib
import json
from blockchain import Blockchain
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from pprint import pprint
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

f.close()

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }

    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    if proof > 0:
        blockchain.new_transaction(
            sender="0",
            recipient=node_identifier,
            amount=1,
        )

        # Forge the new Block by adding it to the chain
        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof, previous_hash)

        response = {
            'message': "New Block Forged",
            'index': block['index'],
            'transactions': block['transactions'],
            'proof': block['proof'],
            'previous_hash': block['previous_hash'],
            'timestamp': block['timestamp']
        }
        return jsonify(response), 200

    else:
        return jsonify({'message': 'mining stopped'}), 200

@app.route('/valid_chain', methods=['GET'])
def valid_chain():
    print('\n //// last 5 in chain\n')
    pprint(blockchain.chain)

    prev_block = request.args.get('prev_block')
    block = request.args.get('block')

    print('\n //// valid_chain last_block then block')
    print(prev_block)
    print(block)

    is_valid = blockchain.valid_chain(json.loads(block), json.loads(prev_block))

    print('\n //// valid or not and the block to add if needed')
    print(str(is_valid))
    pprint(blockchain.chain[-1])

    if len(blockchain.chain) > 1:
        response = { 'valid': is_valid, 'block_to_add': json.dumps(blockchain.chain[-1]), 'prev_block': json.dumps(blockchain.chain[-2]), 'message': 'validity check' }
    else:
        response = { 'valid': is_valid, 'block_to_add': json.dumps(blockchain.chain[-1]), 'prev_block': json.dumps(blockchain.chain[-1]), 'message': 'validity check' }

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

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/chain_length', methods=['GET'])
def chain_length():
    response = {
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/start_mining', methods=['GET'])
def start_mining():
    blockchain.start_mine()
    response = {
        'message': 'mining started'
    }
    return jsonify(response), 200 

@app.route('/stop_mining', methods=['GET'])
def stop_mining():
    blockchain.stop_mine()
    response = {
        'message': 'mining stopped'
    }
    return jsonify(response), 200 

@app.route('/previous_block', methods=['GET'])
def previous_block():
    return jsonify(blockchain.last_block), 200

@app.route('/subtract_block', methods=['DELETE'])
def subtract_block():
    del blockchain.chain[-1]
    return jsonify({ 'message': 'block subtracted' }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)