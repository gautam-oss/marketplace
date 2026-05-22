"""
Seed the database with realistic marketplace data.
Run from backend/ with venv active:
    python seed.py
"""

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Category, Order, OrderItem, Product, Review, User  # noqa: F401


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ── Wipe existing data (order matters for FK constraints) ──────────────
        for model in [Review, OrderItem, Order, Product, Category, User]:
            await db.execute(delete(model))
        await db.commit()
        print("Cleared existing data.")

        # ── Users ──────────────────────────────────────────────────────────────
        pw = hash_password("Test1234!")

        admin = User(id=uuid.uuid4(), email="admin@marketplace.dev", hashed_password=pw,
                     full_name="Admin User", role="admin", is_active=True, is_verified=True)

        seller1 = User(id=uuid.uuid4(), email="ravi@seller.dev", hashed_password=pw,
                       full_name="Ravi Sharma", role="seller", is_active=True, is_verified=True)

        seller2 = User(id=uuid.uuid4(), email="priya@seller.dev", hashed_password=pw,
                       full_name="Priya Nair", role="seller", is_active=True, is_verified=True)

        buyer1 = User(id=uuid.uuid4(), email="amit@buyer.dev", hashed_password=pw,
                      full_name="Amit Verma", role="buyer", is_active=True, is_verified=True)

        buyer2 = User(id=uuid.uuid4(), email="sneha@buyer.dev", hashed_password=pw,
                      full_name="Sneha Patel", role="buyer", is_active=True, is_verified=True)

        buyer3 = User(id=uuid.uuid4(), email="rohan@buyer.dev", hashed_password=pw,
                      full_name="Rohan Mehta", role="buyer", is_active=True, is_verified=True)

        db.add_all([admin, seller1, seller2, buyer1, buyer2, buyer3])
        await db.flush()
        print("Created 6 users (1 admin, 2 sellers, 3 buyers).")

        # ── Categories ─────────────────────────────────────────────────────────
        electronics = Category(id=uuid.uuid4(), name="Electronics", slug="electronics",
                               description="Gadgets, devices and accessories", sort_order=1)
        fashion = Category(id=uuid.uuid4(), name="Fashion", slug="fashion",
                           description="Clothing, footwear and accessories", sort_order=2)
        home = Category(id=uuid.uuid4(), name="Home & Kitchen", slug="home-kitchen",
                        description="Furniture, appliances and decor", sort_order=3)
        books = Category(id=uuid.uuid4(), name="Books", slug="books",
                         description="Textbooks, fiction, non-fiction", sort_order=4)
        sports = Category(id=uuid.uuid4(), name="Sports & Fitness", slug="sports-fitness",
                          description="Equipment, apparel and nutrition", sort_order=5)

        db.add_all([electronics, fashion, home, books, sports])
        await db.flush()

        # Sub-categories
        phones = Category(id=uuid.uuid4(), name="Smartphones", slug="smartphones",
                          parent_id=electronics.id, sort_order=1)
        laptops = Category(id=uuid.uuid4(), name="Laptops", slug="laptops",
                           parent_id=electronics.id, sort_order=2)
        audio = Category(id=uuid.uuid4(), name="Audio", slug="audio",
                         parent_id=electronics.id, sort_order=3)
        mens = Category(id=uuid.uuid4(), name="Men's Clothing", slug="mens-clothing",
                        parent_id=fashion.id, sort_order=1)
        womens = Category(id=uuid.uuid4(), name="Women's Clothing", slug="womens-clothing",
                          parent_id=fashion.id, sort_order=2)

        db.add_all([phones, laptops, audio, mens, womens])
        await db.flush()
        print("Created 10 categories (5 top-level, 5 sub-categories).")

        # ── Products (seller1 = Ravi: Electronics; seller2 = Priya: Fashion/Home) ──
        products = [
            Product(id=uuid.uuid4(), title="OnePlus Nord CE 3 Lite 5G",
                    slug="oneplus-nord-ce-3-lite-5g",
                    description="6.72\" FHD+ display, Snapdragon 695, 108MP camera, 5000mAh battery. "
                                "Comes with 67W SUPERVOOC fast charger.",
                    price=Decimal("19999"), compare_at_price=Decimal("24999"),
                    stock=45, sku="OP-NRDCE3L-8-128", status="active",
                    seller_id=seller1.id, category_id=phones.id,
                    images=["https://placehold.co/600x400?text=OnePlus+Nord"],
                    tags=["5g", "oneplus", "smartphone"]),

            Product(id=uuid.uuid4(), title="boAt Airdopes 141 TWS Earbuds",
                    slug="boat-airdopes-141-tws",
                    description="42H total playtime, ENx™ Technology, BEAST™ Mode low latency, "
                                "IPX4 water resistance.",
                    price=Decimal("1299"), compare_at_price=Decimal("2990"),
                    stock=200, sku="BOAT-AD141-BLK", status="active",
                    seller_id=seller1.id, category_id=audio.id,
                    images=["https://placehold.co/600x400?text=boAt+Airdopes"],
                    tags=["earbuds", "tws", "boat", "audio"]),

            Product(id=uuid.uuid4(), title="Lenovo IdeaPad Slim 3 Laptop",
                    slug="lenovo-ideapad-slim-3",
                    description="AMD Ryzen 5 7520U, 8GB RAM, 512GB SSD, 15.6\" FHD, Windows 11 Home. "
                                "Thin and light design for everyday productivity.",
                    price=Decimal("42999"), compare_at_price=Decimal("52999"),
                    stock=18, sku="LEN-IPS3-R5-8-512", status="active",
                    seller_id=seller1.id, category_id=laptops.id,
                    images=["https://placehold.co/600x400?text=Lenovo+IdeaPad"],
                    tags=["laptop", "lenovo", "ryzen", "windows11"]),

            Product(id=uuid.uuid4(), title="Mi Smart Band 7",
                    slug="mi-smart-band-7",
                    description="1.62\" AMOLED display, 110 workout modes, blood oxygen monitoring, "
                                "14-day battery life, 5ATM water resistance.",
                    price=Decimal("2799"), compare_at_price=Decimal("3499"),
                    stock=120, sku="MI-SB7-BLK", status="active",
                    seller_id=seller1.id, category_id=electronics.id,
                    images=["https://placehold.co/600x400?text=Mi+Band+7"],
                    tags=["smartband", "fitness", "xiaomi"]),

            Product(id=uuid.uuid4(), title="Allen Solly Men's Slim Fit Shirt",
                    slug="allen-solly-mens-slim-shirt",
                    description="Premium cotton blend, slim fit formal shirt. Available in size M. "
                                "Machine washable. Perfect for office and casual wear.",
                    price=Decimal("899"), compare_at_price=Decimal("1699"),
                    stock=60, sku="AS-MSF-WHT-M", status="active",
                    seller_id=seller2.id, category_id=mens.id,
                    images=["https://placehold.co/600x400?text=Allen+Solly+Shirt"],
                    tags=["shirt", "formal", "men", "cotton"]),

            Product(id=uuid.uuid4(), title="Biba Women's Anarkali Kurta",
                    slug="biba-womens-anarkali-kurta",
                    description="Rayon fabric, floral print, 3/4 sleeves. Size: L. "
                                "Dry clean recommended. Festive and casual wear.",
                    price=Decimal("1299"), compare_at_price=Decimal("2499"),
                    stock=35, sku="BIBA-AK-FLR-L", status="active",
                    seller_id=seller2.id, category_id=womens.id,
                    images=["https://placehold.co/600x400?text=Biba+Kurta"],
                    tags=["kurta", "ethnic", "women", "festive"]),

            Product(id=uuid.uuid4(), title="Prestige Svachh Hard Anodised Kadai",
                    slug="prestige-svachh-hard-anodised-kadai",
                    description="3L capacity, hard anodised aluminium, glass lid with steam vent, "
                                "induction compatible, anti-corrosive coating.",
                    price=Decimal("1799"), compare_at_price=Decimal("2499"),
                    stock=55, sku="PRE-SVKD-3L-HA", status="active",
                    seller_id=seller2.id, category_id=home.id,
                    images=["https://placehold.co/600x400?text=Prestige+Kadai"],
                    tags=["cookware", "kitchen", "prestige", "induction"]),

            Product(id=uuid.uuid4(), title="Atomic Habits — James Clear",
                    slug="atomic-habits-james-clear",
                    description="Paperback, 320 pages. The #1 New York Times bestseller on building "
                                "good habits and breaking bad ones. Perfect for self-improvement.",
                    price=Decimal("399"), compare_at_price=Decimal("799"),
                    stock=150, sku="BK-ATOMHAB-PB", status="active",
                    seller_id=seller2.id, category_id=books.id,
                    images=["https://placehold.co/600x400?text=Atomic+Habits"],
                    tags=["book", "self-help", "habits", "bestseller"]),

            Product(id=uuid.uuid4(), title="Boldfit Gym Gloves",
                    slug="boldfit-gym-gloves",
                    description="Full palm protection, anti-slip grip, wrist support strap. "
                                "Breathable neoprene. Unisex, size M.",
                    price=Decimal("449"), compare_at_price=Decimal("799"),
                    stock=90, sku="BF-GGLOV-M-BLK", status="active",
                    seller_id=seller1.id, category_id=sports.id,
                    images=["https://placehold.co/600x400?text=Gym+Gloves"],
                    tags=["gym", "fitness", "gloves", "sports"]),

            Product(id=uuid.uuid4(), title="Skullcandy Hesh ANC Headphones",
                    slug="skullcandy-hesh-anc",
                    description="Active Noise Cancellation, 22H battery, Rapid Charge (10 min = 4H), "
                                "foldable design, personal sound profile via app.",
                    price=Decimal("5999"), compare_at_price=Decimal("9999"),
                    stock=30, sku="SK-HESHANC-BLK", status="active",
                    seller_id=seller1.id, category_id=audio.id,
                    images=["https://placehold.co/600x400?text=Skullcandy+ANC"],
                    tags=["headphones", "anc", "skullcandy", "audio"]),
        ]

        db.add_all(products)
        await db.flush()
        print(f"Created {len(products)} products.")

        # ── Orders (buyer1 has 2 paid orders; buyer2 has 1 processing order) ──
        addr = {"name": "Amit Verma", "line1": "42 MG Road", "city": "Bengaluru",
                "state": "Karnataka", "pincode": "560001", "phone": "9876543210"}

        order1 = Order(
            id=uuid.uuid4(), buyer_id=buyer1.id, status="paid",
            razorpay_order_id="order_fake_001", razorpay_payment_id="pay_fake_001",
            subtotal=Decimal("21298"), shipping_amount=Decimal("0"),
            tax_amount=Decimal("3833.64"), total=Decimal("25131.64"),
            shipping_address=addr,
        )
        db.add(order1)
        await db.flush()

        db.add_all([
            OrderItem(id=uuid.uuid4(), order_id=order1.id,
                      product_id=products[0].id, quantity=1,
                      unit_price=products[0].price,
                      product_title=products[0].title,
                      product_image=products[0].images[0] if products[0].images else None),
            OrderItem(id=uuid.uuid4(), order_id=order1.id,
                      product_id=products[1].id, quantity=1,
                      unit_price=products[1].price,
                      product_title=products[1].title,
                      product_image=products[1].images[0] if products[1].images else None),
        ])

        order2 = Order(
            id=uuid.uuid4(), buyer_id=buyer1.id, status="delivered",
            razorpay_order_id="order_fake_002", razorpay_payment_id="pay_fake_002",
            subtotal=Decimal("399"), shipping_amount=Decimal("50"),
            tax_amount=Decimal("71.82"), total=Decimal("520.82"),
            shipping_address=addr,
        )
        db.add(order2)
        await db.flush()

        db.add(OrderItem(id=uuid.uuid4(), order_id=order2.id,
                         product_id=products[7].id, quantity=1,
                         unit_price=products[7].price,
                         product_title=products[7].title,
                         product_image=products[7].images[0] if products[7].images else None))

        addr2 = {"name": "Sneha Patel", "line1": "12 Juhu Tara Road", "city": "Mumbai",
                 "state": "Maharashtra", "pincode": "400049", "phone": "9123456789"}

        order3 = Order(
            id=uuid.uuid4(), buyer_id=buyer2.id, status="processing",
            razorpay_order_id="order_fake_003", razorpay_payment_id="pay_fake_003",
            subtotal=Decimal("3098"), shipping_amount=Decimal("0"),
            tax_amount=Decimal("557.64"), total=Decimal("3655.64"),
            shipping_address=addr2,
        )
        db.add(order3)
        await db.flush()

        db.add_all([
            OrderItem(id=uuid.uuid4(), order_id=order3.id,
                      product_id=products[3].id, quantity=1,
                      unit_price=products[3].price,
                      product_title=products[3].title,
                      product_image=products[3].images[0] if products[3].images else None),
            OrderItem(id=uuid.uuid4(), order_id=order3.id,
                      product_id=products[5].id, quantity=1,
                      unit_price=products[5].price,
                      product_title=products[5].title,
                      product_image=products[5].images[0] if products[5].images else None),
        ])
        print("Created 3 orders with items.")

        # ── Reviews ────────────────────────────────────────────────────────────
        reviews = [
            Review(id=uuid.uuid4(), product_id=products[0].id, user_id=buyer1.id,
                   rating=5, title="Excellent phone for the price",
                   body="Battery lasts all day, camera is superb in daylight. 5G connectivity is fast. "
                        "Display colours are vivid. Highly recommended under ₹20k.",
                   is_verified_purchase=True, helpful_count=12),

            Review(id=uuid.uuid4(), product_id=products[0].id, user_id=buyer2.id,
                   rating=4, title="Good but heating during gaming",
                   body="Overall a great phone. Slight heating noticed during BGMI sessions. "
                        "Camera and battery are top notch for this price range.",
                   is_verified_purchase=False, helpful_count=5),

            Review(id=uuid.uuid4(), product_id=products[1].id, user_id=buyer3.id,
                   rating=5, title="Best TWS under ₹1500",
                   body="Sound quality is surprisingly good. Call quality with ENx mic is clear. "
                        "42H total battery is not a lie — tested it myself.",
                   is_verified_purchase=True, helpful_count=8),

            Review(id=uuid.uuid4(), product_id=products[2].id, user_id=buyer2.id,
                   rating=4, title="Solid budget laptop",
                   body="Ryzen 5 handles daily tasks and light coding easily. SSD is fast. "
                        "Display could be brighter but acceptable for indoors. Good buy.",
                   is_verified_purchase=False, helpful_count=3),

            Review(id=uuid.uuid4(), product_id=products[7].id, user_id=buyer1.id,
                   rating=5, title="Changed my life — literally",
                   body="I've read dozens of self-help books and this one actually sticks. "
                        "Practical system, not just motivation. The 1% better every day concept is powerful.",
                   is_verified_purchase=True, helpful_count=21),

            Review(id=uuid.uuid4(), product_id=products[9].id, user_id=buyer3.id,
                   rating=4, title="Great ANC for the price",
                   body="ANC is noticeably effective on flights and in cafes. 22H battery delivers. "
                        "Slight bass boost tuning but overall balanced. Build quality feels premium.",
                   is_verified_purchase=False, helpful_count=6),

            Review(id=uuid.uuid4(), product_id=products[6].id, user_id=buyer2.id,
                   rating=5, title="Perfect kadai, induction works flawlessly",
                   body="Even heating, easy to clean, lid fits perfectly. The hard anodised coating "
                        "is holding up well after 3 months of daily use. Worth every rupee.",
                   is_verified_purchase=True, helpful_count=9),
        ]

        db.add_all(reviews)
        await db.commit()
        print(f"Created {len(reviews)} reviews.")

        print("\nSeed complete!")
        print("\nLogin credentials (all passwords: Test1234!)")
        print("  admin@marketplace.dev   — admin")
        print("  ravi@seller.dev         — seller (electronics)")
        print("  priya@seller.dev        — seller (fashion/home)")
        print("  amit@buyer.dev          — buyer (2 orders)")
        print("  sneha@buyer.dev         — buyer (1 order)")
        print("  rohan@buyer.dev         — buyer (no orders)")


if __name__ == "__main__":
    asyncio.run(seed())
