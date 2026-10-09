from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Teacher:
    id: str
    name: str
