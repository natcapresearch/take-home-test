import abc
from typing import Any, Self

from pydantic import (
    UUID4,
    ModelWrapValidatorHandler,
    computed_field,
    model_validator,
)
from src.backend.app.schemas.base import PydanticSchema
from src.backend.app.schemas.user import User


class Condition(PydanticSchema, abc.ABC):
    _name: str = ""

    @computed_field
    @property
    def name(self) -> str:
        """The name of the condition as written in the policy document."""
        return self._name

    @classmethod
    def yaml_to_subclass(cls, data: Any) -> Self | None:
        """
        Parses the yaml string representation of the condition to the condition class,
        if this yaml matches the condition's name.
        """
        if (
            data
            and isinstance(data, str)
            and getattr(cls._name, "default") == data
        ):
            return cls()

    @classmethod
    def all_subclasses(cls) -> set[type[Self]]:
        return set(cls.__subclasses__()).union(
            [s for c in cls.__subclasses__() for s in c.all_subclasses()]
        )

    @model_validator(mode="wrap")
    @classmethod
    def check_if_yaml(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self]
    ) -> Self:
        # This validation method will be called twice for each condition specified in
        # the policy document YAML file: the first time with the `data` set to the
        # incoming YAML object (usually a string) before the condition subclass has been
        # identified, and a second time with the identified condition subclass and the
        # `data` set to the kwargs dict passed to the constructor (usually an empty
        # object).
        if cls == Condition:
            # Identify the subclass matching the yaml
            for c in cls.all_subclasses():
                if inst := c.yaml_to_subclass(data):
                    return inst
            raise ValueError(f"Could not find condition '{data}'")

        return handler(data)

    def __str__(self):
        return self._name

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    @abc.abstractmethod
    def is_valid_with_resource_type(self, required_resource_type: str) -> bool:
        """
        Returns true if this condition is valid with this resource type.
        """
        ...

    @abc.abstractmethod
    def applies_to(
        self,
        user: User,
        resource_uid: str | UUID4 | None,
    ) -> bool: ...


class Unconditional(Condition):
    _name: str = "unconditional"

    def is_valid_with_resource_type(self, required_resource_type: str) -> bool:
        return True

    def applies_to(
        self,
        user: User,
        resource_uid: str | UUID4 | None,
    ) -> bool:
        return True
