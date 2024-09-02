# ST0263 Tópicos especiales en telemática

## Estudiante(s): 
Jonathan Betancur, jbetancur3@eafit.edu.co  
Esteban Vergara, evergarag@eafit.edu.co

## Profesor: 
Alvaro Enrique Ospina SanJuan, aeospinas@eafit.edu.co

---

## 1. Breve descripción

Este proyecto implementa un sistema P2P utilizando la arquitectura basada en Chord. La red Chord permite la distribución y búsqueda eficiente de claves (archivos) en un sistema distribuido. Las operaciones de red, como la búsqueda de sucesores y la notificación entre nodos, se manejan mediante una API REST desarrollada con Flask, mientras que la transferencia de archivos se simula utilizando gRPC. El sistema permite la adición dinámica de nodos a la red, la estabilización automática y operaciones de almacenamiento y búsqueda de archivos a través de comandos de consola.

### 1.1. Aspectos cumplidos o desarrollados de la actividad propuesta por el profesor (requerimientos funcionales y no funcionales):

- Implementación de una red P2P basada en Chord utilizando REST para la comunicación entre nodos.
- Simulación de transferencia de archivos mediante gRPC.
- Configuración flexible a través de un archivo `bootstrap.json` que permite especificar IPs y puertos de forma dinámica.
- Implementación de lógica de estabilización para mantener la red Chord actualizada y en topología de anillo.
- Verificación periódica de la disponibilidad del predecesor para asegurar la consistencia de la red.
- Interfaz de comandos para subir, almacenar, buscar archivos y obtener información del nodo.
- El sistema se puede desplegar en instancias EC2 de AWS.
- Implementación de una opción segura para salir del programa (`exit`), asegurando que todos los hilos se cierren correctamente antes de cerrar la instancia, pero el sistema es capaz de soportar cierres de nodos a pesar de no usar el comando.

### 1.2. Aspectos NO cumplidos o desarrollados de la actividad propuesta por el profesor (requerimientos funcionales y no funcionales):

- El sistema simula la transferencia de archivos usando gRPC, pero no realiza transferencias reales de datos binarios de gran tamaño.
- No se implementó la tabla de fingers para mejorar la eficiencia en la búsqueda de sucesores, simplificando así el modelo a O(N).
- No se implementó la solución usando un Message Oriented Middleware (MOM) por la razón:
    - Facilidad de implementación: se optó por un modelo de peticiones API REST que procesa las solicitudes directamente, evitando la complejidad adicional de un middleware.

---

## 2. Información general de diseño de alto nivel, arquitectura, patrones, mejores prácticas utilizadas

- **Arquitectura P2P basada en Chord (simplificada):** La red se organiza en un anillo, lo que permite la búsqueda de archivos utilizando sucesores y predecesores.
- **REST API para comunicación:** Flask se utiliza para manejar las operaciones de red, proporcionando flexibilidad y facilidad de depuración.
- **gRPC para transferencia de archivos:** gRPC se utiliza para la simulación de la transferencia de archivos, aprovechando su eficiencia en la transmisión de datos binarios.
- **Configuración dinámica:** La configuración del sistema (IP, puerto, nodo de arranque) se realiza a través de un archivo `bootstrap.json`.
- **Estabilización Automática:** El sistema cuenta con mecanismos para la estabilización automática de la red, verificando y corrigiendo los sucesores y predecesores de cada nodo.

---

## 3. Descripción del ambiente de desarrollo y técnico

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

2. **Iniciar el primer nodo:**

   ```bash
   cd QuitoTactico-st0263
   git pull
   sudo nano bootstrap.json
   # Agregar la IP propia en "own_ip" y el puerto en "own_port"
   # Dejar en blanco "bootstrap_ip" y "bootstrap_port", ya sea no definiéndolos o dejándolos como ""
   python3 node.py
   ```

