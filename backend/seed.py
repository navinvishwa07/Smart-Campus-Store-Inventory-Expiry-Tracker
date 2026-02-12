"""
Seed script to populate the database with 50+ items from the CSV dataset.
Generates realistic batch data with varying expiry dates.
"""
import csv
import random
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from backend.database import SessionLocal, init_db
from backend.models import Product, Batch, Transaction

# Campus store product names mapped to categories
PRODUCT_NAMES = {
    "Soft Drinks": [
        "Coca-Cola 500ml", "Pepsi 500ml", "Sprite 330ml", "Mountain Dew 500ml",
        "Red Bull 250ml", "Tropicana Orange 1L", "Limca 300ml", "Fanta 500ml",
        "Maaza Mango 250ml", "Sting Energy 250ml"
    ],
    "Canned": [
        "Baked Beans 400g", "Sweet Corn 200g", "Tuna Chunks 185g", "Chickpeas 400g",
        "Tomato Soup 300ml", "Green Peas 200g", "Mushroom Can 400g", "Pineapple Slices 440g"
    ],
    "Dairy": [
        "Amul Milk 500ml", "Greek Yogurt 200g", "Cheese Slices 100g", "Butter 100g",
        "Paneer 200g", "Curd 400ml", "Lassi Mango 200ml", "Cream 100ml"
    ],
    "Baking Goods": [
        "Wheat Flour 1kg", "Sugar 500g", "Baking Powder 100g", "Vanilla Extract 50ml",
        "Cocoa Powder 200g", "Yeast Packet 10g", "All-Purpose Flour 1kg"
    ],
    "Frozen Foods": [
        "Frozen Pizza 300g", "Ice Cream Vanilla 500ml", "Frozen Fries 450g",
        "Fish Fingers 300g", "Frozen Parathas 400g", "Frozen Momos 300g",
        "Ice Cream Chocolate 500ml"
    ],
    "Fruits & Vegetables": [
        "Apple Pack 1kg", "Banana Bunch", "Tomato 500g", "Onion 1kg",
        "Potato 1kg", "Carrot 500g", "Spinach Bunch", "Orange Pack 1kg"
    ],
    "Snack Foods": [
        "Lays Classic 100g", "Kurkure 100g", "Oreos 120g", "Biscuits 200g",
        "Peanuts Salted 200g", "Trail Mix 150g", "Popcorn 100g", "Nachos 150g"
    ],
    "Household": [
        "Hand Sanitizer 250ml", "Tissue Box 100ct", "Detergent 500g",
        "Dish Soap 200ml", "Garbage Bags 30ct", "Paper Towels 2pk",
        "Air Freshener 300ml"
    ],
    "Health and Hygiene": [
        "Toothpaste 100g", "Shampoo 200ml", "Hand Wash 250ml", "Face Mask 10ct",
        "Bandages 20ct", "Vitamin C 30ct", "Pain Relief 10ct"
    ]
}

# Shelf life in days by category
SHELF_LIFE = {
    "Soft Drinks": (90, 365),
    "Canned": (180, 730),
    "Dairy": (5, 30),
    "Baking Goods": (90, 365),
    "Frozen Foods": (30, 180),
    "Fruits & Vegetables": (3, 14),
    "Snack Foods": (60, 180),
    "Household": (365, 1095),
    "Health and Hygiene": (180, 730),
}


def generate_barcode(item_id: str) -> str:
    """Generate a 13-digit EAN barcode."""
    base = f"890{item_id.replace('ITM', '').zfill(9)}"
    return base[:12] + str(random.randint(0, 9))


def seed_database():
    """Populate DB with products, batches, and sample transactions."""
    init_db()
    db: Session = SessionLocal()

    # Check if already seeded
    if db.query(Product).count() > 0:
        print("Database already seeded. Skipping.")
        db.close()
        return

    try:
        csv_path = "medium_sales_dataset.csv"
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        products_created = 0
        used_names = set()

        for row in rows:
            category = row["Item_Type"]
            if category not in PRODUCT_NAMES:
                continue

            # Pick a unique product name
            available = [n for n in PRODUCT_NAMES[category] if n not in used_names]
            if not available:
                continue

            name = available[0]
            used_names.add(name)
            item_id = row["Item_ID"]

            product = Product(
                item_id=item_id,
                name=name,
                category=category,
                fat_content=row.get("Item_Fat_Content", "Regular"),
                weight=float(row.get("Item_Weight", 0)),
                mrp=float(row.get("Item_MRP", 0)),
                barcode=generate_barcode(item_id),
                min_stock=random.randint(5, 20),
            )
            db.add(product)
            db.flush()

            # Create 2-4 batches per product with varying expiry
            shelf_min, shelf_max = SHELF_LIFE.get(category, (30, 180))
            num_batches = random.randint(2, 4)

            for b in range(num_batches):
                days_offset = random.randint(-10, shelf_max)
                expiry = date.today() + timedelta(days=days_offset)
                mfg = expiry - timedelta(days=random.randint(shelf_min, shelf_max))
                qty = random.randint(0, 50)

                batch = Batch(
                    product_id=product.id,
                    batch_number=f"B{item_id}-{b+1:02d}",
                    quantity=qty,
                    cost_price=round(float(row["Item_MRP"]) * 0.6, 2),
                    manufacture_date=mfg,
                    expiry_date=expiry,
                )
                db.add(batch)
                db.flush()

                # Generate sample sale transactions
                num_sales = random.randint(1, 5)
                for _ in range(num_sales):
                    sale_qty = random.randint(1, max(1, qty // 3))
                    sale_date = datetime.now() - timedelta(
                        days=random.randint(0, 60)
                    )
                    tx = Transaction(
                        product_id=product.id,
                        batch_id=batch.id,
                        transaction_type="sale",
                        quantity=sale_qty,
                        unit_price=float(row["Item_MRP"]),
                        total_amount=round(sale_qty * float(row["Item_MRP"]), 2),
                        transaction_date=sale_date,
                    )
                    db.add(tx)

                # Occasional wastage
                if random.random() < 0.15:
                    waste_qty = random.randint(1, max(1, qty // 5))
                    tx = Transaction(
                        product_id=product.id,
                        batch_id=batch.id,
                        transaction_type="wastage",
                        quantity=waste_qty,
                        unit_price=float(row["Item_MRP"]),
                        total_amount=round(waste_qty * float(row["Item_MRP"]), 2),
                        transaction_date=datetime.now() - timedelta(
                            days=random.randint(0, 30)
                        ),
                        notes="Expired / Damaged",
                    )
                    db.add(tx)

            products_created += 1
            if products_created >= 65:
                break

        db.commit()
        print(f"✅ Seeded {products_created} products with batches and transactions.")
    except Exception as e:
        db.rollback()
        print(f"❌ Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
