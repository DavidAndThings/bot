from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Mapping


@dataclass
class ThereExists:
    variables: tuple[str, ...]
    clause: Clause


@dataclass
class ForAll:
    variables: tuple[str, ...]
    clause: Clause


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
    arguments: tuple[str | SkolemFunction, ...]


@dataclass
class SkolemFunction:

    variables: tuple[str, ...]
    name: str = field(init=False)
    counter: ClassVar[int] = field(init=False, default=0)

    def __post_init__(self):

        self.name = f"F_{SkolemFunction.counter}"
        SkolemFunction.counter += 1


Quantifier = ForAll | ThereExists
Clause = And | Predicate | ForAll | ThereExists | Implies


class NotImplementedException(Exception):
    pass


def eliminate_existantial(
    clause: Clause,
    universally_quantified_variables: tuple[str, ...],
    variable_map: Mapping[str, tuple[str, ...]],
) -> Clause:

    if isinstance(clause, ThereExists):

        new_variable_map = {**variable_map}

        for v in clause.variables:
            new_variable_map = {**new_variable_map, v: universally_quantified_variables}

        return eliminate_existantial(
            clause=clause.clause,
            universally_quantified_variables=universally_quantified_variables,
            variable_map=new_variable_map,
        )

    elif isinstance(clause, ForAll):

        return ForAll(
            variables=clause.variables,
            clause=eliminate_existantial(
                clause=clause.clause,
                universally_quantified_variables=universally_quantified_variables
                + clause.variables,
                variable_map=variable_map,
            ),
        )

    elif isinstance(clause, And):

        return And(
            head=eliminate_existantial(
                clause=clause.head,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
            tail=eliminate_existantial(
                clause=clause.head,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
        )

    elif isinstance(clause, Implies):

        return Implies(
            head=eliminate_existantial(
                clause=clause.head,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
            tail=eliminate_existantial(
                clause=clause.head,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
        )

    elif isinstance(clause, Predicate):

        new_args: tuple[str | SkolemFunction, ...] = ()

        for i in clause.arguments:

            if isinstance(i, str) and i in variable_map:
                new_args += (SkolemFunction(variables=variable_map[i]),)

            else:
                new_args += (i,)

        return Predicate(name=clause.name, arguments=new_args)

    raise NotImplementedException("Clause type not implemented!")
