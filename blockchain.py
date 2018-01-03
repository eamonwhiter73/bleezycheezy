import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
import requests
import ntplib
from time import ctime
from pprint import pprint

class Blockchain(object):
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.stop = False
        self.nodes = set()
        self.c = ntplib.NTPClient()
        # Create the genesis block
        self.new_block(previous_hash=1, proof=100)

    def register_node(self, node):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """
        self.nodes.add(node)

    def valid_chain(self, block, prev_block):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """
        self.stop_mine()

        print('\n //// MINING STOPPED\n')

        print('\n //// block entering valid_chain')
        pprint(block)

        if block is not None and block['message'] != 'mining stopped':
            if block['previous_hash'] == self.hash(prev_block):
                
                # Check that the Proof of Work is correct
                if self.valid_proof(prev_block['proof'], block['proof']):
                    if block['index'] == self.last_block['index']:
                        if self.last_block['timestamp'] > block['timestamp']:
                            del self.chain[-1]
                            self.chain.append(block)
                            print('\n //// true from equal index but older timestamp')
                            return True

                        elif self.last_block['timestamp'] == block['timestamp']:
                            print('\n //// true from timestamps are equal block isnt added')
                            return True
                        else:
                            print('\n //// true timestamp is newer not added but sending false')

                    elif block['index'] > self.last_block['index']:
                        print('\n //// true from index is greater and block is added')
                        self.chain.append(block)
                        return True
                    else:
                        print('\n //// false from adding block had index less than block already there')
                else:
                    print('\n //// false from not a valid proof')

            else:
                print('\n //// false from hashes arent equal')
                if (block['timestamp'] < self.last_block['timestamp']):
                    if (block['index'] == self.last_block['index']):
                        print('\n //// hashes arent equal but block is older, subtracting and adding')
                        del self.chain[-1]
                        self.chain.append(block)
                        return True
                    elif (block['index'] > self.last_block['index']):
                        self.chain.append(block)
                        return True
                    

            return False

        return 'reject'
            

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}:5000/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length:
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """
        servers = [
            "1.us.pool.ntp.org",
            "2.us.pool.ntp.org",
            "3.us.pool.ntp.org"
        ]

        response = {}

        try:
            response = self.c.request('0.us.pool.ntp.org')
        except Exception:
            for server in servers:
                try:
                    response = self.c.request(server)

                    if response:
                        break

                except Exception:
                    print('\n //// alternate ntp server didnt work')

        block = {
            'message': 'New Block Forged',
            'index': len(self.chain) + 1,
            'timestamp': response.tx_time or time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.chain[-1]['hash'],
        }

        # Calculate the hash of this new Block
        block['hash'] = self.hash(block)

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    def stop_mine(self):
        self.stop = True

    def start_mine(self):
        self.stop = False

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:5] == "00000"

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            if not self.stop:
                proof += 1
            else:
                break

        print(dedent(f'''
            New Proof found!
            
             New Proof: {proof}
            Last Proof: {last_proof}
        '''))

        return proof