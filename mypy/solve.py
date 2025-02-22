"""Type inference constraint solving"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence
from typing_extensions import TypeAlias as _TypeAlias

from mypy.constraints import SUBTYPE_OF, SUPERTYPE_OF, Constraint, infer_constraints, neg_op
from mypy.expandtype import expand_type
from mypy.graph_utils import prepare_sccs, strongly_connected_components, topsort
from mypy.join import join_types
from mypy.meet import meet_type_list, meet_types
from mypy.subtypes import is_subtype
from mypy.typeops import get_type_vars
from mypy.types import (
    AnyType,
    Instance,
    NoneType,
    ProperType,
    Type,
    TypeOfAny,
    TypeVarId,
    TypeVarLikeType,
    TypeVarType,
    UninhabitedType,
    UnionType,
    get_proper_type,
    remove_dups,
)
from mypy.typestate import type_state

Bounds: _TypeAlias = "dict[TypeVarId, set[Type]]"
Graph: _TypeAlias = "set[tuple[TypeVarId, TypeVarId]]"
Solutions: _TypeAlias = "dict[TypeVarId, Type | None]"


def solve_constraints(
    original_vars: Sequence[TypeVarLikeType],
    constraints: list[Constraint],
    strict: bool = True,
    allow_polymorphic: bool = False,
) -> tuple[list[Type | None], list[TypeVarLikeType]]:
    """Solve type constraints.

    Return the best type(s) for type variables; each type can be None if the value of
    the variable could not be solved.

    If a variable has no constraints, if strict=True then arbitrarily
    pick UninhabitedType as the value of the type variable. If strict=False, pick AnyType.
    If allow_polymorphic=True, then use the full algorithm that can potentially return
    free type variables in solutions (these require special care when applying). Otherwise,
    use a simplified algorithm that just solves each type variable individually if possible.
    """
    vars = [tv.id for tv in original_vars]
    if not vars:
        return [], []

    originals = {tv.id: tv for tv in original_vars}
    extra_vars: list[TypeVarId] = []
    # Get additional type variables from generic actuals.
    for c in constraints:
        extra_vars.extend([v.id for v in c.extra_tvars if v.id not in vars + extra_vars])
        originals.update({v.id: v for v in c.extra_tvars if v.id not in originals})
    if allow_polymorphic:
        # Constraints like T :> S and S <: T are semantically the same, but they are
        # represented differently. Normalize the constraint list w.r.t this equivalence.
        constraints = normalize_constraints(constraints, vars + extra_vars)

    # Collect a list of constraints for each type variable.
    cmap: dict[TypeVarId, list[Constraint]] = {tv: [] for tv in vars + extra_vars}
    for con in constraints:
        if con.type_var in vars + extra_vars:
            cmap[con.type_var].append(con)

    if allow_polymorphic:
        if constraints:
            solutions, free_vars = solve_with_dependent(
                vars + extra_vars, constraints, vars, originals
            )
        else:
            solutions = {}
            free_vars = []
    else:
        solutions = {}
        free_vars = []
        for tv, cs in cmap.items():
            if not cs:
                continue
            lowers = [c.target for c in cs if c.op == SUPERTYPE_OF]
            uppers = [c.target for c in cs if c.op == SUBTYPE_OF]
            solution = solve_one(lowers, uppers)

            # Do not leak type variables in non-polymorphic solutions.
            if solution is None or not get_vars(
                solution, [tv for tv in extra_vars if tv not in vars]
            ):
                solutions[tv] = solution

    res: list[Type | None] = []
    for v in vars:
        if v in solutions:
            res.append(solutions[v])
        else:
            # No constraints for type variable -- 'UninhabitedType' is the most specific type.
            candidate: Type
            if strict:
                candidate = UninhabitedType()
                candidate.ambiguous = True
            else:
                candidate = AnyType(TypeOfAny.special_form)
            res.append(candidate)
    return res, free_vars


def solve_with_dependent(
    vars: list[TypeVarId],
    constraints: list[Constraint],
    original_vars: list[TypeVarId],
    originals: dict[TypeVarId, TypeVarLikeType],
) -> tuple[Solutions, list[TypeVarLikeType]]:
    """Solve set of constraints that may depend on each other, like T <: List[S].

    The whole algorithm consists of five steps:
      * Propagate via linear constraints and use secondary constraints to get transitive closure
      * Find dependencies between type variables, group them in SCCs, and sort topologically
      * Check that all SCC are intrinsically linear, we can't solve (express) T <: List[T]
      * Variables in leaf SCCs that don't have constant bounds are free (choose one per SCC)
      * Solve constraints iteratively starting from leafs, updating bounds after each step.
    """
    graph, lowers, uppers = transitive_closure(vars, constraints)

    dmap = compute_dependencies(vars, graph, lowers, uppers)
    sccs = list(strongly_connected_components(set(vars), dmap))
    if not all(check_linear(scc, lowers, uppers) for scc in sccs):
        return {}, []
    raw_batches = list(topsort(prepare_sccs(sccs, dmap)))

    free_vars = []
    free_solutions = {}
    for scc in raw_batches[0]:
        # If there are no bounds on this SCC, then the only meaningful solution we can
        # express, is that each variable is equal to a new free variable. For example,
        # if we have T <: S, S <: U, we deduce: T = S = U = <free>.
        if all(not lowers[tv] and not uppers[tv] for tv in scc):
            best_free = choose_free([originals[tv] for tv in scc], original_vars)
            if best_free:
                free_vars.append(best_free.id)
                free_solutions[best_free.id] = best_free

    # Update lowers/uppers with free vars, so these can now be used
    # as valid solutions.
    for l, u in graph:
        if l in free_vars:
            lowers[u].add(free_solutions[l])
        if u in free_vars:
            uppers[l].add(free_solutions[u])

    # Flatten the SCCs that are independent, we can solve them together,
    # since we don't need to update any targets in between.
    batches = []
    for batch in raw_batches:
        next_bc = []
        for scc in batch:
            next_bc.extend(list(scc))
        batches.append(next_bc)

    solutions: dict[TypeVarId, Type | None] = {}
    for flat_batch in batches:
        res = solve_iteratively(flat_batch, graph, lowers, uppers)
        solutions.update(res)
    return solutions, [free_solutions[tv] for tv in free_vars]


def solve_iteratively(
    batch: list[TypeVarId], graph: Graph, lowers: Bounds, uppers: Bounds
) -> Solutions:
    """Solve transitive closure sequentially, updating upper/lower bounds after each step.

    Transitive closure is represented as a linear graph plus lower/upper bounds for each
    type variable, see transitive_closure() docstring for details.

    We solve for type variables that appear in `batch`. If a bound is not constant (i.e. it
    looks like T :> F[S, ...]), we substitute solutions found so far in the target F[S, ...]
    after solving the batch.

    Importantly, after solving each variable in a batch, we move it from linear graph to
    upper/lower bounds, this way we can guarantee consistency of solutions (see comment below
    for an example when this is important).
    """
    solutions = {}
    s_batch = set(batch)
    while s_batch:
        for tv in sorted(s_batch, key=lambda x: x.raw_id):
            if lowers[tv] or uppers[tv]:
                solvable_tv = tv
                break
        else:
            break
        # Solve each solvable type variable separately.
        s_batch.remove(solvable_tv)
        result = solve_one(lowers[solvable_tv], uppers[solvable_tv])
        solutions[solvable_tv] = result
        if result is None:
            # TODO: support backtracking lower/upper bound choices and order within SCCs.
            # (will require switching this function from iterative to recursive).
            continue

        # Update the (transitive) bounds from graph if there is a solution.
        # This is needed to guarantee solutions will never contradict the initial
        # constraints. For example, consider {T <: S, T <: A, S :> B} with A :> B.
        # If we would not update the uppers/lowers from graph, we would infer T = A, S = B
        # which is not correct.
        for l, u in graph.copy():
            if l == u:
                continue
            if l == solvable_tv:
                lowers[u].add(result)
                graph.remove((l, u))
            if u == solvable_tv:
                uppers[l].add(result)
                graph.remove((l, u))

    # We can update uppers/lowers only once after solving the whole SCC,
    # since uppers/lowers can't depend on type variables in the SCC
    # (and we would reject such SCC as non-linear and therefore not solvable).
    subs = {tv: s for (tv, s) in solutions.items() if s is not None}
    for tv in lowers:
        lowers[tv] = {expand_type(lt, subs) for lt in lowers[tv]}
    for tv in uppers:
        uppers[tv] = {expand_type(ut, subs) for ut in uppers[tv]}
    return solutions


def solve_one(lowers: Iterable[Type], uppers: Iterable[Type]) -> Type | None:
    """Solve constraints by finding by using meets of upper bounds, and joins of lower bounds."""
    bottom: Type | None = None
    top: Type | None = None
    candidate: Type | None = None

    # Process each bound separately, and calculate the lower and upper
    # bounds based on constraints. Note that we assume that the constraint
    # targets do not have constraint references.
    for target in lowers:
        if bottom is None:
            bottom = target
        else:
            if type_state.infer_unions:
                # This deviates from the general mypy semantics because
                # recursive types are union-heavy in 95% of cases.
                bottom = UnionType.make_union([bottom, target])
            else:
                bottom = join_types(bottom, target)

    for target in uppers:
        if top is None:
            top = target
        else:
            top = meet_types(top, target)

    p_top = get_proper_type(top)
    p_bottom = get_proper_type(bottom)
    if isinstance(p_top, AnyType) or isinstance(p_bottom, AnyType):
        source_any = top if isinstance(p_top, AnyType) else bottom
        assert isinstance(source_any, ProperType) and isinstance(source_any, AnyType)
        return AnyType(TypeOfAny.from_another_any, source_any=source_any)
    elif bottom is None:
        if top:
            candidate = top
        else:
            # No constraints for type variable
            return None
    elif top is None:
        candidate = bottom
    elif is_subtype(bottom, top):
        candidate = bottom
    else:
        candidate = None
    return candidate


def choose_free(
    scc: list[TypeVarLikeType], original_vars: list[TypeVarId]
) -> TypeVarLikeType | None:
    """Choose the best solution for an SCC containing only type variables.

    This is needed to preserve e.g. the upper bound in a situation like this:
        def dec(f: Callable[[T], S]) -> Callable[[T], S]: ...

        @dec
        def test(x: U) -> U: ...

    where U <: A.
    """

    if len(scc) == 1:
        # Fast path, choice is trivial.
        return scc[0]

    common_upper_bound = meet_type_list([t.upper_bound for t in scc])
    common_upper_bound_p = get_proper_type(common_upper_bound)
    # We include None for when strict-optional is disabled.
    if isinstance(common_upper_bound_p, (UninhabitedType, NoneType)):
        # This will cause to infer <nothing>, which is better than a free TypeVar
        # that has an upper bound <nothing>.
        return None

    values: list[Type] = []
    for tv in scc:
        if isinstance(tv, TypeVarType) and tv.values:
            if values:
                # It is too tricky to support multiple TypeVars with values
                # within the same SCC.
                return None
            values = tv.values.copy()

    if values and not is_trivial_bound(common_upper_bound_p):
        # If there are both values and upper bound present, we give up,
        # since type variables having both are not supported.
        return None

    # For convenience with current type application machinery, we use a stable
    # choice that prefers the original type variables (not polymorphic ones) in SCC.
    best = sorted(scc, key=lambda x: (x.id not in original_vars, x.id.raw_id))[0]
    if isinstance(best, TypeVarType):
        return best.copy_modified(values=values, upper_bound=common_upper_bound)
    if is_trivial_bound(common_upper_bound_p):
        # TODO: support more cases for ParamSpecs/TypeVarTuples
        return best
    return None


def is_trivial_bound(tp: ProperType) -> bool:
    return isinstance(tp, Instance) and tp.type.fullname == "builtins.object"


def normalize_constraints(
    constraints: list[Constraint], vars: list[TypeVarId]
) -> list[Constraint]:
    """Normalize list of constraints (to simplify life for the non-linear solver).

    This includes two things currently:
      * Complement T :> S by S <: T
      * Remove strict duplicates
      * Remove constrains for unrelated variables
    """
    res = constraints.copy()
    for c in constraints:
        if isinstance(c.target, TypeVarType):
            res.append(Constraint(c.target, neg_op(c.op), c.origin_type_var))
    return [c for c in remove_dups(constraints) if c.type_var in vars]


def transitive_closure(
    tvars: list[TypeVarId], constraints: list[Constraint]
) -> tuple[Graph, Bounds, Bounds]:
    """Find transitive closure for given constraints on type variables.

    Transitive closure gives maximal set of lower/upper bounds for each type variable,
    such that we cannot deduce any further bounds by chaining other existing bounds.

    The transitive closure is represented by:
      * A set of lower and upper bounds for each type variable, where only constant and
        non-linear terms are included in the bounds.
      * A graph of linear constraints between type variables (represented as a set of pairs)
    Such separation simplifies reasoning, and allows an efficient and simple incremental
    transitive closure algorithm that we use here.

    For example if we have initial constraints [T <: S, S <: U, U <: int], the transitive
    closure is given by:
      * {} <: T <: {int}
      * {} <: S <: {int}
      * {} <: U <: {int}
      * {T <: S, S <: U, T <: U}
    """
    uppers: Bounds = defaultdict(set)
    lowers: Bounds = defaultdict(set)
    graph: Graph = {(tv, tv) for tv in tvars}

    remaining = set(constraints)
    while remaining:
        c = remaining.pop()
        if isinstance(c.target, TypeVarType) and c.target.id in tvars:
            if c.op == SUBTYPE_OF:
                lower, upper = c.type_var, c.target.id
            else:
                lower, upper = c.target.id, c.type_var
            if (lower, upper) in graph:
                continue
            graph |= {
                (l, u) for l in tvars for u in tvars if (l, lower) in graph and (upper, u) in graph
            }
            for u in tvars:
                if (upper, u) in graph:
                    lowers[u] |= lowers[lower]
            for l in tvars:
                if (l, lower) in graph:
                    uppers[l] |= uppers[upper]
            for lt in lowers[lower]:
                for ut in uppers[upper]:
                    # TODO: what if secondary constraints result in inference
                    # against polymorphic actual (also in below branches)?
                    remaining |= set(infer_constraints(lt, ut, SUBTYPE_OF))
                    remaining |= set(infer_constraints(ut, lt, SUPERTYPE_OF))
        elif c.op == SUBTYPE_OF:
            if c.target in uppers[c.type_var]:
                continue
            for l in tvars:
                if (l, c.type_var) in graph:
                    uppers[l].add(c.target)
            for lt in lowers[c.type_var]:
                remaining |= set(infer_constraints(lt, c.target, SUBTYPE_OF))
                remaining |= set(infer_constraints(c.target, lt, SUPERTYPE_OF))
        else:
            assert c.op == SUPERTYPE_OF
            if c.target in lowers[c.type_var]:
                continue
            for u in tvars:
                if (c.type_var, u) in graph:
                    lowers[u].add(c.target)
            for ut in uppers[c.type_var]:
                remaining |= set(infer_constraints(ut, c.target, SUPERTYPE_OF))
                remaining |= set(infer_constraints(c.target, ut, SUBTYPE_OF))
    return graph, lowers, uppers


def compute_dependencies(
    tvars: list[TypeVarId], graph: Graph, lowers: Bounds, uppers: Bounds
) -> dict[TypeVarId, list[TypeVarId]]:
    """Compute dependencies between type variables induced by constraints.

    If we have a constraint like T <: List[S], we say that T depends on S, since
    we will need to solve for S first before we can solve for T.
    """
    res = {}
    for tv in tvars:
        deps = set()
        for lt in lowers[tv]:
            deps |= get_vars(lt, tvars)
        for ut in uppers[tv]:
            deps |= get_vars(ut, tvars)
        for other in tvars:
            if other == tv:
                continue
            if (tv, other) in graph or (other, tv) in graph:
                deps.add(other)
        res[tv] = list(deps)
    return res


def check_linear(scc: set[TypeVarId], lowers: Bounds, uppers: Bounds) -> bool:
    """Check there are only linear constraints between type variables in SCC.

    Linear are constraints like T <: S (while T <: F[S] are non-linear).
    """
    for tv in scc:
        if any(get_vars(lt, list(scc)) for lt in lowers[tv]):
            return False
        if any(get_vars(ut, list(scc)) for ut in uppers[tv]):
            return False
    return True


def get_vars(target: Type, vars: list[TypeVarId]) -> set[TypeVarId]:
    """Find type variables for which we are solving in a target type."""
    return {tv.id for tv in get_type_vars(target)} & set(vars)
