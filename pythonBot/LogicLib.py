"""
LogicLib, pour manipuler des formules logiques !
"""

from typing import Dict, Optional, Union

Expression = Union["OpBin", "Variable", bool]
VarName = str

Top = True
Bottom = False

class Expression:
    def __repr__(self):
        return str(self)

    def __and__(self, right: Expression):
        return And(self, right)
    def __rand__(self, left: bool):
        return And(left, self)
    def __or__(self, right: Expression):
        return Or(self, right)
    def __ror__(self, left: bool):
        return Or(left, self)
    def __invert__(self):
        return Not(self)

class Variable(Expression):
    def __init__(self, name: VarName, value: Optional[bool] = None):
        self.name = name
        self.val = value

    def __str__(self):
        return self.name if self.val is None else str(self.val)

    def __bool__(self):
        return self.val is True

    def value(self, subst: Optional[Dict["Variable", bool]] = None):
        if subst and self in subst:
            return subst[self]
        else:
            return self if self.val is None else self.val

class OpBin(Expression): #classe abstraite
    def __init__(self, a: Expression, b: Expression):
        self.a, self.b = a, b

class Not(Expression):
    def __init__(self, expr: Expression):
        self.expr = expr

    def __str__(self):
        return f"(~{str(self.expr)})"
    def __bool__(self):
        return not bool(self.expr)

    def value(self, subst: Optional[Dict[Variable, bool]] = None):
        val = self.expr.value(subst)

        if val is True:
            return False
        elif val is False:
            return True
        else:
            return self

class And(OpBin):
    def __str__(self):
        return f"({str(self.a)} & {str(self.b)})"

    def __bool__(self):
        return bool(self.a) and bool(self.b)

    def value(self, subst: Optional[Dict[Variable, bool]] = None):
        valA = self.a.value(subst)

        if valA is False:
            return False
        else:
            valB = self.b.value(subst)
            if valA is True:
                return valB
            elif valB is False:
                return False
            elif valB is True:
                return valA
            else:
                return valA & valB

class Or(OpBin):
    def __str__(self):
        return f"({str(self.a)} | {str(self.b)})"

    def __bool__(self):
        return bool(self.a) or bool(self.b)

    def value(self, subst: Optional[Dict[Variable, bool]] = None):
        valA = self.a.value(subst)

        if valA is True:
            return True
        else:
            valB = self.b.value(subst)

            if valB is True:
                return True
            elif valA is False:
                return valB
            elif valB is False:
                return valA
            else:
                return valA | valB

class Impl(OpBin):
    def __str__(self):
        return f"({str(self.a)} => {str(self.b)})"

    def __bool__(self):
        return not bool(self.a) or bool(self.b)

    def value(self, subst: Optional[Dict[Variable, bool]] = None):
        valA = self.a.value(subst)

        if valA is False:
            return True
        else:
            valB = self.b.value(subst)

            if valB is True:
                return True
            elif valA is True:
                return valB
            elif valB is False:
                return False
            else:
                return Impl(valA, valB)

def vars():
    compteur = [0]
    def aux(nbVars = 1, defaultVal = None):
        ret = tuple(Variable(f"x{compteur[0]+i+1}", defaultVal) for i in range(nbVars))
        compteur[0] += nbVars
        return ret if len(ret) > 1 else ret[0]
    return aux
vars = vars()

def varsOfExpr(expr: Expression):
    if expr in (True, False):
        return set()
    elif isinstance(expr, Variable):
        return {expr}
    elif isinstance(expr, OpBin):
        return varsOfExpr(expr.a) | varsOfExpr(expr.b)
    elif isinstance(expr, Not):
        return varsOfExpr(expr.expr)

def tableVerite(expr: Expression):
    variables = sorted(varsOfExpr(expr), key=lambda x: x.name)
    longueurNomMax = max((len(x.name) for x in variables), default=0)
    tab = " "

    affi = f'{" ".join(map(str, variables))}{tab}|{tab}{str(expr)}\n'
    affi += "-" * (len(affi) - 1) + "\n"
    for n in range(1 << len(variables)): #on fait toutes les combinaisons booléennes possibles des variables
        subst = {x: bool((n >> i) % 2) for i, x in enumerate(variables)}
        affi += f'{tab.join("V" if subst[x] else "F" for x in variables)}{tab}|{tab}{"V" if bool(expr.value(subst)) else "F"}\n'

    return affi
