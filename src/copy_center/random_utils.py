"""Generadores de variables aleatorias, aislados del resto del modelo.

SUPUESTOS.md #7: por ahora se apoya en random.Random (Mersenne Twister). Si la
cátedra exige un generador congruencial propio, alcanza con reemplazar
`RandomGenerator.uniform01`; el resto del modelo no cambia.

SUPUESTOS.md #3: exponencial por transformada inversa, T = -media * ln(1 - RND).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Draw:
    """Un sorteo: el valor resultante junto con el RND crudo que lo generó.

    El vector de estado (§8 del prompt) exige mostrar el RND usado por cada
    variable aleatoria, no solo el valor final.
    """

    value: float
    rnd: float


class RandomGenerator:
    """Fuente única de aleatoriedad de una corrida, seedeable para
    reproducibilidad (DECISIONES.md D7)."""

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    def uniform01(self) -> float:
        """RND ~ Uniforme(0,1). Único punto de contacto con el generador subyacente."""
        return self._random.random()

    def exponential(self, mean: float) -> Draw:
        """Exponencial por transformada inversa: T = -media * ln(1 - RND)."""
        rnd = self.uniform01()
        value = -mean * math.log(1 - rnd)
        return Draw(value=value, rnd=rnd)

    def uniform(self, low: float, high: float) -> Draw:
        """Uniforme[low, high] por transformada inversa: X = low + RND * (high - low)."""
        rnd = self.uniform01()
        value = low + rnd * (high - low)
        return Draw(value=value, rnd=rnd)
