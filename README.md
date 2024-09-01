# ST0263 Tópicos especiales en telemática

## Estudiante(s): 
Jonathan Betancur, jbetancur3@eafit.edu.co  
Esteban Vergara, evergarag@eafit.edu.co

## Profesor: 
Alvaro Enrique Ospina SanJuan, aeospinas@eafit.edu.co

---

## 1. Breve descripción:

Este proyecto implementa un sistema P2P utilizando la arquitectura basada en Chord. La red Chord permite la distribución y búsqueda eficiente de claves (archivos) en un sistema distribuido. Las operaciones de red, como la búsqueda de sucesores y la notificación entre nodos, se manejan mediante una API REST desarrollada con Flask, mientras que la transferencia de archivos se simula utilizando gRPC. El sistema permite la adición dinámica de nodos a la red, la estabilización automática y operaciones de almacenamiento y búsqueda de archivos a través de comandos de consola.

### 1.1. Aspectos cumplidos o desarrollados de la actividad propuesta por el profesor (requerimientos funcionales y no funcionales):

- Implementación de una red P2P basada en Chord utilizando REST para la comunicación entre nodos.
- Simulación de transferencia de archivos mediante gRPC.
- Configuración flexible a través de un archivo `bootstrap.json` que permite especificar IPs y puertos de forma dinámica.
- Implementación de lógica de estabilización para mantener la red Chord actualizada.
- Implementación completa de la finger table para mejorar la eficiencia en la búsqueda de sucesores.
- Verificación periódica de la disponibilidad del predecesor para asegurar la consistencia de la red.
- Interfaz de comandos para almacenar, buscar archivos y obtener información del nodo.
- El sistema se puede desplegar en instancias EC2 de AWS.

### 1.2. Aspectos NO cumplidos o desarrollados de la actividad propuesta por el profesor (requerimientos funcionales y no funcionales):
- El sistema simula la transferencia de archivos, pero no realiza transferencias reales de datos binarios.
- No se implementó la solución usando un Message Oriented Middleware (MOM) por la razón:
-     Facilidad de implementación: añadir un middleware que procese las solicitudes temporalmente, y se las envíe a los o el nodo respectivo, a veces puede ser complicado, por lo que para esta solución optamos por un modelo de peticiones API REST que procese las solicitudes directamente
- Se pensaron en los beneficios que recurría implementar mom, tales como: reducir la interdependencia de nodos, ya que si uno se tardaba en su solicitud, los demás tenían este mismo comportamiento, o también que tener un middleware pued llevar a que la solución sea más escalable aumentando la cantidad de nodos sin comprometer la integridad de uno respecto al otro a la hora de procesar la solicitud o enviarla.
---

## 2. Información general de diseño de alto nivel, arquitectura, patrones, mejores prácticas utilizadas:

- **Arquitectura P2P basada en Chord:** La red se organiza en un anillo, lo que permite la búsqueda eficiente de archivos utilizando una tabla de rutas (finger table).
- **REST API para comunicación:** Flask se utiliza para manejar las operaciones de red, proporcionando flexibilidad y facilidad de depuración.
- **gRPC para transferencia de archivos:** gRPC se utiliza para la simulación de la transferencia de archivos, aprovechando su eficiencia en la transmisión de datos binarios.
- **Configuración dinámica:** La configuración del sistema (IP, puerto, nodo de arranque) se realiza a través de un archivo `bootstrap.json`.
- **Finger Table:** Implementación completa de la finger table para mejorar la eficiencia en la búsqueda de sucesores en la red.
- **Estabilización Automática:** El sistema cuenta con mecanismos para la estabilización automática de la red, verificando y corrigiendo los sucesores y predecesores de cada nodo.

---

## 3. Descripción del ambiente de desarrollo y técnico:

- **Lenguaje de programación:** Python 3.12
- **Librerías y paquetes utilizados:**
  - `grpcio`: Para implementar la comunicación gRPC.
  - `grpcio-tools`: Para compilar los archivos `.proto` en código Python.
  - `Flask`: Utilizado para implementar la API REST.
  - `requests`: Utilizado para realizar solicitudes HTTP en la API REST.

### Cómo se compila y ejecuta:

