from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.db.models import Category, Product, ProductCategoryLink
from app.db.session import SqlAlchemyDatabase
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.publish_job_repository import PublishJobRepository
from app.repositories.sync_run_repository import SyncRunRepository
from app.services.product_image_service import ProductImageService
from app.services.publish_service import PublishSelection, WooCommercePublishService
from app.repositories.product_image_repository import ProductImageRepository


class FakeWooCommerceClient:
    def __init__(self) -> None:
        self.created_categories: list[dict] = []
        self.updated_categories: list[tuple[int, dict]] = []
        self.created_products: list[dict] = []
        self.updated_products: list[tuple[int, dict]] = []
        self._next_category_id = 700
        self._next_product_id = 900

    def create_category(self, payload: dict) -> dict:
        self.created_categories.append(payload)
        self._next_category_id += 1
        return {"id": self._next_category_id}

    def update_category(self, wc_category_id: int, payload: dict) -> dict:
        self.updated_categories.append((wc_category_id, payload))
        return {"id": wc_category_id}

    def create_product(self, payload: dict) -> dict:
        self.created_products.append(payload)
        self._next_product_id += 1
        return {"id": self._next_product_id}

    def update_product(self, wc_product_id: int, payload: dict) -> dict:
        self.updated_products.append((wc_product_id, payload))
        return {"id": wc_product_id}


def _make_database(tmp_path: Path) -> SqlAlchemyDatabase:
    database = SqlAlchemyDatabase(tmp_path / "catalog.db")
    database.initialize()
    return database


