"""Small OO wrapper around Blender objects.

This module is intentionally tiny and internal: it centralizes the handful of
operations this project performs frequently, while keeping an escape hatch to
raw bpy when needed.

Designed to run inside Blender's Python.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence

try:
    import bpy  # type: ignore
    import mathutils  # type: ignore
except Exception:  # pragma: no cover
    bpy = None  # type: ignore
    mathutils = None  # type: ignore


@dataclass(frozen=True)
class SceneObject:
    """Thin wrapper around a `bpy.types.Object`."""

    obj: Any

    @property
    def name(self) -> str:
        return self.obj.name

    def rename(self, name: str) -> "SceneObject":
        self.obj.name = name
        return self

    def set_location(self, xyz: Sequence[float]) -> "SceneObject":
        self.obj.location = xyz
        return self

    def set_scale(self, xyz: Sequence[float]) -> "SceneObject":
        self.obj.scale = xyz
        return self

    def set_rotation_euler(self, xyz_radians: Sequence[float]) -> "SceneObject":
        self.obj.rotation_euler = xyz_radians
        return self

    def set_pass_index(self, idx: int) -> "SceneObject":
        self.obj.pass_index = int(idx)
        return self

    def set_cp(self, key: str, value: Any) -> "SceneObject":
        self.obj[key] = value
        return self

    def get_cp(self, key: str, default: Any = None) -> Any:
        try:
            return self.obj[key]
        except Exception:
            return default

    def del_cp(self, key: str) -> "SceneObject":
        try:
            del self.obj[key]
        except Exception:
            pass
        return self

    def clear_materials(self) -> "SceneObject":
        data = getattr(self.obj, "data", None)
        mats = getattr(data, "materials", None)
        if mats is not None:
            mats.clear()
        return self

    def add_material(self, mat: Any) -> "SceneObject":
        data = getattr(self.obj, "data", None)
        mats = getattr(data, "materials", None)
        if mats is not None:
            mats.append(mat)
        return self

    def hide(self, hidden: bool = True) -> "SceneObject":
        # hide_set controls viewport; hide_render controls render.
        try:
            self.obj.hide_set(hidden)
        except Exception:
            # Some datablocks not linked to view layer can raise.
            pass
        try:
            self.obj.hide_render = hidden
        except Exception:
            pass
        return self

    def reset_for_pool(self, delete_custom_properties: Optional[Iterable[str]] = None) -> "SceneObject":
        self.clear_materials()
        try:
            self.obj.location = (0.0, 0.0, 0.0)
            self.obj.rotation_euler = (0.0, 0.0, 0.0)
            self.obj.scale = (1.0, 1.0, 1.0)
        except Exception:
            pass
        self.set_pass_index(0)
        if delete_custom_properties:
            for k in delete_custom_properties:
                self.del_cp(k)
        self.hide(True)
        return self
