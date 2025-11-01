from util.school_list import schools

##%20 TERCİH BURSU BÖLÜMÜ DÜZENLENMELİ
extra_credit = ["İstinye Üniversitesi", "İstanbul Aydın Üniversitesi", "İstanbul Gelişim Üniversitesi", "İstanbul Kültür Üniversitesi", "Kadir Has Üniversitesi", "Kocaeli Sağlık ve Teknoloji Üniversitesi", "MEF Üniversitesi", "OSTİM Teknik Üniversitesi", "Piri Reis Üniversitesi", "Özyeğin Üniversitesi"]

def normalize_turkish_text(text: str) -> str:
    """Türkçe I/İ problemi ve genel normalize."""
    if not isinstance(text, str):
        return ""
    text = text.replace("İ", "i").replace("I", "ı")
    return text.lower().strip()

_normalized_extra = { normalize_turkish_text(x) for x in extra_credit }

def find_department_prices(
    department_name: str = None,
    university_name: str = None,
    apply_double_credit: bool = False,
    apply_preference_discount: bool = False
):
    """
    dept_query, university ile esnek arama yapar.
    apply_pref_burs True ise extra_credit listesinde olan üniversitelere ek %20 indirim uygulanır.
    """
    normalized_department = normalize_turkish_text(department_name) if department_name else ""
    normalized_university = normalize_turkish_text(university_name) if university_name else ""
    price_results = []

    for university, faculty_data in schools.items():
        # üniversite filtrelemesi
        if normalized_university and normalized_university not in normalize_turkish_text(university):
            continue

        if isinstance(faculty_data, dict):
            for faculty_name, department_data in faculty_data.items():
                if isinstance(department_data, dict):
                    for dept_name, price in department_data.items():
                        if normalized_department and normalized_department not in normalize_turkish_text(dept_name):
                            continue
                        try:
                            price_value = float(price)
                        except Exception:
                            try:
                                cleaned_price_str = str(price).replace(".", "").replace(",", "")
                                price_value = float(cleaned_price_str)
                            except Exception:
                                continue
                        result_price = price_value * 2 if apply_double_credit else price_value
                        
                        if apply_preference_discount:
                            normalized_uni_key = normalize_turkish_text(university)
                            for simple_name in _normalized_extra:
                                if simple_name in normalized_uni_key:
                                    result_price = result_price * 0.8 
                                    break
                                
                        price_results.append({
                            "university": university,
                            "faculty": faculty_name,
                            "department": dept_name,
                            "price": result_price
                        })
                else:
                    try:
                        price_value = float(department_data)
                    except Exception:
                        try:
                            cleaned_price_str = str(department_data).replace(".", "").replace(",", "")
                            price_value = float(cleaned_price_str)
                        except Exception:
                            continue
                    if normalized_department and normalized_department not in normalize_turkish_text(faculty_name):
                        continue
                    result_price = price_value * 2 if apply_double_credit else price_value
                    
                    if apply_preference_discount:
                        normalized_uni_key = normalize_turkish_text(university)
                        for simple_name in _normalized_extra:
                            if simple_name in normalized_uni_key:
                                result_price = result_price * 0.8
                                break
                                
                    price_results.append({
                        "university": university,
                        "faculty": faculty_name,
                        "department": faculty_name,
                        "price": result_price
                    })
        else:
            try:
                price_value = float(faculty_data)
            except Exception:
                try:
                    cleaned_price_str = str(faculty_data).replace(".", "").replace(",", "")
                    price_value = float(cleaned_price_str)
                except Exception:
                    continue
            if normalized_university and normalized_university not in normalize_turkish_text(university):
                continue
            result_price = price_value * 2 if apply_double_credit else price_value
            
            if apply_preference_discount:
                normalized_uni_key = normalize_turkish_text(university)
                for simple_name in _normalized_extra:
                    if simple_name in normalized_uni_key:
                        result_price = result_price * 0.8
                        break
                        
            price_results.append({
                "university": university,
                "faculty": "",
                "department": university,
                "price": result_price
            })

    return price_results