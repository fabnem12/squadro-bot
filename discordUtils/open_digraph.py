#!/usr/bin/python3
import sys
sys.path += ['../', './']# allows us to fetch files from the project root
from math import cos, sin, pi
from typing import List, Tuple, Optional, Dict, Union, Set
try:
    from utilsOD import *
except ImportError:
    from .utilsOD import *
import random

class Node:
    def __init__(self, identity: int, label: str, parents: List[int], children: List[int]):
        '''
        identity: its unique id in the graph
        label: its label
        parents: a sorted list containing the ids of its parents
        children: a sorted list containing the ids of its children
        '''
        #juste pour être sûr, on trie parents et children, sinon ça peut poser des pbs pour la suite
        parents.sort()
        children.sort()

        self.id = identity
        self.label = label
        self.parents = parents
        self.children = children

    def __eq__(self, compare): return isinstance(compare, Node) and self.id == compare.id and self.label == compare.label and self.parents == compare.parents and self.children == compare.children
    def __str__(self): return f"Nœud {self.label}, parents : {self.parents}, enfants : {self.children}"
    __repr__ = __str__

    def getId(self) -> int: return self.id
    def getLabel(self) -> str: return self.label
    def getParentsIds(self) -> List[int]: return self.parents
    def getChildrenIds(self) -> List[int]: return self.children

    def shiftIndices(self: 'Node', n: int) -> None:
        self.id += n

        self.parents = [x + n for x in self.parents]
        self.children = [x + n for x in self.children]

    def setId(self, newId: int) -> None: self.id = newId
    def setLabel(self, newLabel: str) -> None: self.label = newLabel

    def setParentsIds(self, newParents: List[int]) -> None:
        newParents.sort()
        self.parents = newParents
    def setChildrenIds(self, newChildren: List[int]) -> None:
        newChildren.sort()
        self.children = newChildren

    def addParentId(self: 'Node', newParent: int) -> None: #insertion dans une liste triée…
        insertSortedList(self.parents, newParent)

    def addChildId(self: 'Node', newChild: int) -> None:
        insertSortedList(self.children, newChild)

    def copy(self: 'Node') -> 'Node':
        return Node(self.id, self.label, self.parents.copy(), self.children.copy())

    def removeParentId(self: 'Node', ident: int) -> None:
        if ident in self.parents: self.parents.remove(ident)
    def removeChildId(self: 'Node', ident: int) -> None:
        if ident in self.children: self.children.remove(ident)
    def removeParentIdAll(self: 'Node', ident: int) -> None: removeAll(self.parents, ident)
    def removeChildIdAll(self: 'Node', ident: int) -> None: removeAll(self.children, ident)

    def inDegree(self: 'Node') -> int:
        return len(self.parents)
    def outDegree(self: 'Node') -> int:
        return len(self.children)

    def degree(self: 'Node') -> int:
        return self.inDegree() + self.outDegree()

