# add_item.py
from KaltriDB import add_item
import re

def parse_date(date_str):
    # Remove all non-digit characters from the input string
    date_str = re.sub(r'\D', '', date_str)
    # Extract year, month, and day using regex
    match = re.search(r'(\d{4})(\d{2})(\d{2})', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    else:
        print("Invalid date format. Please ensure the date contains at least 8 digits (YYYYMMDD).")
        return None
    
def main():
    hospital = input("Enter hospital (A or B): ").strip().upper()
    name = input("Enter item name: ").strip()
    quantity = int(input("Enter quantity: ").strip())
    cost = float(input("Enter cost: ").strip())
    date_added = input("Enter date added (any format containing YYYY  MM  DD): ").strip()
    expiry_date = input("Enter expiry date (any format containing YYYY  MM  DD): ").strip()

    # Parse dates
    date_added_parsed = parse_date(date_added)
    expiry_date_parsed = parse_date(expiry_date)

    if date_added_parsed and expiry_date_parsed:
        add_item(hospital, name, quantity, cost, date_added_parsed, expiry_date_parsed)
        print("Item added successfully.")

if __name__ == "__main__":
    main()
