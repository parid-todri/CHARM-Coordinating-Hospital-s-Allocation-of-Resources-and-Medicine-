from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from KaltriDB import add_item, get_inventory, update_quantity, delete_item, get_usage_logs
from datetime import datetime, timedelta
import re
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from bson import ObjectId

app = Flask(__name__)
app.secret_key = "supersecretkey"

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['hospital_inventory']
requests_collection = db['requests']
users_collection = db['users']


# --- Seed default users on startup ---
def seed_users():
    if users_collection.count_documents({}) == 0:
        default_users = [
            {
                "username": "admin_a",
                "password": generate_password_hash("password123", method="pbkdf2:sha256"),
                "role": "hospital_admin",
                "hospital": "A",
                "display_name": "Hospital A Admin"
            },
            {
                "username": "admin_b",
                "password": generate_password_hash("password123", method="pbkdf2:sha256"),
                "role": "hospital_admin",
                "hospital": "B",
                "display_name": "Hospital B Admin"
            },
            {
                "username": "distributor1",
                "password": generate_password_hash("password123", method="pbkdf2:sha256"),
                "role": "distributor",
                "hospital": None,
                "display_name": "Main Distributor"
            },
        ]
        users_collection.insert_many(default_users)
        print("✅ Default users seeded.")

def seed_real_data():
    # Check if we already have data to avoid duplicates
    if db['inventory_a'].count_documents({}) > 0:
        return

    print("🌱 Seeding real data for Hospital A...")
    
    # 1. Purchases (Jan 5, 2025)
    purchases = [
        ("Paracetamol", 1200, 1.50, "2025-01-05", "2027-01-05"),
        ("Amoxicillin 500mg", 600, 5.00, "2025-01-05", "2026-05-07"),
        ("Ceftriaxone 1g", 180, 12.00, "2025-01-05", "2026-01-05"),
        ("Ibuprofen 400mg", 500, 2.00, "2025-01-05", "2027-01-05"),
        ("Metformin 850mg", 400, 3.00, "2025-01-05", "2028-01-05"),
        ("Salbutamol inhaler", 90, 8.50, "2025-01-05", "2026-05-12"),
        ("Insulin glargine", 70, 25.00, "2025-01-05", "2026-01-05"),
        ("Omeprazole 20mg", 300, 4.00, "2025-01-05", "2027-01-05"),
        ("Enoxaparin injection", 110, 15.00, "2025-01-05", "2026-05-03"),
        ("Diazepam injection", 40, 6.00, "2025-01-05", "2026-01-05"),
        ("Furosemide 40mg", 200, 2.50, "2025-01-05", "2028-01-05"),
        ("Atorvastatin 20mg", 350, 10.00, "2025-01-05", "2028-01-05"),
        ("Hydrocortisone", 75, 5.50, "2025-01-05", "2026-05-05"),
        ("Adrenaline ampoules", 60, 4.50, "2025-01-05", "2026-01-05"),
        ("Meropenem 1g", 35, 30.00, "2025-01-05", "2026-05-09"),
        ("Vancomycin 1g", 45, 18.00, "2025-01-05", "2026-05-06"),
        ("Heparin sodium", 95, 14.00, "2025-01-05", "2026-05-02"),
        ("Ringer's lactate", 220, 3.00, "2025-01-05", "2028-01-05"),
        ("Normal saline", 260, 2.50, "2025-01-05", "2028-01-05"),
        ("Vitamin C injection", 150, 1.20, "2025-01-05", "2027-01-05")
    ]

    for p in purchases:
        add_item("A", p[0], p[1], p[2], p[3], p[4], user="System Import")

    # 2. Usage Data (Simulated exact dates in Jan)
    # Using the negative values from the provided image
    usage_entries = [
        ("Paracetamol", 28), ("Amoxicillin 500mg", 55), ("Ceftriaxone 1g", 81),
        ("Ibuprofen 400mg", 107), ("Metformin 850mg", 134), ("Salbutamol inhaler", 160),
        ("Insulin glargine", 187), ("Omeprazole 20mg", 213), ("Enoxaparin injection", 239),
        ("Diazepam injection", 266), ("Furosemide 40mg", 292), ("Atorvastatin 20mg", 319),
        ("Hydrocortisone", 345), ("Adrenaline ampoules", 371), ("Meropenem 1g", 398),
        # Assuming some items might be used more than purchased in the dataset 
        # (e.g. Meropenem purchased 35, used 398? That implies negative stock. 
        # I'll clamp usage to available stock to avoid negative inventory for now, 
        # or maybe the purchased amount was just one batch.
        # Let's cap usage at purchase quantity - 1 so we have some stock left for demo.)
    ]

    for u in usage_entries:
        # Get current item to find its ID
        item = db['inventory_a'].find_one({"name": u[0]})
        if item:
            qty_to_use = min(u[1], item['quantity'] - 1) # Keep at least 1 in stock
            if qty_to_use > 0:
                # Calculate new quantity
                new_qty = item['quantity'] - qty_to_use
                update_quantity("A", item['_id'], new_qty, "System Import (Usage)")

    print("✅ Real data seeded.")


