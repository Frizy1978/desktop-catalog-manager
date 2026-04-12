from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

import requests


class WooCommerceClientError(RuntimeError):
    def __init__(self, user_message: str, *, technical_message: str | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_message = technical_message or user_message


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WooCommerceClientConfig:
    base_url: str
    consumer_key: str
    consumer_secret: str
    timeout_seconds: int = 20
    verify_ssl: bool = True
    api_path: str = "wp-json/wc/v3"


class WooCommerceClient:
    def __init__(self, config: WooCommerceClientConfig) -> None:
        self._config = config
        self._base_endpoint = (
            f"{config.base_url.rstrip('/')}/{config.api_path.strip('/')}"
        )

    def fetch_categories(
        self,
        page_callback: Callable[[int, int | None], None] | None = None,
    ) -> list[dict[str, Any]]:
        return self._get_paginated("products/categories", page_callback=page_callback)

    def fetch_products(
        self,
        page_callback: Callable[[int, int | None], None] | None = None,
    ) -> list[dict[str, Any]]:
        return self._get_paginated("products", page_callback=page_callback)

    def _get_paginated(
        self,
        resource: str,
        page_callback: Callable[[int, int | None], None] | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        while True:
            try:
                response = requests.get(
                    f"{self._base_endpoint}/{resource.strip('/')}",
                    params={
                        "consumer_key": self._config.consumer_key,
                        "consumer_secret": self._config.consumer_secret,
                        "per_page": per_page,
                        "page": page,
                    },
                    timeout=self._config.timeout_seconds,
                    verify=self._config.verify_ssl,
                )
            except requests.Timeout as exc:
                logger.exception(
                    "WooCommerce timeout for resource='%s', page=%s",
                    resource,
                    page,
                )
                raise WooCommerceClientError(
                    "Таймаут при подключении к WooCommerce. Проверьте доступность сайта и повторите попытку.",
                    technical_message=f"timeout: {exc}",
                ) from exc
            except requests.ConnectionError as exc:
                logger.exception(
                    "WooCommerce connection failed for resource='%s', page=%s",
                    resource,
                    page,
                )
                raise WooCommerceClientError(
                    "Не удалось подключиться к WooCommerce. Проверьте URL, интернет и SSL-настройки.",
                    technical_message=f"connection_error: {exc}",
                ) from exc
            except requests.RequestException as exc:
                logger.exception(
                    "WooCommerce request failed for resource='%s', page=%s",
                    resource,
                    page,
                )
                raise WooCommerceClientError(
                    "Ошибка HTTP-запроса к WooCommerce. Повторите позже.",
                    technical_message=f"request_error for '{resource}': {exc}",
                ) from exc
            if response.status_code >= 400:
                status = int(response.status_code)
                error_text = response.text[:300]
                logger.error(
                    "WooCommerce API error for resource='%s', page=%s: %s %s",
                    resource,
                    page,
                    status,
                    error_text,
                )
                if status in {401, 403}:
                    user_message = (
                        "Ошибка авторизации WooCommerce. Проверьте Consumer Key и Consumer Secret."
                    )
                elif status == 404:
                    user_message = (
                        "API WooCommerce не найден по указанному адресу. Проверьте FISHOLHA_WC_BASE_URL."
                    )
                elif status >= 500:
                    user_message = (
                        "Сервер WooCommerce временно недоступен (ошибка 5xx). Повторите позже."
                    )
                else:
                    user_message = f"WooCommerce вернул HTTP {status}."
                raise WooCommerceClientError(
                    user_message,
                    technical_message=f"http_{status}: {error_text}",
                )

            try:
                data = response.json()
            except ValueError as exc:
                logger.exception(
                    "WooCommerce returned invalid JSON for resource='%s', page=%s",
                    resource,
                    page,
                )
                raise WooCommerceClientError(
                    "WooCommerce вернул некорректный ответ (JSON).",
                    technical_message=f"invalid_json: {exc}",
                ) from exc
            if not isinstance(data, list):
                logger.error(
                    "Unexpected WooCommerce payload type for resource='%s': %s",
                    resource,
                    type(data),
                )
                raise WooCommerceClientError(
                    "WooCommerce вернул неожиданный формат данных.",
                    technical_message=f"unexpected_payload for {resource}: {type(data)}",
                )

            items.extend(data)

            total_pages: int | None = None
            total_pages_header = response.headers.get("X-WP-TotalPages")
            if total_pages_header:
                total_pages = int(total_pages_header)
            if page_callback is not None:
                page_callback(page, total_pages)
            if total_pages is not None:
                if page >= total_pages:
                    break
            if len(data) < per_page:
                break
            page += 1

        return items
