"""A tiny scalar autograd engine used by the backpropagation article."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable


@dataclass(eq=False)
class Value:
    data: float
    _children: tuple["Value", ...] = field(default_factory=tuple, repr=False)
    _op: str = ""
    grad: float = 0.0
    _backward: Callable[[], None] = field(
        default=lambda: None,
        repr=False,
        compare=False,
    )

    def __add__(self, other: float | "Value") -> "Value":
        other = other if isinstance(other, Value) else Value(float(other))
        result = Value(self.data + other.data, (self, other), "+")

        def backward() -> None:
            self.grad += result.grad
            other.grad += result.grad

        result._backward = backward
        return result

    def __radd__(self, other: float | "Value") -> "Value":
        return self + other

    def __mul__(self, other: float | "Value") -> "Value":
        other = other if isinstance(other, Value) else Value(float(other))
        result = Value(self.data * other.data, (self, other), "*")

        def backward() -> None:
            self.grad += other.data * result.grad
            other.grad += self.data * result.grad

        result._backward = backward
        return result

    def __rmul__(self, other: float | "Value") -> "Value":
        return self * other

    def tanh(self) -> "Value":
        output = math.tanh(self.data)
        result = Value(output, (self,), "tanh")

        def backward() -> None:
            self.grad += (1.0 - output**2) * result.grad

        result._backward = backward
        return result

    def backward(self) -> None:
        ordered: list[Value] = []
        visited: set[Value] = set()

        def build_topology(value: Value) -> None:
            if value in visited:
                return
            visited.add(value)
            for child in value._children:
                build_topology(child)
            ordered.append(value)

        build_topology(self)
        self.grad = 1.0
        for value in reversed(ordered):
            value._backward()


def neuron(x1: Value, x2: Value, w1: Value, w2: Value, bias: Value) -> Value:
    return (x1 * w1 + x2 * w2 + bias).tanh()


def main() -> None:
    x1, x2 = Value(2.0), Value(0.0)
    w1, w2 = Value(-3.0), Value(1.0)
    bias = Value(6.881373587)

    output = neuron(x1, x2, w1, w2, bias)
    output.backward()

    print(f"output={output.data:.6f}")
    print(f"doutput/dw1={w1.grad:.6f}")
    print(f"doutput/dw2={w2.grad:.6f}")
    print(f"doutput/dbias={bias.grad:.6f}")


if __name__ == "__main__":
    main()
