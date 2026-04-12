from enum import StrEnum


class SyncStatus(StrEnum):
    SYNCED = "synced"
    MODIFIED_LOCAL = "modified_local"
    NEW_LOCAL = "new_local"
    PUBLISH_PENDING = "publish_pending"
    PUBLISH_ERROR = "publish_error"
    IMPORTED = "imported"
    ARCHIVED = "archived"


class PublishTarget(StrEnum):
    WOOCOMMERCE = "wc"
    YANDEX = "yandex"
    FUTURE = "future"
