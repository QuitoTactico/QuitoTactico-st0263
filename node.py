import requests
from flask import Flask, request, jsonify
import threading
import grpc
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2
import hashlib
import time
import json

app = Flask(__name__)

class Node:
    def __init__(self, ip: str, port: int, id: int, update_interval: int) -> None:
        self.ip = ip
        self.port = port
        self.id = id
        self.update_interval = update_interval
        self.successor = self
        self.predecessor = None
        self.files = {}

    def find_successor(self, node_id: int) -> dict:
        if self.predecessor and self.predecessor['id'] < self.id:
            if self.predecessor['id'] < node_id <= self.id:
                return self.to_dict()
        elif self.predecessor and self.predecessor['id'] > self.id:
            if node_id > self.predecessor['id'] or node_id <= self.id:
                return self.to_dict()

        if self.id < node_id <= self.successor['id']:
            return self.successor
        else:
            closest_preceding_node = self.closest_preceding_finger(node_id)
            return closest_preceding_node.find_successor(node_id)

    def closest_preceding_finger(self, node_id: int) -> 'Node':
        # lógica simplificada de finger table
        return self  # Para simplificación, retornamos el nodo actual.

    def to_dict(self) -> dict:
        return {'ip': self.ip, 'port': self.port, 'id': self.id}

    def notify(self, new_node: dict) -> str:
        if not self.predecessor or \
           (self.predecessor['id'] < new_node['id'] < self.id) or \
           (self.predecessor['id'] > self.id and (new_node['id'] > self.predecessor['id'] or new_node['id'] < self.id)):
            self.predecessor = new_node
            return f"Predecessor updated to {new_node['id']}"
        return "No update required"

@app.route('/find_successor', methods=['POST'])
def find_successor():
    data = request.json
    node_id = data['id']
    result = node.find_successor(node_id)
    return jsonify(result)

@app.route('/notify', methods=['POST'])
def notify():
    data = request.json
    result = node.notify(data)
    return jsonify({'message': result})

@app.route('/store_file', methods=['POST'])
def store_file():
    data = request.json
    filename = data['filename']
    node.files[filename] = f"Transfiriendo {filename}... Archivo transferido"
    return jsonify({'message': f"Archivo '{filename}' almacenado en el nodo {node.id}"})

@app.route('/lookup_file', methods=['POST'])
def lookup_file():
    data = request.json
    filename = data['filename']
    if filename in node.files:
        return jsonify({'message': f"Archivo '{filename}' encontrado en nodo {node.id} ({node.ip}:{node.port})"})
    else:
        return jsonify({'message': f"Archivo '{filename}' no encontrado"})

def serve_rest() -> None:
    app.run(host=node.ip, port=node.port)

def stabilize():
    while True:
        # lógica para estabilizar la red
        time.sleep(node.update_interval)

def main() -> None:
    with open('bootstrap.json', 'r') as f:
        config = json.load(f)
    
    ip = config.get("own_ip")
    port = config.get("own_port")
    update_interval = config.get("update_interval")
    
    node_id = hash_key(f'{ip}:{port}')
    global node
    node = Node(ip, port, node_id, update_interval)

    bootstrap_ip = config.get("bootstrap_ip")
    bootstrap_port = config.get("bootstrap_port")

    if bootstrap_ip and bootstrap_port:
        if bootstrap_ip != "" and bootstrap_port != "":
            url = f"http://{bootstrap_ip}:{bootstrap_port}/find_successor"
            response = requests.post(url, json={'id': node.id})
            node.successor = response.json()

    threading.Thread(target=serve_rest).start()
    threading.Thread(target=stabilize).start()
    threading.Thread(target=serve_grpc, args=(node,)).start()  # Iniciar gRPC en un hilo separado

def hash_key(key: str) -> int:
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % 2**16

if __name__ == '__main__':
    main()
