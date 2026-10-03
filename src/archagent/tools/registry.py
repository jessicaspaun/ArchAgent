from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum, StrEnum
from pathlib import Path
from stat import S_ISDIR
from types import MappingProxyType

from .list_files import ListFilesSuccess, ListFilesTool
from .read_file import ReadFileSuccess, ReadFileTool
from .results import ToolFailure
from .search_code import SearchCodeSuccess, SearchCodeTool

ToolResult = ListFilesSuccess | ReadFileSuccess | SearchCodeSuccess | ToolFailure
ValidatedArguments = Mapping[str, object]
ToolAdapter = Callable[[ValidatedArguments], ToolResult]


class InitializationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ArgumentType(StrEnum):
    STRING = "string"
    BOOLEAN = "boolean"


class ArgumentConstraint(StrEnum):
    NONEMPTY = "nonempty"
    REPOSITORY_RELATIVE = "repository_relative"


class _NoDefault(Enum):
    VALUE = object()


NO_DEFAULT = _NoDefault.VALUE
ArgumentDefault = str | bool | None | _NoDefault


@dataclass(frozen=True)
class ArgumentDefinition:
    name: str
    argument_type: ArgumentType
    required: bool
    description: str
    default: ArgumentDefault = NO_DEFAULT
    constraints: tuple[ArgumentConstraint, ...] = ()


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    arguments: tuple[ArgumentDefinition, ...]
    allow_extra_arguments: bool
    adapter: ToolAdapter


@dataclass(frozen=True)
class ArgumentMetadata:
    name: str
    type: str
    required: bool
    description: str
    constraints: tuple[str, ...]


@dataclass(frozen=True)
class OptionalArgumentMetadata(ArgumentMetadata):
    default: str | bool | None


@dataclass(frozen=True)
class ToolMetadata:
    name: str
    description: str
    arguments: tuple[ArgumentMetadata, ...]
    allow_extra_arguments: bool


@dataclass(frozen=True, init=False)
class ToolRegistry:
    _definitions: tuple[ToolDefinition, ...]
    _lookup: Mapping[str, ToolDefinition]

    def __init__(self, definitions: tuple[ToolDefinition, ...]) -> None:
        names = [definition.name for definition in definitions]
        duplicate = next((name for name in names if names.count(name) > 1), None)
        if duplicate is not None:
            raise InitializationError(
                code="duplicate_tool_name",
                message=f"Tool name '{duplicate}' is defined more than once.",
            )

        for definition in definitions:
            _validate_definition(definition)

        ordered = tuple(sorted(definitions, key=lambda definition: definition.name))
        lookup = MappingProxyType(
            {definition.name: definition for definition in ordered}
        )
        object.__setattr__(self, "_definitions", ordered)
        object.__setattr__(self, "_lookup", lookup)

    def discover(self) -> tuple[ToolMetadata, ...]:
        return tuple(_metadata_for(definition) for definition in self._definitions)

    def invoke(self, name: str, arguments: Mapping[str, object]) -> ToolResult:
        definition = self._lookup.get(name)
        if definition is None:
            available = ", ".join(self._lookup)
            return ToolFailure(
                code="unknown_tool",
                message=f"Unknown tool '{name}'. Available tools: {available}.",
            )

        validated = _validate_arguments(definition, arguments)
        if isinstance(validated, ToolFailure):
            return validated
        return definition.adapter(MappingProxyType(validated))


