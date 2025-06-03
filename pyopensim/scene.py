"""Simple scene graph for rendering placeholder objects."""

from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass
class ObjectState:
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]

class Scene:
    def __init__(self):
        self.objects: Dict[str, ObjectState] = {}

    def update_object(self, obj_id: str, pos, rot=(0,0,0)):
        self.objects[obj_id] = ObjectState(pos, rot)

    def remove_object(self, obj_id: str):
        self.objects.pop(obj_id, None)