3. **Iniciar los nodos siguientes:**

   ```bash
   cd QuitoTactico-st0263
   git pull
   sudo nano bootstrap.json
   # Agregar la IP propia en "own_ip" y el puerto en "own_port"
   # Agregar la IP a la que se conectará en "bootstrap_ip" y el puerto en "bootstrap_port"
   python3 node.py
   ```

#### (INICIOS RÁPIDOS:)

4. **Cambiar bootstrap rápido de máquina ya montada:**

   ```bash
   cd QuitoTactico-st0263
   git pull
   sudo nano bootstrap.json
   ```

5. **Inicio rápido de una máquina ya montada:**

    ```bash
    cd QuitoTactico-st0263
    git pull
    python3 node.py
    ```


### Misceláneo:

- **Si quieres compilar el proto (asegúrate de instalar requirements.txt primero):**

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
- **`chord.proto`**: Definición de interfaces del servicio gRPC para la transferencia de archivos.
- **`grpc_service.py`**: Definición de lógica/contenido en funciones del servicio gRPC para la transferencia de archivos.

---

## 4. Descripción del ambiente de EJECUCIÓN (en producción)

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
  cd QuitoTactico-st0263
  python3 node.py
  ```

### Mini guía de uso:

- **Para almacenar un archivo en la red (desde la consola):**
  ```bash
  > store <filename> <content>
  ```

- **Para buscar un archivo en el nodo actual (desde la consola):**
  ```bash
  > lookup <filename>
  ```

- **Para obtener la url del nodo en cuyo dominio está un archivo en la red (desde la consola):**
  ```bash
  > search <filename>
  ```

- **Para descargar un archivo en la red (desde la consola):**
  ```bash
  > download <filename>
  ```

- **Para ver la información del nodo (sucesor, predecesor, archivos):**
  ```bash
  > info
  ```

- **Para ver la ayuda (lista de comandos):**
  ```bash
  > help
  ```

- **Para salir del programa de forma segura:**
  ```bash
  > exit
  ```

---

## 5. Otra información relevante:

- **Resiliencia y escalabilidad:** El sistema está diseñado para ser escalable y permitir la adición de nodos sin interrupciones. Y no sólo se puede agregar nodos, sino que también se pueden eliminar nodos sin afectar la red, ya sea a propósito o por errores en esos nodos. La red se estabiliza automáticamente en forma de anillo para mantener la consistencia y la disponibilidad de los archivos.

- **Pruebas en ambiente real:** Se probó la solución en un entorno distribuido (usando múltiples instancias EC2 en AWS) para simular adecuadamente el comportamiento de la red P2P. Las pasó con éxito, demostrando la capacidad de la solución para manejar la distribución y búsqueda de archivos en un entorno real.

---

## Referencias:

- **gRPC Official Documentation:** [https://grpc.io/docs/](https://grpc.io/docs/)
- **Chord: A Scalable Peer-to-peer Lookup Service for Internet Applications** [Chord Paper](https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf)
- **Flask Documentation:** [https://flask.palletsprojects.com/en/2.0.x/](https://flask.palletsprojects.com/en/2.0.x/)
- **AWS EC2 Documentation:** [https://docs.aws.amazon.com/ec2/](https://docs.aws.amazon.com/ec2/)
- **Chord-DHT-for-File-Sharing** https://github.com/MNoumanAbbasi/Chord-DHT-for-File-Sharing/blob/master/Node.py
- **Distributed Hash Tables: In a nutshell (Reupload)** https://youtu.be/1wTucsUm64s?si=S6rqhMLNlAISu9Ad
- **Chord - A Distributed Hash Table** https://youtu.be/9kd1aj8E30k?si=SK5_6vMQEPsI396E
- **CSC 464 Project - Simulation of Chord DHT using threads in Python** https://youtu.be/swGm18mVEmQ?si=6OqHfAg8dbhNtOLz
---

## Video:

Aquí pondremos el link :)