1. **Configuración de la máquina EC2:**

   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip
   sudo apt-get install git
   git clone https://github.com/QuitoTactico/QuitoTactico-st0263
   cd QuitoTactico-st0263
   pip3 install -r requirements.txt
   ```

2. **Compilar el archivo `.proto`:**

   Si necesitas compilar el archivo `chord.proto`, utiliza el siguiente comando:

   ```bash
   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chord.proto
   ```

   Esto generará los archivos `chord_pb2.py` y `chord_pb2_grpc.py`.

3. **Iniciar el primer nodo:**

   ```bash
   sudo nano bootstrap.json
   # Agregar la IP propia en "own_ip" y el puerto en "own_port"
   # Dejar en blanco "bootstrap_ip" y "bootstrap_port" si este es el primer nodo
   python3 node.py
   ```

4. **Iniciar nodos adicionales:**

   ```bash
   sudo nano bootstrap.json
   # Agregar la IP propia en "own_ip" y el puerto en "own_port"
   # Agregar la IP a la que se conectará en "bootstrap_ip" y el puerto en "bootstrap_port"
   python3 node.py
   ```

### Detalles técnicos:

- **Compilación de archivos .proto:**
  Si es necesario recompilar los archivos `.proto`, se puede hacer con el siguiente comando:

  ```bash
  python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chord.proto
  ```

### Descripción y configuración de parámetros:

- **Archivo de configuración `bootstrap.json`:**
  - `own_ip`: La dirección IP que el nodo utilizará para escuchar conexiones REST.
  - `own_port`: El puerto que el nodo utilizará para escuchar conexiones REST.
  - `update_interval`: Intervalo de tiempo en segundos para la estabilización de la red.
  - `bootstrap_ip`: La dirección IP de un nodo existente al cual este nodo se unirá. Dejar en blanco si este es el primer nodo.
  - `bootstrap_port`: El puerto del nodo existente al cual este nodo se unirá. Dejar en blanco si este es el primer nodo.

### Organización del código:

- **`bootstrap.json`**: Archivo de configuración para los nodos.
- **`node.py`**: Implementa la lógica del nodo, la comunicación REST y los comandos de consola.
- **`chord.proto`**: Definición del servicio gRPC para la transferencia de archivos.
- **`grpc_service.py`**: Implementación del servicio gRPC basado en el archivo `.proto`.

---

## 4. Descripción del ambiente de EJECUCIÓN (en producción):

- **Lenguaje de programación:** Python 3.12
- **Librerías y paquetes utilizados:**
  - `grpcio`: Versión utilizada para la comunicación gRPC.
  - `grpcio-tools`: Utilizado para compilar archivos `.proto`.
  - `Flask`: Utilizado para manejar la API REST.

### IP o nombres de dominio en nube o en la máquina servidor:

- **AWS EC2 Instances:** Las instancias EC2 son utilizadas para desplegar los nodos en la red P2P.

### Cómo se lanza el servidor:

- **Iniciar un nodo:**
  ```bash
  python3 node.py
  ```

### Mini guía de uso:

- **Para almacenar un archivo (desde la consola):**
  ```bash
  > store tarea.txt
  ```

- **Para buscar un archivo (desde la consola):**
  ```bash
  > lookup tarea.txt
  ```

- **Para ver la información del nodo (finger table, sucesor, predecesor, archivos):**
  ```bash
  > info
  ```

---

## 5. Otra información relevante:

- **Resiliencia y escalabilidad:** El sistema está diseñado para ser escalable y permitir la adición de nodos sin interrupciones.
- **Pruebas en ambiente real:** Se recomienda probar la solución en un entorno distribuido (por ejemplo, usando múltiples instancias EC2 en AWS) para simular adecuadamente el comportamiento de una red P2P.

---

## Referencias:

- **gRPC Official Documentation:** [https://grpc.io/docs/](https://grpc.io/docs/)
- **Chord: A Scalable Peer-to-peer Lookup Service for Internet Applications** [Chord Paper](https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf)
- **Flask Documentation:** [https://flask.palletsprojects.com/en/2.0.x/](https://flask.palletsprojects.com/en/2.0.x/)
- **AWS EC2 Documentation:** [https://docs.aws.amazon.com/ec2/](https://docs.aws.amazon.com/ec2/)

## Referencias:

- **gRPC Official Documentation:** [https://grpc.io/docs/](https://grpc.io/docs/)
- **Chord: A Scalable Peer-to-peer Lookup Service for Internet Applications** [Chord Paper](https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf)
- **AWS EC2 Documentation:** [https://docs.aws.amazon.com/ec2/](https://docs.aws.amazon.com/ec2/)
