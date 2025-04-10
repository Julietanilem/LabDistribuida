import simpy  # Biblioteca para simulación de eventos discretos
import random  # Añadido para despertar aleatoriamente nodos
import networkx as nx  # Biblioteca para gráficas
import matplotlib.pyplot as plt  # Biblioteca para dibujar gráficas

# Clase que representa un nodo en la gráfica.
class Node:
    def __init__(self, id):
        self.id = id                # Identificador único del nodo
        self.left_neighbor = None   # Vecino izquierdo en la gráfica
        self.right_neighbor = None  # Vecino derecho en la gráfica
        # Atributos para el algoritmo de elección de líder
        self.status = "asleep"      # Estado inicial del nodo
        self.min = None             # El valor mínimo visto
        self.waiting = []           # Mensajes esperando ser enviados [(mensaje, fase, tiempo_recepción)]
        self.is_leader = False      # Indica si este nodo es el líder

# Clase que representa una arista en la gráfica.
class Edge:
    def __init__(self, node1, node2):
        self.node1 = node1              # Primer extremo de la arista
        self.node2 = node2              # Segundo extremo de la arista
        node1.right_neighbor = node2    # Actualiza vecino derecho del nodo1
        node2.left_neighbor = node1     # Actualiza vecino izquierdo del nodo2

