import csv
import util.check_prices

def main():
    print("🎓 Üniversite Bölüm Fiyat Sorgulama Aracı\n")

    # 1️⃣ Tam mı Yarım mı?
    while True:
        ucret_tipi = input("Tam fiyat mı, %50 burslu fiyat mı istiyorsunuz? (tam/yarım): ").strip().lower()
        if ucret_tipi in ["tam", "yarım"]:
            break
        print("⚠️ Lütfen sadece 'tam' veya 'yarım' yazın.")

    # 2️⃣ Üniversite seçimi
    university = input("Hangi üniversiteyi görmek istiyorsunuz? (tüm üniversiteler için 'tüm' yazın): ").strip().lower()

    # 3️⃣ Bölüm seçimi
    department = input("Hangi bölümü görmek istiyorsunuz? (tüm bölümler için 'tüm' yazın): ").strip().lower()

    # 4️⃣ Tercih bursu avantajı
    bursu_goster = input("Tercih bursu avantajlarını da gösterelim mi? (evet/hayır): ").strip().lower()
    show_burs = bursu_goster == "evet"

    print("\n🔎 Veriler getiriliyor, lütfen bekleyin...\n")

    # 5️⃣ Veri çekme
    if university == "tüm":
        schools_list = util.check_prices.find_department_prices()  # tüm üniversiteler
    else:
        schools_list = util.check_prices.find_department_prices(university=university)

    # Filtreleme (örnek: yarım/tam fiyat ya da bölüm bazlı)
    if department != "tüm":
        schools_list = [s for s in schools_list if department.lower() in s["department"].lower()]

    # Tercih bursu bilgisi eklenecekse
    if show_burs:
        for s in schools_list:
            s["scholarship_info"] = "Tercih bursu avantajı mevcuttur."  # örnek bilgi
    else:
        for s in schools_list:
            s["scholarship_info"] = "-"

    # Ücret tipine göre (örnek bir filtre)
    if ucret_tipi == "yarım":
        for s in schools_list:
            if isinstance(s["price"], (int, float)):
                s["price"] = s["price"] / 2

    # 6️⃣ CSV’ye yaz
    csv_filename = "universite_bolum_fiyatlari.csv"
    with open(csv_filename, "w", newline='', encoding="utf-8-sig") as f:
        if schools_list:
            fieldnames = ["university", "faculty", "department", "price", "scholarship_info"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(schools_list)
            print(f"✅ {len(schools_list)} kayıt yazıldı: {csv_filename}")
        else:
            f.write("No results found.")
            print("⚠️ Hiç kayıt bulunamadı.")

    print("\n 📁 CSV dosyanız hazır!")

if __name__ == "__main__":
    main()
