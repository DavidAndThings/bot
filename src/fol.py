from __future__ import annotations

import random
from abc import ABC
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

    def __hash__(self) -> int:
        return hash(self.name)


PredicateArgument = str | SkolemFunction


@dataclass
class UnaryClause:
    subordinate: FirstOrderLogicClause

    def __hash__(self) -> int:
        return hash(self.subordinate)


@dataclass
class BinaryClause:

    left: FirstOrderLogicClause
    right: FirstOrderLogicClause

    def __hash__(self) -> int:
        return hash(self.left) + hash(self.right)


@dataclass
class Quantifier(UnaryClause):
    variables: tuple[str, ...]

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class Predicate:
    name: str
    arguments: tuple[PredicateArgument, ...] = ()

    def __repr__(self) -> str:
        return f"{self.name}({' '.join([str(i) for i in self.arguments])})"

    def __contains__(self, key) -> bool:
        return key in self.arguments

    def __eq__(self, other: object) -> bool:

        if isinstance(other, Predicate):
            return self.name == other.name and self.arguments == other.arguments

        return False

    def replace(self, variable: str, replacement: PredicateArgument) -> Predicate:
        return Predicate(
            name=self.name,
            arguments=tuple(
                [replacement if i == variable else i for i in self.arguments],
            ),
        )

    def __hash__(self) -> int:
        return hash(self.name)


FirstOrderLogicClause = UnaryClause | BinaryClause | Quantifier | Predicate


@dataclass
class ThereExists(Quantifier):
    def __repr__(self) -> str:
        return f"(there_exists ({', '.join(self.variables)}) {self.subordinate})"

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class ForAll(Quantifier):
    def __repr__(self) -> str:
        return f"(for_all ({', '.join(self.variables)}) {self.subordinate})"

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class Not(UnaryClause):
    def __repr__(self) -> str:
        return f"(not {self.subordinate})"

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class And(BinaryClause):
    def __repr__(self) -> str:
        return f"({self.left} and {self.right})"

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class Or(BinaryClause):
    def __repr__(self) -> str:
        return f"({self.left} or {self.right})"

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class Implies(BinaryClause):
    def __repr__(self) -> str:
        return f"({self.left} -> {self.right})"

    def __hash__(self) -> int:
        return super().__hash__()


class NotImplementedException(Exception):
    pass


class ClauseOperation(ABC):
    def __init__(self, next: ClauseOperation | None = None) -> None:

        super().__init__()
        self.__next = next

    def run(self, clause: FirstOrderLogicClause) -> FirstOrderLogicClause:

        processed_clause: FirstOrderLogicClause

        if isinstance(clause, And):
            processed_clause = self.handle_and(clause)

        elif isinstance(clause, Or):
            processed_clause = self.handle_or(clause)

        elif isinstance(clause, Implies):
            processed_clause = self.handle_implies(clause)

        elif isinstance(clause, Not):
            processed_clause = self.handle_not(clause)

        elif isinstance(clause, ForAll):
            processed_clause = self.handle_for_all(clause)

        elif isinstance(clause, ThereExists):
            processed_clause = self.handle_there_exists(clause)

        elif isinstance(clause, Predicate):
            processed_clause = self.handle_predicate(clause)

        else:
            raise NotImplementedException(
                f"Clause of type {type(clause)} is not supported!",
            )

        if self.__next:
            processed_clause = self.__next.run(processed_clause)

        return processed_clause

    def handle_and(self, clause: And) -> FirstOrderLogicClause:

        return And(left=self.run(clause.left), right=self.run(clause.right))

    def handle_or(self, clause: Or) -> FirstOrderLogicClause:

        return Or(left=self.run(clause.left), right=self.run(clause.right))

    def handle_implies(self, clause: Implies) -> FirstOrderLogicClause:

        return Implies(left=self.run(clause.left), right=self.run(clause.right))

    def handle_not(self, clause: Not) -> FirstOrderLogicClause:

        return Not(subordinate=self.run(clause.subordinate))

    def handle_for_all(self, clause: ForAll) -> FirstOrderLogicClause:

        return ForAll(
            variables=clause.variables,
            subordinate=self.run(clause.subordinate),
        )

    def handle_there_exists(self, clause: ThereExists) -> FirstOrderLogicClause:

        return ThereExists(
            variables=clause.variables,
            subordinate=self.run(clause.subordinate),
        )

    def handle_predicate(self, clause: Predicate) -> FirstOrderLogicClause:

        return Predicate(name=clause.name, arguments=clause.arguments)


