import pytest
# 'burs_listesi'ni import etmeye GEREK YOK, sadece check_prices'ı import et
from util.check_prices import find_department_prices, normalize_turkish_text 

# --- 1. Helper Function Tests ---

def test_normalize_turkish_text_basic():
    assert normalize_turkish_text("İSTANBUL IŞIK") == "istanbul ışık"

def test_normalize_turkish_text_spacing():
    assert normalize_turkish_text("  Koç Üniversitesi  ") == "koç üniversitesi"

def test_normalize_turkish_text_empty_or_none():
    assert normalize_turkish_text("") == ""
    assert normalize_turkish_text(None) == ""


# --- 2. Main Function Tests: find_department_prices ---

def test_find_specific_department_and_university():
    results = find_department_prices(
        department_name="Tıp", 
        university_name="Koç Üniversitesi"
    )
    assert len(results) == 1
    assert results[0]['price'] == 1185000

def test_find_department_only():
    results = find_department_prices(department_name="Hukuk")
    assert len(results) > 1 
    found_koc = any(
        r['university'] == 'Koç Üniversitesi' and r['department'] == 'Hukuk' 
        for r in results
    )
    assert found_koc == True

def test_find_university_only():
    results = find_department_prices(university_name="Kadir Has Üniversitesi")
    assert len(results) > 5
    all_kadir_has = all(r['university'] == 'Kadir Has Üniversitesi' for r in results)
    assert all_kadir_has == True

def test_no_results_found():
    results = find_department_prices(
        department_name="Uzay Mühendisliği", 
        university_name="Koç Üniversitesi"
    )
    assert len(results) == 0

def test_apply_double_credit():
    results = find_department_prices(
        department_name="Tıp", 
        university_name="Koç Üniversitesi",
        apply_double_credit=True
    )
    assert len(results) == 1
    assert results[0]['price'] == 1185000 * 2

def test_preference_discount_applies():
    # --- BU TEST GÜNCELLENDİ ---
    # Kod artık dinamik listeyi kullanıyor. İstinye'nin indirimi %15.
    # Orijinal Fiyat: 750,000
    # Beklenen Fiyat: 750,000 * (1 - 0.15) = 637,500
    results = find_department_prices(
        department_name="Tıp (Türkçe)", 
        university_name="İstinye Üniversitesi",
        apply_preference_discount=True
    )
    assert len(results) == 1
    assert results[0]['price'] == 637500.0 # 600000'den 637500.0'a güncellendi

def test_preference_discount_not_applied_when_not_in_list():
    results = find_department_prices(
        department_name="Tıp", 
        university_name="Koç Üniversitesi",
        apply_preference_discount=True
    )
    assert len(results) == 1
    assert results[0]['price'] == 1185000

def test_preference_discount_not_applied_when_flag_is_false():
    results = find_department_prices(
        department_name="Tıp (Türkçe)", 
        university_name="İstinye Üniversitesi",
        apply_preference_discount=False
    )
    assert len(results) == 1
    assert results[0]['price'] == 750000

def test_find_partial_department_name():
    results = find_department_prices(department_name="mühendisliği")
    assert len(results) > 10
    assert all("mühendisliği" in normalize_turkish_text(r['department']) for r in results)

def test_find_partial_university_name():
    results = find_department_prices(university_name="istanbul")
    assert len(results) > 20
    assert all("istanbul" in normalize_turkish_text(r['university']) for r in results)

def test_case_insensitive_search_turkish_chars():
    results_lower = find_department_prices(department_name="dış ticaret", university_name="ışık üniversitesi")
    results_mixed = find_department_prices(department_name="DIŞ TİCARET", university_name="IŞIK ÜNİVERSİTESİ")

    assert len(results_lower) > 0
    assert len(results_mixed) > 0
    assert results_lower[0]['price'] == 195850.0
    assert results_mixed[0]['price'] == 195850.0

def test_find_department_in_2_level_structure():
    results = find_department_prices(
        department_name="Tıp Fakültesi", 
        university_name="İstanbul Okan Üniversitesi"
    )
    assert len(results) == 1
    assert results[0]['price'] == 352357

def test_price_normalization_with_dot_thousands(monkeypatch):
    mock_schools = {"Test Uni": {"Test Fak": {"Bölüm": "1.000.000"}}}
    monkeypatch.setattr("util.check_prices.schools", mock_schools)
    results = find_department_prices(university_name="Test Uni")
    assert results[0]['price'] == 1000000.0

def test_price_normalization_works_with_comma_thousands(monkeypatch):
    mock_schools = {"Test Uni": {"Test Fak": {"Bölüm": "750,000"}}}
    monkeypatch.setattr("util.check_prices.schools", mock_schools)
    results = find_department_prices(university_name="Test Uni")
    assert results[0]['price'] == 750000.0

def test_preference_discount_works_on_complex_key_name():
    # --- BU TEST GÜNCELLENDİ ---
    # Kod artık dinamik listeyi kullanıyor. MEF'in indirimi %25.
    # Orijinal Fiyat: 465,120
    # Beklenen Fiyat: 465,120 * (1 - 0.25) = 348,840
    results = find_department_prices(
        department_name="Bilgisayar Mühendisliği (55% İndirimli, Peşin)", 
        university_name="MEF Üniversitesi",
        apply_preference_discount=True
    )
    assert len(results) > 0
    mef_cs_result = results[0]
    assert mef_cs_result['price'] == 348840.0 # 372096.0'dan 348840.0'a güncellendi