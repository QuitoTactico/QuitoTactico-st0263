# ST0263 Tópicos especiales en telemática

## Estudiante(s): 
Jonathan Betancur, jbetancur3@eafit.edu.co  
Esteban Vergara, evergarag@eafit.edu.co

## Profesor: 
Alvaro Enrique Ospina SanJuan, aeospinas@eafit.edu.co

---

## 1. Breve descripción:

En este reto se implementa un sistema P2P que permite la transferencia de archivos de manera distribuida. Cada nodo en la red P2P puede almacenar, buscar y listar archivos, simulando un sistema de compartición de archivos. El objetivo es simular un sistema distribuido en el que los nodos pueden unirse a la red, estabilizarse, y realizar operaciones de almacenamiento y búsqueda de archivos utilizando una arquitectura basada en Chord.

### 1.1. Aspectos cumplidos o desarrollados de la actividad propuesta por el profesor (requerimientos funcionales y no funcionales):

- Implementación de un esquema de red P2P utilizando el protocolo Chord.
- Despliegue de nodos en una red distribuida, permitiendo la unión y estabilización automática de los nodos.
- Implementación de un sistema básico de transferencia y búsqueda de archivos utilizando gRPC.
- Configuración flexible a través de un archivo `config.json` que permite especificar IPs y puertos de forma dinámica.
- El código está preparado para ser desplegado en instancias EC2 de AWS.

### 1.2. Aspectos NO cumplidos o desarrollados de la actividad propuesta por el profesor (requerimientos funcionales y no funcionales):

- Flask se ha incluido en los requisitos, pero hasta el momento no ha sido utilizado en la implementación actual.
- Aún no se ha implementado una verdadera transferencia de archivos, solo una simulación básica.
- No se ha integrado MOM (Message-Oriented Middleware) en la solución actual.

---

## 2. Información general de diseño de alto nivel, arquitectura, patrones, mejores prácticas utilizadas:

- **Arquitectura P2P basada en Chord:** Se utiliza el protocolo Chord para organizar los nodos en un anillo y permitir la búsqueda eficiente de archivos mediante una tabla de rutas (finger table).
- **gRPC para comunicación entre nodos:** Se utiliza gRPC para la comunicación remota entre los nodos, permitiendo el envío y recepción de mensajes de manera eficiente.
- **Estructura modular:** El código está organizado en clases que representan los nodos, servicios gRPC y la lógica de negocio necesaria para el manejo de archivos y la estabilización de la red.
- **Configuración flexible:** La configuración del sistema (IP, puerto, nodo de arranque) se realiza a través de un archivo `config.json` que se puede modificar según sea necesario.

---

## 3. Descripción del ambiente de desarrollo y técnico:

- **Lenguaje de programación:** Python 3.12
- **Librerías y paquetes utilizados:**
  - `grpcio`: Para implementar la comunicación gRPC entre los nodos.
  - `grpcio-tools`: Para compilar los archivos `.proto` en código Python.
  - `Flask`: Incluido en los requisitos, aunque aún no utilizado.

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
   sudo nano config.json
   # Agregar la IP propia en "own_ip" y el puerto en "own_port"
   # Dejar en blanco "bootstrap_ip" y "bootstrap_port", ya sea no definiéndolos o dejándolos como ""
   python3 node.py
   ```

3. **Iniciar nodos adicionales:**

   ```bash
   sudo nano config.json
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

- **Archivo de configuración `config.json`:**
  - `own_ip`: La dirección IP que el nodo utilizará para escuchar conexiones.
  - `own_port`: El puerto que el nodo utilizará para escuchar conexiones.
  - `bootstrap_ip`: La dirección IP de un nodo existente al cual este nodo se unirá. Dejar en blanco si este es el primer nodo.
  - `bootstrap_port`: El puerto del nodo existente al cual este nodo se unirá. Dejar en blanco si este es el primer nodo.

### Organización del código:

- **`node.py`:** Contiene la implementación del nodo, incluyendo la lógica para estabilización, almacenamiento de archivos y comunicación entre nodos.

---

## 4. Descripción del ambiente de EJECUCIÓN (en producción):

- **Lenguaje de programación:** Python 3.12
- **Librerías y paquetes utilizados:**
  - `grpcio`: Versión utilizada para la comunicación gRPC.
  - `grpcio-tools`: Utilizado para compilar archivos `.proto`.
  - `Flask`: Incluido en los requisitos, pero no utilizado hasta el momento.

### IP o nombres de dominio en nube o en la máquina servidor:

- **AWS EC2 Instances:** Las instancias EC2 son utilizadas para desplegar los nodos en la red P2P.

### Cómo se lanza el servidor:

- **Iniciar un nodo:**
  ```bash
  python3 node.py
  ```

### Mini guía de uso:

- **Para almacenar un archivo:**
  ```bash
  store <nombre_del_archivo>
  ```

- **Para buscar un archivo:**
  ```bash
  lookup <nombre_del_archivo>
  ```

- **Para listar archivos en el nodo:**
  ```bash
  list
  ```

- **Para ver la información del nodo (finger table, sucesor, predecesor, configuración):**
  ```bash
  info
  ```

---

## 5. Otra información relevante:

- **Resiliencia y escalabilidad:** El sistema está diseñado para ser escalable y permitir la adición de nodos sin interrupciones.
- **Pruebas en ambiente real:** Se recomienda probar la solución en un entorno distribuido (por ejemplo, usando múltiples instancias EC2 en AWS) para simular adecuadamente el comportamiento de una red P2P.

---

## Referencias:

- **gRPC Official Documentation:** [https://grpc.io/docs/](https://grpc.io/docs/)
- **Chord: A Scalable Peer-to-peer Lookup Service for Internet Applications** [Chord Paper](https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf)
- **AWS EC2 Documentation:** [https://docs.aws.amazon.com/ec2/](https://docs.aws.amazon.com/ec2/)
