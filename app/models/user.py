from dataclasses import dataclass


@dataclass(slots=True)
class AuthenticatedUser:
    id: int
    username: str
    role: str
