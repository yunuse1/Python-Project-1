import pytest
from util.check_prices import find_department_prices, normalize_turkish_text

# --- 1. Helper Function Tests ---

def test_normalize_turkish_text_basic():
    """ Tests if the Turkish characters 'İ' and 'I' are normalized correctly. """
    assert normalize_turkish_text("İSTANBUL IŞIK") == "istanbul ışık"

def test_normalize_turkish_text_spacing():
    """ Tests if leading/trailing whitespace is removed. """
    assert normalize_turkish_text("  Koç Üniversitesi  ") == "koç üniversitesi"

def test_normalize_turkish_text_empty_or_none():
    """ Tests that it does not error on None or empty strings. """
    assert normalize_turkish_text("") == ""
    assert normalize_turkish_text(None) == ""


# --- 2. Main Function Tests: find_department_prices ---

def test_find_specific_department_and_university():
    """ Finds the correct price when searching for a specific university and department. """
    results = find_department_prices(
        department_name="Tıp", 
        university_name="Koç Üniversitesi"
    )
    assert len(results) == 1
    assert results[0]['university'] == "Koç Üniversitesi"
    assert results[0]['department'] == "Tıp"
    assert results[0]['price'] == 1185000

def test_find_department_only():
    """ Searches by department name only (should return multiple results). """
    results = find_department_prices(department_name="Hukuk")
    assert len(results) > 1 
    found_koc = any(
        r['university'] == 'Koç Üniversitesi' and r['department'] == 'Hukuk' 
        for r in results
    )
    assert found_koc == True

def test_find_university_only():
    """ Searches by university name only (should return all departments for that university). """
    results = find_department_prices(university_name="Kadir Has Üniversitesi")
    assert len(results) > 5
    all_kadir_has = all(r['university'] == 'Kadir Has Üniversitesi' for r in results)
    assert all_kadir_has == True

def test_no_results_found():
    """ Returns an empty list when searching for a non-existent department. """
    results = find_department_prices(
        department_name="Uzay Mühendisliği", 
        university_name="Koç Üniversitesi"
    )
    assert len(results) == 0

def test_apply_double_credit():
    """ Tests that the 'apply_double_credit=True' flag multiplies the price by 2. """
    results = find_department_prices(
        department_name="Tıp", 
        university_name="Koç Üniversitesi",
        apply_double_credit=True
    )
    assert len(results) == 1
    assert results[0]['price'] == 1185000 * 2

def test_preference_discount_applies():
    """ 
    Tests that a 20% discount is applied when the preference discount flag is ON
    and the university is on the discount list.
    (İstinye Üniversitesi is on your list, Medicine price is 750,000)
    """
    results = find_department_prices(
        department_name="Tıp (Türkçe)", 
        university_name="İstinye Üniversitesi",
        apply_preference_discount=True
    )
    assert len(results) == 1
    # Price = 750,000 * 0.8 = 600,000
    assert results[0]['price'] == 600000

def test_preference_discount_not_applied_when_not_in_list():
    """ 
    Tests that the price does not change when the preference discount flag is ON
    but the university is NOT on the discount list. (Koç Üniversitesi is not on your list)
    """
    results = find_department_prices(
        department_name="Tıp", 
        university_name="Koç Üniversitesi",
        apply_preference_discount=True
    )
    assert len(results) == 1
    assert results[0]['price'] == 1185000

def test_preference_discount_not_applied_when_flag_is_false():
    """ 
    Tests that the discount is not applied when the preference discount flag is OFF,
    even if the university is on the discount list. (İstinye Üniversitesi)
    """
    results = find_department_prices(
        department_name="Tıp (Türkçe)", 
        university_name="İstinye Üniversitesi",
        apply_preference_discount=False
    )
    assert len(results) == 1
    assert results[0]['price'] == 750000

def test_find_partial_department_name():
    """ Tests that a partial search like 'mühendisliği' (engineering) returns multiple engineering departments. """
    results = find_department_prices(department_name="mühendisliği")
    assert len(results) > 10
    assert all("mühendisliği" in normalize_turkish_text(r['department']) for r in results)

def test_find_partial_university_name():
    """ Tests that a partial university search like 'istanbul' returns multiple results. """
    results = find_department_prices(university_name="istanbul")
    assert len(results) > 20
    assert all("istanbul" in normalize_turkish_text(r['university']) for r in results)

def test_case_insensitive_search_turkish_chars():
    """ Fully tests that the search is insensitive to 'İ/i' and 'I/ı' characters. """
    results_lower = find_department_prices(department_name="dış ticaret", university_name="ışık üniversitesi")
    results_mixed = find_department_prices(department_name="DIŞ TİCARET", university_name="IŞIK ÜNİVERSİTESİ")

    assert len(results_lower) > 0
    assert len(results_mixed) > 0
    assert results_lower[0]['price'] == 195850.0
    assert results_mixed[0]['price'] == 195850.0

def test_find_department_in_2_level_structure():
    """ 
    Tests entries in the 'schools' dictionary that have 2 levels (Uni -> Dept/Faculty Name -> Price) 
    (e.g., İstanbul Okan Üniversitesi -> "Tıp Fakültesi": 352357)
    """
    results = find_department_prices(
        department_name="Tıp Fakültesi", 
        university_name="İstanbul Okan Üniversitesi"
    )
    assert len(results) == 1
    assert results[0]['university'] == "İstanbul Okan Üniversitesi"
    assert results[0]['department'] == "Tıp Fakültesi"
    assert results[0]['price'] == 352357

def test_price_normalization_with_dot_thousands(monkeypatch):
    """ Tests the logic that cleans dots from price strings like '1.000.000'. """
    mock_schools = {
        "Test Üniversitesi": {
            "Test Fakültesi": {
                "Bölüm 1 (Noktalı)": "1.000.000"
            }
        }
    }
    monkeypatch.setattr("util.check_prices.schools", mock_schools)
    results = find_department_prices(university_name="Test Üniversitesi")
    assert len(results) == 1
    assert results[0]['price'] == 1000000.0

# --- BUG FIX TEST 1 ---
# This test USED to fail (xfail) because of the "750,000" bug.
# Now that the bug is fixed, it should PASS.
def test_price_normalization_works_with_comma_thousands(monkeypatch):
    """ Tests that strings using commas as thousand separators now work correctly. """
    mock_schools = {"Test Uni": {"Test Fak": {"Bölüm": "750,000"}}}
    monkeypatch.setattr("util.check_prices.schools", mock_schools)
    
    results = find_department_prices(university_name="Test Uni")
    
    # We now expect the code to correctly parse "750,000" as 750000.0
    assert results[0]['price'] == 750000.0

# --- BUG FIX TEST 2 ---
# This test USED to fail (xfail) because of the complex name matching bug.
# Now that the bug is fixed, it should PASS.
def test_preference_discount_works_on_complex_key_name():
    """ 
    Tests that the discount now SUCCEEDS even when the 'schools' key
    has a complex name (e.g., 'MEF Üniversitesi (SADECE...)').
    """
    # Expected Discounted Price: 465120 * 0.8 = 372096
    results = find_department_prices(
        department_name="Bilgisayar Mühendisliği (55% İndirimli, Peşin)", 
        university_name="MEF Üniversitesi",
        apply_preference_discount=True
    )
    
    assert len(results) > 0
    mef_cs_result = results[0]
    
    # We now expect the 20% discount to be applied correctly.
    assert mef_cs_result['price'] == 372096.0