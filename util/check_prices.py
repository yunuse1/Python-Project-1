from util.school_list import schools, scholarship_rates

def normalize_turkish_text(text: str) -> str:
    """Turkish I/İ problem and general normalization."""
    if not isinstance(text, str):
        return ""
    text = text.replace("İ", "i").replace("I", "ı")
    return text.lower().strip()

_normalized_scholarships = {normalize_turkish_text(k): v for k, v in scholarship_rates}


def find_department_prices(
    department_name: str = None,
    university_name: str = None,
    apply_double_credit: bool = False,
    apply_preference_discount: bool = False
):
    """
    Searches and calculates university department prices with flexible text matching.

    Args:
        department_name (str, optional): Department name to search for. Case-insensitive partial matching.
        university_name (str, optional): University name to search for. Case-insensitive partial matching.
        apply_double_credit (bool, default=False): If True, doubles the base price.
        apply_preference_discount (bool, default=False): If True, applies scholarship discount rate
            defined in scholarship_rates for eligible universities.

    """
    normalized_department = normalize_turkish_text(department_name) if department_name else ""
    normalized_university = normalize_turkish_text(university_name) if university_name else ""
    price_results = []

    for university, faculty_data in schools.items():
        if normalized_university and normalized_university not in normalize_turkish_text(university):
            continue

        normalized_uni_key = normalize_turkish_text(university)
        pref_applicable = normalized_uni_key in _normalized_scholarships
        scholarship_rate = _normalized_scholarships.get(normalized_uni_key, 0)

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

                        if apply_preference_discount and scholarship_rate > 0:
                            result_price = result_price * (1 - scholarship_rate/100)
                            
                        result_price = round(result_price, 2) 

                        price_results.append({
                            "university": university,
                            "faculty": faculty_name,
                            "department": dept_name,
                            "price": result_price,
                            "preference_applicable": pref_applicable,
                            "scholarship_rate": scholarship_rate if pref_applicable else 0
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

                    if apply_preference_discount and scholarship_rate > 0:
                        result_price = result_price * (1 - scholarship_rate/100)
                    result_price = round(result_price, 2) 

                    price_results.append({
                        "university": university,
                        "faculty": faculty_name,
                        "department": faculty_name,
                        "price": result_price,
                        "preference_applicable": pref_applicable,
                        "scholarship_rate": scholarship_rate if pref_applicable else 0
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


            if apply_preference_discount and scholarship_rate > 0:
                result_price = result_price * (1 - scholarship_rate/100)
            
            result_price = round(result_price, 2) 

            price_results.append({
                "university": university,
                "faculty": "",
                "department": university,
                "price": result_price,
                "preference_applicable": pref_applicable,
                "scholarship_rate": scholarship_rate if pref_applicable else 0
            })

    return price_results