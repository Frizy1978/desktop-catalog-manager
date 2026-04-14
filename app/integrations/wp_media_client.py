from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class WordPressMediaClientError(RuntimeError):
    def __init__(
        self,
        user_message: str,
        *,
        technical_message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_message = technical_message or user_message
        self.status_code = status_code


@dataclass(slots=True)
class WordPressMediaClientConfig:
    base_url: str
    username: str
    application_password: str
    timeout_seconds: int = 20
    verify_ssl: bool = True


class WordPressMediaClient:
    def __init__(self, config: WordPressMediaClientConfig) -> None:
        self._config = config
        self._base_url = config.base_url.rstrip("/")
        self._media_endpoint = f"{self._base_url}/wp-json/wp/v2/media"
        self._validate_config()

    def upload_media(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise WordPressMediaClientError(
                "Файл изображения не найден для загрузки в WordPress.",
                technical_message=f"file_not_found: {path}",
            )

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        headers = {
            "Content-Disposition": f'attachment; filename="{path.name}"',
            "Content-Type": content_type,
        }

        try:
            with path.open("rb") as file_handle:
                response = requests.post(
                    self._media_endpoint,
                    data=file_handle,
                    headers=headers,
                    auth=(
                        self._config.username,
                        self._config.application_password,
                    ),
                    timeout=self._config.timeout_seconds,
                    verify=self._config.verify_ssl,
                )
        except requests.Timeout as exc:
            logger.exception("WordPress media upload timeout: path=%s", path)
            raise WordPressMediaClientError(
                "Таймаут загрузки изображения в WordPress.",
                technical_message=f"timeout: {exc}",
            ) from exc
        except requests.ConnectionError as exc:
            logger.exception("WordPress media upload connection error: path=%s", path)
            raise WordPressMediaClientError(
                "Ошибка соединения при загрузке изображения в WordPress.",
                technical_message=f"connection_error: {exc}",
            ) from exc
        except requests.RequestException as exc:
            logger.exception("WordPress media upload request error: path=%s", path)
            raise WordPressMediaClientError(
                "HTTP-ошибка при загрузке изображения в WordPress.",
                technical_message=f"request_error: {exc}",
            ) from exc

        if response.status_code >= 400:
            self._raise_http_error(response=response, path=path)

        try:
            payload = response.json()
        except ValueError as exc:
            logger.exception("WordPress media upload invalid JSON: path=%s", path)
            raise WordPressMediaClientError(
                "WordPress вернул некорректный JSON при загрузке изображения.",
                technical_message=f"invalid_json: {exc}",
            ) from exc

        if not isinstance(payload, dict):
            raise WordPressMediaClientError(
                "WordPress вернул неожиданный формат ответа при загрузке изображения.",
                technical_message=f"unexpected_payload_type: {type(payload)}",
            )
        return payload

    def _raise_http_error(self, *, response: requests.Response, path: Path) -> None:
        status = int(response.status_code)
        error_text = response.text[:500]
        parsed_code = ""
        parsed_message = ""
        try:
            data = response.json()
            if isinstance(data, dict):
                parsed_code = str(data.get("code") or "").strip()
                parsed_message = str(data.get("message") or "").strip()
        except ValueError:
            parsed_code = ""
            parsed_message = ""

        logger.error(
            "WordPress media upload failed: status=%s code=%s message=%s path=%s body=%s",
            status,
            parsed_code,
            parsed_message,
            path,
            error_text,
        )

        if parsed_code == "rest_cannot_create" or "upload_files" in error_text.lower():
            raise WordPressMediaClientError(
                "Нет прав на загрузку media в WordPress. Проверьте пользователя и право upload_files.",
                technical_message=(
                    f"http_{status} rest_cannot_create: {parsed_message or error_text}"
                ),
                status_code=status,
            )
        if status in {401, 403}:
            raise WordPressMediaClientError(
                "Ошибка авторизации WordPress media. Проверьте wp_username и wp_application_password.",
                technical_message=f"http_{status}: {parsed_code} {parsed_message or error_text}",
                status_code=status,
            )
        if status == 404:
            raise WordPressMediaClientError(
                "Эндпоинт WordPress media не найден. Проверьте wp_base_url и REST API.",
                technical_message=f"http_404: {parsed_code} {parsed_message or error_text}",
                status_code=status,
            )
        if status >= 500:
            raise WordPressMediaClientError(
                "Сервер WordPress временно недоступен (ошибка 5xx).",
                technical_message=f"http_{status}: {parsed_code} {parsed_message or error_text}",
                status_code=status,
            )

        raise WordPressMediaClientError(
            f"WordPress media вернул HTTP {status}.",
            technical_message=f"http_{status}: {parsed_code} {parsed_message or error_text}",
            status_code=status,
        )

    def _validate_config(self) -> None:
        parsed = urlparse(self._base_url)
        if parsed.scheme.lower() != "https":
            raise WordPressMediaClientError(
                "Для загрузки media требуется HTTPS в wp_base_url.",
                technical_message=f"insecure_scheme: {self._base_url}",
            )
        if not self._config.username.strip():
            raise WordPressMediaClientError(
                "Не задан wp_username для загрузки media в WordPress.",
                technical_message="empty_wp_username",
            )
        if not self._config.application_password.strip():
            raise WordPressMediaClientError(
                "Не задан wp_application_password для загрузки media в WordPress.",
                technical_message="empty_wp_application_password",
            )
