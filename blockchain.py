# {
#     "index":0,
#     "timestamp":"",
#     "transactions":[
#         {
#             "sender":"",
#             "recipient":"",
#             "amount":5,
#         }
#     ],
#     "proof":"",
#     "previous_hash":"",
# }
import hashlib
import json
from time import time, sleep
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request
from argparse import ArgumentParser


class Blockchain:

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        # set里面的元素没有重复项
        self.nodes = set()

        self.new_block(proof=100, previous_hash = 1)

    def register_node(self, address:str):
        # http://127.0.0.1:5001
        # urlparse解析地址
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self,chain) -> bool:

        #取链条的第一个区块
        last_block = chain[0]
        #取链条的第一个区块
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if block['previous_hash']!=self.hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'],block['proof']):
                return False

            last_block = block
            current_index += 1

        return True



    def resolve_conflicts(self) -> bool:
        neighbours = self.nodes

        max_length = len(self.chain)
        new_chain = None

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                #response.json()把response从string转换成json格式
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False


    def new_block(self, proof, previous_hash = None):
        block = {
            'index':len(self.chain) + 1,
            'timestamp':time(),
            'transactions':self.current_transactions,
            'proof':proof,
            'previous_hash':previous_hash or self.hash(self.chain[-1])
        }

        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        self.current_transactions.append(
            {
                'sender':sender,
                'recipient':recipient,
                'amount':amount
            }
        )

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        #把json格式的区块信息转换成字符串，sort_key对字符排序，encode()
        block_string = json.dumps(block,sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof:int) -> int:
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof +=1
        print(proof)
        return proof

    # 判断条件
    def valid_proof(self, last_proof: int, proof: int) -> bool:
        # 把last_proof和proof拼接成字符串，编码
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[0:4] == "0000"



app = Flask(__name__)
blockchain = Blockchain()

node_identifier = str(uuid4()).replace('-','')

# 接收请求
@app.route('/transactions/new',methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ["sender","recipient","amount"]

    if values is None:
        return "No values",400

    # 每个在required里面的元素都在values中
    if not all(k in values for k in required):
        return "Missing values",400

    index = blockchain.new_transaction(values['sender'],
                               values['recipient'],
                               values['amount'])

    response = {"message":f'Transaction will be added to Block {index}'}
    return jsonify(response),201


@app.route('/mine',methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 增加一笔交易作为区块奖励
    blockchain.new_transaction(sender="0",
                               recipient=node_identifier,
                               amount=1)

    block = blockchain.new_block(proof, None)

    response = {
        "message":"New Block Forged",
        "index":block['index'],
        "transactions":block['transactions'],
        "proof":block['proof'],
        "previous_hash":block['previous_hash']
    }

    return jsonify(response),200


@app.route('/chain',methods=['GET'])
def full_chain():
    response = {
        'chain':blockchain.chain,
        'length':len(blockchain.chain)
    }
    # Flask中可以使用jsonify把jsonify变成字符串
    return jsonify(response),200


# {"nodes":["http://127.0.0.2:5000"]}
@app.route('/nodes/register',methods=['POST'])
def register_nodes():
    # 获取请求内容
    values = request.get_json()
    nodes = values.get("nodes")
    if nodes is None:
        return "Error:please supply a valid list of nodes",400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        "message":"New nodes have been added",
        "total_nodes":list(blockchain.nodes)
    }

    return jsonify(response),201

@app.route('/nodes/resolve',methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message':"Our chain is replaced",
            'new_chain':blockchain.chain
        }
    else:
        response = {
            'message': "Our chain is authoritative",
            'chain': blockchain.chain
        }

    return jsonify(response),200


if __name__=='__main__':

    parser = ArgumentParser()
    print('test=',parser)
    # -p --port 5001
    parser.add_argument('-p', '--port',default=5000,type=int,help='port to listen to')
    args = parser.parse_args()
    print('test=',args)
    port = args.port
    print('test=',port)

    app.run(host='0.0.0.0',port=port)


