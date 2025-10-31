from util.school_list import schools

##%20 TERCİH BURSU BÖLÜMÜ DÜZENLENMELİ
extra_credit = ["istinye Üniversitesi", "istanbul Aydın Üniversitesi", "istanbul Gelişim Üniversitesi", "istanbul Kültür Üniversitesi", "kadir Has Üniversitesi", "kocaeli Üniversitesi", "mef Üniversitesi", "ostim Teknik Üniversitesi", "piri Reis Üniversitesi", "özyeğin Üniversitesi"]

def _normalize(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return s.replace('İ', 'i').replace('I', 'ı').lower().strip()

def find_department_prices(
    dept_query: str = "",
    university: str = "",
    uncredit: bool = True
):
    """
    dept_query, university ve faculty ile esnek arama yapar.
    Boş bırakılan parametreler için filtre uygulanmaz, tüm kayıtlar döner.
    """
    query = _normalize(dept_query) if dept_query else ""
    university_query = _normalize(university) if university else ""
    results = []
    for uni, faculties in schools.items():
        if university_query and university_query not in _normalize(uni):
            continue
        for fac, depts in faculties.items():
            for dept, price in depts.items():
                if query and query not in _normalize(dept):
                    continue
                result_price = price * 2 if uncredit else price
                extra = price * 5 if _normalize(uni) in [_normalize(u) for u in extra_credit] else result_price
                results.append({
                    "university": uni,
                    "faculty": fac,
                    "department": dept,
                    "price": extra
                })
    return results