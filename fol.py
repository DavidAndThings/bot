from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThereExists:
    variables: tuple[str, ...]
    children: tuple[Clause, ...]


@dataclass
class ForAll:
    variables: tuple[str, ...]
    children: tuple[Clause, ...]


@dataclass
class And:
    head: Clause
    tail: Clause


@dataclass
class Implies:
    head: Clause
    tail: Clause


@dataclass
class Predicate:
    name: str
    arguments: tuple[str, ...]


Quantifier = ForAll | ThereExists
Clause = And | Predicate | ForAll | ThereExists | Implies
