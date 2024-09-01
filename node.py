import requests
from flask import Flask, request, jsonify
import threading
import grpc
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2
import hashlib
import time
import json
from grpc_service import serve_grpc

app = Flask(__name__)

class Node:
    def __init__(self, ip: str, port: int, id: int, update_interval: int) -> None:
        self.ip = ip  #ip del nodo donde estará escuchando
        self.port = port  #puerto del nodo donde estará escuchando
        self.id = id  #id del nodo calculado con hash
        self.update_interval = update_interval  #intervalo de estabilización
        self.successor = {}  #sucesor inicial como un diccionario vacío
        self.predecessor = {}  #predecesor inicial como un diccionario vacío
        self.files = {}  #diccionario para almacenar archivos

    def find_successor(self, id_to_find: int) -> dict:
        #si el id buscado está entre el nodo actual y su sucesor, retornamos el sucesor
        if self.is_in_interval(id_to_find, self.id, self.successor['id']):
            return self.successor
        else:
            #iniciamos desde el sucesor actual
            next_node = self.successor
            while True:
                #consultamos al siguiente nodo por su sucesor
                url = f"http://{next_node['ip']}:{next_node['port']}/get_successor"
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    next_successor = response.json()
                    
                    #verificamos si el id buscado está entre el nodo actual y su sucesor
                    if self.is_in_interval(id_to_find, next_node['id'], next_successor['id']):
                        return next_successor
                    else:
                        next_node = next_successor
                except requests.exceptions.RequestException as e:
                    print(f"Error al contactar al nodo {next_node['id']}: {e}")
                    return {}
    
    def is_in_interval(self, id_to_check: int, start: int, end: int) -> bool:
        #verifica si id_to_check está en el intervalo (start, end]
        if start < end:
            return start < id_to_check <= end
        else:
            return start < id_to_check or id_to_check <= end

    def search(self, filename: str) -> dict:
        #calculamos el id del archivo basado en su nombre
        file_id = hash_key(filename)
        
        #buscamos el nodo responsable del archivo
        responsible_node = self.find_successor(file_id)
        
        if not responsible_node:
            return {'error': 'No se pudo encontrar el nodo responsable'}
        
        #verificamos si el nodo responsable tiene el archivo
        if responsible_node['id'] == self.id:
            if filename in self.files:
                return {'url': f"http://{self.ip}:{self.port}/download/{filename}"}
            else:
                return {'error': f"Archivo '{filename}' no encontrado en nodo actual ({self.id})"}
        else:
            return {'url': f"http://{responsible_node['ip']}:{responsible_node['port']}/download/{filename}"}

    def stabilize(self):
        #estabiliza el nodo verificando su sucesor y predecesor
        while True:
            try:
                #preguntamos al sucesor por su predecesor
                url = f"http://{self.successor['ip']}:{self.successor['port']}/get_predecessor"
                response = requests.get(url)
                response.raise_for_status()
                successor_predecessor = response.json()
                
                #verificamos si el predecesor del sucesor está entre el nodo actual y su sucesor
                if successor_predecessor and self.is_in_interval(successor_predecessor['id'], self.id, self.successor['id']):
                    self.successor = successor_predecessor

                #notificamos al sucesor que este nodo es su predecesor
                notify_url = f"http://{self.successor['ip']}:{self.successor['port']}/notify"
                requests.post(notify_url, json=self.to_dict())
            except requests.exceptions.RequestException as e:
                print(f"Error durante estabilización: {e}")
            time.sleep(self.update_interval)

    def notify(self, new_predecessor: dict) -> None:
        #actualiza el predecesor si es nulo o si el nuevo es más adecuado
        if not self.predecessor or self.is_in_interval(new_predecessor['id'], self.predecessor['id'], self.id):
            self.predecessor = new_predecessor
            print(f"Predecesor actualizado: {self.predecessor['id']} ({self.predecessor['ip']}:{self.predecessor['port']})")

    def check_predecessor(self):
        #verifica periódicamente si el predecesor está activo
        while True:
            if self.predecessor:
                try:
                    url = f"http://{self.predecessor['ip']}:{self.predecessor['port']}/ping"
                    response = requests.get(url)
                    response.raise_for_status()
                except requests.exceptions.RequestException:
                    print(f"Predecesor {self.predecessor['id']} no responde. Eliminando predecesor.")
                    self.predecessor = {}
            time.sleep(self.update_interval)

    def to_dict(self) -> dict:
        #convierte la información del nodo a un diccionario para fácil transmisión
        return {'ip': self.ip, 'port': self.port, 'id': self.id}

    def store_file(self, filename: str) -> str:
        #almacena el archivo en el nodo actual
        self.files[filename] = f"Contenido de {filename}"
        return f"Archivo '{filename}' almacenado en el nodo {self.id}"

    def lookup_file(self, filename: str) -> str:
        #busca el archivo en el nodo actual
        if filename in self.files:
            return f"Archivo '{filename}' encontrado en nodo actual ({self.id})"
        else:
            return f"Archivo '{filename}' no encontrado en nodo actual ({self.id})"

    def display_info(self) -> None:
        #muestra información del nodo: id, ip, puerto, sucesor, predecesor y archivos almacenados
        print("\n=== Información del Nodo ===")
        print(f"id: {self.id} (ip: {self.ip}, puerto: {self.port})\n")
        print("Sucesor:")
        if self.successor:
            print(f"  id: {self.successor['id']}, ip: {self.successor['ip']}, puerto: {self.successor['port']}\n")
        else:
            print("  Ninguno\n")
        print("Predecesor:")
        if self.predecessor:
            print(f"  id: {self.predecessor['id']}, ip: {self.predecessor['ip']}, puerto: {self.predecessor['port']}\n")
        else:
            print("  Ninguno\n")
        print("Archivos almacenados:")
        if self.files:
            for filename in self.files:
                print(f"  - {filename}")
        else:
            print("  No hay archivos almacenados")
        print("===========================\n")

