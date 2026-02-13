# 🏥 CHARM — Coordinating Hospital's Allocation of Resources and Medicine

<p align="center">
  <img src="static/images/charm_logo.png" alt="CHARM Logo" width="80">
</p>

<p align="center">
  A modern, full-stack hospital inventory management and analytics platform built with Flask and MongoDB.
</p>

---

## ✨ Features

### 📦 Inventory Management
- **Add, edit, delete** medications with barcode-aware forms
- **Hospital-scoped** inventories (Hospital A, Hospital B, etc.)
- **Expiry tracking** with 90-day advance alerts
- **Low stock detection** (< 100 units) with reorder recommendations

### 📊 Analytics Dashboard
- **Real-time KPI cards** — Total used, most-used medication, stock efficiency, expiring items, low stock
- **Top Medications Used** — Interactive Chart.js bar chart
- **Stock Flow** — Purchase vs Usage comparison (grouped bars)
- **Monthly filtering** — Analyze any month from 2025-01 to present

### 🔄 Inter-Hospital Resource Requests
- **Request medications** from partner hospitals
- **Approve / Reject** incoming requests from admin panel
- **Track request status** (Pending → Approved / Rejected)

### 🎨 Modern UI/UX
- **Glassmorphism** cards with animated gradients
- **Staggered entrance** animations on page load
- **Hover micro-interactions** — lift, glow, icon bounce, button pulse
- **Responsive layout** — works on desktop and tablet
- **Dark teal + white** color palette with CSS custom properties

---

## 🛠 Tech Stack

| Layer         | Technology              |
|---------------|-------------------------|
| **Backend**   | Python 3, Flask 2+      |
| **Database**  | MongoDB (via PyMongo 4) |
| **Frontend**  | Jinja2, Vanilla CSS, Chart.js |
| **Auth**      | Session-based with Werkzeug password hashing |
| **AI/ML**     | scikit-learn, pandas (copilot module) |
| **Testing**   | pytest                  |

---

## 📂 Project Structure

```
Kaltri/
├── app.py                  # Flask application & routes
├── KaltriDB.py             # Database helper functions (CRUD)
├── import_nene_data.py     # CSV → MongoDB data import script
├── reset_db.py             # Database reset utility
├── requirements.txt        # Python dependencies
│
├── charm/                  # AI Copilot module
│   ├── db.py               # Database connector
│   ├── ingest.py           # Data ingestion pipeline
│   └── ...
│
├── data/
│   └── nene_tereza_synthetic_orders_2025_with_consumption.csv
│
├── static/
│   ├── css/style.css       # Global styles + animations
│   └── images/             # Logo and assets
│
├── templates/
│   ├── base.html           # Layout with navbar + footer
│   ├── index.html          # Home page (animated cards)
│   ├── dashboard.html      # Analytics + Chart.js graphs
│   ├── list.html           # Inventory table
│   ├── add.html             # Add/Edit medication form
│   ├── login.html          # Authentication
│   ├── request.html        # Submit inter-hospital request
│   ├── requests.html       # Incoming requests (admin)
│   └── my_requests.html    # Outgoing request tracker
│
└── tests/
    └── test_schema.py      # Schema validation tests
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- MongoDB running locally on `mongodb://localhost:27017/`

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd Kaltri

# Install dependencies
pip install -r requirements.txt

# Start the application
python3 app.py
```

The app will be available at **http://127.0.0.1:5000**.

### Default Accounts

| Username       | Password      | Role             | Hospital |
|----------------|---------------|------------------|----------|
| `admin_a`      | `password123` | Hospital Admin   | A        |
| `admin_b`      | `password123` | Hospital Admin   | B        |
| `distributor1` | `password123` | Distributor      | —        |

### Import Sample Data

To load the Nene Tereza 2025 synthetic dataset (240 medication orders, 20 medications):

```bash
python3 import_nene_data.py
```

---

## 📈 Dataset

The included dataset (`nene_tereza_synthetic_orders_2025_with_consumption.csv`) contains:

- **240 rows** of medication orders across 12 months (Jan–Dec 2025)
- **20 unique medications** including Paracetamol, Amoxicillin, Atorvastatin, Insulin Glargine, Ceftriaxone, and more
- Fields: `medication_name`, `quantity`, `unit_cost`, `order_date`, `expiration_date`, `quantity_used`, `avg_daily_consumption`

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📸 Screenshots

### Home Page
Ultra-compact layout with staggered card entrance animations, hover lift effects, and glowing title.

### Analytics Dashboard
Real-time metrics with Chart.js visualizations — monthly medication usage trends and purchase-vs-usage stock flow analysis.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is for educational and demonstration purposes.

---

<p align="center">
  Built with ❤️ for hospital resource management
</p>
