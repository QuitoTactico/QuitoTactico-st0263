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
    def __init__(self, ip: str, port: int, id: int, update_interval: int, m: int = 16) -> None:
        self.ip = ip  #ip del nodo donde estará escuchando
        self.port = port  #puerto del nodo donde estará escuchando
        self.id = id  #id del nodo calculado con hash
        self.update_interval = update_interval  #intervalo de estabilización
        self.successor = None  #el sucesor inicial es None
        self.predecessor = None  #el predecesor inicial es None
        self.files = {}  #diccionario para almacenar archivos
        self.m = m  #número de bits en el espacio de identificadores
        self.finger_table = [None] * self.m  #inicializamos la finger table

    def find_successor(self, node_id: int) -> dict:
        #si el id está entre el nodo actual y su sucesor, entonces el sucesor es el nodo que buscamos
        if self.successor and (self.id < node_id <= self.successor['id'] or
                            (self.successor['id'] < self.id and (node_id > self.id or node_id <= self.successor['id']))):
            return self.successor
        elif self.id == node_id:
            #si el nodo actual es su propio sucesor (solo en red o el primer nodo)
            return self.to_dict()
        else:
            #si no, preguntamos al nodo más cercano de nuestra finger table
            closest_preceding_node = self.closest_preceding_finger(node_id)
            if closest_preceding_node['id'] == self.id:
                #si el nodo más cercano es el propio nodo, evitamos hacer la llamada a sí mismo
                return self.to_dict()
            url = f"http://{closest_preceding_node['ip']}:{closest_preceding_node['port']}/find_successor"
            try:
                response = requests.post(url, json={'id': node_id})
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error al contactar al nodo más cercano: {e}")
                return {'error': 'Failed to find successor'}


    def closest_preceding_finger(self, node_id: int) -> dict:
        #buscamos el nodo más cercano que precede al id que estamos buscando
        for i in range(self.m - 1, -1, -1):
            if self.finger_table[i] and 'id' in self.finger_table[i] and self.id < self.finger_table[i]['id'] < node_id:
                return self.finger_table[i] #recorremos la tabla en orden inverso buscando si existe un id, necesitamos verificar que el nodo actual tenga un id menor al id del nodo en la finger table
        return self.to_dict()  #si no encontramos uno más cercano, devolvemos el propio nodo

    def stabilize(self):
        #estabiliza el nodo verificando su sucesor y predecesor
        while True:
            if self.successor:
                #preguntamos al sucesor por su predecesor
                url = f"http://{self.successor['ip']}:{self.successor['port']}/get_predecessor"
                response = requests.get(url)
                successor_predecessor = response.json()

                #si el predecesor del sucesor debería ser nuestro nuevo sucesor, lo actualizamos
                if successor_predecessor and self.id < successor_predecessor['id'] < self.successor['id']:
                    self.successor = successor_predecessor

                #notificamos al sucesor que somos su predecesor
                url = f"http://{self.successor['ip']}:{self.successor['port']}/notify"
                requests.post(url, json=self.to_dict())

            time.sleep(self.update_interval)  #esperamos el intervalo de actualización

    def notify(self, new_predecessor: dict) -> None:
        #actualiza el predecesor si no tenemos uno, si somos nuestro propio predecesor, o si el nuevo predecesor es más cercano que el actual
        if (not self.predecessor) or (self.predecessor['id'] == self.id) or (self.predecessor['id'] < new_predecessor['id'] < self.id):
            self.predecessor = new_predecessor
            print(f"Predecesor actualizado: {self.predecessor['id']} ({self.predecessor['ip']}:{self.predecessor['port']})")
        
        #si el sucesor es el propio nodo, lo actualizamos al nuevo predecesor
        if self.successor['id'] == self.id:
            self.successor = new_predecessor
            print(f"Sucesor actualizado: {self.successor['id']} ({self.successor['ip']}:{self.successor['port']})")


    def fix_fingers(self):
        #ciclo que repara la finger table periódicamente
        while True:
            for i in range(self.m):
                finger_id = (self.id + 2 ** i) % (2 ** self.m)
                #Asegúrate de que `find_successor` siempre devuelve un diccionario válido
                successor = self.find_successor(finger_id)
                if successor and 'id' in successor:
                    self.finger_table[i] = successor
                else:
                    print(f"Error al encontrar sucesor para finger {i} con id {finger_id}")
            time.sleep(self.update_interval)

    def check_predecessor(self):
        #verifica si el predecesor está activo
        while True:
            if self.predecessor:
                try:
                    url = f"http://{self.predecessor['ip']}:{self.predecessor['port']}/ping"
                    requests.get(url)
                except:
                    self.predecessor = None  #si falla el ping, eliminamos el predecesor
            time.sleep(self.update_interval)

    def to_dict(self) -> dict:
        #convierte la información del nodo a un diccionario para fácil transmisión
        return {'ip': self.ip, 'port': self.port, 'id': self.id}

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
        if self.successor:
            print(f"  id: {self.successor['id']}, IP: {self.successor['ip']}, Puerto: {self.successor['port']}\n")
        else:
            print("  Ninguno\n")
        print("Predecesor:")
        if self.predecessor:
            print(f"  id: {self.predecessor['id']}, IP: {self.predecessor['ip']}, Puerto: {self.predecessor['port']}\n")
        else:
            print("  Ninguno\n")
        print("Finger Table:")
        for i, finger in enumerate(self.finger_table):
            if finger:
                print(f"  {i}: id={finger['id']}, IP={finger['ip']}, Puerto={finger['port']}")
            else:
                print(f"  {i}: None")
        print("Archivos almacenados:")
        if self.files:
            for filename in self.files:
                print(f"  - {filename}")
        else:
            print("  No hay archivos almacenados")
        print("===========================\n")

