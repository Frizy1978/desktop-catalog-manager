from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)


class WooCommerceClientError(RuntimeError):
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

    def create_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json_dict("POST", "products/categories", payload=payload)

    def update_category(self, wc_category_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json_dict(
            "PUT",
            f"products/categories/{int(wc_category_id)}",
            payload=payload,
        )

    def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json_dict("POST", "products", payload=payload)

    def update_product(self, wc_product_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json_dict(
            "PUT",
            f"products/{int(wc_product_id)}",
            payload=payload,
        )

    def _get_paginated(
        self,
        resource: str,
        page_callback: Callable[[int, int | None], None] | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        while True:
            response = self._request(
                "GET",
                resource,
                params={
                    "per_page": per_page,
                    "page": page,
                },
            )
            data = self._parse_json_list(response, resource=resource, page=page)
            items.extend(data)

            total_pages: int | None = None
            total_pages_header = response.headers.get("X-WP-TotalPages")
            if total_pages_header:
                try:
                    total_pages = int(total_pages_header)
                except ValueError:
                    total_pages = None

            if page_callback is not None:
                page_callback(page, total_pages)

            if total_pages is not None:
                if page >= total_pages:
                    break
            if len(data) < per_page:
                break
            page += 1

        return items

    def _request_json_dict(
        self,
        method: str,
        resource: str,
        *,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response = self._request(method, resource, payload=payload)
        try:
            data = response.json()
        except ValueError as exc:
            logger.exception(
                "WooCommerce returned invalid JSON for method=%s resource=%s",
                method,
                resource,
            )
            raise WooCommerceClientError(
                "WooCommerce вернул некорректный JSON-ответ.",
                technical_message=f"invalid_json: {exc}",
            ) from exc

        if not isinstance(data, dict):
            logger.error(
                "Unexpected WooCommerce payload type for method=%s resource=%s type=%s",
                method,
                resource,
                type(data),
            )
            raise WooCommerceClientError(
                "WooCommerce вернул неожиданный формат данных.",
                technical_message=f"unexpected_payload: {type(data)}",
            )
        return data

    def _request(
        self,
        method: str,
        resource: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> requests.Response:
        request_params = {
            "consumer_key": self._config.consumer_key,
            "consumer_secret": self._config.consumer_secret,
        }
        if params:
            request_params.update(params)

        url = f"{self._base_endpoint}/{resource.strip('/')}"
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                params=request_params,
                json=payload,
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_ssl,
            )
        except requests.Timeout as exc:
            logger.exception(
                "WooCommerce timeout for method=%s resource=%s",
                method,
                resource,
            )
            raise WooCommerceClientError(
                "Таймаут при подключении к WooCommerce.",
                technical_message=f"timeout: {exc}",
            ) from exc
        except requests.ConnectionError as exc:
            logger.exception(
                "WooCommerce connection failed for method=%s resource=%s",
                method,
                resource,
            )
            raise WooCommerceClientError(
                "Не удалось подключиться к WooCommerce. Проверьте URL, интернет и SSL.",
                technical_message=f"connection_error: {exc}",
            ) from exc
        except requests.RequestException as exc:
            logger.exception(
                "WooCommerce request failed for method=%s resource=%s",
                method,
                resource,
            )
            raise WooCommerceClientError(
                "Ошибка HTTP-запроса к WooCommerce.",
                technical_message=f"request_error: {exc}",
            ) from exc

        if response.status_code >= 400:
            status = int(response.status_code)
            error_text = response.text[:500]
            logger.error(
                "WooCommerce API error: method=%s resource=%s status=%s body=%s",
                method,
                resource,
                status,
                error_text,
            )
            raise WooCommerceClientError(
                self._status_user_message(status),
                technical_message=f"http_{status}: {error_text}",
                status_code=status,
            )
        return response

    def _parse_json_list(
        self,
        response: requests.Response,
        *,
        resource: str,
        page: int,
    ) -> list[dict[str, Any]]:
        try:
            data = response.json()
        except ValueError as exc:
            logger.exception(
                "WooCommerce returned invalid JSON for resource=%s page=%s",
                resource,
                page,
            )
            raise WooCommerceClientError(
                "WooCommerce вернул некорректный JSON-ответ.",
                technical_message=f"invalid_json: {exc}",
            ) from exc

        if not isinstance(data, list):
            logger.error(
                "Unexpected WooCommerce payload type for resource=%s page=%s type=%s",
                resource,
                page,
                type(data),
            )
            raise WooCommerceClientError(
                "WooCommerce вернул неожиданный формат данных.",
                technical_message=f"unexpected_payload: {type(data)}",
            )

        return [item for item in data if isinstance(item, dict)]

    def _status_user_message(self, status: int) -> str:
        if status in {401, 403}:
            return (
                "Ошибка авторизации WooCommerce. Проверьте Consumer Key и Consumer Secret."
            )
        if status == 404:
            return (
                "API WooCommerce не найден по указанному адресу. Проверьте FISHOLHA_WC_BASE_URL."
            )
        if status >= 500:
            return "Сервер WooCommerce временно недоступен (ошибка 5xx)."
        return f"WooCommerce вернул HTTP {status}."
