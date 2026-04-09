"""Function and decorator registry for SDK introspection.

This module provides a thread-safe global registry to track all decorated functions,
SDK functions, and configuration options for auto-documentation and API introspection.
"""

import inspect
import threading
from dataclasses import dataclass, field, is_dataclass, asdict
from typing import Any, Callable, Dict, List, Optional, get_type_hints
import json


@dataclass
class FunctionMetadata:
    """Metadata for a registered function."""

    name: str
    """Fully qualified name of the function (module.qualname)"""

    function: Optional[Callable] = None
    """Reference to the actual function object"""

    module: str = ""
    """Module where the function is defined"""

    qualname: str = ""
    """Qualified name of the function"""

    signature: str = ""
    """Function signature as a string"""

    docstring: Optional[str] = None
    """Function docstring"""

    parameters: Dict[str, Any] = field(default_factory=dict)
    """Parameter names and their type hints"""

    return_type: Optional[str] = None
    """Return type annotation as a string"""

    is_async: bool = False
    """Whether the function is async"""

    is_decorated: bool = False
    """Whether this is a user's decorated function"""

    decorator_name: Optional[str] = None
    """Name of the decorator applied (e.g., 'trace')"""

    decorator_options: Dict[str, Any] = field(default_factory=dict)
    """Options passed to the decorator"""

    examples: List[str] = field(default_factory=list)
    """Code examples showing how to use this function"""

    category: str = "general"
    """Category: 'decorator', 'initialization', 'integration', 'logging', 'tracing', etc."""

    tags: List[str] = field(default_factory=list)
    """Additional tags for filtering/searching"""


@dataclass
class DecoratorMetadata:
    """Metadata for a registered decorator."""

    name: str
    """Decorator name (e.g., 'trace')"""

    function: Optional[Callable] = None
    """Reference to the decorator function"""

    docstring: Optional[str] = None
    """Decorator docstring"""

    options_class: Optional[type] = None
    """Options class (e.g., TraceOptions)"""

    options_schema: Dict[str, Any] = field(default_factory=dict)
    """Schema describing available options"""

    examples: List[str] = field(default_factory=list)
    """Code examples"""

    category: str = "tracing"
    """Category of decorator"""


@dataclass
class ConfigFieldMetadata:
    """Metadata for a configuration field."""

    name: str
    """Field name"""

    type_hint: str
    """Type annotation as string"""

    default_value: Any = None
    """Default value"""

    description: Optional[str] = None
    """Field description"""

    required: bool = False
    """Whether the field is required"""

    category: str = "general"
    """Category: 'identification', 'aws', 'opentelemetry', 'security', etc."""

    env_var: Optional[str] = None
    """Environment variable name if applicable"""


