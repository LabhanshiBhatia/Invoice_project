import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect("database.db")

customers = [
    "Acme Corp", "Reliance Ltd", "TechStart AI", "Infosys", "Wipro",
    "Tata Consultancy", "HCL Technologies", "Mahindra Group", "Bajaj Auto",
    "Zomato India", "Swiggy Pvt Ltd", "Paytm Payments", "PhonePe Ltd",
    "Razorpay Inc", "Freshworks", "Zoho Corp", "MakeMyTrip", "Nykaa Fashion",
    "Meesho Network", "Ola Electric", "Byju's Ed", "Unacademy", "Groww App",
    "Zerodha Pvt", "Angel One", "Upstox India", "Dream11 Sports", "CRED Club",
    "ShareChat", "Lenskart", "Boat Lifestyle", "Mamaearth", "Sugar Cosmetics",
    "Wakefit Sleep", "Urban Company", "BlueStone Jewels", "CarDekho", "Policy Bazaar"
]

products = [
    "Web Design", "Brand Strategy", "Dev Retainer", "SEO Audit", "UI/UX Design",
    "Mobile App Dev", "Logo Design", "Social Media Mgmt", "Content Writing",
    "Video Editing", "Email Campaign", "PPC Management", "Data Analytics",
    "Cloud Setup", "Cybersecurity Audit", "CRM Integration", "API Development",
    "ERP Implementation", "Digital Marketing", "Copywriting", "Pitch Deck Design",
    "Photography", "3D Modelling", "Motion Graphics", "DevOps Setup",
    "React Development", "Flutter App", "WordPress Site", "Shopify Store",
    "ChatBot Development"
]

statuses = ["paid", "unpaid", "overdue"]
status_weights = [0.6, 0.25, 0.15]  # 60% paid, 25% unpaid, 15% overdue

entries = []
base_date = datetime(2024, 1, 1)

for _ in range(5000):
    customer  = random.choice(customers)
    product   = random.choice(products)
    price     = round(random.choice([500, 1000, 1500, 2000, 2500, 5000,
                                     7500, 10000, 15000, 20000, 25000, 50000]), 2)
    qty       = random.randint(1, 10)
    tax_rate  = random.choice([0, 5, 12, 18, 28])
    subtotal  = round(price * qty, 2)
    tax_amt   = round(subtotal * tax_rate / 100, 2)
    grand     = round(subtotal + tax_amt, 2)
    status    = random.choices(statuses, weights=status_weights)[0]
    created   = base_date + timedelta(days=random.randint(0, 470))
    created_at = created.isoformat()

    entries.append((customer, product, price, qty, subtotal, tax_rate, tax_amt, grand, status, created_at))

conn.executemany("""
    INSERT INTO invoices
        (customer, product, price, qty, subtotal, tax_rate, tax_amt, grand_total, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", entries)

conn.commit()
conn.close()

print(f"✅ Done — inserted {len(entries)} invoices into database.db")