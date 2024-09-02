import requests
from flask import Flask, request, jsonify
import threading
import grpc
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2
import hashlib
import time
import json
from concurrent import futures
from grpc_service import ChordService

app = Flask(__name__)

class Node:
    def __init__(self, ip: str, port: int, id: int, update_interval: int, config: dict) -> None:
        self.ip = ip  #ip del nodo donde estará escuchando
        self.port = port  #puerto del nodo donde estará escuchando
        self.grpc_port = port + 1  #puerto para el servidor grpc (puerto rest + 1)
        self.id = id  #id del nodo calculado con hash
        self.update_interval = update_interval  #intervalo de estabilización
        self.successor = {}  #sucesor inicial como un diccionario vacío
        self.predecessor = {}  #predecesor inicial como un diccionario vacío
        self.files = {}  #diccionario para almacenar archivos
        self.config = config  #configuración del nodo, bootstrap
        self.successor_fails = 0  #contador de fallos del sucesor
        self.predecessor_fails = 0  #contador de fallos del predecesor

    def bootstrap(self):
        bootstrap_ip = self.config.get("bootstrap_ip")
        bootstrap_port = self.config.get("bootstrap_port")
        
        if bootstrap_ip and bootstrap_port and bootstrap_ip != "" and bootstrap_port != "":
            try:
                #contactamos al nodo bootstrap para encontrar nuestro sucesor
                url = f"http://{bootstrap_ip}:{bootstrap_port}/find_successor"
                response = requests.post(url, json={'id': self.id})
                response.raise_for_status()
                self.successor = response.json()
                print(f"sucesor inicial establecido: {self.successor['id']} ({self.successor['ip']}:{self.successor['port']})")
            except requests.exceptions.RequestException as e:
                print(f"error al conectarse al nodo bootstrap: {e}")
                self.successor = self.to_dict()
        else:
            #si no hay nodo bootstrap, nos establecemos como nuestro propio sucesor y predecesor
            self.successor = self.to_dict()
            self.predecessor = self.to_dict()
            print("nodo inicial de la red creado.")

    def is_in_interval(self, id_to_check: int, start: int, end: int) -> bool:
        #verifica si id_to_check está en el intervalo (start, end]
        if start < end:
            return start < id_to_check <= end
        else:
            return start < id_to_check or id_to_check <= end

    def find_successor(self, id_to_find: int) -> dict:
        print(f"[find_successor] buscando sucesor para id {id_to_find}, nodo actual: {self.id}, sucesor actual: {self.successor['id']}")
        if self.is_in_interval(id_to_find, self.id, self.successor['id']):
            print(f"[find_successor] sucesor directo encontrado: {self.successor['id']}")
            return self.successor
        else:
            next_node = self.successor
            attempts = 0
            while attempts < 10:  #limite de intentos para evitar bucles infinitos
                print(f"[find_successor] intento {attempts + 1}, consultando nodo {next_node['id']} para id {id_to_find}")
                url = f"http://{next_node['ip']}:{next_node['port']}/get_successor"
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    next_successor = response.json()
                    if self.is_in_interval(id_to_find, next_node['id'], next_successor['id']):
                        print(f"[find_successor] sucesor encontrado: {next_successor['id']} en nodo {next_node['id']}")
                        return next_successor
                    else:
                        next_node = next_successor
                except requests.exceptions.RequestException as e:
                    print(f"[find_successor] error al contactar al nodo {next_node['id']}: {e}")
                    return {}
                attempts += 1
            print(f"[find_successor] exceso de intentos para encontrar sucesor de id {id_to_find}")
            return {}

    def search(self, filename: str) -> dict:
        #calculamos el id del archivo basado en su nombre
        file_id = hash_key(filename)
        
        #buscamos el nodo responsable del archivo
        responsible_node = self.find_successor(file_id)
        
        if not responsible_node:
            return {'error': 'no se pudo encontrar el nodo responsable'}
        
        #verificamos si el nodo responsable tiene el archivo
        if responsible_node['id'] == self.id:
            if filename in self.files:
                return {'url': f"http://{self.ip}:{self.port}/download/{filename}"}
            else:
                return {'error': f"archivo '{filename}' no encontrado en nodo actual ({self.id})"}
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
                if successor_predecessor:
                    if self.is_in_interval(successor_predecessor['id'], self.id, self.successor['id']):
                        self.successor = successor_predecessor
                else:
                    #si el sucesor no tiene predecesor, este nodo debe ser su predecesor
                    notify_url = f"http://{self.successor['ip']}:{self.successor['port']}/notify"
                    requests.post(notify_url, json=self.to_dict())

                #notificamos al sucesor que este nodo es su predecesor si es necesario
                if not self.predecessor or self.is_in_interval(self.id, self.predecessor['id'], self.successor['id']):
                    notify_url = f"http://{self.successor['ip']}:{self.successor['port']}/notify"
                    requests.post(notify_url, json=self.to_dict())
                
                self.successor_fails = 0  #resetea el contador de fallos
            except:
                print(f"error durante estabilización")
                self.successor_fails += 1
                if self.successor_fails >= 3:
                    print("demasiados errores de estabilización con sucesor, ", end="")
                    if self.predecessor:
                        print("poniendo a predecesor como sucesor")
                        self.successor = self.predecessor
                    else:
                        print("comenzando con bootstrap")
                        self.bootstrap()

            time.sleep(self.update_interval)

    def notify(self, new_predecessor: dict) -> None:
        #actualiza el predecesor si es nulo o si el nuevo es más adecuado
        if not self.predecessor or self.is_in_interval(new_predecessor['id'], self.predecessor['id'], self.id):
            self.predecessor = new_predecessor
            print(f"predecesor actualizado: {self.predecessor['id']} ({self.predecessor['ip']}:{self.predecessor['port']})")

    def check_predecessor(self):
        #verifica periódicamente si el predecesor está activo
        while True:
            if self.predecessor:
                try:
                    url = f"http://{self.predecessor['ip']}:{self.predecessor['port']}/ping"
                    response = requests.get(url)
                    response.raise_for_status()
                    self.predecessor_fails = 0  #resetea el contador de fallos
                except requests.exceptions.RequestException:
                    print(f"predecesor {self.predecessor['id']} no responde. eliminando predecesor.")
                    self.predecessor = {}
                    self.predecessor_fails += 1
                    if self.predecessor_fails >= 3:
                        print("demasiados errores con predecesor. ", end="")
                        if self.successor:
                            print("poniendo a sucesor como predecesor")
                            self.predecessor = self.successor
                        else:
                            print("comenzando con bootstrap")
                            self.bootstrap()
            time.sleep(self.update_interval)

    def find_responsible_node(self, file_id: int) -> dict:
        #encuentra el nodo responsable de un archivo basado en el id del archivo
        current_node = self.to_dict()

        while True:
            #si el id del archivo está entre el nodo actual y su sucesor, retornamos el sucesor
            if self.is_in_interval(file_id, current_node['id'], self.successor['id']):
                return self.successor
            else:
                #si no es así, seguimos preguntando al sucesor
                next_node = self.successor
                url = f"http://{next_node['ip']}:{next_node['port']}/find_successor"
                try:
                    response = requests.post(url, json={'id': file_id})
                    response.raise_for_status()
                    next_node = response.json()
                    
                    #actualizamos el nodo actual y seguimos
                    current_node = next_node
                except requests.exceptions.RequestException as e:
                    print(f"error al contactar al nodo {next_node['id']}: {e}")
                    return {}

    def store_file_grpc(self, filename: str, content: str) -> str:
        #almacena un archivo en el nodo responsable utilizando grpc
        #calculamos el id del archivo
        file_id = hash_key(filename)
        responsible_node = self.find_responsible_node(file_id)

        if not responsible_node:
            return "error: no se pudo encontrar el nodo responsable"

        try:
            #conectamos al nodo responsable y enviamos el archivo
            with grpc.insecure_channel(f"{responsible_node['ip']}:{responsible_node['port'] + 1}") as channel:
                stub = pb2_grpc.ChordServiceStub(channel)
                request = pb2.FileRequest(filename=filename, content=content)
                response = stub.StoreFile(request)
                return response.message
        except grpc.RpcError as e:
            print(f"error al almacenar archivo en nodo {responsible_node['id']}: {e}")
            return "error al almacenar el archivo"

    def download_file_grpc(self, filename: str) -> str:
        #descarga un archivo del nodo responsable utilizando grpc
        #calculamos el id del archivo
        file_id = hash_key(filename)
        responsible_node = self.find_responsible_node(file_id)

        if not responsible_node:
            return "error: no se pudo encontrar el nodo responsable"

        try:
            #conectamos al nodo responsable y solicitamos el archivo
            with grpc.insecure_channel(f"{responsible_node['ip']}:{responsible_node['port'] + 1}") as channel:
                stub = pb2_grpc.ChordServiceStub(channel)
                request = pb2.FileRequest(filename=filename)
                response = stub.DownloadFile(request)
                return response.content
        except grpc.RpcError as e:
            print(f"error al descargar archivo de nodo {responsible_node['id']}: {e}")
            return "error al descargar el archivo"

    def serve_grpc(self):
        #inicia el servidor grpc para manejar la transferencia de archivos
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        pb2_grpc.add_ChordServiceServicer_to_server(ChordService(self), server)
        server.add_insecure_port(f"[::]:{self.grpc_port}")
        server.start()
        print(f"servidor grpc escuchando en el puerto {self.grpc_port}")
        server.wait_for_termination()

    def to_dict(self) -> dict:
        #convierte la información del nodo a un diccionario para fácil transmisión
        return {'ip': self.ip, 'port': self.port, 'id': self.id}

    def store_file(self, filename: str) -> str:
        #almacena el archivo en el nodo actual
        self.files[filename] = f"contenido de {filename}"
        return f"archivo '{filename}' almacenado en el nodo {self.id}"

    def lookup_file(self, filename: str) -> str:
        #busca el archivo en el nodo actual
        if filename in self.files:
            return f"archivo '{filename}' encontrado en nodo actual ({self.id})"
        else:
            return f"archivo '{filename}' no encontrado en nodo actual ({self.id})"

    def display_info(self) -> None:
        #muestra información del nodo: id, ip, puerto, sucesor, predecesor y archivos almacenados
        print("\n=== información del nodo ===")
        print(f"id: {self.id} (ip: {self.ip}, puerto: {self.port})\n")
        print("sucesor:")
        if self.successor:
            print(f"  id: {self.successor['id']}, ip: {self.successor['ip']}, puerto: {self.successor['port']}\n")
        else:
            print("  ninguno\n")
        print("predecesor:")
        if self.predecessor:
            print(f"  id: {self.predecessor['id']}, ip: {self.predecessor['ip']}, puerto: {self.predecessor['port']}\n")
        else:
            print("  ninguno\n")
        print("\narchivos almacenados:")
        if self.files:
            for filename in self.files:
                print(f"  - {filename}")
        else:
            print("  no hay archivos almacenados")
        print("===========================\n")