class FunctionRegistry:
    """Thread-safe global registry for SDK functions, decorators, and config."""

    _instance: Optional['FunctionRegistry'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure only one registry exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the registry if not already initialized."""
        if self._initialized:
            return

        self._functions: Dict[str, FunctionMetadata] = {}
        self._decorators: Dict[str, DecoratorMetadata] = {}
        self._config_fields: Dict[str, ConfigFieldMetadata] = {}
        self._user_traced_functions: Dict[str, FunctionMetadata] = {}
        self._lock = threading.Lock()
        self._initialized = True

    def _make_serializable(self, obj: Any) -> Any:
        """Convert non-serializable objects to serializable formats.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable version of the object
        """
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        if is_dataclass(obj):
            try:
                # Convert dataclass to dict and recursively clean it
                return self._make_serializable(asdict(obj))
            except Exception:
                return str(obj)

        if isinstance(obj, dict):
            return {str(k): self._make_serializable(v) for k, v in obj.items()}

        if isinstance(obj, (list, tuple, set)):
            return [self._make_serializable(item) for item in obj]

        if inspect.isclass(obj) or inspect.isfunction(obj):
            return f"{obj.__module__}.{obj.__qualname__}"

        # Default fallback to string
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)

    def register_function(
        self,
        func: Callable,
        category: str = "general",
        examples: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Register an SDK function.

        Args:
            func: Function to register
            category: Function category
            examples: Code examples
            tags: Additional tags
        """
        with self._lock:
            try:
                name = f"{func.__module__}.{func.__qualname__}"
                sig = inspect.signature(func)

                # Get type hints safely
                try:
                    type_hints = get_type_hints(func)
                except Exception:
                    type_hints = {}

                # Extract parameter info
                parameters = {}
                for param_name, param in sig.parameters.items():
                    param_type = type_hints.get(param_name, Any)
                    parameters[param_name] = {
                        "type": str(param_type),
                        "default": self._make_serializable(param.default) if param.default != inspect.Parameter.empty else None,
                        "kind": str(param.kind),
                    }

                # Extract return type
                return_type = type_hints.get('return', None)
                return_type_str = str(return_type) if return_type else None

                metadata = FunctionMetadata(
                    name=name,
                    function=func,
                    module=func.__module__,
                    qualname=func.__qualname__,
                    signature=str(sig),
                    docstring=inspect.getdoc(func),
                    parameters=parameters,
                    return_type=return_type_str,
                    is_async=inspect.iscoroutinefunction(func),
                    category=category,
                    examples=examples or [],
                    tags=tags or [],
                )

                self._functions[name] = metadata
            except Exception as e:
                # Silently fail registration - don't break SDK functionality
                pass

    def register_decorator(
        self,
        name: str,
        decorator_func: Callable,
        options_class: Optional[type] = None,
        examples: Optional[List[str]] = None,
        category: str = "tracing",
    ) -> None:
        """Register a decorator.

        Args:
            name: Decorator name
            decorator_func: The decorator function
            options_class: Options dataclass (e.g., TraceOptions)
            examples: Code examples
            category: Decorator category
        """
        with self._lock:
            try:
                # Extract options schema from dataclass
                options_schema = {}
                if options_class and hasattr(options_class, '__dataclass_fields__'):
                    for field_name, field_info in options_class.__dataclass_fields__.items():
                        options_schema[field_name] = {
                            "type": str(field_info.type),
                            "default": self._make_serializable(field_info.default) if field_info.default != inspect.Parameter.empty else None,
                        }

                metadata = DecoratorMetadata(
                    name=name,
                    function=decorator_func,
                    docstring=inspect.getdoc(decorator_func),
                    options_class=options_class,
                    options_schema=options_schema,
                    examples=examples or [],
                    category=category,
                )

                self._decorators[name] = metadata
            except Exception:
                pass

    def register_traced_function(
        self,
        func: Callable,
        decorator_name: str = "trace",
        options: Optional[Any] = None,
    ) -> None:
        """Register a user's @trace decorated function.

        Args:
            func: The decorated function
            decorator_name: Name of decorator applied
            options: Decorator options object
        """
        with self._lock:
            try:
                name = f"{func.__module__}.{func.__qualname__}"
                sig = inspect.signature(func)

                # Extract options as dict
                decorator_options = {}
                if options:
                    if hasattr(options, '__dict__'):
                        decorator_options = {k: self._make_serializable(v) for k, v in options.__dict__.items()}
                    elif is_dataclass(options):
                        decorator_options = self._make_serializable(asdict(options))

                metadata = FunctionMetadata(
                    name=name,
                    function=func,
                    module=func.__module__,
                    qualname=func.__qualname__,
                    signature=str(sig),
                    docstring=inspect.getdoc(func),
                    is_async=inspect.iscoroutinefunction(func),
                    is_decorated=True,
                    decorator_name=decorator_name,
                    decorator_options=decorator_options,
                    category="traced",
                )

                self._user_traced_functions[name] = metadata
            except Exception:
                pass

    def register_config_field(
        self,
        name: str,
        type_hint: str,
        default_value: Any = None,
        description: Optional[str] = None,
        required: bool = False,
        category: str = "general",
        env_var: Optional[str] = None,
    ) -> None:
        """Register a configuration field.

        Args:
            name: Field name
            type_hint: Type annotation as string
            default_value: Default value
            description: Field description
            required: Whether required
            category: Field category
            env_var: Associated environment variable
        """
        with self._lock:
            metadata = ConfigFieldMetadata(
                name=name,
                type_hint=type_hint,
                default_value=default_value,
                description=description,
                required=required,
                category=category,
                env_var=env_var,
            )
            self._config_fields[name] = metadata

    def get_function(self, name: str) -> Optional[FunctionMetadata]:
        """Get metadata for a specific function."""
        with self._lock:
            return self._functions.get(name)

    def get_all_functions(self) -> Dict[str, FunctionMetadata]:
        """Get all registered SDK functions."""
        with self._lock:
            return self._functions.copy()

    def get_functions_by_category(self, category: str) -> Dict[str, FunctionMetadata]:
        """Get functions filtered by category."""
        with self._lock:
            return {
                name: meta
                for name, meta in self._functions.items()
                if meta.category == category
            }

    def get_decorator(self, name: str) -> Optional[DecoratorMetadata]:
        """Get metadata for a specific decorator."""
        with self._lock:
            return self._decorators.get(name)

    def get_all_decorators(self) -> Dict[str, DecoratorMetadata]:
        """Get all registered decorators."""
        with self._lock:
            return self._decorators.copy()

    def get_config_field(self, name: str) -> Optional[ConfigFieldMetadata]:
        """Get metadata for a specific config field."""
        with self._lock:
            return self._config_fields.get(name)

    def get_all_config_fields(self) -> Dict[str, ConfigFieldMetadata]:
        """Get all configuration fields."""
        with self._lock:
            return self._config_fields.copy()

    def get_config_fields_by_category(self, category: str) -> Dict[str, ConfigFieldMetadata]:
        """Get config fields filtered by category."""
        with self._lock:
            return {
                name: meta
                for name, meta in self._config_fields.items()
                if meta.category == category
            }

    def get_traced_functions(self) -> Dict[str, FunctionMetadata]:
        """Get all user's @trace decorated functions."""
        with self._lock:
            return self._user_traced_functions.copy()

    def clear(self) -> None:
        """Clear all registered items (mainly for testing)."""
        with self._lock:
            self._functions.clear()
            self._decorators.clear()
            self._config_fields.clear()
            self._user_traced_functions.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Export registry as a dictionary for serialization."""
        with self._lock:
            return {
                "functions": {
                    name: {
                        "name": meta.name,
                        "module": meta.module,
                        "qualname": meta.qualname,
                        "signature": meta.signature,
                        "docstring": meta.docstring,
                        "parameters": meta.parameters,
                        "return_type": meta.return_type,
                        "is_async": meta.is_async,
                        "category": meta.category,
                        "examples": meta.examples,
                        "tags": meta.tags,
                    }
                    for name, meta in self._functions.items()
                },
                "decorators": {
                    name: {
                        "name": meta.name,
                        "docstring": meta.docstring,
                        "options_schema": meta.options_schema,
                        "examples": meta.examples,
                        "category": meta.category,
                    }
                    for name, meta in self._decorators.items()
                },
                "config_fields": {
                    name: {
                        "name": meta.name,
                        "type_hint": meta.type_hint,
                        "default_value": str(meta.default_value) if meta.default_value is not None else None,
                        "description": meta.description,
                        "required": meta.required,
                        "category": meta.category,
                        "env_var": meta.env_var,
                    }
                    for name, meta in self._config_fields.items()
                },
                "traced_functions": {
                    name: {
                        "name": meta.name,
                        "module": meta.module,
                        "qualname": meta.qualname,
                        "signature": meta.signature,
                        "docstring": meta.docstring,
                        "is_async": meta.is_async,
                        "decorator_name": meta.decorator_name,
                        "decorator_options": meta.decorator_options,
                    }
                    for name, meta in self._user_traced_functions.items()
                },
            }


# Global registry instance
_registry = FunctionRegistry()


def get_registry() -> FunctionRegistry:
    """Get the global function registry instance."""
    return _registry