#---------------------------------------------- REST API ----------------------------------------------

@app.route('/find_successor', methods=['POST'])
def find_successor_route():
    try:
        data = request.json
        if 'id' not in data:
            return jsonify({'error': 'Missing id'}), 400
        
        node_id = data['id']
        result = node.find_successor(node_id)
        if not result:
            return jsonify({'error': 'No se pudo encontrar el sucesor'}), 500
        return jsonify(result)
    except Exception as e:
        print(f"Error en /find_successor: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@app.route('/get_predecessor', methods=['GET'])
def get_predecessor():
    #devuelve el predecesor del nodo actual
    if node.predecessor:
        return jsonify(node.predecessor)
    return jsonify({}), 404

@app.route('/get_successor', methods=['GET'])
def get_successor():
    #devuelve el sucesor del nodo actual
    if node.successor:
        return jsonify(node.successor)
    return jsonify({}), 404

@app.route('/notify', methods=['POST'])
def notify():
    #maneja las notificaciones sobre nuevos predecesores
    data = request.json
    if not data or 'id' not in data:
        return jsonify({'error': 'Invalid request'}), 400
    node.notify(data)
    return jsonify({'message': 'Predecesor actualizado'})

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.json
        if 'filename' not in data:
            return jsonify({'error': 'Missing filename'}), 400

        result = node.search(data['filename'])
        return jsonify(result)
    except Exception as e:
        print(f"Error en /search: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

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
    
    if bootstrap_ip and bootstrap_port and bootstrap_ip != "" and bootstrap_port != "":
        try:
            #contactamos al nodo bootstrap para encontrar nuestro sucesor
            url = f"http://{bootstrap_ip}:{bootstrap_port}/find_successor"
            response = requests.post(url, json={'id': node.id})
            response.raise_for_status()
            node.successor = response.json()
            print(f"Sucesor inicial establecido: {node.successor['id']} ({node.successor['ip']}:{node.successor['port']})")
        except requests.exceptions.RequestException as e:
            print(f"Error al conectarse al nodo bootstrap: {e}")
            node.successor = node.to_dict()
    else:
        #si no hay nodo bootstrap, nos establecemos como nuestro propio sucesor y predecesor
        node.successor = node.to_dict()
        node.predecessor = node.to_dict()
        print("Nodo inicial de la red creado.")

    #iniciamos los servidores y procesos de estabilización
    threading.Thread(target=serve_rest).start()
    threading.Thread(target=serve_grpc, args=(node,)).start()
    threading.Thread(target=node.stabilize).start()
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
        elif command.startswith("search"):
            _, filename = command.split()
            response = node.search(filename)
            if 'error' in response:
                print(response['error'])
            else:
                print(f"Archivo '{filename}' está en {response['url']}")
        elif command == "info":
            node.display_info()
        else:
            print("Comando no reconocido")

def hash_key(key: str) -> int:
    #genera un id único basado en el hash SHA-1 de la clave
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**16)

if __name__ == '__main__':
    main()
