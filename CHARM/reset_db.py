from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client.hospital_inventory

# Clear collections to allow re-seeding
db['inventory_a'].drop()
db['usage_logs'].delete_many({'hospital': 'A'}) # Only clear usage for A

print("✅ Hospital A inventory and usage logs cleared.")
