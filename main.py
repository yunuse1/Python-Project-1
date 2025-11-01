import csv
import util.check_prices as check_prices
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    university = input("Would you like to see all universities or do you have a preferred university? (To see all universities, type “all.” For your preferred university, type the university name): ").strip().lower()

    while True:
        price_option = input("Would you like to see the full price of the university or the price with a half scholarship? (If you want to see the full price, write “full”; if you want to see the price with a half scholarship, write “half”): ").strip().lower()
        if price_option in ["full", "half"]:
            break
        

    department = input("Would you like to see all departments or do you have a preferred department? (To see all department, type “all.” For your preferred department, type the department name): ").strip().lower()

    while True:
        preference_discount_input = input("Should we also show the preference discount? (yes / no): ").strip().lower()
        if preference_discount_input in ("yes", "y"):
            apply_preference_discount = True
            break
        if preference_discount_input in ("no", "n"):
            apply_preference_discount = False
            break
        logger.info("Please answer yes/no.")


    dept_arg = None if department == "all" else department
    univ_arg = None if university == "all" else university

    schools_list = check_prices.find_department_prices(
        department_name=dept_arg,
        university_name=univ_arg,
        apply_preference_discount=apply_preference_discount
    )

    if department != "all":
        schools_list = [s for s in schools_list if department.lower() in s["department"].lower()]

    if apply_preference_discount:
        for scholarship_info in schools_list:
            scholarship_info["scholarship_info"] = "A preference discount is available." 
    else:
        for scholarship_info in schools_list:
            scholarship_info["scholarship_info"] = "A preference discount is not available."

    if price_option == "half":
        for scholarship_info in schools_list:
            if isinstance(scholarship_info["price"], (int, float)):
                scholarship_info["price"] = scholarship_info["price"]

    csv_filename = "university_department_prices.csv"
    with open(csv_filename, "w", newline='', encoding="utf-8-sig") as f:
        if schools_list:
            fieldnames = ["university", "faculty", "department", "price", "scholarship_info"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(schools_list)
            logger.info(f" {len(schools_list)} recorded: {csv_filename}")
        else:

            logger.error("Hiç kayıt bulunamadı.")

if __name__ == "__main__":
    main()
