from __future__ import annotations

from typing import Final, Iterable, Mapping, Sequence, TypeVar, cast, overload

from mypy.nodes import ARG_POS, ARG_STAR, ArgKind, Var
from mypy.state import state
from mypy.types import (
    ANY_STRATEGY,
    AnyType,
    BoolTypeQuery,
    CallableType,
    DeletedType,
    ErasedType,
    FunctionLike,
    Instance,
    LiteralType,
    NoneType,
    Overloaded,
    Parameters,
    ParamSpecFlavor,
    ParamSpecType,
    PartialType,
    ProperType,
    TrivialSyntheticTypeTranslator,
    TupleType,
    Type,
    TypeAliasType,
    TypedDictType,
    TypeType,
    TypeVarId,
    TypeVarLikeType,
    TypeVarTupleType,
    TypeVarType,
    UnboundType,
    UninhabitedType,
    UnionType,
    UnpackType,
    flatten_nested_tuples,
    flatten_nested_unions,
    get_proper_type,
    split_with_prefix_and_suffix,
)
from mypy.typevartuples import find_unpack_in_list, split_with_instance

# Solving the import cycle:
import mypy.type_visitor  # ruff: isort: skip

# WARNING: these functions should never (directly or indirectly) depend on
# is_subtype(), meet_types(), join_types() etc.
# TODO: add a static dependency test for this.


@overload
def expand_type(typ: CallableType, env: Mapping[TypeVarId, Type]) -> CallableType:
    ...


@overload
def expand_type(typ: ProperType, env: Mapping[TypeVarId, Type]) -> ProperType:
    ...


@overload
def expand_type(typ: Type, env: Mapping[TypeVarId, Type]) -> Type:
    ...


def expand_type(typ: Type, env: Mapping[TypeVarId, Type]) -> Type:
    """Substitute any type variable references in a type given by a type
    environment.
    """
    return typ.accept(ExpandTypeVisitor(env))


@overload
def expand_type_by_instance(typ: CallableType, instance: Instance) -> CallableType:
    ...


@overload
def expand_type_by_instance(typ: ProperType, instance: Instance) -> ProperType:
    ...


@overload
def expand_type_by_instance(typ: Type, instance: Instance) -> Type:
    ...


def expand_type_by_instance(typ: Type, instance: Instance) -> Type:
    """Substitute type variables in type using values from an Instance.
    Type variables are considered to be bound by the class declaration."""
    if not instance.args:
        return typ
    else:
        variables: dict[TypeVarId, Type] = {}
        if instance.type.has_type_var_tuple_type:
            assert instance.type.type_var_tuple_prefix is not None
            assert instance.type.type_var_tuple_suffix is not None

            args_prefix, args_middle, args_suffix = split_with_instance(instance)
            tvars_prefix, tvars_middle, tvars_suffix = split_with_prefix_and_suffix(
                tuple(instance.type.defn.type_vars),
                instance.type.type_var_tuple_prefix,
                instance.type.type_var_tuple_suffix,
            )
            tvar = tvars_middle[0]
            assert isinstance(tvar, TypeVarTupleType)
            variables = {tvar.id: TupleType(list(args_middle), tvar.tuple_fallback)}
            instance_args = args_prefix + args_suffix
            tvars = tvars_prefix + tvars_suffix
        else:
            tvars = tuple(instance.type.defn.type_vars)
            instance_args = instance.args

        for binder, arg in zip(tvars, instance_args):
            assert isinstance(binder, TypeVarLikeType)
            variables[binder.id] = arg

        return expand_type(typ, variables)


F = TypeVar("F", bound=FunctionLike)