def create_repository_registry(
    target: Path, protected_source_root: Path
) -> ToolRegistry:
    protected = _resolve_protected_root(protected_source_root)
    root = _resolve_target(target)

    if root.is_relative_to(protected) or protected.is_relative_to(root):
        raise InitializationError(
            code="target_overlaps_archagent",
            message="The target repository overlaps the protected application source.",
        )

    list_tool = ListFilesTool(root)
    read_tool = ReadFileTool(root)
    search_tool = SearchCodeTool(root)

    def invoke_list(arguments: ValidatedArguments) -> ToolResult:
        return list_tool.list_files(
            path=_string_argument(arguments, "path"),
            include_hidden=_boolean_argument(arguments, "include_hidden"),
        )

    def invoke_read(arguments: ValidatedArguments) -> ToolResult:
        return read_tool.read_file(path=_string_argument(arguments, "path"))

    def invoke_search(arguments: ValidatedArguments) -> ToolResult:
        return search_tool.search_code(
            path=_string_argument(arguments, "path"),
            query=_string_argument(arguments, "query"),
            include_hidden=_boolean_argument(arguments, "include_hidden"),
        )

    path_constraints = (
        ArgumentConstraint.NONEMPTY,
        ArgumentConstraint.REPOSITORY_RELATIVE,
    )
    hidden = ArgumentDefinition(
        name="include_hidden",
        argument_type=ArgumentType.BOOLEAN,
        required=False,
        default=False,
        description="Include entries whose names begin with a dot.",
    )
    return ToolRegistry(
        (
            ToolDefinition(
                name="list_files",
                description=(
                    "Lists the immediate entries of one directory within the "
                    "configured repository without modifying them."
                ),
                arguments=(
                    ArgumentDefinition(
                        name="path",
                        argument_type=ArgumentType.STRING,
                        required=True,
                        description="A repository-relative directory path.",
                        constraints=path_constraints,
                    ),
                    hidden,
                ),
                allow_extra_arguments=False,
                adapter=invoke_list,
            ),
            ToolDefinition(
                name="read_file",
                description=(
                    "Reads the exact supported text of one file within the "
                    "configured repository without modifying it."
                ),
                arguments=(
                    ArgumentDefinition(
                        name="path",
                        argument_type=ArgumentType.STRING,
                        required=True,
                        description="A repository-relative file path.",
                        constraints=path_constraints,
                    ),
                ),
                allow_extra_arguments=False,
                adapter=invoke_read,
            ),
            ToolDefinition(
                name="search_code",
                description=(
                    "Recursively searches supported repository files for a "
                    "literal, case-sensitive string."
                ),
                arguments=(
                    ArgumentDefinition(
                        name="path",
                        argument_type=ArgumentType.STRING,
                        required=True,
                        description="A repository-relative directory path.",
                        constraints=path_constraints,
                    ),
                    ArgumentDefinition(
                        name="query",
                        argument_type=ArgumentType.STRING,
                        required=True,
                        description="The literal string to find; empty is allowed.",
                    ),
                    hidden,
                ),
                allow_extra_arguments=False,
                adapter=invoke_search,
            ),
        )
    )


def _validate_definition(definition: ToolDefinition) -> None:
    if not definition.name or not definition.description:
        _invalid_definition("Tool names and descriptions must be nonempty.")

    argument_names = [argument.name for argument in definition.arguments]
    if len(argument_names) != len(set(argument_names)):
        _invalid_definition(
            f"Tool '{definition.name}' contains duplicate argument names."
        )

    for argument in definition.arguments:
        if not argument.name or not argument.description:
            _invalid_definition("Argument names and descriptions must be nonempty.")
        has_default = argument.default is not NO_DEFAULT
        if argument.required and has_default:
            _invalid_definition(
                f"Required argument '{argument.name}' cannot define a default."
            )
        if not argument.required and not has_default:
            _invalid_definition(
                f"Optional argument '{argument.name}' must define a default."
            )
        if argument.constraints and argument.argument_type is not ArgumentType.STRING:
            _invalid_definition(
                f"Argument '{argument.name}' has constraints that require a string."
            )
        if len(argument.constraints) != len(set(argument.constraints)):
            _invalid_definition(
                f"Argument '{argument.name}' contains duplicate constraints."
            )
        if has_default:
            error = _value_error(argument, argument.default)
            if error is not None:
                _invalid_definition(
                    f"Default for argument '{argument.name}' is invalid: {error}"
                )