@app.route('/find_successor', methods=['POST'])
def find_successor():
    try:
        data = request.json
        if 'id' not in data:
            return jsonify({'error': 'Missing id'}), 400
        
        node_id = data['id']
        result = node.find_successor(node_id)
        if 'error' in result:
            return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        print(f"Error en /find_successor: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500


@app.route('/notify', methods=['POST'])
def notify():
    #maneja las notificaciones sobre nuevos nodos en la red a través de REST
    data = request.json
    if not data or 'id' not in data:
        return jsonify({'error': 'Invalid request'}), 400
    node.notify(data)
    return jsonify({'message': 'Predecessor updated'})

@app.route('/get_predecessor', methods=['GET'])
def get_predecessor():
    #devuelve el predecesor del nodo actual
    if node.predecessor:
        return jsonify(node.predecessor)
    return jsonify({'message': 'No predecessor found'}), 404

@app.route('/ping', methods=['GET'])
def ping():
    #función simple para verificar si el nodo está activo
    return jsonify({'message': 'pong'})

def serve_rest() -> None:
    #inicia el servidor REST
    app.run(host=node.ip, port=node.port)

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

            #notificamos al sucesor sobre la existencia de este nodo
            notify_url = f"http://{node.successor['ip']}:{node.successor['port']}/notify"
            requests.post(notify_url, json=node.to_dict())

            #si no tenemos predecesor, lo configuramos como el nodo bootstrap
            if not node.predecessor:
                node.predecessor = {
                    'ip': bootstrap_ip,
                    'port': bootstrap_port,
                    'id': hash_key(f'{bootstrap_ip}:{bootstrap_port}')
                }

    #inicia los servidores REST y gRPC, y el proceso de estabilización
    threading.Thread(target=serve_rest).start()
    threading.Thread(target=serve_grpc, args=(node,)).start()
    threading.Thread(target=node.stabilize).start()
    threading.Thread(target=node.fix_fingers).start()
    threading.Thread(target=node.check_predecessor).start()

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
