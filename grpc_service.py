import grpc
from concurrent import futures
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2

class ChordService(pb2_grpc.ChordServiceServicer):
    def __init__(self, node):
        self.node = node

    def StoreFile(self, request, context):
        filename = request.filename
        self.node.files[filename] = f"Transfiriendo {filename}... Archivo transferido"
        return pb2.FileResponse(message=f"Archivo '{filename}' almacenado en el nodo {self.node.id}")

    def LookupFile(self, request, context):
        filename = request.filename
        if filename in self.node.files:
            return pb2.FileResponse(message=f"Archivo '{filename}' encontrado en nodo {self.node.id} ({self.node.ip}:{self.node.port})")
        else:
            return pb2.FileResponse(message=f"Archivo '{filename}' no encontrado")

    def TransferFile(self, request, context):
        filename = request.filename
        if filename in self.node.files:
            return pb2.FileResponse(message=self.node.files[filename])
        else:
            return pb2.FileResponse(message=f"Archivo '{filename}' no encontrado")

def serve_grpc(node):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_ChordServiceServicer_to_server(ChordService(node), server)
    server.add_insecure_port(f'{node.ip}:{node.port + 1}')  # gRPC server en un puerto diferente
    server.start()
    server.wait_for_termination()
