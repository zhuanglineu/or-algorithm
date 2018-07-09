import numbers
import numpy as np

from Constant import *


class Variable(object):

    def __init__(self, name=None, index=None, lb=0, ub=INF):

        # if not specified, using "var"+str(solver.variable_index)
        self.name = name if name and isinstance(name, str) else None

        # if not specified, using solver.variable_index
        self.index = index if index else None

        # False for name or index being specified
        self.auto = True if name or index else False

        self.coefficient = 1
        self.sign = POSITIVE  # Expression record
        self.lower_bound = lb
        self.upper_bound = ub
        self.value = None

    def __add__(self, other):
        if isinstance(other, Variable) or isinstance(other, Expression):
            try:
                return Expression(variable=self) + other
            finally:
                self.clean()
        else:
            print("'+' is not implemented between Variable and " + str(type(other)))
            return None

    def __sub__(self, other):
        if isinstance(other, Variable) or isinstance(other, Expression):
            try:
                return Expression(variable=self) - other
            finally:
                self.clean()
        else:
            print("'-' is not implemented between Variable and " + str(type(other)))
            return None

    def __mul__(self, other):
        if isinstance(other, numbers.Real):
            self.coefficient *= other
            return self
        else:
            print("Not supported type for " + str(type(other)))
            return None

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        if isinstance(other, numbers.Real):
            self.coefficient /= other

    def __rtruediv__(self, other):
        return self / other

    def __str__(self):
        return self.name + "_" + str(self.index)

    # TODO: make sense? is there any better way?
    def clean(self):
        self.coefficient = 1
        self.sign = POSITIVE


class Expression(object):

    def __init__(self, variable=None):

        # [(variable_name, variable_index, variable_coefficient), ...]
        self.variable_list = list()

        # [POSITIVE, NEGATIVE, ...]
        self.sign_list = list()

        if isinstance(variable, Variable):
            self.variable_list.append((
                variable.name,
                variable.index,
                variable.coefficient
            ))
            self.sign_list.append(variable.sign)
            variable.clean()

    def __le__(self, other):
        return Constraint(self, LE, other)

    def __lt__(self, other):
        return Constraint(self, LT, other)

    def __ge__(self, other):
        return Constraint(self, GE, other)

    def __gt__(self, other):
        return Constraint(self, GT, other)

    def __eq__(self, other):
        return Constraint(self, EQ, other)

    def __ne__(self, other):
        return Constraint(self, NE, other)

    def __neg__(self):
        self.sign_list = [-s for s in self.sign_list]
        return self

    def __add__(self, other):
        if isinstance(other, Variable):
            self.variable_list.append((other.name, other.index, other.coefficient))
            self.sign_list.append(other.sign)
            other.clean()
            return self
        elif isinstance(other, Expression):
            self.variable_list += other.variable_list
            self.sign_list += other.sign_list
            return self
        else:
            print("'+' is not implemented between Expression and " + str(type(other)))
            return None

    def __sub__(self, other):
        if isinstance(other, Variable):
            self.variable_list.append((other.name, other.index, other.coefficient))
            self.sign_list.append(-1 * other.sign)
            other.clean()
            return self
        elif isinstance(other, Expression):
            return self + (-other)
        else:
            print("'-' is not implemented between Expression and " + str(type(other)))
            return None

    def __mul__(self, other):
        if isinstance(other, numbers.Real):
            self.variable_list = list(map(
                lambda x: (x[0], x[1], x[2] * other),
                self.variable_list
            ))
            return self
        else:
            print("'*' is not implemented between Expression and " + str(type(other)))
            return None

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        if isinstance(other, numbers.Real):
            self.variable_list = list(map(
                lambda x: (x[0], x[1], x[2] / other),
                self.variable_list
            ))
            return self
        else:
            print("'/' is not implemented between Expression and " + str(type(other)))
            return None

    def __rtruediv__(self, other):
        return self / other

    def to_list(self):
        return [
            (x[0], x[1], x[2] * self.sign_list[i])
            for i, x in enumerate(self.variable_list)
        ]


class Constraint(object):

    def __init__(self, expression, operator, value):
        self.expression = expression.tolist()
        self.compare_operator = operator
        self.compare_value = value


if __name__ == "__main__":
    a = Variable(name="x", index=(0, 0))
    b = Variable(name="x", index=(0, 1))
    c = Variable(name="x", index=(0, 2))
    d = Variable(name="y", index=3)
    print(a.coefficient)
    e = 3 * (3 * a + b * 2) - (5 * c + 6 * d) / 3
    print(a.coefficient)
    print(a)
    print(b.coefficient)
    print(c.coefficient)
    print(d.coefficient)
    print(d)
    print(isinstance(a + b, Expression))
    print(isinstance(e, Expression))
    print(e.variable_list)
    print(e.sign_list)
    f = e <= 3
    print(f.expression)
    print(f.compare_operator)
    print(f.compare_value)