class OpenDigraph: #for open directed graphs
    def __init__(self, inputs: List[int], outputs: List[int], nodes: List[Node]):
        '''
        inputs: the ids of the input nodes
        outputs: the ids of the output nodes
        nodes: list of nodes
        '''
        self.inputs = inputs
        self.outputs = outputs
        self.nodes = {node.id: node for node in nodes}

    def __str__(self): return "\n".join(str(x) for x in self.nodes.values())
    __repr__ = __str__

    def __eq__(self, compare):
        return isinstance(compare, OpenDigraph) and self.inputs == compare.inputs and self.outputs == compare.outputs and self.nodes == compare.nodes

    def getInputIds(self) -> List[int]: return self.inputs
    def getOutputIds(self) -> List[int]: return self.outputs
    def getIdNodeMap(self) -> List[Node]: return self.nodes
    def getNodes(self) -> List[Node]: return list(self.nodes.values())
    def getNodeIds(self) -> List[int]: return list(self.nodes.keys())
    def getNodeById(self, id: int) -> List[int]: return self.nodes[id]
    def getNodesByIds(self, ids: List[int]) -> List[Node]: return [self.nodes[id] for id in ids]

    def setInputIds(self, newInputs: List[int]) -> None: self.inputs = newInputs
    def setOutputIds(self, newOutputs: List[int]) -> None: self.outputs = newOutputs
    def addInputId(self, newInput: int) -> None: self.inputs.append(newInput)
    def addOutputId(self, newOutput: int) -> None: self.outputs.append(newOutput)

    def maxId(self) -> int:
        return max(self.nodes.keys(), default = 0)

    def minId(self) -> int:
        return min(self.nodes.keys(), default = 0)

    def newId(self) -> int:
        """
        Renvoie un identifiant non utilisé dans le graphe,
        donc libre pour être utilisé par un nouveau nœud.
        """
        return self.maxId()+1

    def addEdge(self, src: int, tgt: int) -> None:
        """
        Ajoute une arête du nœud d'id 'src' vers celui d'id 'tgt'.
        """
        self.getNodeById(src).addChildId(tgt)
        self.getNodeById(tgt).addParentId(src)

    def addEdges(self, *edges: List[Tuple[int, int]]) -> None:
        """
        Ajouter une série d'arêtes avec la méthode 'addEdge'.
        """
        for src, tgt in edges:
            self.addEdge(src, tgt)

    def addNode(self: 'OpenDigraph', label: str = '', parents: List[int] = [], children: List[int] = []) -> int:
        """
        Ajouter un nouveau nœud au graphe à partir de son label, des ids de ses parents et enfants.
        """
        id = self.newId()
        self.nodes[id] = Node(id, label, parents.copy(), children.copy())
        for parent in parents:
            self.getNodeById(parent).addChildId(id)
        for child in children:
            self.getNodeById(child).addParentId(id)
        return id

    def mergeNodes(self: 'OpenDigraph', a: int, b: int, newLabel: Optional[str] = None) -> int:
        if a != b:
            nodeA = self.getNodeById(a)
            nodeB = self.getNodeById(b)

            for parent in nodeB.getParentsIds():
                self.addEdge(parent, a)
            for child in nodeB.getChildrenIds():
                self.addEdge(a, child)

            if newLabel: nodeA.setLabel(newLabel)
            for i, val in enumerate(self.inputs):
                if val == b: self.inputs[i] = a
            for i, val in enumerate(self.outputs):
                if val == b: self.outputs[i] = a

            self.removeNodeById(b)

        return a

    def removeEdge(self, src: int, tgt: int) -> None:
        """
        Retirer une arête allant du nœud d'id 'src' vers celui d'id 'tgt'
        """
        self.getNodeById(src).removeChildId(tgt)
        self.getNodeById(tgt).removeParentId(src)

    def removeNodeById(self, ident: int) -> None:
        """
        Retirer un nœud (et les arêtes correspondantes) d'id 'ident'.
        """

        nodeBye = self.nodes.pop(ident)
        for parent in (self.nodes[identParent] for identParent in nodeBye.getParentsIds()):
            parent.removeChildIdAll(ident)
        for child in (self.nodes[identChild] for identChild in nodeBye.getChildrenIds()):
            child.removeParentIdAll(ident)

        removeAll(self.inputs, ident)
        removeAll(self.outputs, ident)

    def removeEdges(self, *edges: List[Tuple[int, int]]) -> None:
        """
        Retirer une série d'arêtes avec la méthode 'removeEdge'
        """
        for src, tgt in edges:
            self.removeEdge(src, tgt)

    def removeNodesById(self, *ids: List[int]) -> None:
        """
        Retirer une série de nœuds avec la méthode 'removeNodeById'
        """
        for id in ids:
            self.removeNodeById(id)

    def copy(self):
        """
        Génère une copie du graphe courant et la renvoie.
        Renvoie un OpenDigraph.
        """
        return OpenDigraph(self.inputs.copy(), self.outputs.copy(), [node.copy() for node in self.nodes.values()])

    def isWellFormed(self) -> bool:
        """
        Le graphe courant est-il bien formé ?
        """
        idsOk = all(x in self.nodes for x in self.inputs + self.outputs)
        keysOk = all(self.nodes[cle].getId() == cle for cle in self.nodes)

        suiteOk = True
        for node in self.nodes.values():
            enfants = node.getChildrenIds()
            parents = node.getParentsIds()

            for child in enfants:
                nbOcc = countOccurences(enfants, child)

                if nbOcc != countOccurences(self.nodes[child].getParentsIds(), node.getId()):
                    suiteOk = False

            for parent in parents:
                nbOcc = countOccurences(parents, parent)

                if parent not in self.nodes:
                    print(self.nodes)
                    print(parents, parent)

                if nbOcc != countOccurences(self.nodes[parent].getChildrenIds(), node.getId()):
                    suiteOk = False

        return idsOk and keysOk and suiteOk

    def random(n: int, bound: int, inputs: int=0, outputs: int=0, loopFree: bool=False, DAG: bool=False, oriented: bool=False, undirected: bool=False):
        """
        Générer un graphe aléatoire suivant les critères énumérés en paramètres.
        Renvoie un objet OpenDigraph représentant un tel graphe.
        """
        ret = graphFromAdjacencyMatrix(randomMatrix(n, bound, nullDiag=loopFree, symetric=undirected, oriented=oriented, triangular=DAG))
        ret.setInputIds([randint(0, n-1) for _ in range(inputs)])
        ret.setOutputIds([randint(0, n-1) for _ in range(outputs)])

        return ret

    def changeId(self, nodeId: int, newId: int) -> None:
        """
        Changer l'id du nœud d'indice 'nodeId' en 'newid'.
        """

        if newId in self.nodes:
            raise ValueError(f"Le nœud d'id {newId} existe déjà")
        elif nodeId not in self.nodes:
            raise ValueError(f"Le nœud d'id {nodeId} n'existe pas")
        else:
            node = self.nodes[nodeId]
            node.setId(newId)
            self.nodes[newId] = node

            for otherNodeId, otherNode in self.nodes.items():
                if otherNodeId in otherNode.getParentsIds():
                    self.removeEdge(nodeId, otherNodeId)
                    self.addEdge(newId, otherNodeId)
                if otherNodeId in otherNode.getChildrenIds():
                    self.removeEdge(otherNodeId, nodeId)
                    self.addEdge(otherNodeId, newId)

            del self.nodes[nodeId]

    def changeIds(self, *changes: List[Tuple[int, int]]) -> None:
        """
        Changer une série d'identifiants avec la méthode 'changeId'
        """
        if not any(any(a == y for a, b in changes[i+1:]) for i, (x, y) in enumerate(changes)):
            for x, y in changes:
                self.changeId(x, y)
        else:
            raise ValueError("Nan mais t'abuses là ! On va éviter les problèmes")

    def normalizeIds(self) -> None:
        """
        Normaliser les identifiants des nœuds dans [[0, n-1]], où n est le nb de nœuds.
        """
        for i in range(len(self.nodes)):
            if i not in self.nodes:
                self.changeId(self.maxId(), i)

    def adjacencyMatrix(self) -> List[List[int]]:
        """
        Renvoie la matrice d'adjacence du graphe courant, telle que définie dans le TD3.
        """
        self.normalizeIds()
        n = self.newId()
        nodes = self.nodes
        return [[countOccurences(nodes[i].getChildrenIds(), j) for j in range(n)] for i in range(n)]

    def maxInDegree(self: 'OpenDigraph') -> int:
        return max((x.inDegree() for x in self.nodes.values()), default = 0)

    def minInDegree(self: 'OpenDigraph') -> int:
        return min((x.inDegree() for x in self.nodes.values()), default = 0)

    def maxOutDegree(self: 'OpenDigraph') -> int:
        return max((x.outDegree() for x in self.nodes.values()), default = 0)

    def minOutDegree(self: 'OpenDigraph') -> int:
        return min((x.outDegree() for x in self.nodes.values()), default = 0)

    def maxDegree(self: 'OpenDigraph') -> int:
        return max((x.degree() for x in self.nodes.values()), default = 0)

    def minDegree(self: 'OpenDigraph') -> int:
        return min((x.degree() for x in self.nodes.values()), default = 0)

    def empty() -> 'OpenDigraph':
        """
        Renvoie un graphe vide.
        """
        return OpenDigraph([], [], [])

    def isCyclic(self: 'OpenDigraph') -> bool:
        count = len(self.nodes)

        degrees = {id: node.outDegree() for id, node in self.nodes.items()}
        leafs = {id for id, deg in degrees.items() if deg == 0}
        while leafs:
            id = leafs.pop()
            for parentId in self.getNodeById(id).getParentsIds():
                degrees[parentId] -= 1
                if degrees[parentId] == 0:
                    leafs.add(parentId)
            count -= 1
        return count != 0

    def shiftIndices(self: 'OpenDigraph', n: int) -> None:
        for idNode, node in self.nodes.items():
            node.shiftIndices(n)
        self.nodes = {ident+n: node for ident, node in self.nodes.items()}
        #ou en une ligne (sale)
        #self.nodes = {ident+n: node.shiftIndices(n) or node for ident, node in self.nodes.items()}

        self.inputs = [x + n for x in self.inputs]
        self.outputs = [x + n for x in self.outputs]

    def iparallel(self: 'OpenDigraph', g: 'OpenDigraph', inPerm: Optional[List[int]] = None, outPerm: Optional[List[int]] = None) -> None:
        if inPerm is None:
            inPerm = list(range(len(g.inputs)))
        if outPerm is None:
            outPerm = list(range(len(g.outputs)))

        g = g.copy()
        self.shiftIndices(g.maxId() - self.minId() + 1)
        self.inputs += applyPerm(inPerm, g.inputs)
        self.outputs += applyPerm(outPerm, g.outputs)
        self.nodes.update(g.nodes)

    def parallel(g1: 'OpenDigraph', g2: 'OpenDigraph', inPerm: Optional[List[int]] = None, outPerm: Optional[List[int]] = None) -> 'OpenDigraph':
        g = g1.copy()
        g.iparallel(g2, inPerm, outPerm)
        return g

    def icompose(self: 'OpenDigraph', g: 'OpenDigraph') -> None:
        g = g.copy()
        self.shiftIndices(g.maxId() - self.minId() + 1)
        if len(self.inputs) != len(g.outputs):
            raise ValueError("On ne peut pas composer ces deux graphes dans cet ordre !")
        else:
            self.nodes.update(g.nodes)

            for idNodeG, idNodeSelf in zip(g.outputs, self.inputs):
                self.addEdge(idNodeG, idNodeSelf)

            g.outputs = []
            self.inputs = g.inputs.copy()

    def compose(g1: 'OpenDigraph', g2: 'OpenDigraph') -> 'OpenDigraph':
        g = g1.copy()
        g.icompose(g2)
        return g

    def connectedComponents(self: 'OpenDigraph') -> Tuple[Dict[int, int], int]:
        #à un id de nœud on associe un numéro de cc
        uf = {id: id for id in self.nodes.keys()}

        def find(e):
            p = uf[e]
            if p == e:
                return e
            else:
                r = find(p)
                uf[e] = r
                return r

        def union(e1, e2):
            r1 = find(e1)
            r2 = find(e2)
            uf[r2] = r1

        for id, node in self.nodes.items():
            for childId in node.getChildrenIds():
                union(id, childId)

        ret = dict()
        cpt = [0]

        def fillRet(e):
            if ret.get(e) is None:
                p = find(e)
                if p == e:
                    ret[e] = cpt[0]
                    cpt[0] += 1
                else:
                    ret[e] = fillRet(p)
            return ret[e]

        for id in self.nodes.keys():
            fillRet(id)

        return ret, cpt[0]

    def splitCC(self: 'OpenDigraph') -> Tuple[List['OpenDigraph'], List[int], List[int]]:
        dicoCCs, nbCC = self.connectedComponents()
        listeCCs = [set() for _ in range(nbCC)]

        for idNode, idCC in dicoCCs.items():
            listeCCs[idCC].add(idNode)

        inputPerm = sorted(range(len(self.inputs)), key = lambda i: dicoCCs[self.inputs[i]])
        outputPerm = sorted(range(len(self.outputs)), key = lambda i: dicoCCs[self.outputs[i]])

        listeCCsDigraph = [OpenDigraph([x for x in self.inputs if x in idNodes], [x for x in self.outputs if x in idNodes], [self.nodes[idNode].copy() for idNode in idNodes]) for idNodes in listeCCs]

        return listeCCsDigraph, invPerm(inputPerm), invPerm(outputPerm)

    def dijkstra(self: 'OpenDigraph', src: int, tgt: Optional[int] = None, direction: Optional[int] = None) -> Tuple[Dict[int, int], Dict[int, int]]:
        Q: List[int] = [src]
        dist: Dict[int, int] = {src: 0}
        prev: Dict[int] = dict()

        while len(Q) > 0:
            u = min(Q, key=lambda x: dist[x]) #il y a forcément un résultat, Q est non vide
            removeAll(Q, u)

            node = self.getNodeById(u)
            if direction == 1:
                neighbours = node.getChildrenIds()
            elif direction == -1:
                neighbours = node.getParentsIds()
            else: #direction is None
                neighbours = node.getParentsIds() + node.getChildrenIds()

            for v in neighbours:
                if v not in dist:
                    Q.append(v)

                if v not in dist or dist[v] > dist[u] + 1:
                    dist[v] = dist[u] + 1
                    prev[v] = u

            if u == tgt: #la tgt est traitée, donc c'est bon
                return dist, prev

        return dist, prev

    def computePath(prev: Dict[int, int], u: int, v: int) -> List[int]:
        res: List[int] = [v]
        while res[-1] != u:
            dernier = res[-1]
            if dernier in prev:
                res.append(prev[dernier])
            else: #pas possible ^^'
                raise ValueError(f"Pas de chemin possible entre {u} et {v}")

        res.reverse()

        return res

    def shortestPath(self: 'OpenDigraph', u: int, v: int, direction: Optional[int] = None) -> List[int]:
        _, prev = self.dijkstra(u, v, direction)
        return OpenDigraph.computePath(prev, u, v)

    def distancesToCommonAncester(self: 'OpenDigraph', a: int, b: int) -> Dict[int, Tuple[int, int]]:
        da, _ = self.dijkstra(a, direction=-1)
        db, _ = self.dijkstra(b, direction=-1)
        return {id : (distA, db[id]) for id, distA in da.items() if id in db}

    def topologicalSort(self: 'OpenDigraph') -> List[Set[int]]:
        count = len(self.nodes)

        degrees = {id: node.inDegree() for id, node in self.nodes.items()}
        i = 0
        nextLeaves = {id for id, deg in degrees.items() if deg == 0}
        l: List[Set[int]] = []
        while nextLeaves:
            l.append(nextLeaves)
            nextLeaves = set()
            for id in l[i]:
                for childId in self.getNodeById(id).getChildrenIds():
                    degrees[childId] -= 1
                    if degrees[childId] == 0:
                        nextLeaves.add(childId)
                count -= 1
            i += 1

        if count != 0:
            raise ValueError("Impossible de trier topologiquement un graphe cyclique")
        return l

    def depthNode(self: 'OpenDigraph', nodeId: int) -> int:
        triTopo = self.topologicalSort()

        for index, classe in enumerate(triTopo):
            if nodeId in classe: return index

    def depthGraph(self: 'OpenDigraph') -> int:
        return len(self.topologicalSort()) - 1

    def longestPath(self: 'OpenDigraph', u: int, v: int) -> Tuple[List[int], int]:
        triTopo = self.topologicalSort()

        profondeurU = self.depthNode(u)
        profondeurV = self.depthNode(v)

        dist: Dict[int, int] = {u: 0}
        prev: Dict[int, int] = dict()
        for i in range(profondeurU+1, profondeurV+1):
            for id in triTopo[i]:
                parentId, maxDist = max(((parentId, dist.get(parentId)) for parentId in self.getNodeById(id).getParentsIds()), key=(lambda d: 0 if d[1] is None else d[1]), default=(None, None))
                if maxDist is not None:
                    dist[id]=maxDist+1
                    prev[id]=parentId
                if id == v:
                    if dist[id] is not None:
                        return (OpenDigraph.computePath(prev, u, v), dist[id])
                    else:
                        raise ValueError(f"Il n'y a pas de chemin entre {u} et {v}")

        raise ValueError(f"Il n'y a pas de chemin entre {u} et {v}")

    def normalizeBinary(self: 'OpenDigraph') -> None:
        #permet de gérer les duplications d'opérateur…
        for id, node in list(self.nodes.items()):
            while node.inDegree() > 2:
                nid = self.addNode(node.getLabel(), [], [])
                nnode = self.getNodeById(nid)
                self.addEdge(node.getParentsIds()[0], nid)
                self.removeEdge(node.getParentsIds()[0], id)
                for cid in node.getChildrenIds():
                    self.addEdge(nid, cid)
                    self.removeEdge(id, cid)
                for i, oid in enumerate(self.outputs):
                    if oid == id: self.outputs[i] = nid
                self.addEdge(id, nid)
