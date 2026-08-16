"""Load assets from .blend files without relying on bpy operators.

Using `bpy.data.libraries.load()` avoids many context/operator pitfalls and is
less sensitive to UI state.

Designed to run inside Blender's Python.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

try:
    import bpy  # type: ignore
except Exception:  # pragma: no cover
    bpy = None  # type: ignore


@dataclass
class BlendAssetLibrary:
    """Utility for importing datablocks from .blend files."""

    link: bool = False

    def load_objects(self, blend_path: str, object_names: Iterable[str]) -> list[Any]:
        if bpy is None:
            raise RuntimeError("BlendAssetLibrary must run inside Blender (bpy unavailable)")

        object_names = list(object_names)
        with bpy.data.libraries.load(blend_path, link=self.link) as (data_from, data_to):
            available = set(getattr(data_from, "objects", []) or [])
            to_load = [n for n in object_names if n in available]
            data_to.objects = to_load

        # data_to.objects only holds the actual loaded datablocks once the 'with' block
        # has exited; inside it, it's still just the list of requested names.
        loaded = list(data_to.objects)
        return [o for o in loaded if o is not None]

    def load_node_groups(self, blend_path: str, group_names: Iterable[str]) -> list[Any]:
        if bpy is None:
            raise RuntimeError("BlendAssetLibrary must run inside Blender (bpy unavailable)")

        group_names = list(group_names)
        with bpy.data.libraries.load(blend_path, link=self.link) as (data_from, data_to):
            available = set(getattr(data_from, "node_groups", []) or [])
            to_load = [n for n in group_names if n in available]
            data_to.node_groups = to_load

        # data_to.node_groups only holds the actual loaded datablocks once the 'with' block
        # has exited; inside it, it's still just the list of requested names.
        loaded = list(data_to.node_groups)
        return [g for g in loaded if g is not None]


def ensure_linked(obj: Any, *, collection: Optional[Any] = None) -> None:
    """Ensure `obj` is linked to a collection (defaults to current scene collection)."""

    if bpy is None:
        raise RuntimeError("ensure_linked must run inside Blender (bpy unavailable)")

    if collection is None:
        collection = bpy.context.scene.collection

    # Already linked?
    try:
        if obj.name in collection.objects:
            return
    except Exception:
        pass

    collection.objects.link(obj)
