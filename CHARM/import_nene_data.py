import csv
from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['charm_inventory']
inventory_collection = db['inventory']
usage_collection = db['usage_logs']

# Clear existing data for Hospital A
print("Clearing existing data for Hospital A...")
inventory_collection.delete_many({'hospital': 'A'})
usage_collection.delete_many({'hospital': 'A'})

# Read and process CSV
print("Loading data from CSV...")
with open('data/nene_tereza_synthetic_orders_2025_with_consumption.csv', 'r') as file:
    csv_reader = csv.DictReader(file)
    
    # Dictionary to accumulate inventory
    inventory_items = {}
    
    for row in csv_reader:
        medication = row['medication']
        quantity = int(row['quantity'])
        quantity_used = int(row['quantity_used'])
        purchase_date_str = row['purchase_date']
        expiration_date_str = row['expiration_date']
        order_month = row['order_month']
        avg_daily_consumption = float(row['avg_daily_consumption'])
        
        # Parse dates
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
        expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
        
        # Add to inventory (accumulate quantities from multiple orders)
        if medication not in inventory_items:
            inventory_items[medication] = {
                'item_name': medication,
                'quantity': quantity - quantity_used,  # Current stock
                'expiry_date': expiration_date,  # Use latest expiry
                'hospital': 'A',
                'unit_cost': 10.0,  # Default unit cost
                'last_updated': purchase_date
            }
        else:
            # Accumulate remaining quantity
            inventory_items[medication]['quantity'] += (quantity - quantity_used)
            # Keep the latest expiry date
            if expiration_date > inventory_items[medication]['expiry_date']:
                inventory_items[medication]['expiry_date'] = expiration_date
            # Keep the latest update date
            if purchase_date > inventory_items[medication]['last_updated']:
                inventory_items[medication]['last_updated'] = purchase_date
        
        # Add usage log entry
        usage_entry = {
            'medication': medication,
            'quantity': quantity_used,
            'date': purchase_date.strftime('%Y-%m-%d'),
            'month': order_month,
            'hospital': 'A',
            'avg_daily_consumption': avg_daily_consumption,
            'logged_at': datetime.now()
        }
        usage_collection.insert_one(usage_entry)
    
    # Insert inventory items
    print(f"Inserting {len(inventory_items)} unique medications into inventory...")
    inventory_collection.insert_many(list(inventory_items.values()))

print(f"\n✅ Data import complete!")
print(f"   - Inventory items: {inventory_collection.count_documents({'hospital': 'A'})}")
print(f"   - Usage log entries: {usage_collection.count_documents({'hospital': 'A'})}")

# Calculate and display some stats
total_stock = sum(item['quantity'] for item in inventory_items.values())
print(f"   - Total stock value: {total_stock} units")

# Find items expiring soon (within 90 days)
from datetime import timedelta
ninety_days = datetime.now() + timedelta(days=90)
expiring_soon = inventory_collection.count_documents({
    'hospital': 'A',
    'expiry_date': {'$lt': ninety_days, '$gt': datetime.now()}
})
print(f"   - Items expiring within 90 days: {expiring_soon}")

# Find low stock items (< 100)
low_stock = inventory_collection.count_documents({
    'hospital': 'A',
    'quantity': {'$lt': 100}
})
print(f"   - Low stock items (< 100 units): {low_stock}")

client.close()
