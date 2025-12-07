import pytest
import datetime
import os
import sys

# Add project root directory to path (to locate modules)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from util.connect import get_client
from repository.repository import UniversityPriceRepository
from models.university_models import UniversityDepartmentPrice

# --- TEST SETTINGS ---
TEST_DB_NAME = "test_university_prices_integration"
MONGO_CONNECTION_STRING = os.getenv("MONGO_URI", "mongodb://localhost:27017")

@pytest.fixture(scope="function")
def test_repo():
    # 1. Connection check (Fail fast)
    try:
        client = get_client(MONGO_CONNECTION_STRING, timeout_ms=2000)
    except ConnectionError:
        pytest.fail(f"Could not connect to MongoDB! Please ensure MongoDB is running at {MONGO_CONNECTION_STRING}.")

    # 2. Initialize Repository with the test database name
    # It will use this DB name thanks to its __init__ structure
    repo = UniversityPriceRepository(database_name=TEST_DB_NAME)
    
    # Clean the test environment (Delete previous remnants)
    client.drop_database(TEST_DB_NAME)

    # Yield the Repository to the test
    yield repo

    # --- TEARDOWN (Cleanup) ---
    client.drop_database(TEST_DB_NAME)
    client.close()

def test_integration_upsert_and_read(test_repo):
    # 1. Prepare Data
    uni_price = UniversityDepartmentPrice(
        university_name="Integration Test Uni",
        department_name="Computer Engineering",
        faculty_name="Engineering Faculty",
        price_amount=75000.0,
        currency_code="TRY",
        price_description="75.000 TL KDV Dahil",
        last_scraped_at=datetime.datetime.now(datetime.timezone.utc)
    )

    # 2. Write to Database (Upsert - Insert mode)
    was_inserted, was_updated = test_repo.upsert(uni_price)
    
    # Since we are inserting for the first time, insert must be True
    assert was_inserted is True
    assert was_updated is False

    # 3. Read from Database
    saved_record = test_repo.find_price_by_department("Integration Test Uni", "Computer Engineering")
    
    # 4. Verify
    assert saved_record is not None
    assert saved_record.price_amount == 75000.0
    assert saved_record.currency_code == "TRY"
    assert saved_record.faculty_name == "Engineering Faculty"

def test_integration_upsert_update_existing(test_repo):
    # 1. Create the initial record
    uni_price = UniversityDepartmentPrice(
        university_name="Update Test Uni",
        department_name="Law",
        price_amount=50000.0,
        currency_code="TRY"
    )
    test_repo.upsert(uni_price)

    # 2. Change the price and send again
    uni_price.price_amount = 60000.0
    was_inserted, was_updated = test_repo.upsert(uni_price)

    # Now it should be an update, not an insert
    assert was_inserted is False
    assert was_updated is True

    # 3. Check the final state in the DB
    updated_record = test_repo.find_price_by_department("Update Test Uni", "Law")
    assert updated_record.price_amount == 60000.0
    
    # Total record count should still be 1 (Duplicate check)
    all_prices = test_repo.get_all_prices()
    assert len(all_prices) == 1

def test_integration_delete_by_composite_id(test_repo):
    # 1. Insert data
    uni_price = UniversityDepartmentPrice(
        university_name="Delete Uni",
        department_name="Architecture",
        price_amount=100.0
    )
    test_repo.upsert(uni_price)

    # Make sure the record exists
    assert test_repo.find_price_by_department("Delete Uni", "Architecture") is not None

    # 2. Delete operation (Using the get_composite_id format from the Model)
    composite_id = "Delete Uni::Architecture"
    result = test_repo.delete(composite_id)

    assert result is True

    # 3. Verify it's deleted
    assert test_repo.find_price_by_department("Delete Uni", "Architecture") is None

def test_integration_get_all_prices(test_repo):
    prices = [
        UniversityDepartmentPrice(university_name="Uni A", department_name="Dept 1", price_amount=100),
        UniversityDepartmentPrice(university_name="Uni A", department_name="Dept 2", price_amount=200),
        UniversityDepartmentPrice(university_name="Uni B", department_name="Dept 1", price_amount=300),
    ]

    for p in prices:
        test_repo.upsert(p)

    # Get all
    all_records = test_repo.get_all()
    
    assert len(all_records) == 3
    # A random check
    uni_a_records = [r for r in all_records if r.university_name == "Uni A"]
    assert len(uni_a_records) == 2