# --- Auth decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                flash("Please log in to access this page.", "error")
                return redirect(url_for('login'))
            if session.get('role') != role:
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def parse_date(date_str):
    date_str = re.sub(r'\D', '', date_str)
    match = re.search(r'(\d{4})(\d{2})(\d{2})', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    else:
        return None


# --- Auth routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['role'] = user['role']
            session['hospital'] = user.get('hospital')
            session['display_name'] = user['display_name']
            flash(f"Welcome, {user['display_name']}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "error")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))


# --- Main routes ---
@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/add', methods=['GET', 'POST'])
@role_required('hospital_admin')
def add():
    if request.method == 'POST':
        hospital = session.get('hospital', 'A')
        name = request.form['name'].strip()
        quantity = int(request.form['quantity'].strip())
        cost = float(request.form['cost'].strip())
        date_added = parse_date(request.form['date_added'].strip())
        expiry_date = parse_date(request.form['expiry_date'].strip())

        if date_added and expiry_date:
            add_item(hospital, name, quantity, cost, date_added, expiry_date, user=session.get('display_name', 'Unknown'))
            flash("Item added successfully.", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid date format. Please ensure the date contains at least 8 digits (YYYYMMDD).", "error")

    return render_template('add.html')


@app.route('/list')
@login_required
def list_items():
    if session.get('role') == 'hospital_admin':
        hospital = session.get('hospital', '').upper()
    else:
        hospital = request.args.get('hospital', '').strip().upper()

    inventory = get_inventory(hospital) if hospital else []
    usage_logs = get_usage_logs(hospital) if hospital else []
    
    if not inventory and hospital:
        flash("No items found for this hospital.", "error")
    return render_template('list.html', inventory=inventory, usage_logs=usage_logs, hospital=hospital)


@app.route('/update_item/<item_id>', methods=['POST'])
@login_required
def update_item_route(item_id):
    if session.get('role') != 'hospital_admin':
        flash("Unauthorized", "error")
        return redirect(url_for('index'))
        
    hospital = session.get('hospital')
    new_quantity = int(request.form['quantity'])
    user = session.get('display_name')
    
    if update_quantity(hospital, item_id, new_quantity, user):
        flash("Item quantity updated.", "success")
    else:
        flash("Failed to update item.", "error")
        
    return redirect(url_for('list_items'))


@app.route('/delete_item/<item_id>', methods=['POST'])
@login_required
def delete_item_route(item_id):
    if session.get('role') != 'hospital_admin':
        flash("Unauthorized", "error")
        return redirect(url_for('index'))

    hospital = session.get('hospital')
    user = session.get('display_name')
    
    if delete_item(hospital, item_id, user):
        flash("Item deleted.", "success")
    else:
        flash("Failed to delete item.", "error")
        
    return redirect(url_for('list_items'))


# --- Dashboard ---
@app.route('/dashboard')
@login_required
def dashboard():
    usage_collection = db['usage_logs']
    
    # Get available months for filter dropdown
    # Format: YYYY-MM
    pipeline_months = [
        {
            '$project': {
                'month_str': {'$dateToString': {'format': '%Y-%m', 'date': '$date'}}
            }
        },
        {'$group': {'_id': '$month_str'}},
        {'$sort': {'_id': -1}}
    ]
    available_months_docs = list(usage_collection.aggregate(pipeline_months))
    available_months = [d['_id'] for d in available_months_docs]
    
    # Current month default
    current_month_str = datetime.now().strftime('%Y-%m')
    selected_month = request.args.get('month', current_month_str)
    
    # 1. Total Usage per Medication (Filtered by Month)
    pipeline_usage = [
        {
            '$addFields': {
                'month_str': {'$dateToString': {'format': '%Y-%m', 'date': '$date'}}
            }
        },
        {'$match': {'type': {'$ne': 'purchase'}, 'month_str': selected_month}}, 
        # Note: 'type' might be 'usage' or 'removed'. We want consumption.
        # Let's assume 'action' field usage: 'usage', 'removed', 'restock', 'added'.
        # Previously we had 'type'. Now we have 'action'.
        # Let's adjust for the new schema: 'action' in ['usage', 'removed'] count as usage.
        # But wait, old data had 'type'. New data has 'action'.
        # I need to handle both or migrate.
        # Since I reset the DB, we have only New Data with 'action'.
        # Actions: 'added', 'restock', 'usage', 'removed'.
        # We want to show USAGE (consumption).
        # So action='usage' or 'removed'? Probably 'usage'. 'removed' is waste/adjustment.
        # Let's include both as "Outflow" for now, or just 'usage' if strict.
        # User asked for "usage". Let's stick to action='usage' or 'removed' (as depletion).
        
        {'$match': {'action': {'$in': ['usage', 'removed']}}},
        {'$group': {'_id': '$medication', 'total_usage': {'$sum': {'$abs': '$quantity_change'}}}},
        {'$sort': {'total_usage': -1}}
    ]
    usage_data = list(usage_collection.aggregate(pipeline_usage))
    
    # 2. Balance (Restock vs Usage)
    pipeline_balance = [
        {
            '$addFields': {
                'month_str': {'$dateToString': {'format': '%Y-%m', 'date': '$date'}}
            }
        },
        {'$match': {'month_str': selected_month}},
        {'$group': {
            '_id': '$medication',
            'purchased': {
                '$sum': {'$cond': [{'$in': ['$action', ['added', 'restock']]}, '$quantity_change', 0]}
            },
            'used': {
                '$sum': {'$cond': [{'$in': ['$action', ['usage', 'removed']]}, {'$abs': '$quantity_change'}, 0]}
            }
        }}
    ]
    balance_data = list(usage_collection.aggregate(pipeline_balance))

    # 3. Key Metrics (Snapshot of current inventory, not monthly)
    # Expiring Soon (within 90 days)
    today = datetime.now()
    ninety_days = today + timedelta(days=90)
    # Since dates are stored as strings "YYYY-MM-DD" in my add_item... wait.
    # KaltriDB.add_item stores date_added and expiry_date as passed.
    # My parse_date returns "YYYY-MM-DD".
    # String comparison works for ISO dates.
    expiring_count = 0
    low_stock_count = 0
    
    # We need to iterate all hospitals or just the logged in one?
    # Dashboard implies global or specific? 
    # The previous dashboard code didn't filter by hospital for metrics, but usage logs sort of did?
    # Actually usage logs were global in the previous code?
    # `usage_collection = db['usage_logs']`
    # `list(usage_collection.aggregate(...))` matches ALL.
    # The user is likely a "Hospital Admin" (e.g. A).
    # Metrics should probably be for THEIR hospital if they are admin.
    
    hospital_filter = session.get('hospital')
    if hospital_filter:
         # Filter usage logs by hospital as well for more accuracy
         # Inject match stage at start of pipelines?
         # For simplicity, I'll keep usage global (or per hospital if I add match).
         # Let's filter metrics by hospital at least.
         inventory_col = db[f"inventory_{hospital_filter.lower()}"]
         all_items = list(inventory_col.find({}))
         
         ninety_days_str = ninety_days.strftime('%Y-%m-%d')
         
         for item in all_items:
             if item.get('expiry_date') and item['expiry_date'] <= ninety_days_str:
                 expiring_count += 1
             if item.get('quantity', 0) < 100: # Threshold for Low Stock
                 low_stock_count += 1

    return render_template('dashboard.html', 
                         usage_data=usage_data,
                         balance_data=balance_data,
                         available_months=available_months,
                         selected_month=selected_month,
                         expiring_count=expiring_count,
                         low_stock_count=low_stock_count)


# --- Request flow ---
@app.route('/request', methods=['GET', 'POST'])
@role_required('hospital_admin')
def request_item():
    if request.method == 'POST':
        hospital = session.get('hospital', 'A')
        item_name = request.form['item_name'].strip()
        quantity = int(request.form['quantity'].strip())

        request_data = {
            'requesting_hospital': hospital,
            'item_name': item_name,
            'quantity': quantity,
            'status': 'pending',  # pending → offered → accepted / declined
            'offers': [],
            'request_time': datetime.now()
        }
        requests_collection.insert_one(request_data)

        flash("Request submitted successfully.", "success")
        return redirect(url_for('index'))

    return render_template('request.html')


@app.route('/requests', methods=['GET'])
@login_required
def requested_items():
    if session.get('role') == 'hospital_admin':
        my_hospital = session.get('hospital', '')
        # Show pending requests from OTHER hospitals
        all_requests = list(requests_collection.find({
            'requesting_hospital': {'$ne': my_hospital},
            'status': 'pending'
        }))
    else:
        all_requests = list(requests_collection.find({}))
    return render_template('requests.html', requests=all_requests)


@app.route('/make_offer/<request_id>', methods=['POST'])
@login_required
def make_offer(request_id):
    price = float(request.form['offer_price'].strip())
    offering_hospital = session.get('hospital') or 'Distributor'

    offer = {
        'offering_hospital': offering_hospital,
        'offer_price': price,
        'offer_time': datetime.now(),
        'status': 'pending'  # offer status: pending → accepted / declined
    }

    requests_collection.update_one(
        {'_id': ObjectId(request_id)},
        {
            '$push': {'offers': offer},
            '$set': {'status': 'offered'}
        }
    )

    flash(f"Your offer of ${price:.2f} has been sent!", "success")
    return redirect(url_for('requested_items'))


@app.route('/my_requests')
@role_required('hospital_admin')
def my_requests():
    my_hospital = session.get('hospital', '')
    my_reqs = list(requests_collection.find({'requesting_hospital': my_hospital}))
    return render_template('my_requests.html', requests=my_reqs)


@app.route('/accept_offer/<request_id>/<int:offer_index>', methods=['POST'])
@role_required('hospital_admin')
def accept_offer(request_id, offer_index):
    req = requests_collection.find_one({'_id': ObjectId(request_id)})
    if not req or req['requesting_hospital'] != session.get('hospital'):
        flash("Unauthorized action.", "error")
        return redirect(url_for('my_requests'))

    # Mark the accepted offer
    requests_collection.update_one(
        {'_id': ObjectId(request_id)},
        {
            '$set': {
                f'offers.{offer_index}.status': 'accepted',
                'status': 'accepted'
            }
        }
    )
    # Decline all other offers
    for i, offer in enumerate(req.get('offers', [])):
        if i != offer_index:
            requests_collection.update_one(
                {'_id': ObjectId(request_id)},
                {'$set': {f'offers.{i}.status': 'declined'}}
            )

    flash("Offer accepted!", "success")
    return redirect(url_for('my_requests'))


@app.route('/decline_offer/<request_id>/<int:offer_index>', methods=['POST'])
@role_required('hospital_admin')
def decline_offer(request_id, offer_index):
    req = requests_collection.find_one({'_id': ObjectId(request_id)})
    if not req or req['requesting_hospital'] != session.get('hospital'):
        flash("Unauthorized action.", "error")
        return redirect(url_for('my_requests'))

    requests_collection.update_one(
        {'_id': ObjectId(request_id)},
        {'$set': {f'offers.{offer_index}.status': 'declined'}}
    )

    # If all offers are declined, set request back to pending
    updated_req = requests_collection.find_one({'_id': ObjectId(request_id)})
    all_declined = all(o.get('status') == 'declined' for o in updated_req.get('offers', []))
    if all_declined:
        requests_collection.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {'status': 'pending'}}
        )

    flash("Offer declined.", "success")
    return redirect(url_for('my_requests'))


# --- AI Copilot API ---
@app.route('/api/copilot', methods=['POST'])
@login_required
def api_copilot():
    """AI Copilot endpoint — predict demand and recommend orders.

    Expects JSON body:
        {
            "month": "April",
            "current_stock": {"Paracetamol 500mg tablets": 200, ...},
            "safety_buffer": 0.20  // optional, default 0.20
        }
    """
    try:
        from charm.copilot import recommend_orders
    except ImportError:
        return jsonify({"error": "CHARM Copilot package not installed. Run `pip install -r requirements.txt`."}), 500

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    month = data.get("month")
    current_stock = data.get("current_stock", {})
    safety_buffer = data.get("safety_buffer", 0.20)

    if not month:
        return jsonify({"error": "Missing required field: 'month'."}), 400

    try:
        recs = recommend_orders(
            next_month=month,
            current_stock=current_stock,
            safety_buffer=safety_buffer,
        )
        return jsonify({"month": month, "safety_buffer": safety_buffer, "recommendations": recs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    seed_users()
    seed_real_data()
    app.run(debug=True)
