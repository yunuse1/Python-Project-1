schools = {
    "İstinye Üniversitesi": {
        "Mühendislik Fakültesi": {
            "Bilgisayar Mühendisliği": 525.0,
            "Bilgisayar Mühendisliği (İngilizce)": 525.0,
            "Biyomedikal Mühendisliği (İngilizce)": 530.0,
            "Elektrik-Elektronik Mühendisliği (İngilizce)": 540.0,
            "Endüstri Mühendisliği (İngilizce)": 535.0,
            "Makine Mühendisliği (İngilizce)": 545.0,
            "Matematik (İngilizce)": 520.0,
            "Moleküler Biyoloji ve Genetik (İngilizce)": 530.0,
            "Yazılım Geliştirme": 525.0,
            "Yazılım Mühendisliği": 525.0,
            "Yazılım Mühendisliği (İngilizce)": 525.0,
        }
    },
    "Beykent Üniversitesi": {
        "Tıp Fakültesi": {
            "Tıp": 785.185,
        },
        "Diş Hekimliği Fakültesi": {
            "Tıp": 785.185,
        },
        "Mühendislik-Mimarlık Fakültesi": {
            "Bilgisayar Mühendisliği": 592.593,
            "Bilgisayar Mühendisliği (İngilizce)": 592.593,
            "Elektrik-Elektronik Mühendisliği (İngilizce)": 362.963,
            "Endüstri Mühendisliği (İngilizce)": 429.630 ,
            "Endüstri Mühendisliği": 429.630 ,
            "Makine Mühendisliği (İngilizce)": 325.926 ,
            "Matematik (İngilizce)": 392.593,
            "Yazılım Geliştirme": 474.074,
            "Yazılım Mühendisliği": 592.593,
            "Endüstriyel Tasarım": 422.222,
            "Endüstriyel Tasarım (İngilizce)": 422.222,
            "İç Mimarlık": 503.704 ,
            "İç Mimarlık (İngilizce)": 503.704 ,
            "İnşaat Mühendisliği (İngilizce)": 503.704 ,
            "İnşaat Mühendisliği": 503.704 ,
            
        }
    },
}



def find_department_prices(dept_query: str):
    """
    dept_query ile eşleşen tüm bölümleri bulur.
    Dönen liste elemanı örneği: {"university": ..., "faculty": ..., "department": ..., "price": ...}
    """
    query = dept_query.strip().lower()
    results = []
    for uni, faculties in schools.items():
        for fac, depts in faculties.items():
            for dept, price in depts.items():
                if query in dept.lower():
                    results.append({
                        "university": uni,
                        "faculty": fac,
                        "department": dept,
                        "price": price
                    })
    return results