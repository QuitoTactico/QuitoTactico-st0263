import grpc
import chord_pb2_grpc as pb2_grpc
import chord_pb2 as pb2

class ChordService(pb2_grpc.ChordServiceServicer):
    def __init__(self, node):
        self.node = node

    def StoreFile(self, request, context):
        """
        Implementa el almacenamiento de un archivo en el nodo actual.
        """
        filename = request.filename
        content = request.content
        self.node.files[filename] = content
        return pb2.FileResponse(message=f"Archivo '{filename}' almacenado en nodo {self.node.id}")

    def DownloadFile(self, request, context):
        """
        Implementa la descarga de un archivo desde el nodo actual.
        """
        filename = request.filename
        if filename in self.node.files:
            return pb2.FileResponse(content=self.node.files[filename])
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Archivo '{filename}' no encontrado en nodo {self.node.id}")
            return pb2.FileResponse(content="No encontrado.") #no se puede devolver None