# Clase que representa la gráfica y gestiona la simulación del algoritmo
class Graph:
    def __init__(self, nodes, edges):
        self.env = simpy.Environment()  # Entorno de simulación para controlar el tiempo
        self.nodes = nodes              # Lista de todos los nodos en la gráfica
        self.edges = edges              # Lista de todas las aristas en la gráfica
        self.messages = {node: [] for node in nodes}  # Mensajes por procesar para cada nodo
        self.orderNode = nodes
    def process_round(self):
        """Ejecuta una ronda del algoritmo para todos los nodos activos"""
        # Guardar mensajes actuales y limpiar para la próxima ronda
        current_messages = {node: msgs[:] for node, msgs in self.messages.items()}
        self.messages = {node: [] for node in self.nodes}
        
        activity = False  # Para detectar si hay actividad en la ronda
        
        # Procesar cada nodo (solo si está activo o ha recibido mensajes)
        for node in self.nodes:
            # 1: let R be the set of messages received in this computation event
            R = current_messages[node]

            # 2: S := ∅ // the messages to be sent
            S = []
            
            # 3: if status = asleep then
            if node.status == "asleep":
                # 4: if R is empty then // woke up spontaneously
                if not R:
                    # 5: status := participating
                    node.status = "participating"
                    # 6: min := id
                    node.min = node.id
                    # 7: add (id, 1) to S // first phase message
                    S.append((node.id, 1))
                # 8: else
                else:
                    # 9: status := relay
                    node.status = "relay"
                    # 10: min := ∞
                    node.min = float('inf')
            
            # 9: for each (m,h) in R do
            for m, h in R:
                # 10: if m < min then
                if node.min is None or m < node.min:
                    # 11: become not elected
                    past_status = node.status
                    
                    node.status = "not_elected"
                    # 12: min := m
                    node.min = m
                    
                    # 13: if (status = relay) and (h = 1) then // m stays first phase
                    if past_status == "relay" and h == 1:
                        # 14: add (m,h) to S
                        S.append((m, h))
                    # 15: else // m is/becomes second phase
                    else:
                        # 16: add (m,2) to waiting tagged with current time
                        node.waiting.append((m, 2, self.env.now))
                
                # 17: elseif m = id then become elected
                elif m == node.id:
                        node.status = "elected"
                        node.is_leader = True
                        print(f"Nodo {node.id} se ha declarado líder al recibir su propio ID")
            
            # 18: for each (m,2) in waiting do
            new_waiting = []
            for m, h, stored_time in node.waiting:
                # 19: if (m,2) was received 2^m - 1 rounds ago then
                if self.env.now - stored_time >= (2**m - 1):
                    # 20: remove (m) from waiting and add to S
                    S.append((m, h))
                else:
                    new_waiting.append((m, h, stored_time))
            
            node.waiting = new_waiting
            
            # 21: send S to left
            if S or node.waiting:
                activity = True
                self.messages[node.left_neighbor].extend(S)
        
        return activity
    
    def round_process(self):
        """Proceso SimPy para controlar las rondas"""
        activity = True
       
        while activity and self.env.now < self.max_rounds:
            print(f"Ronda {self.env.now}")
            activity = self.process_round()
            
            # Mostrar estado de cada nodo
            for node in self.nodes:
                leader_status = " (LÍDER)" if node.is_leader else ""
                print(f"Nodo {node.id}: Estatus = {node.status}, Min = {node.min}{leader_status}")
            print()
            
            # Esperar un tiempo entre rondas
            yield self.env.timeout(1)
    
    def run_election(self, max_rounds=100, initiator_id=None):
        """Ejecuta el algoritmo de elección de líder usando SimPy"""

        self.max_rounds = max_rounds

        #Hacemos del iniciador el primero en la lista para que sea el primero en ser procesado 
        self.nodes = [n for n in self.nodes if n.id == initiator_id] + [n for n in self.nodes if n.id != initiator_id]

        # Crear y ejecutar el proceso de rondas
        proc = self.env.process(self.round_process())
        self.env.run(until=proc)
      
        # Verificar resultado final
        leaders = [node for node in self.nodes if node.is_leader]
        if leaders:
            print(f"¡Elección terminada! El líder es el nodo {leaders[0].id}")
        else:
            print("La elección terminó sin un líder claro")
        
        return leaders

    def graficar_anillo(self):
        """
        Grafica la red después de que el algoritmo de elección de líder
        ha terminado. Los nodos se colorearán según su estado final en la elección:
            - Amarillo (gold) si el nodo es el líder
            - Celeste (skyblue) si el nodo participó en la elección
            - Naranja (orange) si el nodo fue relay
            - Rojo (red) si el nodo no fue elegido
            - Gris (gray) si el nodo no cambió de estado
        """

        G = nx.Graph() 
           
        for node in self.orderNode:
            G.add_node(node.id)

        for node in self.orderNode:
            if node.right_neighbor:
                G.add_edge(node.id, node.right_neighbor.id)
        
        pos = nx.circular_layout(G) 

        # Colorear según estado final
        color_map = []
        for node in self.orderNode:
            if node.status == "elected":
                color_map.append("gold")
            elif node.status == "participating":
                color_map.append("skyblue")
            elif node.status == "relay":
                color_map.append("orange")
            elif node.status == "not_elected":
                color_map.append("red")
            else:
                color_map.append("gray") 

        plt.figure(figsize=(8, 8))
        nx.draw(G, pos, with_labels=True, node_color=color_map, node_size=1000)
        plt.title("Red según los estados finales de los nodos")
        plt.axis("off")
        plt.show()



# Solicitar al usuario el número de nodos
print("Algoritmo de Elección de Líder")
try:
    num_nodes = int(input("Ingrese el número de nodos en la red: "))
    if num_nodes <= 0:
        print("El número de nodos debe ser positivo. Usando 10 por defecto.")
        num_nodes = 10
except ValueError:
    print("Entrada inválida. Usando 10 nodos por defecto.")
    num_nodes = 10

# Crear nodos
nodes = [Node(i) for i in range(num_nodes)]

# Crear conexiones en anillo
edges = []
for i in range(len(nodes)):
    edges.append(Edge(nodes[i], nodes[(i+1) % len(nodes)]))

# Crear gráfica
graph = Graph(nodes, edges)


# Seleccionar un iniciador aleatorio
random_initiator = random.choice([node.id for node in nodes])
print(f"Iniciando elección con nodo aleatorio: {random_initiator}")

# Ejecutar elección con el nodo aleatorio como iniciador
leaders = graph.run_election(initiator_id=random_initiator)


# Gráficar anillo
graph.graficar_anillo()