#---------------------------------------------- rest api ----------------------------------------------

@app.route('/find_successor', methods=['POST'])
def find_successor_route():
    try:
        data = request.json
        if 'id' not in data:
            return jsonify({'error': 'missing id'}), 400
        
        node_id = data['id']
        result = node.find_responsible_node(node_id)
        if not result:
            return jsonify({'error': 'no se pudo encontrar el sucesor'}), 500
        return jsonify(result)
    except Exception as e:
        print(f"error en /find_successor: {str(e)}")
        return jsonify({'error': f"internal server error: {str(e)}"}), 500

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
        return jsonify({'error': 'invalid request'}), 400
    node.notify(data)
    return jsonify({'message': 'predecesor actualizado'})

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.json
        if 'filename' not in data:
            return jsonify({'error': 'missing filename'}), 400

        result = node.search(data['filename'])
        return jsonify(result)
    except Exception as e:
        print(f"error en /search: {str(e)}")
        return jsonify({'error': f"internal server error: {str(e)}"}), 500

@app.route('/ping', methods=['GET'])
def ping():
    #función simple para verificar si el nodo está activo
    return jsonify({'message': 'pong'})

def serve_rest() -> None:
    #inicia el servidor rest
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
    node = Node(ip, port, node_id, update_interval, config)
    
    node.bootstrap()

    #iniciamos los servidores y procesos de estabilización
    threading.Thread(target=serve_rest).start()
    threading.Thread(target=node.serve_grpc).start()  #iniciar el servidor grpc en un hilo separado
    threading.Thread(target=node.stabilize).start()
    threading.Thread(target=node.check_predecessor).start()

    #loop principal para manejar comandos desde la consola
    while True:
        command = input("> ").strip()
        if command.startswith("store"):
            _, filename, content = command.split(maxsplit=2)
            print(node.store_file_grpc(filename, content))
        elif command.startswith("lookup"):
            _, filename = command.split()
            print(node.lookup_file(filename))
        elif command.startswith("search"):
            _, filename = command.split()
            response = node.search(filename)
            if 'error' in response:
                print(response['error'])
            else:
                print(f"archivo '{filename}' está en {response['url']}")
        elif command.startswith("download"):
            _, filename = command.split()
            content = node.download_file_grpc(filename)
            print(f"contenido descargado: {content}")
        elif command == "info":
            node.display_info()
        else:
            print("comando no reconocido")

def hash_key(key: str) -> int:
    #genera un id único basado en el hash sha-1 de la clave
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**16)

if __name__ == '__main__':
    main()