def freshen_function_type_vars(callee: F) -> F:
    """Substitute fresh type variables for generic function type variables."""
    if isinstance(callee, CallableType):
        if not callee.is_generic():
            return cast(F, callee)
        tvs = []
        tvmap: dict[TypeVarId, Type] = {}
        for v in callee.variables:
            tv = v.new_unification_variable(v)
            tvs.append(tv)
            tvmap[v.id] = tv
        fresh = expand_type(callee, tvmap).copy_modified(variables=tvs)
        return cast(F, fresh)
    else:
        assert isinstance(callee, Overloaded)
        fresh_overload = Overloaded([freshen_function_type_vars(item) for item in callee.items])
        return cast(F, fresh_overload)


class HasGenericCallable(BoolTypeQuery):
    def __init__(self) -> None:
        super().__init__(ANY_STRATEGY)

    def visit_callable_type(self, t: CallableType) -> bool:
        return t.is_generic() or super().visit_callable_type(t)


# Share a singleton since this is performance sensitive
has_generic_callable: Final = HasGenericCallable()


T = TypeVar("T", bound=Type)


def freshen_all_functions_type_vars(t: T) -> T:
    result: Type
    has_generic_callable.reset()
    if not t.accept(has_generic_callable):
        return t  # Fast path to avoid expensive freshening
    else:
        result = t.accept(FreshenCallableVisitor())
        assert isinstance(result, type(t))
        return result


class FreshenCallableVisitor(mypy.type_visitor.TypeTranslator):
    def visit_callable_type(self, t: CallableType) -> Type:
        result = super().visit_callable_type(t)
        assert isinstance(result, ProperType) and isinstance(result, CallableType)
        return freshen_function_type_vars(result)

    def visit_type_alias_type(self, t: TypeAliasType) -> Type:
        # Same as for ExpandTypeVisitor
        return t.copy_modified(args=[arg.accept(self) for arg in t.args])


