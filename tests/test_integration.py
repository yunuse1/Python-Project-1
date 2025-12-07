import pytest
import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from util.connect import get_client
from repository.repository import UniversityPriceRepository
from models.university_models import UniversityDepartmentPrice

TEST_DB_NAME = "test_university_prices_integration"
MONGO_CONNECTION_STRING = os.getenv("MONGO_URI", "mongodb://localhost:27017")

@pytest.fixture(scope="function")
def test_repo():
    try:
        client = get_client(MONGO_CONNECTION_STRING, timeout_ms=2000)
    except ConnectionError:
        pytest.fail(f"Could not connect to MongoDB! Please ensure MongoDB is running at {MONGO_CONNECTION_STRING}.")

    repo = UniversityPriceRepository(database_name=TEST_DB_NAME)
    
    client.drop_database(TEST_DB_NAME)

    yield repo

    client.drop_database(TEST_DB_NAME)
    client.close()

def test_integration_upsert_and_read(test_repo):
    uni_price = UniversityDepartmentPrice(
        university_name="Integration Test Uni",
        department_name="Computer Engineering",
        faculty_name="Engineering Faculty",
        price_amount=75000.0,
        currency_code="TRY",
        price_description="75.000 TL KDV Dahil",
        last_scraped_at=datetime.datetime.now(datetime.timezone.utc)
    )

    was_inserted, was_updated = test_repo.upsert(uni_price)
    
    assert was_inserted is True
    assert was_updated is False

    saved_record = test_repo.find_price_by_department("Integration Test Uni", "Computer Engineering")
    
    assert saved_record is not None
    assert saved_record.price_amount == 75000.0
    assert saved_record.currency_code == "TRY"
    assert saved_record.faculty_name == "Engineering Faculty"

def test_integration_upsert_update_existing(test_repo):
    uni_price = UniversityDepartmentPrice(
        university_name="Update Test Uni",
        department_name="Law",
        price_amount=50000.0,
        currency_code="TRY"
    )
    test_repo.upsert(uni_price)

    uni_price.price_amount = 60000.0
    was_inserted, was_updated = test_repo.upsert(uni_price)

    assert was_inserted is False
    assert was_updated is True

    updated_record = test_repo.find_price_by_department("Update Test Uni", "Law")
    assert updated_record.price_amount == 60000.0
    
    all_prices = test_repo.get_all_prices()
    assert len(all_prices) == 1

def test_integration_delete_by_composite_id(test_repo):
    uni_price = UniversityDepartmentPrice(
        university_name="Delete Uni",
        department_name="Architecture",
        price_amount=100.0
    )
    test_repo.upsert(uni_price)

    assert test_repo.find_price_by_department("Delete Uni", "Architecture") is not None

    composite_id = "Delete Uni::Architecture"
    result = test_repo.delete(composite_id)

    assert result is True

    assert test_repo.find_price_by_department("Delete Uni", "Architecture") is None

def test_integration_get_all_prices(test_repo):
    prices = [
        UniversityDepartmentPrice(university_name="Uni A", department_name="Dept 1", price_amount=100),
        UniversityDepartmentPrice(university_name="Uni A", department_name="Dept 2", price_amount=200),
        UniversityDepartmentPrice(university_name="Uni B", department_name="Dept 1", price_amount=300),
    ]

    for p in prices:
        test_repo.upsert(p)

    all_records = test_repo.get_all()
    
    assert len(all_records) == 3
    uni_a_records = [r for r in all_records if r.university_name == "Uni A"]
    assert len(uni_a_records) == 2