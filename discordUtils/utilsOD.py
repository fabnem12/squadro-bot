#!/usr/bin/python3
from math import cos, sin, atan2, pi, sqrt
from random import randint
from typing import List, Any, Union, Tuple, Optional

def removeAll(l: List[Any], x: Any) -> None:
    try:
        for _ in range(len(l)):
            l.remove(x)
    except:
        pass

def removeAll2(l: List[Any], x: Any, sorted: bool = True) -> None:
    if sorted:
        j = 0
        for val in l:
            if val > x: return
            elif val == x: del l[j]
            else: j += 1
    else:
        removeAll(l, x)

def insertSortedList(l: List[Any], x: Any) -> None:
    for index, val in enumerate(l):
        if x <= val:
            l.insert(index, x)
            return
    l.append(x)

def countOccurences(l: List[Any], x: Any) -> int:
    return sum(val == x for val in l)

def randomIntList(n: int, bound: int) -> List[int]:
    return [randint(0, bound) for _ in range(n)]

def randomIntMatrix(n: int, bound: int, nullDiag: bool=True) -> List[List[int]]:
    if nullDiag:
        return [randomIntList(i, bound) + [0] + randomIntList(n-i-1, bound) for i in range(n)]
    else:
        return [randomIntList(n, bound) for _ in range(n)]

def randomSymetricIntMatrix(n: int, bound: int, nullDiag: bool=True) -> List[List[int]]:
    ret = [[0 for _ in range(n)] for _ in range(n)]

    for i in range(n):
        ligne = ret[i]
        for j in range(i + (1 if nullDiag else 0), n):
            ligne[j] = randint(0, bound)
            ret[j][i] = ligne[j]

    return ret

def randomOrientedIntMatrix(n: int, bound: int, nullDiag: bool=True) -> List[List[int]]:
    ret = [[0 for _ in range(n)] for _ in range(n)]

    for i in range(n):
        for j in range(i + (1 if nullDiag else 0), n):
            if randint(0, 1) == 0:
                ret[i][j] = randint(0, bound)
            else:
                ret[j][i] = randint(0, bound)

def randomTriangularIntMatrix(n: int, bound: int, nullDiag: bool=True) -> List[List[int]]:
    return [[randint(0, bound) if i + (1 if nullDiag else 0) <= j else 0 for j in range(n)] for i in range(n)]

def randomMatrix(n: int, bound: int, nullDiag: bool=False, symetric: bool=False, oriented: bool=False, triangular: bool=False):
    if triangular:
        return randomTriangularIntMatrix(n, bound, nullDiag and oriented)
    elif oriented:
        return randomOrientedIntMatrix(n, bound, nullDiag)
    elif symetric:
        return randomSymetricIntMatrix(n, bound, nullDiag)
    else:
        return randomIntMatrix(n, bound, nullDiag)

class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def n(self) -> Tuple[float, float]:
        return (round(self.x), round(self.y))

    def copy(self):
        return Point(self.x, self.y)

    def __add__(self, p2): #p2: Union[Point, Tuple[float, float]]
        p2 = convPoint(p2)
        return Point(self.x + p2.x, self.y + p2.y)

    def __rmul__(self, s: Union[int, float]):
        return Point(s * self.x, s * self.y)
    def __mul__(self, s: Union[int, float]):
        return Point(s * self.x, s * self.y)

    def __div__(self, s: Union[int, float]):
        return Point(self.x / s, self.y / s)

    def __sub__(self, p2): #p2: Union[Point, Tuple[float, float]]
        p2 = convPoint(p2)
        return Point(self.x - p2.x, self.y - p2.y)

    def rotate(self, theta: float, c = (0, 0)): #c: Union[Point, Tuple[float, float]]
        c = convPoint(c)
        nouv = self - c
        cosT = cos(theta)
        sinT = sin(theta)
        return Point(nouv.x * cosT - nouv.y * sinT, nouv.x * sinT + nouv.y * cosT) + c

    def normalize(self):
        norm = sqrt(self.x**2 + self.y**2)
        return self if norm == 0 else (1/sqrt(self.x**2 + self.y**2)) * self

PointBis = Union[Point, Tuple[float, float]]

def convPoint(x: PointBis) -> Point:
    if not isinstance(x, Point): return Point(*x)
    else: return x

def slopeAngle(p1: PointBis, p2: PointBis) -> int:
    p1 = convPoint(p1)
    p2 = convPoint(p2)
    v = p2 - p1
    return atan2(v.y, v.x)

def invPerm(sigma: List[int]) -> List[int]:
    inv = [0] * len(sigma)
    for i in sigma:
        inv[sigma[i]] = i
    return inv

def applyPerm(sigma: List[int], l: List[Any]) -> List[Any]:
    return [l[i] for i in sigma]
