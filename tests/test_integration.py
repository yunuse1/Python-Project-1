import pytest
import datetime
import os
import sys

# Proje kök dizinini path'e ekle (Modüllerin bulunabilmesi için)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from util.connect import get_client
from repository.repository import UniversityPriceRepository
from models.university_models import UniversityDepartmentPrice

# --- TEST AYARLARI ---
TEST_DB_NAME = "test_university_prices_integration"
MONGO_CONNECTION_STRING = os.getenv("MONGO_URI", "mongodb://localhost:27017")

@pytest.fixture(scope="function")
def test_repo():
    """
    Bu fixture her testten önce:
    1. Gerçek MongoDB'ye bağlanır.
    2. Temiz bir test veritabanı oluşturur.
    3. Repository nesnesini hazırlar.
    
    Test bittikten sonra (yield sonrası):
    4. Test veritabanını siler (Temizlik).
    """
    # 1. Bağlantı kontrolü (Fail fast)
    try:
        client = get_client(MONGO_CONNECTION_STRING, timeout_ms=2000)
    except ConnectionError:
        pytest.fail(f"MongoDB'ye bağlanılamadı! Lütfen MongoDB'nin {MONGO_CONNECTION_STRING} adresinde çalıştığından emin olun.")

    # 2. Repository'yi test veritabanı ismiyle başlat
    # Kodundaki __init__ yapısı sayesinde bu DB ismini kullanacak
    repo = UniversityPriceRepository(database_name=TEST_DB_NAME)
    
    # Test ortamını temizle (Önceki kalıntıları sil)
    client.drop_database(TEST_DB_NAME)

    # Repository'yi teste gönder
    yield repo

    # --- TEARDOWN (Temizlik) ---
    client.drop_database(TEST_DB_NAME)
    client.close()

def test_integration_upsert_and_read(test_repo):
    """
    Senaryo: Yeni bir fiyat kaydı ekle ve veritabanından geri oku.
    Amaç: Yazma ve okuma işleminin veri kaybı olmadan çalıştığını doğrulamak.
    """
    # 1. Veri Hazırla
    uni_price = UniversityDepartmentPrice(
        university_name="Integration Test Uni",
        department_name="Computer Engineering",
        faculty_name="Engineering Faculty",
        price_amount=75000.0,
        currency_code="TRY",
        price_description="75.000 TL KDV Dahil",
        last_scraped_at=datetime.datetime.now(datetime.timezone.utc)
    )

    # 2. Veritabanına Yaz (Upsert - Insert modu)
    was_inserted, was_updated = test_repo.upsert(uni_price)
    
    # İlk kez eklediğimiz için insert True olmalı
    assert was_inserted is True
    assert was_updated is False

    # 3. Veritabanından Oku
    saved_record = test_repo.find_price_by_department("Integration Test Uni", "Computer Engineering")
    
    # 4. Doğrula
    assert saved_record is not None
    assert saved_record.price_amount == 75000.0
    assert saved_record.currency_code == "TRY"
    assert saved_record.faculty_name == "Engineering Faculty"

def test_integration_upsert_update_existing(test_repo):
    """
    Senaryo: Var olan bir kaydı güncelle.
    Amaç: update_one upsert=True mantığının duplicate (çift) kayıt yaratmadığını doğrulamak.
    """
    # 1. İlk kaydı oluştur
    uni_price = UniversityDepartmentPrice(
        university_name="Update Test Uni",
        department_name="Law",
        price_amount=50000.0,
        currency_code="TRY"
    )
    test_repo.upsert(uni_price)

    # 2. Fiyatı değiştir ve tekrar gönder
    uni_price.price_amount = 60000.0
    was_inserted, was_updated = test_repo.upsert(uni_price)

    # Artık update olmalı, insert değil
    assert was_inserted is False
    assert was_updated is True

    # 3. DB'deki son durumu kontrol et
    updated_record = test_repo.find_price_by_department("Update Test Uni", "Law")
    assert updated_record.price_amount == 60000.0
    
    # Toplam kayıt sayısı hala 1 olmalı (Duplicate kontrolü)
    all_prices = test_repo.get_all_prices()
    assert len(all_prices) == 1

def test_integration_delete_by_composite_id(test_repo):
    """
    Senaryo: Bir kaydı composite ID (UniName::DeptName) ile sil.
    """
    # 1. Veri ekle
    uni_price = UniversityDepartmentPrice(
        university_name="Delete Uni",
        department_name="Architecture",
        price_amount=100.0
    )
    test_repo.upsert(uni_price)

    # Kayıt var mı emin ol
    assert test_repo.find_price_by_department("Delete Uni", "Architecture") is not None

    # 2. Silme işlemi (Modelindeki get_composite_id formatını kullanıyoruz)
    composite_id = "Delete Uni::Architecture"
    result = test_repo.delete(composite_id)

    assert result is True

    # 3. Silindiğini doğrula
    assert test_repo.find_price_by_department("Delete Uni", "Architecture") is None

def test_integration_get_all_prices(test_repo):
    """
    Senaryo: Birden fazla kayıt ekleyip hepsini listele.
    """
    prices = [
        UniversityDepartmentPrice(university_name="Uni A", department_name="Dept 1", price_amount=100),
        UniversityDepartmentPrice(university_name="Uni A", department_name="Dept 2", price_amount=200),
        UniversityDepartmentPrice(university_name="Uni B", department_name="Dept 1", price_amount=300),
    ]

    for p in prices:
        test_repo.upsert(p)

    # Hepsini getir
    all_records = test_repo.get_all()
    
    assert len(all_records) == 3
    # Rastgele bir kontrol
    uni_a_records = [r for r in all_records if r.university_name == "Uni A"]
    assert len(uni_a_records) == 2 