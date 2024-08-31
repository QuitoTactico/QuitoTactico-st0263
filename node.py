import grpc
from concurrent import futures
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2
import hashlib
import threading
import sys
import time

def hash_key(key):
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % 2**16

class ChordService(pb2_grpc.ChordServiceServicer):
    def __init__(self, node):
        self.node = node
        self.files = {}  #diccionario para guardar archivos (simulados)
    
    def FindSuccessor(self, request, context):
        #lógica para encontrar el sucesor en el anillo chord
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
            # reenviar la solicitud al sucesor
            with grpc.insecure_channel(f'{self.node.successor.ip}:{self.node.successor.port}') as channel:
                stub = pb2_grpc.ChordServiceStub(channel)
                return stub.FindSuccessor(pb2.Node(id=id, ip=self.node.ip, port=self.node.port))

    def Notify(self, request, context):
        #notificar al nodo sobre un posible predecesor
        predecessor_id = request.id
        if self.node.predecessor is None or \
           (self.node.predecessor.id < predecessor_id < self.node.id) or \
           (self.node.predecessor.id > self.node.id and (predecessor_id > self.node.predecessor.id or predecessor_id < self.node.id)):
            self.node.predecessor = request
            print(f"nodo {self.node.id} actualizó su predecesor a {request.id}")
        return pb2.Empty()

    def StoreFile(self, request, context):
        #guardar un archivo en el nodo
        filename = request.filename
        self.files[filename] = f"Transfiriendo {filename}... Archivo transferido"
        return pb2.FileResponse(message=f"archivo '{filename}' almacenado en el nodo {self.node.id}")

    def LookupFile(self, request, context):
        #buscar un archivo en el nodo
        filename = request.filename
        if filename in self.files:
            return pb2.FileResponse(message=f"archivo '{filename}' encontrado en nodo {self.node.id} ({self.node.ip}:{self.node.port})")
        else:
            return pb2.FileResponse(message=f"archivo '{filename}' no encontrado")

    def TransferFile(self, request, context):
        #simular la transferencia de un archivo
        filename = request.filename
        if filename in self.files:
            return pb2.FileResponse(message=self.files[filename])
        else:
            return pb2.FileResponse(message=f"archivo '{filename}' no encontrado")

def serve(node):
    #configura el servidor gRPC
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_ChordServiceServicer_to_server(ChordService(node), server)
    server.add_insecure_port(f'{node.ip}:{node.port}')
    server.start()
    server.wait_for_termination()

class Node:
    def __init__(self, ip, port, id):
        self.ip = ip
        self.port = port
        self.id = id
        self.successor = self
        self.predecessor = None

    def join_network(self, existing_node):
        #unirse a la red existente
        with grpc.insecure_channel(f'{existing_node.ip}:{existing_node.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            self.successor = stub.FindSuccessor(pb2.Node(ip=self.ip, port=self.port, id=self.id))

    def stabilize(self):
        #proceso de estabilización
        while True:
            try:
                with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
                    stub = pb2_grpc.ChordServiceStub(channel)
                    x = stub.FindSuccessor(pb2.Node(id=self.successor.id)).id
                    if x != self.successor.id and (self.id < x < self.successor.id or
                                                   (self.id > self.successor.id and (x > self.id or x < self.successor.id))):
                        self.successor = x
                        print(f"nodo {self.id} actualizó su sucesor a {x}")
                    
                    # notificar al sucesor sobre este nodo
                    stub.Notify(pb2.Node(id=self.id, ip=self.ip, port=self.port))
            except Exception as e:
                print(f"error en estabilización: {e}")
            time.sleep(5)  # ajustar el intervalo según sea necesario

    def store_file(self, filename):
        #guardar archivo en el sucesor
        with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            response = stub.StoreFile(pb2.FileRequest(filename=filename))
            print(response.message)

    def lookup_file(self, filename):
        #buscar archivo en el sucesor
        with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            response = stub.LookupFile(pb2.FileRequest(filename=filename))
            print(response.message)

    def list_files(self):
        #listar archivos almacenados en el nodo actual
        if hasattr(self, 'files') and self.files:
            print("archivos almacenados en este nodo:")
            for filename in self.files:
                print(f" - {filename}")
        else:
            print("no hay archivos almacenados en este nodo")

def main():
    ip = sys.argv[1]
    port = int(sys.argv[2])
    id = hash_key(f'{ip}:{port}')
    node = Node(ip, port, id)

    if len(sys.argv) > 3:
        #unir nodo a red existente
        existing_node_ip = sys.argv[3]
        existing_node_port = int(sys.argv[4])
        existing_node = Node(existing_node_ip, existing_node_port, None)
        node.join_network(existing_node)

    #procesos en hilos separados:
    threading.Thread(target=serve, args=(node,)).start()  #ejecuta la función serve en un hilo separado
    threading.Thread(target=node.stabilize).start()  #inicia el proceso de estabilización

    while True:
        command = input("> ")
        if command.startswith("store"):
            #comando para almacenar archivo
            _, filename = command.split()
            node.store_file(filename)
        elif command.startswith("lookup"):
            #comando para buscar archivo
            _, filename = command.split()
            node.lookup_file(filename)
        elif command == "list":
            #comando para listar los archivos almacenados en el nodo
            node.list_files()

if __name__ == '__main__':
    main()
