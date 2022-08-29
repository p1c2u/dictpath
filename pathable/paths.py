"""Pathable paths module"""
from contextlib import contextmanager
from typing import Any
from typing import Hashable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple

from pathable.accessors import LookupAccessor
from pathable.dataclasses import BasePathData
from pathable.parsers import SEPARATOR
from pathable.parsers import parse_args


class BasePath(BasePathData):
    """Base path."""

    def __init__(self, *args: Any, **kwargs: Any):
        separator = kwargs.pop("separator", SEPARATOR)
        self.parts = parse_args(list(args))
        self.separator = separator

        self._cparts_cached: Optional[List[str]] = None

    @classmethod
    def __from_parts(cls, args: List[Any], separator: str = SEPARATOR) -> "BasePath":
        self = cls(separator=separator)
        self.parts = parse_args(args)
        return self

    @classmethod
    def __from_parsed_parts(
        cls, parts: List[Hashable], separator: str = SEPARATOR
    ) -> "BasePath":
        self = cls(separator=separator)
        self.parts = parts
        return self

    @property
    def _cparts(self) -> List[Any]:
        # Cached casefolded parts, for hashing and comparison
        if self._cparts_cached is None:
            self._cparts_cached = self._get_cparts()
        return self._cparts_cached

    def _get_cparts(self) -> List[str]:
        return [str(p) for p in self.parts]

    def _make_child(self, args: List[Any]) -> "BasePath":
        parts = parse_args(args, self.separator)
        parts_joined = self.parts + parts
        return self.__from_parsed_parts(parts_joined, self.separator)

    def _make_child_relpath(self, part: Hashable) -> "BasePath":
        # This is an optimization used for dir walking.  `part` must be
        # a single part relative to this path.
        parts = self.parts + [part]
        return self.__from_parsed_parts(parts, self.separator)

    def __str__(self) -> str:
        return self.separator.join(self._cparts)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)!r})"

    def __hash__(self) -> int:
        return hash(tuple(self._cparts))

    def __truediv__(self, key: Any) -> "BasePath":
        try:
            return self._make_child(
                [
                    key,
                ]
            )
        except TypeError:
            return NotImplemented

    def __rtruediv__(self, key: Hashable) -> "BasePath":
        try:
            return self.__from_parts([key] + self.parts)
        except TypeError:
            return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BasePath):
            return NotImplemented
        return self._cparts == other._cparts

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, BasePath):
            return NotImplemented
        return self._cparts < other._cparts

    def __le__(self, other: Any) -> bool:
        if not isinstance(other, BasePath):
            return NotImplemented
        return self._cparts <= other._cparts

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, BasePath):
            return NotImplemented
        return self._cparts > other._cparts

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, BasePath):
            return NotImplemented
        return self._cparts >= other._cparts


class AccessorPath(BasePath):
    """Path for object that can be read by accessor."""

    def __init__(self, accessor: LookupAccessor, *args: Any, **kwargs: Any):
        separator = kwargs.pop("separator", SEPARATOR)
        super().__init__(*args, separator=separator)
        self.accessor = accessor

        self._content_cached: Optional[Any] = None

    @classmethod
    def __from_parsed_parts(
        cls,
        accessor: LookupAccessor,
        parts: List[Hashable],
        separator: str = SEPARATOR,
    ) -> "AccessorPath":
        self = cls(accessor, separator=separator)
        self.parts = parts
        return self

    def __iter__(self) -> Iterator["AccessorPath"]:
        return self.iter()

    def __getitem__(self, key: Hashable) -> Any:
        with self.open() as d:
            return d[key]

    def __contains__(self, key: Hashable) -> bool:
        with self.open() as d:
            return key in d

    def __len__(self) -> int:
        return self.accessor.len(self.parts)

    def keys(self) -> Any:
        return self.accessor.keys(self.parts)

    def getkey(self, key: Hashable, default: Any = None) -> Any:
        """Return the value for key if key is in the path, else default."""
        with self.open() as d:
            try:
                return d[key]
            except KeyError:
                return default

    @contextmanager
    def open(self) -> Any:
        """Open the path."""
        # Cached path content
        if self._content_cached is None:
            with self._open() as content:
                self._content_cached = content
                yield self._content_cached
        else:
            yield self._content_cached

    def _open(self) -> Any:
        return self.accessor.open(self.parts)

    def iter(self) -> Iterator["AccessorPath"]:
        """Iterate over all child paths."""
        for idx in range(self.accessor.len(self.parts)):
            yield self._make_child_relpath(idx)

    def iteritems(self) -> Iterator[Tuple[Any, "AccessorPath"]]:
        """Return path's items."""
        return self.items()

    def items(self) -> Iterator[Tuple[Any, "AccessorPath"]]:
        """Return path's items."""
        for key in self.accessor.keys(self.parts):
            yield key, self._make_child_relpath(key)

    def content(self) -> Any:
        """Return content of the path."""
        with self.open() as d:
            return d

    def get(self, key: Hashable, default: Any = None) -> Any:
        """Return the child path for key if key is in the path, else default."""
        if key in self:
            return self.__truediv__(key)
        return default

    def _make_child(self, args: List[Any]) -> "AccessorPath":
        parts = parse_args(args, self.separator)
        parts_joined = self.parts + parts
        return self.__from_parsed_parts(
            self.accessor, parts_joined, self.separator
        )

    def _make_child_relpath(self, part: Hashable) -> "AccessorPath":
        # This is an optimization used for dir walking.  `part` must be
        # a single part relative to this path.
        parts = self.parts + [part]
        return self.__from_parsed_parts(self.accessor, parts, self.separator)


class LookupPath(AccessorPath):
    """Path for object that supports __getitem__ lookups."""

    def __init__(
        self, lookup: Mapping[Hashable, Any], *args: Any, **kwargs: Any
    ):
        accessor = LookupAccessor(lookup)
        return super().__init__(accessor, *args, **kwargs)
