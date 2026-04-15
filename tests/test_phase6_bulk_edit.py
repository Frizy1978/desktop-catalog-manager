from __future__ import annotations

from pathlib import Path
from decimal import Decimal

from app.db.models import Category, Product, ProductCategoryLink
from app.db.session import SqlAlchemyDatabase
from app.repositories.catalog_repository import CatalogRepository
from app.services.catalog_service import CatalogService


def _make_database(tmp_path: Path) -> SqlAlchemyDatabase:
    database = SqlAlchemyDatabase(tmp_path / "catalog.db")
    database.initialize()
    return database


def test_bulk_update_product_price_unit_updates_selected_products_only(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        synced_product = Product(
            name="Форель",
            slug="forel",
            sku="SKU-1",
            price_unit="кг",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        new_local_product = Product(
            name="Сёмга",
            slug="semga",
            sku="SKU-2",
            price_unit=None,
            sync_status="new_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        untouched_product = Product(
            name="Креветки",
            slug="krevetki",
            sku="SKU-3",
            price_unit="уп.",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add_all([synced_product, new_local_product, untouched_product])
        session.flush()

        synced_product_id = int(synced_product.id)
        new_local_product_id = int(new_local_product.id)
        untouched_product_id = int(untouched_product.id)

    updated_count = service.bulk_update_product_price_unit(
        product_ids=[synced_product_id, new_local_product_id, synced_product_id],
        price_unit="шт",
    )

    assert updated_count == 2

    with database.session_scope() as session:
        refreshed_synced_product = session.get(Product, synced_product_id)
        refreshed_new_local_product = session.get(Product, new_local_product_id)
        refreshed_untouched_product = session.get(Product, untouched_product_id)

        assert refreshed_synced_product is not None
        assert refreshed_new_local_product is not None
        assert refreshed_untouched_product is not None

        assert refreshed_synced_product.price_unit == "шт"
        assert refreshed_synced_product.sync_status == "modified_local"
        assert refreshed_new_local_product.price_unit == "шт"
        assert refreshed_new_local_product.sync_status == "new_local"
        assert refreshed_untouched_product.price_unit == "уп."
        assert refreshed_untouched_product.sync_status == "synced"


def test_bulk_archive_products_archives_selected_products_only(tmp_path: Path) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        remote_product = Product(
            name="Икра",
            slug="ikra",
            sku="SKU-4",
            sync_status="synced",
            external_wc_id=401,
            published_state="publish",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        local_product = Product(
            name="Филе трески",
            slug="file-treski",
            sku="SKU-5",
            sync_status="new_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        untouched_product = Product(
            name="Минтай",
            slug="mintay",
            sku="SKU-6",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add_all([remote_product, local_product, untouched_product])
        session.flush()

        remote_product_id = int(remote_product.id)
        local_product_id = int(local_product.id)
        untouched_product_id = int(untouched_product.id)

    archived_count = service.bulk_archive_products(
        product_ids=[remote_product_id, local_product_id]
    )

    assert archived_count == 2

    with database.session_scope() as session:
        refreshed_remote_product = session.get(Product, remote_product_id)
        refreshed_local_product = session.get(Product, local_product_id)
        refreshed_untouched_product = session.get(Product, untouched_product_id)

        assert refreshed_remote_product is not None
        assert refreshed_local_product is not None
        assert refreshed_untouched_product is not None

        assert refreshed_remote_product.is_archived is True
        assert refreshed_remote_product.sync_status == "archived"
        assert refreshed_local_product.is_archived is True
        assert refreshed_local_product.sync_status == "new_local"
        assert refreshed_untouched_product.is_archived is False
        assert refreshed_untouched_product.sync_status == "modified_local"


def test_bulk_update_product_price_updates_selected_products_only(tmp_path: Path) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        synced_product = Product(
            name="Палтус",
            slug="paltus",
            sku="SKU-7",
            price=Decimal("100.00"),
            regular_price=Decimal("100.00"),
            sale_price=Decimal("90.00"),
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        new_local_product = Product(
            name="Судак",
            slug="sudak",
            sku="SKU-8",
            price=Decimal("200.00"),
            regular_price=Decimal("200.00"),
            sale_price=None,
            sync_status="new_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        untouched_product = Product(
            name="Навага",
            slug="navaga",
            sku="SKU-9",
            price=Decimal("300.00"),
            regular_price=Decimal("300.00"),
            sale_price=None,
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add_all([synced_product, new_local_product, untouched_product])
        session.flush()

        synced_product_id = int(synced_product.id)
        new_local_product_id = int(new_local_product.id)
        untouched_product_id = int(untouched_product.id)

    updated_count = service.bulk_update_product_price(
        product_ids=[synced_product_id, new_local_product_id],
        price="1290.50",
    )

    assert updated_count == 2

    with database.session_scope() as session:
        refreshed_synced_product = session.get(Product, synced_product_id)
        refreshed_new_local_product = session.get(Product, new_local_product_id)
        refreshed_untouched_product = session.get(Product, untouched_product_id)

        assert refreshed_synced_product is not None
        assert refreshed_new_local_product is not None
        assert refreshed_untouched_product is not None

        assert refreshed_synced_product.price == Decimal("1290.50")
        assert refreshed_synced_product.regular_price == Decimal("1290.50")
        assert refreshed_synced_product.sale_price is None
        assert refreshed_synced_product.sync_status == "modified_local"

        assert refreshed_new_local_product.price == Decimal("1290.50")
        assert refreshed_new_local_product.regular_price == Decimal("1290.50")
        assert refreshed_new_local_product.sale_price is None
        assert refreshed_new_local_product.sync_status == "new_local"

        assert refreshed_untouched_product.price == Decimal("300.00")
        assert refreshed_untouched_product.sync_status == "synced"


def test_bulk_replace_product_category_updates_selected_products_only(tmp_path: Path) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        old_category = Category(
            name="Старая категория",
            slug="old-category",
            sync_status="synced",
            is_archived=False,
        )
        new_category = Category(
            name="Новая категория",
            slug="new-category",
            sync_status="synced",
            is_archived=False,
        )
        untouched_category = Category(
            name="Без изменений",
            slug="untouched-category",
            sync_status="synced",
            is_archived=False,
        )
        session.add_all([old_category, new_category, untouched_category])
        session.flush()

        selected_product = Product(
            name="Кальмар",
            slug="kalmar",
            sku="SKU-10",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        second_selected_product = Product(
            name="Окунь",
            slug="okun",
            sku="SKU-11",
            sync_status="new_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        untouched_product = Product(
            name="Щука",
            slug="shuka",
            sku="SKU-12",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add_all([selected_product, second_selected_product, untouched_product])
        session.flush()

        session.add_all(
            [
                ProductCategoryLink(
                    product_id=int(selected_product.id),
                    category_id=int(old_category.id),
                ),
                ProductCategoryLink(
                    product_id=int(second_selected_product.id),
                    category_id=int(old_category.id),
                ),
                ProductCategoryLink(
                    product_id=int(untouched_product.id),
                    category_id=int(untouched_category.id),
                ),
            ]
        )

        selected_product_id = int(selected_product.id)
        second_selected_product_id = int(second_selected_product.id)
        untouched_product_id = int(untouched_product.id)
        new_category_id = int(new_category.id)

    updated_count = service.bulk_replace_product_category(
        product_ids=[selected_product_id, second_selected_product_id],
        category_id=new_category_id,
    )

    assert updated_count == 2

    with database.session_scope() as session:
        refreshed_selected_product = session.get(Product, selected_product_id)
        refreshed_second_selected_product = session.get(Product, second_selected_product_id)
        refreshed_untouched_product = session.get(Product, untouched_product_id)

        selected_links = session.query(ProductCategoryLink).filter_by(
            product_id=selected_product_id
        ).all()
        second_selected_links = session.query(ProductCategoryLink).filter_by(
            product_id=second_selected_product_id
        ).all()
        untouched_links = session.query(ProductCategoryLink).filter_by(
            product_id=untouched_product_id
        ).all()

        assert refreshed_selected_product is not None
        assert refreshed_second_selected_product is not None
        assert refreshed_untouched_product is not None

        assert [int(link.category_id) for link in selected_links] == [new_category_id]
        assert [int(link.category_id) for link in second_selected_links] == [new_category_id]
        assert len(untouched_links) == 1

        assert refreshed_selected_product.sync_status == "modified_local"
        assert refreshed_second_selected_product.sync_status == "new_local"
        assert refreshed_untouched_product.sync_status == "modified_local"


def test_bulk_update_product_published_state_updates_selected_products_only(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        synced_product = Product(
            name="Треска",
            slug="treska",
            sku="SKU-13",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        new_local_product = Product(
            name="Пикша",
            slug="piksha",
            sku="SKU-14",
            sync_status="new_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        untouched_product = Product(
            name="Камбала",
            slug="kambala",
            sku="SKU-15",
            sync_status="synced",
            published_state="private",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add_all([synced_product, new_local_product, untouched_product])
        session.flush()

        synced_product_id = int(synced_product.id)
        new_local_product_id = int(new_local_product.id)
        untouched_product_id = int(untouched_product.id)

    updated_count = service.bulk_update_product_published_state(
        product_ids=[synced_product_id, new_local_product_id],
        published_state="publish",
    )

    assert updated_count == 2

    with database.session_scope() as session:
        refreshed_synced_product = session.get(Product, synced_product_id)
        refreshed_new_local_product = session.get(Product, new_local_product_id)
        refreshed_untouched_product = session.get(Product, untouched_product_id)

        assert refreshed_synced_product is not None
        assert refreshed_new_local_product is not None
        assert refreshed_untouched_product is not None

        assert refreshed_synced_product.published_state == "publish"
        assert refreshed_synced_product.sync_status == "modified_local"
        assert refreshed_new_local_product.published_state == "publish"
        assert refreshed_new_local_product.sync_status == "new_local"
        assert refreshed_untouched_product.published_state == "private"
        assert refreshed_untouched_product.sync_status == "synced"


def test_bulk_update_product_visibility_updates_selected_products_only(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        synced_product = Product(
            name="Сайра",
            slug="saira",
            sku="SKU-16",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        new_local_product = Product(
            name="Кета",
            slug="keta",
            sku="SKU-17",
            sync_status="new_local",
            published_state="draft",
            visibility="search",
            is_featured=False,
            is_archived=False,
        )
        untouched_product = Product(
            name="Ставрида",
            slug="stavrida",
            sku="SKU-18",
            sync_status="modified_local",
            published_state="draft",
            visibility="catalog",
            is_featured=False,
            is_archived=False,
        )
        session.add_all([synced_product, new_local_product, untouched_product])
        session.flush()

        synced_product_id = int(synced_product.id)
        new_local_product_id = int(new_local_product.id)
        untouched_product_id = int(untouched_product.id)

    updated_count = service.bulk_update_product_visibility(
        product_ids=[synced_product_id, new_local_product_id],
        visibility="hidden",
    )

    assert updated_count == 2

    with database.session_scope() as session:
        refreshed_synced_product = session.get(Product, synced_product_id)
        refreshed_new_local_product = session.get(Product, new_local_product_id)
        refreshed_untouched_product = session.get(Product, untouched_product_id)

        assert refreshed_synced_product is not None
        assert refreshed_new_local_product is not None
        assert refreshed_untouched_product is not None

        assert refreshed_synced_product.visibility == "hidden"
        assert refreshed_synced_product.sync_status == "modified_local"
        assert refreshed_new_local_product.visibility == "hidden"
        assert refreshed_new_local_product.sync_status == "new_local"
        assert refreshed_untouched_product.visibility == "catalog"
        assert refreshed_untouched_product.sync_status == "modified_local"


def test_bulk_update_product_featured_updates_selected_products_only(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        synced_product = Product(
            name="Корюшка",
            slug="koryushka",
            sku="SKU-19",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        new_local_product = Product(
            name="Нерка",
            slug="nerka",
            sku="SKU-20",
            sync_status="new_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        untouched_product = Product(
            name="Хек",
            slug="hek",
            sku="SKU-21",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add_all([synced_product, new_local_product, untouched_product])
        session.flush()

        synced_product_id = int(synced_product.id)
        new_local_product_id = int(new_local_product.id)
        untouched_product_id = int(untouched_product.id)

    updated_count = service.bulk_update_product_featured(
        product_ids=[synced_product_id, new_local_product_id],
        is_featured=True,
    )

    assert updated_count == 2

    with database.session_scope() as session:
        refreshed_synced_product = session.get(Product, synced_product_id)
        refreshed_new_local_product = session.get(Product, new_local_product_id)
        refreshed_untouched_product = session.get(Product, untouched_product_id)

        assert refreshed_synced_product is not None
        assert refreshed_new_local_product is not None
        assert refreshed_untouched_product is not None

        assert refreshed_synced_product.is_featured is True
        assert refreshed_synced_product.sync_status == "modified_local"
        assert refreshed_new_local_product.is_featured is True
        assert refreshed_new_local_product.sync_status == "new_local"
        assert refreshed_untouched_product.is_featured is False
        assert refreshed_untouched_product.sync_status == "synced"


def test_bulk_update_product_stock_status_updates_selected_products_only(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        synced_product = Product(
            name="Муксун",
            slug="muksun",
            sku="SKU-22",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            stock_status="instock",
            is_featured=False,
            is_archived=False,
        )
        new_local_product = Product(
            name="Камбала филе",
            slug="kambala-file",
            sku="SKU-23",
            sync_status="new_local",
            published_state="draft",
            visibility="visible",
            stock_status="instock",
            is_featured=False,
            is_archived=False,
        )
        untouched_product = Product(
            name="Чавыча",
            slug="chavycha",
            sku="SKU-24",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            stock_status="outofstock",
            is_featured=False,
            is_archived=False,
        )
        session.add_all([synced_product, new_local_product, untouched_product])
        session.flush()

        synced_product_id = int(synced_product.id)
        new_local_product_id = int(new_local_product.id)
        untouched_product_id = int(untouched_product.id)

    updated_count = service.bulk_update_product_stock_status(
        product_ids=[synced_product_id, new_local_product_id],
        stock_status="onbackorder",
    )

    assert updated_count == 2

    with database.session_scope() as session:
        refreshed_synced_product = session.get(Product, synced_product_id)
        refreshed_new_local_product = session.get(Product, new_local_product_id)
        refreshed_untouched_product = session.get(Product, untouched_product_id)

        assert refreshed_synced_product is not None
        assert refreshed_new_local_product is not None
        assert refreshed_untouched_product is not None

        assert refreshed_synced_product.stock_status == "onbackorder"
        assert refreshed_synced_product.sync_status == "modified_local"
        assert refreshed_new_local_product.stock_status == "onbackorder"
        assert refreshed_new_local_product.sync_status == "new_local"
        assert refreshed_untouched_product.stock_status == "outofstock"
        assert refreshed_untouched_product.sync_status == "synced"


def test_products_table_filters_by_sync_status_and_published_state(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        session.add_all(
            [
                Product(
                    name="Филе лосося",
                    slug="losos-file",
                    sku="FILTER-1",
                    sync_status="modified_local",
                    published_state="draft",
                    visibility="visible",
                    is_featured=False,
                    is_archived=False,
                ),
                Product(
                    name="Стейк тунца",
                    slug="tuna-steak",
                    sku="FILTER-2",
                    sync_status="new_local",
                    published_state="draft",
                    visibility="visible",
                    is_featured=False,
                    is_archived=False,
                ),
                Product(
                    name="Креветки",
                    slug="shrimps",
                    sku="FILTER-3",
                    sync_status="modified_local",
                    published_state="publish",
                    visibility="visible",
                    is_featured=False,
                    is_archived=False,
                ),
            ]
        )

    modified_draft_page = service.get_products_table_page(
        page=1,
        page_size=50,
        search_query="",
        sync_status_filter="modified_local",
        published_state_filter="draft",
    )

    assert modified_draft_page["total_items"] == 1
    assert [row["sku"] for row in modified_draft_page["items"]] == ["FILTER-1"]

    modified_any_state_page = service.get_products_table_page(
        page=1,
        page_size=50,
        search_query="",
        sync_status_filter="modified_local",
        published_state_filter="",
    )

    assert modified_any_state_page["total_items"] == 2
    assert sorted(row["sku"] for row in modified_any_state_page["items"]) == [
        "FILTER-1",
        "FILTER-3",
    ]


def test_products_table_selection_ids_follow_category_search_and_status_filters(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        fish_category = Category(
            name="Рыба",
            slug="fish",
            sync_status="synced",
            is_archived=False,
        )
        caviar_category = Category(
            name="Икра",
            slug="caviar",
            sync_status="synced",
            is_archived=False,
        )
        session.add_all([fish_category, caviar_category])
        session.flush()

        selected_first = Product(
            name="Филе семги",
            slug="semga-file",
            sku="SELECT-1",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        selected_second = Product(
            name="Стейк семги",
            slug="semga-steak",
            sku="SELECT-2",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        wrong_state = Product(
            name="Семга премиум",
            slug="semga-premium",
            sku="SELECT-3",
            sync_status="modified_local",
            published_state="publish",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        wrong_category = Product(
            name="Семга слабосоленая",
            slug="semga-salted",
            sku="SELECT-4",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        archived_match = Product(
            name="Семга архив",
            slug="semga-archive",
            sku="SELECT-5",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=True,
        )
        session.add_all(
            [
                selected_first,
                selected_second,
                wrong_state,
                wrong_category,
                archived_match,
            ]
        )
        session.flush()

        session.add_all(
            [
                ProductCategoryLink(
                    product_id=int(selected_first.id),
                    category_id=int(fish_category.id),
                ),
                ProductCategoryLink(
                    product_id=int(selected_second.id),
                    category_id=int(fish_category.id),
                ),
                ProductCategoryLink(
                    product_id=int(wrong_state.id),
                    category_id=int(fish_category.id),
                ),
                ProductCategoryLink(
                    product_id=int(wrong_category.id),
                    category_id=int(caviar_category.id),
                ),
                ProductCategoryLink(
                    product_id=int(archived_match.id),
                    category_id=int(fish_category.id),
                ),
            ]
        )

        fish_category_id = int(fish_category.id)
        expected_ids = sorted([int(selected_first.id), int(selected_second.id)])

    selection_ids = service.get_products_table_selection_ids(
        category_id=fish_category_id,
        search_query="семга",
        sync_status_filter="modified_local",
        published_state_filter="draft",
    )

    assert sorted(selection_ids) == expected_ids


def test_products_table_filters_by_visibility_and_featured_state(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        session.add_all(
            [
                Product(
                    name="Лосось филе",
                    slug="salmon-file",
                    sku="VIS-1",
                    sync_status="synced",
                    published_state="publish",
                    visibility="catalog",
                    is_featured=True,
                    is_archived=False,
                ),
                Product(
                    name="Лосось стейк",
                    slug="salmon-steak",
                    sku="VIS-2",
                    sync_status="synced",
                    published_state="publish",
                    visibility="catalog",
                    is_featured=False,
                    is_archived=False,
                ),
                Product(
                    name="Тунец",
                    slug="tuna",
                    sku="VIS-3",
                    sync_status="synced",
                    published_state="publish",
                    visibility="hidden",
                    is_featured=True,
                    is_archived=False,
                ),
            ]
        )

    filtered_page = service.get_products_table_page(
        page=1,
        page_size=50,
        visibility_filter="catalog",
        is_featured_filter="true",
    )

    assert filtered_page["total_items"] == 1
    assert [row["sku"] for row in filtered_page["items"]] == ["VIS-1"]


def test_products_table_filters_by_stock_status(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        session.add_all(
            [
                Product(
                    name="Треска",
                    slug="treska-stock",
                    sku="STOCK-1",
                    sync_status="synced",
                    published_state="publish",
                    visibility="visible",
                    stock_status="instock",
                    is_featured=False,
                    is_archived=False,
                ),
                Product(
                    name="Палтус",
                    slug="paltus-stock",
                    sku="STOCK-2",
                    sync_status="synced",
                    published_state="publish",
                    visibility="visible",
                    stock_status="outofstock",
                    is_featured=False,
                    is_archived=False,
                ),
                Product(
                    name="Сибас",
                    slug="sibas-stock",
                    sku="STOCK-3",
                    sync_status="synced",
                    published_state="publish",
                    visibility="visible",
                    stock_status="onbackorder",
                    is_featured=False,
                    is_archived=False,
                ),
            ]
        )

    filtered_page = service.get_products_table_page(
        page=1,
        page_size=50,
        stock_status_filter="outofstock",
    )

    assert filtered_page["total_items"] == 1
    assert [row["sku"] for row in filtered_page["items"]] == ["STOCK-2"]


def test_products_table_page_includes_wc_state_fields(
    tmp_path: Path,
) -> None:
    database = _make_database(tmp_path)
    service = CatalogService(repository=CatalogRepository(database=database))

    with database.session_scope() as session:
        session.add(
            Product(
                name="Палтус премиум",
                slug="paltus-premium",
                sku="STATE-1",
                sync_status="modified_local",
                published_state="private",
                visibility="catalog",
                stock_status="onbackorder",
                is_featured=True,
                is_archived=False,
            )
        )

    page = service.get_products_table_page(
        page=1,
        page_size=50,
    )

    assert page["total_items"] == 1
    assert page["items"][0]["sku"] == "STATE-1"
    assert page["items"][0]["status"] == "private"
    assert page["items"][0]["visibility"] == "catalog"
    assert page["items"][0]["is_featured"] is True
    assert page["items"][0]["stock_status"] == "onbackorder"
