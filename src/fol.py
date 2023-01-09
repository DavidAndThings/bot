from __future__ import annotations

import random
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


PredicateArgument = str | SkolemFunction


@dataclass
class UnaryClause:
    subordinate: FirstOrderLogicClause


@dataclass
class BinaryClause:

    left: FirstOrderLogicClause
    right: FirstOrderLogicClause


@dataclass
class Quantifier(UnaryClause):
    variables: tuple[str, ...]


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


FirstOrderLogicClause = UnaryClause | BinaryClause | Quantifier | Predicate


@dataclass
class ThereExists(Quantifier):
    def __repr__(self) -> str:
        return f"(there_exists ({', '.join(self.variables)}) {self.subordinate})"


@dataclass
class ForAll(Quantifier):
    def __repr__(self) -> str:
        return f"(for_all ({', '.join(self.variables)}) {self.subordinate})"


@dataclass
class Not(UnaryClause):
    def __repr__(self) -> str:
        return f"(not {self.subordinate})"


@dataclass
class And(BinaryClause):
    def __repr__(self) -> str:
        return f"({self.left} and {self.right})"


@dataclass
class Or(BinaryClause):
    def __repr__(self) -> str:
        return f"({self.left} or {self.right})"


@dataclass
class Implies(BinaryClause):
    def __repr__(self) -> str:
        return f"({self.left} -> {self.right})"


class NotImplementedException(Exception):
    pass


class NoUnifierException(Exception):
    pass


class DisagreementSet:
    def __init__(self) -> None:
        self._disagreements: list[tuple[PredicateArgument, PredicateArgument]] = []

    def add(self, x: PredicateArgument, y: PredicateArgument) -> None:
        self._disagreements.append((x, y))

    def replace_variable(
        self,
        variable: PredicateArgument,
        replacement: PredicateArgument,
    ) -> None:

        new_disagreements = []

        for i in self._disagreements:

            new_disagreement: tuple[PredicateArgument, PredicateArgument] = ()

            if i[0] == variable:
                new_disagreement += (replacement,)
            elif isinstance(i[0], SkolemFunction) and variable in i[0]:
                new_disagreement += (i[0].replace(variable, replacement),)
            else:
                new_disagreement += (i[0],)

            if i[1] == variable:
                new_disagreement += (replacement,)
            elif isinstance(i[1], SkolemFunction) and variable in i[1]:
                new_disagreement += (i[1].replace(variable, replacement),)
            else:
                new_disagreement += (i[1],)

            new_disagreements.append(new_disagreement)

        self._disagreements = new_disagreements

    def is_empty(self) -> bool:
        return len(self._disagreements) == 0

    def pop(self) -> tuple[PredicateArgument, PredicateArgument]:
        return self._disagreements.pop(0)


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

    elif isinstance(clause, BinaryClause):

        return clause.__class__.__init__(
            self=clause,
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

    elif isinstance(clause, UnaryClause):

        return clause.__class__.__init__(
            self=clause,
            subordinate=skolemize(
                clause=clause.subordinate,
                universally_quantified_variables=universally_quantified_variables,
                variable_map=variable_map,
            ),
        )

    else:
        raise NotImplementedException(f"Clause type {type(clause)} not implemented!")


def distribute_or(clause: FirstOrderLogicClause) -> FirstOrderLogicClause:

    if isinstance(clause, Predicate):
        return clause

    elif isinstance(clause, And):
        return And(left=distribute_or(clause.left), right=distribute_or(clause.right))

    elif isinstance(clause, Or):
        left_distributed = distribute_or(clause.left)
        right_distributed = distribute_or(clause.right)

        if isinstance(left_distributed, And) or isinstance(right_distributed, And):

            and_distributed: list[FirstOrderLogicClause] = (
                [] + [left_distributed]
                if isinstance(left_distributed, And)
                else [] + [right_distributed]
                if isinstance(right_distributed, And)
                else []
            )

            to_be_distributed = random.choice(and_distributed)
            other = (set(and_distributed) - {to_be_distributed}).pop()

            return And(
                left=distribute_or(Or(left=to_be_distributed.left, right=other)),
                right=distribute_or(Or(left=to_be_distributed.right, right=other)),
            )

        else:
            return Or(left=left_distributed, right=right_distributed)

    elif isinstance(clause, UnaryClause):
        return clause.__class__.__init__(subordinate=distribute_or(clause.subordinate))

    elif isinstance(clause, BinaryClause):
        return clause.__class__.__init__(
            left=distribute_or(clause.left),
            right=distribute_or(clause.right),
        )

    else:
        raise NotImplementedException(
            f"Clause of type: {type(clause)} is not supported for distribute_or!",
        )


def eliminate_implication(clause: FirstOrderLogicClause) -> FirstOrderLogicClause:

    if isinstance(clause, Implies):

        eliminated_left = eliminate_implication(clause.left)
        eliminated_right = eliminate_implication(clause.right)

        return Or(left=negate(eliminated_left), right=eliminated_right)

    elif isinstance(clause, UnaryClause):
        return clause.__class__.__init__(
            subordinate=eliminate_implication(clause.subordinate),
        )

    elif isinstance(clause, BinaryClause):
        return clause.__class__.__init__(
            left=eliminate_implication(clause.left),
            right=eliminate_implication(clause.right),
        )

    else:
        raise NotImplementedException(
            f"Clause of type: {type(clause)} is not supported for distribute_or!",
        )


def move_negation_inward(clause: FirstOrderLogicClause) -> FirstOrderLogicClause:

    if isinstance(clause, Not):
        return negate(clause)

    else:
        return clause


def negate(clause: FirstOrderLogicClause) -> FirstOrderLogicClause:

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


def extract_all_predicates(clause: FirstOrderLogicClause) -> tuple[Predicate, ...]:

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


def find_most_general_unifier(
    x: FirstOrderLogicClause,
    y: FirstOrderLogicClause,
) -> list[tuple[PredicateArgument, PredicateArgument]]:

    disagreement_set = DisagreementSet()

    for i in extract_all_predicates(x):
        for j in extract_all_predicates(y):

            if i.name == j.name:

                assert len(i.arguments) == len(j.arguments)

                for index in range(len(i.arguments)):
                    disagreement_set.add(i.arguments[index], j.arguments[index])

    unifier = []

    while not disagreement_set.is_empty():

        disagreement = disagreement_set.pop()

        if is_variable(disagreement[0]):
            disagreement_set.replace_variable(disagreement[0], disagreement[1])
            unifier.append(disagreement)

        elif is_variable(disagreement[1]):
            disagreement_set.replace_variable(disagreement[1], disagreement[0])
            unifier.append(disagreement)

        else:
            raise NoUnifierException(
                f"No unifier available for disagreements: {disagreement_set}",
            )

    return unifier


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
