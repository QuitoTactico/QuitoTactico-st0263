import requests
from flask import Flask, request, jsonify
import threading
import grpc
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2
import hashlib
import time
import json
from grpc_service import serve_grpc  #importamos serve_grpc para manejar el servidor gRPC

app = Flask(__name__)

class Node:
    def __init__(self, ip: str, port: int, id: int, update_interval: int) -> None:
        self.ip = ip  #ip del nodo donde estará escuchando
        self.port = port  #puerto del nodo donde estará escuchando
        self.id = id  #id del nodo calculado con hash
        self.update_interval = update_interval  #intervalo de estabilización
        self.successor = self.to_dict()  #al principio, el sucesor es el propio nodo
        self.predecessor = None  #el predecesor inicial es None
        self.files = {}  #diccionario para almacenar archivos

    def find_successor(self, node_id: int) -> dict:
        #busca quién es el sucesor del id dado en la red
        if self.predecessor and self.predecessor['id'] < self.id:
            if self.predecessor['id'] < node_id <= self.id:
                return self.to_dict()
        elif self.predecessor and self.predecessor['id'] > self.id:
            if node_id > self.predecessor['id'] or node_id <= self.id:
                return self.to_dict()

        #si el id está entre el nodo actual y su sucesor, entonces ese sucesor es el que buscamos
        if self.id < node_id <= self.successor['id']:
            return self.successor
        else:
            #si no, se busca el nodo más cercano en la finger table
            closest_preceding_node = self.closest_preceding_finger(node_id)
            url = f"http://{closest_preceding_node['ip']}:{closest_preceding_node['port']}/find_successor"
            response = requests.post(url, json={'id': node_id})
            return response.json()

    def closest_preceding_finger(self, node_id: int) -> dict:
        #esto está simplificado, devolvemos el sucesor actual
        return self.successor

    def to_dict(self) -> dict:
        #convierte la información del nodo a un diccionario para fácil transmisión
        return {'ip': self.ip, 'port': self.port, 'id': self.id}

    def notify(self, new_node: dict) -> str:
        #actualiza el predecesor si es necesario cuando un nuevo nodo aparece
        if not self.predecessor or \
           (self.predecessor['id'] < new_node['id'] < self.id) or \
           (self.predecessor['id'] > self.id and (new_node['id'] > self.predecessor['id'] or new_node['id'] < self.id)):
            self.predecessor = new_node  #actualiza el predecesor
            return f"Predecessor updated to {new_node['id']}"
        return "No update required"

    def store_file(self, filename: str) -> str:
        #almacena el archivo en el nodo actual
        self.files[filename] = f"Transfiriendo {filename}... Archivo transferido"
        return f"Archivo '{filename}' almacenado en el nodo {self.id}"

    def lookup_file(self, filename: str) -> str:
        #busca el archivo en el nodo actual
        if filename in self.files:
            return f"Archivo '{filename}' encontrado en nodo {self.id} ({self.ip}:{self.port})"
        else:
            return f"Archivo '{filename}' no encontrado en nodo {self.id}"

    def display_info(self) -> None:
        #muestra información del nodo: id, ip, puerto, sucesor, predecesor y archivos almacenados
        print("\n=== Información del Nodo ===")
        print(f"id: {self.id} (IP: {self.ip}, Puerto: {self.port})\n")
        print("Sucesor:")
        print(f"  id: {self.successor['id']}, IP: {self.successor['ip']}, Puerto: {self.successor['port']}\n")
        print("Predecesor:")
        if self.predecessor:
            print(f"  id: {self.predecessor['id']}, IP: {self.predecessor['ip']}, Puerto: {self.predecessor['port']}\n")
        else:
            print("  Ninguno\n")
        print("Archivos almacenados:")
        if self.files:
            for filename in self.files:
                print(f"  - {filename}")
        else:
            print("  No hay archivos almacenados")
        print("===========================\n")


@app.route('/find_successor', methods=['POST'])
def find_successor():
    #maneja la solicitud para encontrar el sucesor a través de REST
    data = request.json
    node_id = data['id']
    result = node.find_successor(node_id)
    return jsonify(result)

@app.route('/notify', methods=['POST'])
def notify():
    #maneja las notificaciones sobre nuevos nodos en la red a través de REST
    data = request.json
    result = node.notify(data)
    return jsonify({'message': result})

def serve_rest() -> None:
    #inicia el servidor REST
    app.run(host=node.ip, port=node.port)

def stabilize():
    #proceso de estabilización para mantener la red actualizada
    while True:
        #lógica para estabilizar la red periódicamente
        time.sleep(node.update_interval)

def main() -> None:
    #lee la configuración desde el archivo bootstrap.json
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

    #si el nodo no es el primero, se conecta al nodo bootstrap
    if bootstrap_ip and bootstrap_port:
        if bootstrap_ip != "" and bootstrap_port != "":
            url = f"http://{bootstrap_ip}:{bootstrap_port}/find_successor"
            response = requests.post(url, json={'id': node.id})
            node.successor = response.json()

    #inicia los servidores REST y gRPC, y el proceso de estabilización
    threading.Thread(target=serve_rest).start()
    threading.Thread(target=stabilize).start()
    threading.Thread(target=serve_grpc, args=(node,)).start()

    #loop principal para manejar comandos desde la consola
    while True:
        command = input("> ").strip()
        if command.startswith("store"):
            _, filename = command.split()
            print(node.store_file(filename))
        elif command.startswith("lookup"):
            _, filename = command.split()
            print(node.lookup_file(filename))
        elif command == "info":
            node.display_info()
        else:
            print("Comando no reconocido")

def hash_key(key: str) -> int:
    #genera un id único basado en el hash SHA-1 de la clave
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % 2**16

if __name__ == '__main__':
    main()