class ExpandTypeVisitor(TrivialSyntheticTypeTranslator):
    """Visitor that substitutes type variables with values."""

    variables: Mapping[TypeVarId, Type]  # TypeVar id -> TypeVar value

    def __init__(self, variables: Mapping[TypeVarId, Type]) -> None:
        self.variables = variables

    def visit_unbound_type(self, t: UnboundType) -> Type:
        return t

    def visit_any(self, t: AnyType) -> Type:
        return t

    def visit_none_type(self, t: NoneType) -> Type:
        return t

    def visit_uninhabited_type(self, t: UninhabitedType) -> Type:
        return t

    def visit_deleted_type(self, t: DeletedType) -> Type:
        return t

    def visit_erased_type(self, t: ErasedType) -> Type:
        # This may happen during type inference if some function argument
        # type is a generic callable, and its erased form will appear in inferred
        # constraints, then solver may check subtyping between them, which will trigger
        # unify_generic_callables(), this is why we can get here. Another example is
        # when inferring type of lambda in generic context, the lambda body contains
        # a generic method in generic class.
        return t

    def visit_instance(self, t: Instance) -> Type:
        args = self.expand_types_with_unpack(list(t.args))
        if isinstance(args, list):
            return t.copy_modified(args=args)
        else:
            return args

    def visit_type_var(self, t: TypeVarType) -> Type:
        # Normally upper bounds can't contain other type variables, the only exception is
        # special type variable Self`0 <: C[T, S], where C is the class where Self is used.
        if t.id.raw_id == 0:
            t = t.copy_modified(upper_bound=t.upper_bound.accept(self))
        repl = self.variables.get(t.id, t)
        if isinstance(repl, ProperType) and isinstance(repl, Instance):
            # TODO: do we really need to do this?
            # If I try to remove this special-casing ~40 tests fail on reveal_type().
            return repl.copy_modified(last_known_value=None)
        return repl

    def visit_param_spec(self, t: ParamSpecType) -> Type:
        # set prefix to something empty so we don't duplicate it
        repl = get_proper_type(
            self.variables.get(t.id, t.copy_modified(prefix=Parameters([], [], [])))
        )
        if isinstance(repl, Instance):
            # TODO: what does prefix mean in this case?
            # TODO: why does this case even happen? Instances aren't plural.
            return repl
        elif isinstance(repl, (ParamSpecType, Parameters, CallableType)):
            if isinstance(repl, ParamSpecType):
                return repl.copy_modified(
                    flavor=t.flavor,
                    prefix=t.prefix.copy_modified(
                        arg_types=t.prefix.arg_types + repl.prefix.arg_types,
                        arg_kinds=t.prefix.arg_kinds + repl.prefix.arg_kinds,
                        arg_names=t.prefix.arg_names + repl.prefix.arg_names,
                    ),
                )
            else:
                # if the paramspec is *P.args or **P.kwargs:
                if t.flavor != ParamSpecFlavor.BARE:
                    assert isinstance(repl, CallableType), "Should not be able to get here."
                    # Is this always the right thing to do?
                    param_spec = repl.param_spec()
                    if param_spec:
                        return param_spec.with_flavor(t.flavor)
                    else:
                        return repl
                else:
                    return Parameters(
                        t.prefix.arg_types + repl.arg_types,
                        t.prefix.arg_kinds + repl.arg_kinds,
                        t.prefix.arg_names + repl.arg_names,
                        variables=[*t.prefix.variables, *repl.variables],
                    )

        else:
            # TODO: should this branch be removed? better not to fail silently
            return repl

    def visit_type_var_tuple(self, t: TypeVarTupleType) -> Type:
        # Sometimes solver may need to expand a type variable with (a copy of) itself
        # (usually together with other TypeVars, but it is hard to filter out TypeVarTuples).
        repl = self.variables[t.id]
        if isinstance(repl, TypeVarTupleType):
            return repl
        raise NotImplementedError

    def visit_unpack_type(self, t: UnpackType) -> Type:
        # It is impossible to reasonably implement visit_unpack_type, because
        # unpacking inherently expands to something more like a list of types.
        #
        # Relevant sections that can call unpack should call expand_unpack()
        # instead.
        # However, if the item is a variadic tuple, we can simply carry it over.
        # it is hard to assert this without getting proper type.
        return UnpackType(t.type.accept(self))

    def expand_unpack(self, t: UnpackType) -> list[Type] | Instance | AnyType | None:
        return expand_unpack_with_variables(t, self.variables)

    def visit_parameters(self, t: Parameters) -> Type:
        return t.copy_modified(arg_types=self.expand_types(t.arg_types))

    def interpolate_args_for_unpack(
        self, t: CallableType, var_arg: UnpackType
    ) -> tuple[list[str | None], list[ArgKind], list[Type]]:
        star_index = t.arg_kinds.index(ARG_STAR)

        # We have something like Unpack[Tuple[X1, X2, Unpack[Ts], Y1, Y2]]
        var_arg_type = get_proper_type(var_arg.type)
        if isinstance(var_arg_type, TupleType):
            expanded_tuple = var_arg_type.accept(self)
            # TODO: handle the case that expanded_tuple is a variable length tuple.
            assert isinstance(expanded_tuple, ProperType) and isinstance(expanded_tuple, TupleType)
            expanded_items = expanded_tuple.items
        else:
            expanded_items_res = self.expand_unpack(var_arg)
            if isinstance(expanded_items_res, list):
                expanded_items = expanded_items_res
            elif (
                isinstance(expanded_items_res, Instance)
                and expanded_items_res.type.fullname == "builtins.tuple"
            ):
                # TODO: We shouldnt't simply treat this as a *arg because of suffix handling
                # (there cannot be positional args after a *arg)
                arg_types = (
                    t.arg_types[:star_index]
                    + [expanded_items_res.args[0]]
                    + t.arg_types[star_index + 1 :]
                )
                return (t.arg_names, t.arg_kinds, arg_types)
            else:
                return (t.arg_names, t.arg_kinds, t.arg_types)

        expanded_unpack_index = find_unpack_in_list(expanded_items)
        # This is the case where we just have Unpack[Tuple[X1, X2, X3]]
        # (for example if either the tuple had no unpacks, or the unpack in the
        # tuple got fully expanded to something with fixed length)
        if expanded_unpack_index is None:
            arg_names = (
                t.arg_names[:star_index]
                + [None] * len(expanded_items)
                + t.arg_names[star_index + 1 :]
            )
            arg_kinds = (
                t.arg_kinds[:star_index]
                + [ARG_POS] * len(expanded_items)
                + t.arg_kinds[star_index + 1 :]
            )
            arg_types = (
                self.expand_types(t.arg_types[:star_index])
                + expanded_items
                + self.expand_types(t.arg_types[star_index + 1 :])
            )
        else:
            # If Unpack[Ts] simplest form still has an unpack or is a
            # homogenous tuple, then only the prefix can be represented as
            # positional arguments, and we pass Tuple[Unpack[Ts-1], Y1, Y2]
            # as the star arg, for example.
            expanded_unpack = expanded_items[expanded_unpack_index]
            assert isinstance(expanded_unpack, UnpackType)

            # Extract the typevartuple so we can get a tuple fallback from it.
            expanded_unpacked_tvt = expanded_unpack.type
            if isinstance(expanded_unpacked_tvt, TypeVarTupleType):
                fallback = expanded_unpacked_tvt.tuple_fallback
            else:
                # This can happen when tuple[Any, ...] is used to "patch" a variadic
                # generic type without type arguments provided.
                assert isinstance(expanded_unpacked_tvt, ProperType)
                assert isinstance(expanded_unpacked_tvt, Instance)
                assert expanded_unpacked_tvt.type.fullname == "builtins.tuple"
                fallback = expanded_unpacked_tvt

            prefix_len = expanded_unpack_index
            arg_names = t.arg_names[:star_index] + [None] * prefix_len + t.arg_names[star_index:]
            arg_kinds = (
                t.arg_kinds[:star_index] + [ARG_POS] * prefix_len + t.arg_kinds[star_index:]
            )
            arg_types = (
                self.expand_types(t.arg_types[:star_index])
                + expanded_items[:prefix_len]
                # Constructing the Unpack containing the tuple without the prefix.
                + [
                    UnpackType(TupleType(expanded_items[prefix_len:], fallback))
                    if len(expanded_items) - prefix_len > 1
                    else expanded_items[0]
                ]
                + self.expand_types(t.arg_types[star_index + 1 :])
            )
        return (arg_names, arg_kinds, arg_types)

    def visit_callable_type(self, t: CallableType) -> CallableType:
        param_spec = t.param_spec()
        if param_spec is not None:
            repl = get_proper_type(self.variables.get(param_spec.id))
            # If a ParamSpec in a callable type is substituted with a
            # callable type, we can't use normal substitution logic,
            # since ParamSpec is actually split into two components
            # *P.args and **P.kwargs in the original type. Instead, we
            # must expand both of them with all the argument types,
            # kinds and names in the replacement. The return type in
            # the replacement is ignored.
            if isinstance(repl, (CallableType, Parameters)):
                # Substitute *args: P.args, **kwargs: P.kwargs
                prefix = param_spec.prefix
                # we need to expand the types in the prefix, so might as well
                # not get them in the first place
                t = t.expand_param_spec(repl, no_prefix=True)
                return t.copy_modified(
                    arg_types=self.expand_types(prefix.arg_types) + t.arg_types,
                    arg_kinds=prefix.arg_kinds + t.arg_kinds,
                    arg_names=prefix.arg_names + t.arg_names,
                    ret_type=t.ret_type.accept(self),
                    type_guard=(t.type_guard.accept(self) if t.type_guard is not None else None),
                )
            # TODO: Conceptually, the "len(t.arg_types) == 2" should not be here. However, this
            #       errors without it. Either figure out how to eliminate this or place an
            #       explanation for why this is necessary.
            elif isinstance(repl, ParamSpecType) and len(t.arg_types) == 2:
                # We're substituting one paramspec for another; this can mean that the prefix
                # changes. (e.g. sub Concatenate[int, P] for Q)
                prefix = repl.prefix
                old_prefix = param_spec.prefix

                # Check assumptions. I'm not sure what order to place new prefix vs old prefix:
                assert not old_prefix.arg_types or not prefix.arg_types

                t = t.copy_modified(
                    arg_types=prefix.arg_types + old_prefix.arg_types + t.arg_types,
                    arg_kinds=prefix.arg_kinds + old_prefix.arg_kinds + t.arg_kinds,
                    arg_names=prefix.arg_names + old_prefix.arg_names + t.arg_names,
                )

        var_arg = t.var_arg()
        if var_arg is not None and isinstance(var_arg.typ, UnpackType):
            arg_names, arg_kinds, arg_types = self.interpolate_args_for_unpack(t, var_arg.typ)
        else:
            arg_names = t.arg_names
            arg_kinds = t.arg_kinds
            arg_types = self.expand_types(t.arg_types)

        return t.copy_modified(
            arg_types=arg_types,
            arg_names=arg_names,
            arg_kinds=arg_kinds,
            ret_type=t.ret_type.accept(self),
            type_guard=(t.type_guard.accept(self) if t.type_guard is not None else None),
        )

    def visit_overloaded(self, t: Overloaded) -> Type:
        items: list[CallableType] = []
        for item in t.items:
            new_item = item.accept(self)
            assert isinstance(new_item, ProperType)
            assert isinstance(new_item, CallableType)
            items.append(new_item)
        return Overloaded(items)

    def expand_types_with_unpack(
        self, typs: Sequence[Type]
    ) -> list[Type] | AnyType | UninhabitedType | Instance:
        """Expands a list of types that has an unpack.

        In corner cases, this can return a type rather than a list, in which case this
        indicates use of Any or some error occurred earlier. In this case callers should
        simply propagate the resulting type.
        """
        # TODO: this will cause a crash on aliases like A = Tuple[int, Unpack[A]].
        # Although it is unlikely anyone will write this, we should fail gracefully.
        typs = flatten_nested_tuples(typs)
        items: list[Type] = []
        for item in typs:
            if isinstance(item, UnpackType) and isinstance(item.type, TypeVarTupleType):
                unpacked_items = self.expand_unpack(item)
                if unpacked_items is None:
                    # TODO: better error, something like tuple of unknown?
                    return UninhabitedType()
                elif isinstance(unpacked_items, Instance):
                    if len(typs) == 1:
                        return unpacked_items
                    else:
                        assert False, "Invalid unpack of variable length tuple"
                elif isinstance(unpacked_items, AnyType):
                    return unpacked_items
                else:
                    items.extend(unpacked_items)
            else:
                # Must preserve original aliases when possible.
                items.append(item.accept(self))
        return items

    def visit_tuple_type(self, t: TupleType) -> Type:
        items = self.expand_types_with_unpack(t.items)
        if isinstance(items, list):
            fallback = t.partial_fallback.accept(self)
            assert isinstance(fallback, ProperType) and isinstance(fallback, Instance)
            return t.copy_modified(items=items, fallback=fallback)
        else:
            return items

    def visit_typeddict_type(self, t: TypedDictType) -> Type:
        fallback = t.fallback.accept(self)
        assert isinstance(fallback, ProperType) and isinstance(fallback, Instance)
        return t.copy_modified(item_types=self.expand_types(t.items.values()), fallback=fallback)

    def visit_literal_type(self, t: LiteralType) -> Type:
        # TODO: Verify this implementation is correct
        return t

    def visit_union_type(self, t: UnionType) -> Type:
        expanded = self.expand_types(t.items)
        # After substituting for type variables in t.items, some resulting types
        # might be subtypes of others, however calling  make_simplified_union()
        # can cause recursion, so we just remove strict duplicates.
        simplified = UnionType.make_union(
            remove_trivial(flatten_nested_unions(expanded)), t.line, t.column
        )
        # This call to get_proper_type() is unfortunate but is required to preserve
        # the invariant that ProperType will stay ProperType after applying expand_type(),
        # otherwise a single item union of a type alias will break it. Note this should not
        # cause infinite recursion since pathological aliases like A = Union[A, B] are
        # banned at the semantic analysis level.
        return get_proper_type(simplified)

    def visit_partial_type(self, t: PartialType) -> Type:
        return t

    def visit_type_type(self, t: TypeType) -> Type:
        # TODO: Verify that the new item type is valid (instance or
        # union of instances or Any).  Sadly we can't report errors
        # here yet.
        item = t.item.accept(self)
        return TypeType.make_normalized(item)

    def visit_type_alias_type(self, t: TypeAliasType) -> Type:
        # Target of the type alias cannot contain type variables (not bound by the type
        # alias itself), so we just expand the arguments.
        args = self.expand_types_with_unpack(t.args)
        if isinstance(args, list):
            return t.copy_modified(args=args)
        else:
            return args

    def expand_types(self, types: Iterable[Type]) -> list[Type]:
        a: list[Type] = []
        for t in types:
            a.append(t.accept(self))
        return a


