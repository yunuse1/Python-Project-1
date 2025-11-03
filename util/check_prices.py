from util.school_list import schools, scholarship_rates # Düzeltme: 'burs_listesi' yerine 'scholarship_rates' import edildi

def normalize_turkish_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("İ", "i").replace("I", "ı")
    return text.lower().strip()

# Düzeltme: 'burs_listesi' yerine 'scholarship_rates' kullanıldı
_normalized_scholarships = {
    normalize_turkish_text(uni): rate 
    for uni, rate in scholarship_rates
}

def find_department_prices(
    department_name: str = None,
    university_name: str = None,
    apply_double_credit: bool = False,
    apply_preference_discount: bool = False
):
    normalized_department = normalize_turkish_text(department_name) if department_name else ""
    normalized_university = normalize_turkish_text(university_name) if university_name else ""
    price_results = []

    for university, faculty_data in schools.items():
        if normalized_university and normalized_university not in normalize_turkish_text(university):
            continue
        
        normalized_uni_key = normalize_turkish_text(university)

        discount_rate = 0
        if apply_preference_discount:
            for simple_name, rate in _normalized_scholarships.items():
                if simple_name in normalized_uni_key:
                    discount_rate = rate
                    break

        if isinstance(faculty_data, dict):
            for faculty_name, department_data in faculty_data.items():
                if isinstance(department_data, dict):
                    for dept_name, price in department_data.items():
                        if normalized_department and normalized_department not in normalize_turkish_text(dept_name):
                            continue
                        try:
                            cleaned_price_str = str(price).replace(".", "").replace(",", "")
                            price_value = float(cleaned_price_str)
                        except Exception:
                            continue
                        
                        result_price = price_value * 2 if apply_double_credit else price_value
                        
                        if discount_rate > 0:
                            multiplier = 1.0 - (discount_rate / 100.0)
                            result_price = result_price * multiplier
                                
                        price_results.append({
                            "university": university,
                            "faculty": faculty_name,
                            "department": dept_name,
                            "price": result_price
                        })
                else:
                    try:
                        cleaned_price_str = str(department_data).replace(".", "").replace(",", "")
                        price_value = float(cleaned_price_str)
                    except Exception:
                        continue
                    if normalized_department and normalized_department not in normalize_turkish_text(faculty_name):
                        continue
                    
                    result_price = price_value * 2 if apply_double_credit else price_value
                    
                    if discount_rate > 0:
                        multiplier = 1.0 - (discount_rate / 100.0)
                        result_price = result_price * multiplier
                                
                    price_results.append({
                        "university": university,
                        "faculty": faculty_name,
                        "department": faculty_name,
                        "price": result_price
                    })
        else:
            try:
                cleaned_price_str = str(faculty_data).replace(".", "").replace(",", "")
                price_value = float(cleaned_price_str)
            except Exception:
                continue
            if normalized_university and normalized_university not in normalize_turkish_text(university):
                continue
            
            result_price = price_value * 2 if apply_double_credit else price_value
            
            if discount_rate > 0:
                multiplier = 1.0 - (discount_rate / 100.0)
                result_price = result_price * multiplier
                        
            price_results.append({
                "university": university,
                "faculty": "",
                "department": university,
                "price": result_price
            })

    return price_results