from app.db.models import Category, Product, ProductCategoryLink, ProductImage, SyncRun


def test_phase2_model_table_names() -> None:
    assert Category.__tablename__ == "categories"
    assert Product.__tablename__ == "products"
    assert ProductImage.__tablename__ == "product_images"
    assert ProductCategoryLink.__tablename__ == "product_categories"
    assert SyncRun.__tablename__ == "sync_runs"


def test_product_image_has_local_path_column() -> None:
    assert "local_path" in ProductImage.__table__.c