def expand_unpack_with_variables(
    t: UnpackType, variables: Mapping[TypeVarId, Type]
) -> list[Type] | Instance | AnyType | None:
    """May return either a list of types to unpack to, any, or a single
    variable length tuple. The latter may not be valid in all contexts.
    """
    if isinstance(t.type, TypeVarTupleType):
        repl = get_proper_type(variables.get(t.type.id, t))
        if isinstance(repl, TupleType):
            return repl.items
        elif isinstance(repl, Instance) and repl.type.fullname == "builtins.tuple":
            return repl
        elif isinstance(repl, AnyType):
            # tuple[Any, ...] would be better, but we don't have
            # the type info to construct that type here.
            return repl
        elif isinstance(repl, TypeVarTupleType):
            return [UnpackType(typ=repl)]
        elif isinstance(repl, UnpackType):
            return [repl]
        elif isinstance(repl, UninhabitedType):
            return None
        else:
            raise NotImplementedError(f"Invalid type replacement to expand: {repl}")
    else:
        raise NotImplementedError(f"Invalid type to expand: {t.type}")


@overload
def expand_self_type(var: Var, typ: ProperType, replacement: ProperType) -> ProperType:
    ...


@overload
def expand_self_type(var: Var, typ: Type, replacement: Type) -> Type:
    ...


def expand_self_type(var: Var, typ: Type, replacement: Type) -> Type:
    """Expand appearances of Self type in a variable type."""
    if var.info.self_type is not None and not var.is_property:
        return expand_type(typ, {var.info.self_type.id: replacement})
    return typ


def remove_trivial(types: Iterable[Type]) -> list[Type]:
    """Make trivial simplifications on a list of types without calling is_subtype().

    This makes following simplifications:
        * Remove bottom types (taking into account strict optional setting)
        * Remove everything else if there is an `object`
        * Remove strict duplicate types
    """
    removed_none = False
    new_types = []
    all_types = set()
    for t in types:
        p_t = get_proper_type(t)
        if isinstance(p_t, UninhabitedType):
            continue
        if isinstance(p_t, NoneType) and not state.strict_optional:
            removed_none = True
            continue
        if isinstance(p_t, Instance) and p_t.type.fullname == "builtins.object":
            return [p_t]
        if p_t not in all_types:
            new_types.append(t)
            all_types.add(p_t)
    if new_types:
        return new_types
    if removed_none:
        return [NoneType()]
    return [UninhabitedType()]