def _validate_arguments(
    definition: ToolDefinition, arguments: Mapping[str, object]
) -> dict[str, object] | ToolFailure:
    supplied = dict(arguments)
    validated: dict[str, object] = {}

    for argument in definition.arguments:
        if argument.name not in supplied:
            if argument.required:
                return _invalid_arguments(
                    f"Missing required argument '{argument.name}'."
                )
            validated[argument.name] = argument.default
            continue

        value = supplied[argument.name]
        error = _value_error(argument, value)
        if error is not None:
            return _invalid_arguments(f"Argument '{argument.name}' {error}")
        validated[argument.name] = value

    extras = sorted(set(supplied) - {item.name for item in definition.arguments})
    if extras and not definition.allow_extra_arguments:
        return _invalid_arguments(f"Unexpected argument '{extras[0]}'.")
    if definition.allow_extra_arguments:
        for name in extras:
            validated[name] = supplied[name]
    return validated


def _value_error(argument: ArgumentDefinition, value: object) -> str | None:
    expected_type = str if argument.argument_type == ArgumentType.STRING else bool
    if type(value) is not expected_type:
        return f"must be a {argument.argument_type.value}."
    if ArgumentConstraint.NONEMPTY in argument.constraints and value == "":
        return "must not be empty."
    if (
        ArgumentConstraint.REPOSITORY_RELATIVE in argument.constraints
        and isinstance(value, str)
        and Path(value).is_absolute()
    ):
        return "must be repository-relative."
    return None


def _metadata_for(definition: ToolDefinition) -> ToolMetadata:
    metadata: list[ArgumentMetadata] = []
    for argument in definition.arguments:
        constraints = tuple(item.value for item in argument.constraints)
        if argument.default is NO_DEFAULT:
            metadata.append(
                ArgumentMetadata(
                    name=argument.name,
                    type=argument.argument_type.value,
                    required=argument.required,
                    description=argument.description,
                    constraints=constraints,
                )
            )
        else:
            metadata.append(
                OptionalArgumentMetadata(
                    name=argument.name,
                    type=argument.argument_type.value,
                    required=argument.required,
                    description=argument.description,
                    constraints=constraints,
                    default=argument.default,
                )
            )
    return ToolMetadata(
        name=definition.name,
        description=definition.description,
        arguments=tuple(metadata),
        allow_extra_arguments=definition.allow_extra_arguments,
    )


def _resolve_target(target: Path) -> Path:
    try:
        root = target.resolve(strict=True)
        if not S_ISDIR(root.stat().st_mode):
            raise InitializationError(
                code="target_not_a_directory",
                message="The target repository is not a directory.",
            )
        return root
    except FileNotFoundError as error:
        raise InitializationError(
            code="target_not_found",
            message="The target repository does not exist.",
        ) from error
    except NotADirectoryError as error:
        raise InitializationError(
            code="target_not_a_directory",
            message="The target repository is not a directory.",
        ) from error
    except PermissionError as error:
        raise InitializationError(
            code="target_permission_denied",
            message="Permission to access the target repository was denied.",
        ) from error


def _resolve_protected_root(protected_source_root: Path) -> Path:
    try:
        protected = protected_source_root.resolve(strict=True)
        if not S_ISDIR(protected.stat().st_mode):
            raise InitializationError(
                code="invalid_protected_source_root",
                message="The protected application source root is invalid.",
            )
        return protected
    except (FileNotFoundError, NotADirectoryError, PermissionError) as error:
        raise InitializationError(
            code="invalid_protected_source_root",
            message="The protected application source root is invalid.",
        ) from error


def _string_argument(arguments: ValidatedArguments, name: str) -> str:
    value = arguments[name]
    if type(value) is not str:
        raise RuntimeError("Validated string argument has an unexpected type.")
    return value


def _boolean_argument(arguments: ValidatedArguments, name: str) -> bool:
    value = arguments[name]
    if type(value) is not bool:
        raise RuntimeError("Validated Boolean argument has an unexpected type.")
    return value


def _invalid_arguments(message: str) -> ToolFailure:
    return ToolFailure(code="invalid_arguments", message=message)


def _invalid_definition(message: str) -> None:
    raise InitializationError(code="invalid_tool_definition", message=message)
