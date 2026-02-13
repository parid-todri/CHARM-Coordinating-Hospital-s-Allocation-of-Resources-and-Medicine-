# list_items.py
from KaltriDB import get_inventory

def main():
    hospital = input("Enter hospital (A or B): ").strip().upper()
    inventory = get_inventory(hospital)
    if not inventory:
        print("No items found or invalid hospital identifier.")
        return

    print(f"Inventory for Hospital {hospital}:")
    for item in inventory:
        print(f"Name: {item['name']}, Quantity: {item['quantity']}, Cost: {item['cost']}, Date Added: {item['date_added']}, Expiry Date: {item['expiry_date']}")

if __name__ == "__main__":
    main()
