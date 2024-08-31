import grpc
from concurrent import futures
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2
import hashlib
import threading
import sys

class ChordService(pb2_grpc.ChordServiceServicer):
    def __init__(self, node):
        self.node = node
        self.files = {}  #diccionario para guardar archivos (simulados)
    
    def FindSuccessor(self, request, context):
        #lógica para encontrar el sucesor en el anillo chord
        #por ahora devolvemos el mismo nodo para simplificar
        return self.node

    def Notify(self, request, context):
        #notificar que un nodo se ha unido
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
            return pb2.FileResponse(message=self.files[filename])
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

def main():
    ip = sys.argv[1]
    port = int(sys.argv[2])
    id = int(hashlib.sha1(f'{ip}:{port}'.encode()).hexdigest(), 16) % 2**16
    node = Node(ip, port, id)

    if len(sys.argv) > 3:
        #unir nodo a red existente
        existing_node_ip = sys.argv[3]
        existing_node_port = int(sys.argv[4])
        existing_node = Node(existing_node_ip, existing_node_port, None)
        node.join_network(existing_node)

    threading.Thread(target=serve, args=(node,)).start()  #ejecuta la función serve en un hilo separado

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

if __name__ == '__main__':
    main()
