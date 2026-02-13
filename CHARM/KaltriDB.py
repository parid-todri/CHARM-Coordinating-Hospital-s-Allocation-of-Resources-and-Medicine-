from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

client = MongoClient('mongodb://localhost:27017/')
db = client.hospital_inventory
usage_collection = db['usage_logs']

def log_usage(hospital, medication, quantity_change, action, user):
    """Logs any change to inventory (add, use, edit, delete)"""
    log_entry = {
        "hospital": hospital,
        "medication": medication,
        "quantity_change": quantity_change,
        "action": action,
        "user": user,
        "date": datetime.now()
    }
    usage_collection.insert_one(log_entry)

def add_item(hospital, name, quantity, cost, date_added, expiry_date, user="System"):
    collection = db[f"inventory_{hospital.lower()}"]
    item = {
        "name": name,
        "quantity": quantity,
        "cost": cost,
        "date_added": date_added,
        "expiry_date": expiry_date
    }
    collection.insert_one(item)
    log_usage(hospital, name, quantity, "added", user)

def get_inventory(hospital):
    collection = db[f"inventory_{hospital.lower()}"]
    return list(collection.find({}))

def update_quantity(hospital, item_id, new_quantity, user):
    collection = db[f"inventory_{hospital.lower()}"]
    item = collection.find_one({"_id": ObjectId(item_id)})
    
    if item:
        old_quantity = item['quantity']
        diff = new_quantity - old_quantity
        
        if diff != 0:
            collection.update_one({"_id": ObjectId(item_id)}, {"$set": {"quantity": new_quantity}})
            action = "restock" if diff > 0 else "usage"
            log_usage(hospital, item['name'], diff, action, user)
            return True
    return False

def delete_item(hospital, item_id, user):
    collection = db[f"inventory_{hospital.lower()}"]
    item = collection.find_one({"_id": ObjectId(item_id)})
    
    if item:
        collection.delete_one({"_id": ObjectId(item_id)})
        log_usage(hospital, item['name'], -item['quantity'], "removed", user)
        return True
    return False

def get_usage_logs(hospital):
    """Get usage logs for a specific hospital"""
    return list(usage_collection.find({"hospital": hospital}).sort("date", -1))