class DistributeOr(ClauseOperation):
    def handle_or(self, clause: Or) -> FirstOrderLogicClause:

        left_distributed = self.run(clause.left)
        right_distributed = self.run(clause.right)

        if isinstance(left_distributed, And) or isinstance(right_distributed, And):

            and_distributed: list[And] = (
                [] + [left_distributed]
                if isinstance(left_distributed, And)
                else [] + [right_distributed]
                if isinstance(right_distributed, And)
                else []
            )

            to_be_distributed = random.choice(and_distributed)
            other = (set(and_distributed) - {to_be_distributed}).pop()

            return And(
                left=self.run(Or(left=to_be_distributed.left, right=other)),
                right=self.run(Or(left=to_be_distributed.right, right=other)),
            )

        else:
            return Or(left=left_distributed, right=right_distributed)


class EliminateImplication(ClauseOperation):
    def handle_implies(self, clause: Implies) -> FirstOrderLogicClause:

        eliminated_left = self.run(clause.left)
        eliminated_right = self.run(clause.right)

        return Or(left=Not(eliminated_left), right=eliminated_right)


class MoveNegationInwards(ClauseOperation):
    def handle_not(self, clause: Not) -> FirstOrderLogicClause:

        next_clause = clause.subordinate

        if isinstance(next_clause, Predicate):

            return Predicate(name=next_clause.name, arguments=next_clause.arguments)

        elif isinstance(next_clause, ForAll):
            return ThereExists(
                variables=next_clause.variables,
                subordinate=self.run(Not(subordinate=next_clause.subordinate)),
            )

        elif isinstance(next_clause, ThereExists):
            return ForAll(
                variables=next_clause.variables,
                subordinate=self.run(Not(subordinate=next_clause.subordinate)),
            )

        elif isinstance(next_clause, Not):
            return self.run(next_clause.subordinate)

        elif isinstance(next_clause, And):
            return Or(
                left=self.run(Not(subordinate=next_clause.left)),
                right=self.run(Not(subordinate=next_clause.right)),
            )

        elif isinstance(next_clause, Or):
            return And(
                left=self.run(Not(subordinate=next_clause.left)),
                right=self.run(Not(subordinate=next_clause.right)),
            )

        elif isinstance(next_clause, Implies):
            return And(
                left=self.run(next_clause.left),
                right=self.run(Not(subordinate=next_clause.right)),
            )

        else:
            raise NotImplementedException(
                f"Clause of type {type(clause)} is not supported!",
            )


def skolemize(
    clause: FirstOrderLogicClause,
    universally_quantified_variables: tuple[str, ...],
    variable_map: Mapping[str, tuple[str, ...]],
) -> FirstOrderLogicClause:

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

    elif isinstance(clause, Predicate):

        new_args: tuple[str | SkolemFunction, ...] = ()

        for i in clause.arguments:

            if isinstance(i, str) and i in variable_map:
                new_args += (SkolemFunction(variables=variable_map[i]),)

            else:
                new_args += (i,)

        return Predicate(name=clause.name, arguments=new_args)

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

    elif isinstance(clause, Or):
        return Or(
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

    elif isinstance(clause, Not):

        return Not(
            subordinate=skolemize(
                clause=clause.subordinate,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
        )

    else:
        raise NotImplementedException(f"Clause type {type(clause)} not implemented!")


def extract_all_predicates(clause: FirstOrderLogicClause) -> tuple[Predicate, ...]:

    assert clause

    if isinstance(clause, Predicate):
        return (clause,)

    elif (
        isinstance(clause, And) or isinstance(clause, Or) or isinstance(clause, Implies)
    ):
        return extract_all_predicates(clause.left) + extract_all_predicates(
            clause.right,
        )

    elif (
        isinstance(clause, ThereExists)
        or isinstance(clause, ForAll)
        or isinstance(clause, Not)
    ):
        return extract_all_predicates(clause.subordinate)

    else:
        raise NotImplementedException(f"Clause type f{type(clause)} is not supported!")


def is_variable(arg: PredicateArgument) -> bool:

    if isinstance(arg, str):
        return arg.isupper()

    return False


def is_monolithic_or(clause: FirstOrderLogicClause) -> bool:

    assert clause

    if isinstance(clause, Or):
        return is_monolithic_or(clause.left) and is_monolithic_or(clause.right)

    if isinstance(clause, Not):
        return is_monolithic_or(clause.subordinate)

    elif isinstance(clause, Predicate):
        return True

    else:
        return False
