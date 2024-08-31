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
    #hacemos el hash del id para convertirlo en un número que se usa en el espacio de claves
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % 2**16

class ChordService(pb2_grpc.ChordServiceServicer):
    def __init__(self, node):
        #inicializamos el servicio chord con el nodo asociado
        self.node = node
        self.files = {}  #guardamos los archivos en este diccionario (simulados)

    def FindSuccessor(self, request, context):
        #primero vamos a buscar el sucesor de un id en el anillo chord
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
            #usamos la finger table para saltar al nodo más cercano que precede al id
            closest_preceding_node = self.node.closest_preceding_finger(id)
            if closest_preceding_node.id != self.node.id:
                with grpc.insecure_channel(f'{closest_preceding_node.ip}:{closest_preceding_node.port}') as channel:
                    stub = pb2_grpc.ChordServiceStub(channel)
                    return stub.FindSuccessor(pb2.Node(id=id))
            else:
                return self.node.successor

    def Notify(self, request, context):
        #el nodo notifica a su sucesor para ver si debe actualizar su predecesor
        predecessor_id = request.id
        if self.node.predecessor is None or \
           (self.node.predecessor.id < predecessor_id < self.node.id) or \
           (self.node.predecessor.id > self.node.id and (predecessor_id > self.node.predecessor.id or predecessor_id < self.node.id)):
            self.node.predecessor = request
            print(f"nodo {self.node.id} actualizó su predecesor a {request.id}")
        return pb2.Empty()

    def StoreFile(self, request, context):
        #guardamos el archivo en este nodo y lo simulamos con un mensaje
        filename = request.filename
        self.files[filename] = f"Transfiriendo {filename}... Archivo transferido"
        return pb2.FileResponse(message=f"archivo '{filename}' almacenado en el nodo {self.node.id}")

    def LookupFile(self, request, context):
        #buscamos el archivo en el nodo actual y respondemos si está aquí
        filename = request.filename
        if filename in self.files:
            return pb2.FileResponse(message=f"archivo '{filename}' encontrado en nodo {self.node.id} ({self.node.ip}:{self.node.port})")
        else:
            return pb2.FileResponse(message=f"archivo '{filename}' no encontrado")

    def TransferFile(self, request, context):
        #simulamos la transferencia de un archivo (es solo un mensaje)
        filename = request.filename
        if filename in self.files:
            return pb2.FileResponse(message=self.files[filename])
        else:
            return pb2.FileResponse(message=f"archivo '{filename}' no encontrado")

def serve(node):
    #configuramos el servidor gRPC y lo ponemos a escuchar conexiones
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_ChordServiceServicer_to_server(ChordService(node), server)
    server.add_insecure_port(f'{node.ip}:{node.port}')
    server.start()
    server.wait_for_termination()

class Node:
    def __init__(self, ip, port, id, update_interval):
        #inicializamos el nodo con su ip, puerto, id, intervalo de actualización y demás
        self.ip = ip
        self.port = port
        self.id = id
        self.update_interval = update_interval
        self.successor = self  #sucesor inicial es el mismo nodo
        self.predecessor = None
        self.finger_table = []  #inicializamos la finger table vacía
        self.init_finger_table()  #y luego la llenamos

    def init_finger_table(self):
        #llenamos la finger table con las posiciones iniciales (con nosotros mismos como nodo inicial)
        m = 16  #suponemos un espacio de clave de 2^16
        for i in range(m):
            start = (self.id + 2**i) % 2**m
            self.finger_table.append((start, self))

    def update_finger_table(self):
        #actualizamos la finger table encontrando el sucesor correcto para cada entrada
        m = 16  #asumimos un espacio de clave de 2^16
        for i in range(m):
            start = (self.id + 2**i) % 2**m
            with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
                stub = pb2_grpc.ChordServiceStub(channel)
                self.finger_table[i] = (start, stub.FindSuccessor(pb2.Node(id=start)))

    def closest_preceding_finger(self, id):
        #buscamos en la finger table el nodo más cercano que precede al id
        for i in range(len(self.finger_table)-1, -1, -1):
            if self.id < self.finger_table[i][1].id < id:
                return self.finger_table[i][1]
        return self

    def join_network(self, existing_node):
        #nos unimos a la red contactando a un nodo existente para encontrar nuestro lugar
        with grpc.insecure_channel(f'{existing_node.ip}:{existing_node.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            self.successor = stub.FindSuccessor(pb2.Node(ip=self.ip, port=self.port, id=self.id))

    def stabilize(self):
        #hacemos la estabilización periódica para actualizar sucesor y finger table
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
                self.update_finger_table()  #actualizamos la finger table periódicamente
            except Exception as e:
                print(f"error en estabilización: {e}")
            time.sleep(self.update_interval)

    def store_file(self, filename):
        #almacenamos el archivo en el sucesor (simulado)
        with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            response = stub.StoreFile(pb2.FileRequest(filename=filename))
            print(response.message)

    def lookup_file(self, filename):
        #buscamos un archivo y mostramos dónde se encuentra
        with grpc.insecure_channel(f'{self.successor.ip}:{self.successor.port}') as channel:
            stub = pb2_grpc.ChordServiceStub(channel)
            response = stub.LookupFile(pb2.FileRequest(filename=filename))
            print(response.message)

    def list_files(self):
        #listamos los archivos almacenados en este nodo
        if hasattr(self, 'files') and self.files:
            print("archivos almacenados en este nodo:")
            for filename in self.files:
                print(f" - {filename}")
        else:
            print("no hay archivos almacenados en este nodo")

    def display_info(self):
        #mostramos la finger table, el predecesor, el sucesor y la configuración actual
        print("\n=== Información del Nodo ===")
        print(f"id: {self.id} (IP: {self.ip}, Puerto: {self.port})\n")
        print("Sucesor:")
        print(f"  id: {self.successor.id}, IP: {self.successor.ip}, Puerto: {self.successor.port}\n")
        print("Predecesor:")
        if self.predecessor:
            print(f"  id: {self.predecessor.id}, IP: {self.predecessor.ip}, Puerto: {self.predecessor.port}\n")
        else:
            print("  Ninguno\n")
        print("Finger Table:")
        for start, node in self.finger_table:
            print(f"  start: {start}, id: {node.id}, IP: {node.ip}, Puerto: {node.port}\n")
        print("===========================\n")

def main():
    #leemos la configuración desde el archivo JSON
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    ip = config.get("own_ip")
    port = config.get("own_port")
    update_interval = config.get("update_interval")
    
    id = hash_key(f'{ip}:{port}')
    node = Node(ip, port, id, update_interval)

    bootstrap_ip = config.get("bootstrap_ip")
    bootstrap_port = config.get("bootstrap_port")

    #si hay un bootstrap_ip y bootstrap_port configurado y no están vacíos, unimos el nodo a la red existente
    if bootstrap_ip and bootstrap_port:
        if bootstrap_ip != "" and bootstrap_port != "":
            existing_node_id = hash_key(f'{bootstrap_ip}:{bootstrap_port}')
            existing_node = Node(bootstrap_ip, int(bootstrap_port), existing_node_id, update_interval)
            node.join_network(existing_node)
    else:
        print(f"nodo {node.id} es el primer nodo en la red")

    #iniciamos el servidor gRPC y el proceso de estabilización en hilos separados
    threading.Thread(target=serve, args=(node,)).start()
    threading.Thread(target=node.stabilize).start()

    #bucle para manejar los comandos de la consola
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
        elif command == "info":
            node.display_info()

if __name__ == '__main__':
    main()
