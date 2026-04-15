from app.db.models import Category, Product, ProductCategoryLink, ProductImage, SyncRun
from app.db.session import SqlAlchemyDatabase
from app.repositories.product_repository import ProductRepository


def _make_database(tmp_path) -> SqlAlchemyDatabase:
    database = SqlAlchemyDatabase(tmp_path / "catalog.db")
    database.initialize()
    return database


def test_phase2_model_table_names() -> None:
    assert Category.__tablename__ == "categories"
    assert Product.__tablename__ == "products"
    assert ProductImage.__tablename__ == "product_images"
    assert ProductCategoryLink.__tablename__ == "product_categories"
    assert SyncRun.__tablename__ == "sync_runs"


def test_product_image_has_local_path_column() -> None:
    assert "local_path" in ProductImage.__table__.c


def test_replace_images_from_wc_payload_reassigns_primary_without_unique_error(tmp_path) -> None:
    database = _make_database(tmp_path)
    repository = ProductRepository()

    with database.session_scope() as session:
        product = Product(
            name="Форель",
            slug="forel",
            sync_status="synced",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add(product)
        session.flush()

        first_image = ProductImage(
            product_id=int(product.id),
            original_path="https://example.com/1.jpg",
            local_path=None,
            source_type="wc_url",
            metadata_json=None,
            is_primary=True,
            sort_order=0,
        )
        second_image = ProductImage(
            product_id=int(product.id),
            original_path="https://example.com/2.jpg",
            local_path=None,
            source_type="wc_url",
            metadata_json=None,
            is_primary=False,
            sort_order=1,
        )
        session.add_all([first_image, second_image])
        session.flush()
        product_id = int(product.id)

        count = repository.replace_images_from_wc_payload(
            session,
            product_id=product_id,
            images=[
                {"src": "https://example.com/2.jpg", "position": 0},
                {"src": "https://example.com/1.jpg", "position": 1},
            ],
        )

        assert count == 2

    with database.session_scope() as session:
        images = (
            session.query(ProductImage)
            .filter(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
            .all()
        )
        assert len(images) == 2
        assert [image.original_path for image in images] == [
            "https://example.com/2.jpg",
            "https://example.com/1.jpg",
        ]
        primary_images = [image for image in images if image.is_primary]
        assert len(primary_images) == 1
        assert primary_images[0].original_path == "https://example.com/2.jpg"


def test_replace_images_from_wc_payload_preserves_local_primary_image(tmp_path) -> None:
    database = _make_database(tmp_path)
    repository = ProductRepository()

    with database.session_scope() as session:
        product = Product(
            name="Сёмга",
            slug="semga",
            sync_status="modified_local",
            published_state="draft",
            visibility="visible",
            is_featured=False,
            is_archived=False,
        )
        session.add(product)
        session.flush()

        wc_image = ProductImage(
            product_id=int(product.id),
            original_path="https://example.com/wc.jpg",
            local_path=None,
            source_type="wc_url",
            metadata_json=None,
            is_primary=False,
            sort_order=0,
        )
        local_primary_image = ProductImage(
            product_id=int(product.id),
            original_path="E:\\TestImages\\local.jpg",
            local_path="C:\\media\\local.jpg",
            source_type="local_file",
            metadata_json=None,
            is_primary=True,
            sort_order=1,
        )
        session.add_all([wc_image, local_primary_image])
        session.flush()
        product_id = int(product.id)

        count = repository.replace_images_from_wc_payload(
            session,
            product_id=product_id,
            images=[
                {"src": "https://example.com/wc.jpg", "position": 0},
                {"src": "https://example.com/wc-2.jpg", "position": 1},
            ],
        )

        assert count == 2

    with database.session_scope() as session:
        images = (
            session.query(ProductImage)
            .filter(ProductImage.product_id == product_id)
            .order_by(ProductImage.id.asc())
            .all()
        )
        assert len(images) == 3
        primary_images = [image for image in images if image.is_primary]
        assert len(primary_images) == 1
        assert primary_images[0].source_type == "local_file"
        assert primary_images[0].original_path == "E:\\TestImages\\local.jpg"
