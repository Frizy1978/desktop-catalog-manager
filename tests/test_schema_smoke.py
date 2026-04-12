from app.core.database import SCHEMA_SQL


def test_schema_contains_required_tables() -> None:
    required = [
        "roles",
        "users",
        "categories",
        "products",
        "product_images",
        "product_image_versions",
        "sync_runs",
        "publish_jobs",
    ]
    for table_name in required:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in SCHEMA_SQL
