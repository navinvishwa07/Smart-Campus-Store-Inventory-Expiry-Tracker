
import sys
import os
import random
from datetime import date, timedelta
from sqlalchemy import text

# Add parent directory to path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, engine, Base
from backend.models import Product, Batch, Supplier, ItemCategory

def seed_db():
    print("Seeding database with ~300 items...")
    db = SessionLocal()

    # Clear existing data - ensure clean slate
    try:
        db.execute(text("DELETE FROM transactions")) # Delete transactions first due to FK
        db.execute(text("DELETE FROM batches"))      # Delete batches second
        db.execute(text("DELETE FROM purchase_orders"))
        db.execute(text("DELETE FROM products"))     # Delete products third
        db.execute(text("DELETE FROM suppliers"))    # Delete suppliers last
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error clearing tables: {e}")
        return

    # Seed Suppliers (One per category)
    print("Creating suppliers...")
    suppliers = {}
    for cat in ItemCategory:
        supplier = Supplier(
            name=f"{cat.value} Distributor Inc.",
            category=cat.value,
            contact_email=f"sales@{cat.name.lower()}.com",
            phone=f"555-01{random.randint(10, 99)}"
        )
        db.add(supplier)
        suppliers[cat.value] = supplier
    db.commit()

    # Generate ~300 Products
    print("Generating products...")
    products_data = []

    # Category specific data templates
    categories = {
        ItemCategory.SOFT_DRINKS: ["Cola", "Lemon Lime", "Orange Soda", "Root Beer", "Ginger Ale", "Club Soda", "Tonic Water", "Energy Drink", "Iced Tea", "Lemonade"],
        ItemCategory.CANNED: ["Tomato Soup", "Chicken Soup", "Corn", "Peas", "Beans", "Peaches", "Pears", "Tuna", "Salmon", "Chili"],
        ItemCategory.DAIRY: ["Milk", "Cheese", "Yogurt", "Butter", "Cream", "Eggs", "Cottage Cheese", "Sour Cream", "Almond Milk", "Soy Milk"],
        ItemCategory.BAKING_GOODS: ["Flour", "Sugar", "Baking Powder", "Yeast", "Chocolate Chips", "Cocoa Powder", "Vanilla Extract", "Cake Mix", "Brownie Mix", "Frosting"],
        ItemCategory.FROZEN_FOODS: ["Pizza", "Ice Cream", "Vegetables", "Waffles", "Burritos", "Fish Sticks", "Chicken Nuggets", "Fries", "Dumplings", "Fruit"],
        ItemCategory.FRUITS_VEGETABLES: ["Apple", "Banana", "Carrot", "Potato", "Onion", "Tomato", "Lettuce", "Cucumber", "Orange", "Pepper"],
        ItemCategory.SNACK_FOODS: ["Chips", "Pretzels", "Popcorn", "Crackers", "Cookies", "Nuts", "Granola Bar", "Candy", "Chocolate", "Gum"],
        ItemCategory.HOUSEHOLD: ["Detergent", "Soap", "Paper Towels", "Toilet Paper", "Trash Bags", "Light Bulbs", "Batteries", "Cleaner", "Sponge", "Foil"],
        ItemCategory.HEALTH_HYGIENE: ["Shampoo", "Soap", "Toothpaste", "Deodorant", "Lotion", "Sunscreen", "Vitamins", "Bandages", "Tissue", "Razor"]
    }

    brands = ["StoreBrand", "Premium", "Organic", "Value", "BestChoice", "EcoErrors", "ChefSelect", "HomeBasic", "FreshField", "GreenValley", "Golden", "Sunny", "Daily", "Prime"]
    variants = ["Original", "Large", "Small", "Regular", "Family Size", "Mini", "Spicy", "Sweet", "Unsalted", "Low Fat", "Classic", "Extra"]

    count = 1
    total_target = 300
    
    # We loop until we hit the target count
    while count <= total_target:
        for cat, items in categories.items():
            if count > total_target: break
            
            item_base = random.choice(items)
            brand = random.choice(brands)
            variant = random.choice(variants)
            name = f"{brand} {item_base} {variant}"
            
            # Simple check to avoid exact duplicate names in this batch
            exists = False
            for p in products_data:
                if p['name'] == name: 
                    exists = True
                    break
            if exists: continue

            # Pricing logic
            base_price = random.uniform(25, 550)
            mrp = round(base_price * random.uniform(1.1, 1.4), 2)
            
            products_data.append({
                "item_id": f"ITM{count:04d}",
                "name": name,
                "category": cat.value,
                "mrp": mrp,
                "barcode": f"890123{count:04d}",
                "min_stock": random.randint(5, 20),
            })
            count += 1

    # Add items to DB
    print(f"Adding {len(products_data)} products to database...")
    db_products = []
    for p_data in products_data:
        prod = Product(
            item_id=p_data["item_id"],
            name=p_data["name"],
            category=p_data["category"],
            mrp=p_data["mrp"],
            barcode=p_data["barcode"],
            min_stock=p_data["min_stock"]
        )
        db.add(prod)
        db_products.append(prod)
    db.commit()
    
    # Refresh to get IDs
    for p in db_products:
        db.refresh(p)

    # Seed Batches for each product
    print("Creating batches...")
    batch_count = 0
    for prod in db_products:
        # 1-3 batches per product
        num_batches = random.choices([1, 2, 3], weights=[0.5, 0.3, 0.2])[0]
        
        for i in range(num_batches):
            # Expiry logic: 
            # 5% Expired (-30 to -1 days)
            # 10% Critical (1 to 7 days)
            # 15% Warning (8 to 15 days)
            # 70% Fresh (16 to 365 days)
            rand_val = random.random()
            today = date.today()
            
            if rand_val < 0.05:
                # Expired
                expiry = today - timedelta(days=random.randint(1, 45))
            elif rand_val < 0.15:
                # Critical
                expiry = today + timedelta(days=random.randint(1, 7))
            elif rand_val < 0.30:
                # Warning
                expiry = today + timedelta(days=random.randint(8, 15))
            else:
                # Fresh
                expiry = today + timedelta(days=random.randint(16, 400))

            # Cost price logic (margin)
            cost_price = round(prod.mrp * random.uniform(0.6, 0.85), 2)
            
            qty = random.randint(10, 100)
            
            batch = Batch(
                product_id=prod.id,
                batch_number=f"BATCH-{prod.item_id}-{i+1}",
                quantity=qty,
                cost_price=cost_price,
                expiry_date=expiry,
                manufacture_date=expiry - timedelta(days=180)
            )
            db.add(batch)
            batch_count += 1
    
    db.commit()
    print(f"Database seeded successfully with {len(db_products)} items and {batch_count} batches!")
    db.close()

if __name__ == "__main__":
    seed_db()
