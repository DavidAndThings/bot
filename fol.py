from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Mapping


@dataclass
class SkolemFunction:

    variables: tuple[str, ...]
    name: str = field(init=False)
    counter: ClassVar[int] = 0

    def __post_init__(self):

        self.name = f"F_{SkolemFunction.counter}"
        SkolemFunction.counter += 1

    def __repr__(self) -> str:
        return f"{self.name}({', '.join(self.variables)})"


@dataclass
class FolClause:

    variables: tuple[str, ...] = ()
    subordinate: FolClause | None = None
    left: FolClause | None = None
    right: FolClause | None = None
    name: str | None = None
    arguments: tuple[str | SkolemFunction, ...] = ()


@dataclass
class ThereExists(FolClause):
    def __repr__(self) -> str:
        return f"(there_exists ({', '.join(self.variables)}) {self.subordinate})"


@dataclass
class ForAll(FolClause):
    def __repr__(self) -> str:
        return f"(for_all ({', '.join(self.variables)}) {self.subordinate})"


@dataclass
class Not(FolClause):
    def __repr__(self) -> str:
        return f"(not {self.subordinate})"


@dataclass
class And(FolClause):
    def __repr__(self) -> str:
        return f"({self.left} and {self.right})"


@dataclass
class Or(FolClause):
    def __repr__(self) -> str:
        return f"({self.left} or {self.right})"


@dataclass
class Implies(FolClause):
    def __repr__(self) -> str:
        return f"({self.left} -> {self.right})"


@dataclass
class Predicate(FolClause):
    def __repr__(self) -> str:
        return f"{self.name}({' '.join([str(i) for i in self.arguments])})"


class NotImplementedException(Exception):
    pass


def skolemize(
    clause: FolClause | None,
    universally_quantified_variables: tuple[str, ...],
    variable_map: Mapping[str, tuple[str, ...]],
) -> FolClause:

    if isinstance(clause, ThereExists):

        new_variable_map = {**variable_map}

        for v in clause.variables:
            new_variable_map = {**new_variable_map, v: universally_quantified_variables}

        return skolemize(
            clause=clause.subordinate,
            universally_quantified_variables=universally_quantified_variables,
            variable_map=new_variable_map,
        )

    elif isinstance(clause, ForAll):

        return ForAll(
            variables=clause.variables,
            subordinate=skolemize(
                clause=clause.subordinate,
                universally_quantified_variables=universally_quantified_variables
                + clause.variables,
                variable_map=variable_map,
            ),
        )

    elif isinstance(clause, And):

        return And(
            left=skolemize(
                clause=clause.left,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
            right=skolemize(
                clause=clause.right,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
        )

    elif isinstance(clause, Implies):

        return Implies(
            left=skolemize(
                clause=clause.left,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
            right=skolemize(
                clause=clause.right,
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

    else:
        raise NotImplementedException(f"Clause type {type(clause)} not implemented!")


def negate(clause: FolClause | None) -> FolClause | None:

    if isinstance(clause, Predicate):
        return Not(subordinate=clause)

    elif isinstance(clause, Not):
        return clause.subordinate

    elif isinstance(clause, And):
        return Or(left=negate(clause.left), right=negate(clause.right))

    elif isinstance(clause, Or):
        return And(left=negate(clause.left), right=negate(clause.right))

    elif isinstance(clause, ForAll):
        return ThereExists(
            variables=clause.variables,
            subordinate=negate(clause.subordinate),
        )

    elif isinstance(clause, ThereExists):
        return ForAll(
            variables=clause.variables,
            subordinate=negate(clause.subordinate),
        )

    elif isinstance(clause, Implies):
        return And(left=clause.left, right=negate(clause.right))

    else:
        raise NotImplementedException(f"Clause type {type(clause)} not supported!")


def extract_all_predicates(clause: FolClause | None) -> tuple[Predicate, ...]:

    assert clause

    if isinstance(clause, Predicate):
        return (clause,)

    elif any(
        [isinstance(clause, And), isinstance(clause, Or), isinstance(clause, Implies)],
    ):
        return extract_all_predicates(clause.left) + extract_all_predicates(
            clause.right,
        )

    elif any(
        [
            isinstance(clause, ThereExists),
            isinstance(clause, ForAll),
            isinstance(clause, Not),
        ],
    ):
        return extract_all_predicates(clause.subordinate)

    else:
        raise NotImplementedException(f"Clause type f{type(clause)} is not supported!")


c = ForAll(
    variables=("X",),
    subordinate=ThereExists(
        variables=("Y",),
        subordinate=Implies(
            left=Predicate(name="A", arguments=("X",)),
            right=Predicate(name="B", arguments=("Y",)),
        ),
    ),
)

c_1 = skolemize(clause=c, universally_quantified_variables=(), variable_map=dict())
c_2 = negate(c)
print(c_2)