def test_product_image_changes_mark_synced_product_as_modified_local(tmp_path: Path) -> None:
    database = _make_database(tmp_path)
    media_root = tmp_path / "media"
    service = ProductImageService(
        database=database,
        repository=ProductImageRepository(),
        product_repository=ProductRepository(),
        media_root=media_root,
    )

    with database.session_scope() as session:
        product = Product(
            name="Товар",
            slug="tovar",
            sync_status="synced",
            published_state="publish",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add(product)
        session.flush()
        product_id = int(product.id)

    source_image = tmp_path / "source.jpg"
    source_image.write_bytes(b"fake-image")

    service.add_local_image(product_id, str(source_image))

    with database.session_scope() as session:
        product = session.get(Product, product_id)
        assert product is not None
        assert product.sync_status == "modified_local"


def test_publish_service_can_publish_selected_scope_only(tmp_path: Path) -> None:
    database = _make_database(tmp_path)

    with database.session_scope() as session:
        selected_category = Category(
            name="Рыба",
            slug="ryba",
            sync_status="modified_local",
            is_archived=False,
        )
        skipped_category = Category(
            name="Икра",
            slug="ikra",
            sync_status="modified_local",
            is_archived=False,
            external_wc_id=300,
        )
        session.add_all([selected_category, skipped_category])
        session.flush()

        selected_product = Product(
            name="Форель",
            slug="forel",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=True,
            stock_status="outofstock",
            is_archived=False,
            price=Decimal("100.00"),
            regular_price=Decimal("100.00"),
        )
        skipped_product = Product(
            name="Сёмга",
            slug="semga",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
            external_wc_id=444,
            price=Decimal("200.00"),
            regular_price=Decimal("200.00"),
        )
        session.add_all([selected_product, skipped_product])
        session.flush()

        session.add_all(
            [
                ProductCategoryLink(
                    product_id=int(selected_product.id),
                    category_id=int(selected_category.id),
                ),
                ProductCategoryLink(
                    product_id=int(skipped_product.id),
                    category_id=int(skipped_category.id),
                ),
            ]
        )

        selected_category_id = int(selected_category.id)
        skipped_category_id = int(skipped_category.id)
        selected_product_id = int(selected_product.id)
        skipped_product_id = int(skipped_product.id)

    fake_client = FakeWooCommerceClient()
    service = WooCommercePublishService(
        database=database,
        category_repository=CategoryRepository(),
        product_repository=ProductRepository(),
        sync_run_repository=SyncRunRepository(database=database),
        publish_job_repository=PublishJobRepository(database=database),
        wc_client=fake_client,
        media_publish_service=None,
    )

    result = service.run_publish(
        selection=PublishSelection(
            category_ids=[selected_category_id],
            product_ids=[selected_product_id],
        )
    )

    assert result.success is True
    assert result.counters["categories_total"] == 1
    assert result.counters["products_total"] == 1
    assert len(fake_client.created_categories) == 1
    assert len(fake_client.created_products) == 1
    assert fake_client.created_products[0]["featured"] is True
    assert fake_client.created_products[0]["stock_status"] == "outofstock"
    assert fake_client.updated_categories == []
    assert fake_client.updated_products == []

    with database.session_scope() as session:
        refreshed_selected_category = session.get(Category, selected_category_id)
        refreshed_skipped_category = session.get(Category, skipped_category_id)
        refreshed_selected_product = session.get(Product, selected_product_id)
        refreshed_skipped_product = session.get(Product, skipped_product_id)

        assert refreshed_selected_category is not None
        assert refreshed_selected_product is not None
        assert refreshed_skipped_category is not None
        assert refreshed_skipped_product is not None

        assert refreshed_selected_category.sync_status == "synced"
        assert refreshed_selected_category.external_wc_id is not None
        assert refreshed_selected_product.sync_status == "synced"
        assert refreshed_selected_product.external_wc_id is not None

        assert refreshed_skipped_category.sync_status == "modified_local"
        assert refreshed_skipped_category.external_wc_id == 300
        assert refreshed_skipped_product.sync_status == "modified_local"
        assert refreshed_skipped_product.external_wc_id == 444


def test_publish_service_includes_required_unpublished_categories_for_selected_products(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)

    with database.session_scope() as session:
        parent_category = Category(
            name="Морепродукты",
            slug="moreprodukty",
            sync_status="new_local",
            is_archived=False,
        )
        session.add(parent_category)
        session.flush()

        child_category = Category(
            name="Креветки",
            slug="krevetki",
            parent_id=int(parent_category.id),
            sync_status="new_local",
            is_archived=False,
        )
        session.add(child_category)
        session.flush()

        product = Product(
            name="Тигровые креветки",
            slug="tigrovye-krevetki",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
            price=Decimal("350.00"),
            regular_price=Decimal("350.00"),
        )
        session.add(product)
        session.flush()

        session.add(
            ProductCategoryLink(
                product_id=int(product.id),
                category_id=int(child_category.id),
            )
        )

        parent_category_id = int(parent_category.id)
        child_category_id = int(child_category.id)
        product_id = int(product.id)

    fake_client = FakeWooCommerceClient()
    service = WooCommercePublishService(
        database=database,
        category_repository=CategoryRepository(),
        product_repository=ProductRepository(),
        sync_run_repository=SyncRunRepository(database=database),
        publish_job_repository=PublishJobRepository(database=database),
        wc_client=fake_client,
        media_publish_service=None,
    )

    result = service.run_publish(
        selection=PublishSelection(
            category_ids=[],
            product_ids=[product_id],
        )
    )

    assert result.success is True
    assert result.counters["categories_total"] == 2
    assert result.counters["products_total"] == 1
    assert len(fake_client.created_categories) == 2
    assert len(fake_client.created_products) == 1
    assert fake_client.created_categories[0]["name"] == "Морепродукты"
    assert fake_client.created_categories[0]["parent"] == 0
    assert fake_client.created_categories[1]["name"] == "Креветки"
    assert fake_client.created_categories[1]["parent"] == 701

    with database.session_scope() as session:
        refreshed_parent_category = session.get(Category, parent_category_id)
        refreshed_child_category = session.get(Category, child_category_id)
        refreshed_product = session.get(Product, product_id)

        assert refreshed_parent_category is not None
        assert refreshed_child_category is not None
        assert refreshed_product is not None

        assert refreshed_parent_category.sync_status == "synced"
        assert refreshed_parent_category.external_wc_id == 701
        assert refreshed_child_category.sync_status == "synced"
        assert refreshed_child_category.external_wc_id == 702
        assert refreshed_product.sync_status == "synced"
        assert refreshed_product.external_wc_id == 901


def test_publish_service_includes_parent_categories_for_selected_category_scope(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)

    with database.session_scope() as session:
        parent_category = Category(
            name="Рыба",
            slug="ryba",
            sync_status="modified_local",
            is_archived=False,
        )
        session.add(parent_category)
        session.flush()

        child_category = Category(
            name="Филе",
            slug="file",
            parent_id=int(parent_category.id),
            sync_status="modified_local",
            is_archived=False,
        )
        session.add(child_category)
        session.flush()

        parent_category_id = int(parent_category.id)
        child_category_id = int(child_category.id)

    fake_client = FakeWooCommerceClient()
    service = WooCommercePublishService(
        database=database,
        category_repository=CategoryRepository(),
        product_repository=ProductRepository(),
        sync_run_repository=SyncRunRepository(database=database),
        publish_job_repository=PublishJobRepository(database=database),
        wc_client=fake_client,
        media_publish_service=None,
    )

    result = service.run_publish(
        selection=PublishSelection(
            category_ids=[child_category_id],
            product_ids=[],
        )
    )

    assert result.success is True
    assert result.counters["categories_total"] == 2
    assert result.counters["products_total"] == 0
    assert len(fake_client.created_categories) == 2
    assert fake_client.created_products == []
    assert fake_client.created_categories[0]["name"] == "Рыба"
    assert fake_client.created_categories[0]["parent"] == 0
    assert fake_client.created_categories[1]["name"] == "Филе"
    assert fake_client.created_categories[1]["parent"] == 701

    with database.session_scope() as session:
        refreshed_parent_category = session.get(Category, parent_category_id)
        refreshed_child_category = session.get(Category, child_category_id)

        assert refreshed_parent_category is not None
        assert refreshed_child_category is not None

        assert refreshed_parent_category.sync_status == "synced"
        assert refreshed_parent_category.external_wc_id == 701
        assert refreshed_child_category.sync_status == "synced"
        assert refreshed_child_category.external_wc_id == 702
