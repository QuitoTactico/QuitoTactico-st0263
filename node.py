import grpc
from concurrent import futures
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2
import hashlib
import threading
import sys
import time
import json

def hash_key(key):
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % 2**16

class ChordService(pb2_grpc.ChordServiceServicer):
    def __init__(self, node):
        self.node = node
        self.files = {}  #diccionario para guardar archivos (simulados)
    
    def FindSuccessor(self, request, context):
        id = request.id
        if self.node.predecessor and self.node.predecessor.id < self.node.id:
            if self.node.predecessor.id < id <= self.node.id:
                return self.node
        elif self.node.predecessor and self.node.predecessor.id > self.node.id:
            if id > self.node.predecessor.id or id <= self.node.id:
                return self.node
        if self.node.id < id <= self.node.successor.id:
            return self.node.successor
        else:
            with grpc.insecure_channel(f'{self.node.successor.ip}:{self.node.successor.port}') as channel:
                stub = pb2_grpc.ChordServiceStub(channel)
                return stub.FindSuccessor(pb2.Node(id=id, ip=self.node.ip, port=self.node.port))

    def Notify(self, request, context):
        predecessor_id = request.id
        if self.node.predecessor is None or \
           (self.node.predecessor.id < predecessor_id < self.node.id) or \
           (self.node.predecessor.id > self.node.id and (predecessor_id > self.node.predecessor.id or predecessor_id < self.node.id)):
            self.node.predecessor = request
            print(f"nodo {self.node.id} actualizó su predecesor a {request.id}")
        return pb2.Empty()

    def StoreFile(self, request, context):
        filename = request.filename
        self.files[filename] = f"Transfiriendo {filename}... Archivo transferido"
        return pb2.FileResponse(message=f"archivo '{filename}' almacenado en el nodo {self.node.id}")

    def LookupFile(self, request, context):
        filename = request.filename
        if filename in self.files:
            return pb2.FileResponse(message=f"archivo '{filename}' encontrado en nodo {self.node.id} ({self.node.ip}:{self.node.port})")
        else:
            return pb2.FileResponse(message=f"archivo '{filename}' no encontrado")

    def TransferFile(self, request, context):
        filename = request.filename
        if filename in self.files:
            return pb2.FileResponse(message=self.files[filename])
        else:
            return pb2.FileResponse(message=f"archivo '{filename}' no encontrado")

def serve(node):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_ChordServiceServicer_to_server(ChordService(node), server)
    server.add_insecure_port(f'{node.ip}:{node.port}')
    server.start()
    server.wait_for_termination()

class Node:
    def __init__(self, ip, port, id, update_interval):
        self.ip = ip
        self.port = port
        self.id = id
        self.update_interval = update_interval
        self.successor = self
        self.predecessor = None

    def join_network(self, existing_node):
        with grpc.insecure_channel(f'{existing_node.ip}:{existing_node.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            self.successor = stub.FindSuccessor(pb2.Node(ip=self.ip, port=self.port, id=self.id))

    def stabilize(self):
        while True:
            try:
                with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
                    stub = pb2_grpc.ChordServiceStub(channel)
                    x = stub.FindSuccessor(pb2.Node(id=self.successor.id)).id
                    if x != self.successor.id and (self.id < x < self.successor.id or
                                                   (self.id > self.successor.id and (x > self.id or x < self.successor.id))):
                        self.successor = x
                        print(f"nodo {self.id} actualizó su sucesor a {x}")
                    
                    stub.Notify(pb2.Node(id=self.id, ip=self.ip, port=self.port))
            except Exception as e:
                print(f"error en estabilización: {e}")
            time.sleep(self.update_interval)

    def store_file(self, filename):
        with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            response = stub.StoreFile(pb2.FileRequest(filename=filename))
            print(response.message)

    def lookup_file(self, filename):
        with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            response = stub.LookupFile(pb2.FileRequest(filename=filename))
            print(response.message)

    def list_files(self):
        if hasattr(self, 'files') and self.files:
            print("archivos almacenados en este nodo:")
            for filename in self.files:
                print(f" - {filename}")
        else:
            print("no hay archivos almacenados en este nodo")

def main():
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    ip = config.get("own_ip")
    port = config.get("own_port")
    update_interval = config.get("update_interval")
    
    id = hash_key(f'{ip}:{port}')
    node = Node(ip, port, id, update_interval)

    bootstrap_ip = config.get("bootstrap_ip")
    bootstrap_port = config.get("bootstrap_port")

    if bootstrap_ip and bootstrap_port:
        if bootstrap_ip != "" and bootstrap_port != "":
            existing_node = Node(bootstrap_ip, int(bootstrap_port), None, update_interval)
            node.join_network(existing_node)
    else:
        print(f"nodo {node.id} es el primer nodo en la red")

    threading.Thread(target=serve, args=(node,)).start()
    threading.Thread(target=node.stabilize).start()

    while True:
        command = input("> ")
        if command.startswith("store"):
            _, filename = command.split()
            node.store_file(filename)
        elif command.startswith("lookup"):
            _, filename = command.split()
            node.lookup_file(filename)
        elif command == "list":
            node.list_files()

if __name__ == '__main__':
    main()
