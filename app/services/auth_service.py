from __future__ import annotations

from app.core.security import hash_password, verify_password
from app.models.user import AuthenticatedUser
from app.repositories.auth_repository import AuthRepository


class AuthService:
    def __init__(
        self,
        auth_repository: AuthRepository,
        default_admin_username: str,
        default_admin_password: str,
    ) -> None:
        self._auth_repository = auth_repository
        self._default_admin_username = default_admin_username
        self._default_admin_password = default_admin_password

    def ensure_bootstrap_user(self) -> None:
        if self._auth_repository.count_users() > 0:
            return

        admin_role_id = self._auth_repository.ensure_role(
            name="admin",
            description="Default local administrator role",
        )
        salt_hex, hash_hex = hash_password(self._default_admin_password)
        self._auth_repository.create_user(
            username=self._default_admin_username,
            password_hash=hash_hex,
            password_salt=salt_hex,
            role_id=admin_role_id,
        )

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        credentials = self._auth_repository.get_user_credentials(username=username)
        if not credentials:
            return None

        if not verify_password(
            password=password,
            salt_hex=credentials["password_salt"],
            expected_hash_hex=credentials["password_hash"],
        ):
            return None

        user_id = int(credentials["id"])
        self._auth_repository.update_last_login(user_id=user_id)
        return AuthenticatedUser(
            id=user_id,
            username=str(credentials["username"]),
            role=str(credentials["role_name"]),
        )
