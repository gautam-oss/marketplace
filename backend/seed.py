"""
Seed: wipe all DB data, upload real product images to S3, create full dataset.
Run from backend/ with venv active:
    python seed.py
"""
import asyncio
import io
import sys
import uuid
import urllib.request
from datetime import datetime
from decimal import Decimal

import boto3
from PIL import Image
from sqlalchemy import delete

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Category, Order, OrderItem, Product, Review, User  # noqa: F401

# ── S3 helpers ────────────────────────────────────────────────────────────────

_s3_client = None

def s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    return _s3_client


def upload_bytes(data: bytes) -> str:
    """Resize to 800×800, convert to JPEG, upload to S3, return public URL."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((800, 800), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    key = f"products/{uuid.uuid4()}.jpg"
    s3().put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=buf.getvalue(),
        ContentType="image/jpeg",
        ACL="public-read",
    )
    return (
        f"https://{settings.S3_BUCKET_NAME}"
        f".s3.{settings.AWS_REGION}.amazonaws.com/{key}"
    )


def fetch_image(seed: str) -> bytes:
    """Download a deterministic photo from picsum.photos by seed string."""
    url = f"https://picsum.photos/seed/{seed}/800/800"
    req = urllib.request.Request(url, headers={"User-Agent": "marketplace-seed/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read()


def upload_image(seed: str, label: str) -> str:
    """Download from picsum + upload to S3. Falls back to picsum URL on failure."""
    print(f"    ^ {label} (seed={seed}) ... ", end="", flush=True)
    try:
        url = upload_bytes(fetch_image(seed))
        print("OK")
        return url
    except Exception as exc:
        print(f"FAIL ({exc}) -- fallback")
        return f"https://picsum.photos/seed/{seed}/800/800"


# ── Product catalog ───────────────────────────────────────────────────────────
# Each entry: title, slug, desc, price, compare_at_price, stock, sku,
#             seeds (list of 2 picsum seed strings), tags, seller, category key

CATALOG = [
    # ── Ravi: Electronics & Sports ─────────────────────────────────────────
    dict(
        title="OnePlus Nord CE 3 Lite 5G",
        slug="oneplus-nord-ce-3-lite-5g",
        desc=(
            "6.72\" FHD+ display, Snapdragon 695 5G, 108MP triple camera, "
            "5000mAh battery with 67W SUPERVOOC fast charging. "
            "Sleek design, 8GB RAM, 128GB storage."
        ),
        price=Decimal("19999"), compare=Decimal("24999"),
        stock=45, sku="OP-NRDCE3L-8-128",
        seeds=["abstract-tech-city", "vibrant-neon-tech"],
        tags=["5g", "oneplus", "smartphone", "snapdragon"],
        seller="ravi", cat="phones",
    ),
    dict(
        title="boAt Airdopes 141 TWS Earbuds",
        slug="boat-airdopes-141-tws",
        desc=(
            "42H total playtime with charging case, ENx™ Technology for clear calls, "
            "BEAST™ Mode low-latency gaming, IPX4 water resistance. "
            "Lightweight at just 4.1g per earbud."
        ),
        price=Decimal("1299"), compare=Decimal("2990"),
        stock=200, sku="BOAT-AD141-BLK",
        seeds=["music-minimal-dark", "audio-wave-blue"],
        tags=["earbuds", "tws", "boat", "wireless", "gaming"],
        seller="ravi", cat="audio",
    ),
    dict(
        title="Lenovo IdeaPad Slim 3",
        slug="lenovo-ideapad-slim-3",
        desc=(
            "AMD Ryzen 5 7520U (up to 4.5GHz), 8GB DDR5 RAM, 512GB NVMe SSD, "
            "15.6\" FHD IPS display, Windows 11 Home, 1.62kg. "
            "All-day battery with Rapid Charge."
        ),
        price=Decimal("42999"), compare=Decimal("52999"),
        stock=18, sku="LEN-IPS3-R5-8-512",
        seeds=["modern-workspace-laptop", "minimal-desk-setup"],
        tags=["laptop", "lenovo", "ryzen", "windows11", "ultrabook"],
        seller="ravi", cat="laptops",
    ),
    dict(
        title="Mi Smart Band 7",
        slug="mi-smart-band-7",
        desc=(
            "1.62\" AMOLED always-on display, 110+ workout modes, "
            "blood oxygen & continuous heart rate monitoring, "
            "14-day battery life, 5ATM waterproof."
        ),
        price=Decimal("2799"), compare=Decimal("3499"),
        stock=120, sku="MI-SB7-BLK",
        seeds=["sleek-wristwatch-dark", "fitness-tracker-sport"],
        tags=["smartband", "fitness", "xiaomi", "wearable", "amoled"],
        seller="ravi", cat="electronics",
    ),
    dict(
        title="Skullcandy Hesh ANC Headphones",
        slug="skullcandy-hesh-anc",
        desc=(
            "Active Noise Cancellation, 22H battery life, "
            "Rapid Charge (10 min = 4H playback), foldable over-ear design, "
            "personal sound profile via app. Certified for Google Assistant."
        ),
        price=Decimal("5999"), compare=Decimal("9999"),
        stock=30, sku="SK-HESHANC-BLK",
        seeds=["premium-headphones-studio", "over-ear-audio-dark"],
        tags=["headphones", "anc", "skullcandy", "wireless", "foldable"],
        seller="ravi", cat="audio",
    ),
    dict(
        title="Portronics Kronos Y2 Smart Watch",
        slug="portronics-kronos-y2",
        desc=(
            "1.69\" HD full-touch display, 100+ watch faces, "
            "SpO2 & heart rate monitor, 7-day battery, IP68 waterproof, "
            "multi-sport modes, call & notification alerts."
        ),
        price=Decimal("1499"), compare=Decimal("2999"),
        stock=85, sku="PORT-KY2-BLK",
        seeds=["smartwatch-round-silver", "digital-watch-sport-blue"],
        tags=["smartwatch", "portronics", "wearable", "ip68"],
        seller="ravi", cat="electronics",
    ),
    dict(
        title="Wildcraft Unisex Yoga Mat 6mm",
        slug="wildcraft-yoga-mat-6mm",
        desc=(
            "6mm thick EVA foam, anti-slip texture on both sides, "
            "183×61cm, carry strap included. Odour-free material. "
            "Ideal for yoga, pilates, stretching and floor exercises."
        ),
        price=Decimal("699"), compare=Decimal("1299"),
        stock=75, sku="WC-YM6-PUR",
        seeds=["yoga-serene-mat-purple", "fitness-stretch-floor"],
        tags=["yoga", "fitness", "mat", "wildcraft", "eva"],
        seller="ravi", cat="sports",
    ),
    dict(
        title="Boldfit Gym Gloves with Wrist Support",
        slug="boldfit-gym-gloves",
        desc=(
            "Full palm silicone grip pads, anti-slip texture, "
            "adjustable velcro wrist strap, breathable neoprene back. "
            "Unisex design, size M. Machine washable."
        ),
        price=Decimal("449"), compare=Decimal("799"),
        stock=90, sku="BF-GGLOV-M-BLK",
        seeds=["gym-workout-gloves-dark", "fitness-equipment-weight"],
        tags=["gym", "gloves", "fitness", "boldfit", "wrist-support"],
        seller="ravi", cat="sports",
    ),
    # ── Priya: Fashion, Home & Kitchen, Books ──────────────────────────────
    dict(
        title="Allen Solly Men's Slim Fit Shirt",
        slug="allen-solly-mens-slim-shirt",
        desc=(
            "Premium 100% cotton blend, slim fit formal shirt, Size M. "
            "Easy-iron fabric, button-down collar. "
            "Machine washable at 30°C. Perfect for office and smart-casual."
        ),
        price=Decimal("899"), compare=Decimal("1699"),
        stock=60, sku="AS-MSF-WHT-M",
        seeds=["formal-shirt-white-men", "fashion-clothing-minimal"],
        tags=["shirt", "formal", "men", "cotton", "allen-solly"],
        seller="priya", cat="mens",
    ),
    dict(
        title="Biba Women's Anarkali Kurta",
        slug="biba-womens-anarkali-kurta",
        desc=(
            "Rayon fabric, vibrant floral print Anarkali, 3/4 sleeves, Size L. "
            "Pair with churidar or leggings. "
            "Perfect for festivals and casual outings. Dry clean recommended."
        ),
        price=Decimal("1299"), compare=Decimal("2499"),
        stock=35, sku="BIBA-AK-FLR-L",
        seeds=["ethnic-kurta-floral-colorful", "indian-fashion-dress"],
        tags=["kurta", "ethnic", "women", "biba", "festive"],
        seller="priya", cat="womens",
    ),
    dict(
        title="Fabindia Cotton Block Print Kurti Set",
        slug="fabindia-cotton-kurti-set",
        desc=(
            "100% handloom cotton, traditional block-printed kurti with matching palazzo. "
            "Size M, hand wash cold. "
            "Breathable, comfortable all-day wear."
        ),
        price=Decimal("1899"), compare=Decimal("3200"),
        stock=25, sku="FBI-CKS-BLK-M",
        seeds=["cotton-print-fabric-blue", "artisan-fabric-pattern"],
        tags=["kurti", "cotton", "women", "fabindia", "handloom"],
        seller="priya", cat="womens",
    ),
    dict(
        title="Prestige Svachh Hard Anodised Kadai 3L",
        slug="prestige-svachh-kadai-3l",
        desc=(
            "3L capacity, hard anodised aluminium body, "
            "tempered glass lid with steam vent, induction compatible base. "
            "Anti-corrosive coating, cool-touch handle."
        ),
        price=Decimal("1799"), compare=Decimal("2499"),
        stock=55, sku="PRE-SVKD-3L-HA",
        seeds=["kitchen-cookware-dark-pan", "cooking-utensil-modern"],
        tags=["cookware", "kadai", "prestige", "induction", "kitchen"],
        seller="priya", cat="home",
    ),
    dict(
        title="Philips HD9252 Digital Air Fryer 4.1L",
        slug="philips-hd9252-air-fryer",
        desc=(
            "1400W Rapid Air Technology, 4.1L family-size basket, "
            "digital touch display, 13 preset cooking programmes, "
            "up to 90% less fat, dishwasher-safe basket."
        ),
        price=Decimal("7999"), compare=Decimal("11999"),
        stock=22, sku="PHL-HD9252-BLK",
        seeds=["kitchen-appliance-modern-black", "healthy-cooking-air"],
        tags=["airfryer", "philips", "kitchen", "healthy", "digital"],
        seller="priya", cat="home",
    ),
    dict(
        title="Atomic Habits — James Clear",
        slug="atomic-habits-james-clear",
        desc=(
            "Paperback, 320 pages. #1 New York Times bestseller. "
            "A practical framework for building good habits and breaking bad ones. "
            "The 1% better every day system — backed by science."
        ),
        price=Decimal("399"), compare=Decimal("799"),
        stock=150, sku="BK-ATOMHAB-PB",
        seeds=["open-book-pages-light", "bookshelf-reading-warm"],
        tags=["book", "self-help", "habits", "bestseller", "productivity"],
        seller="priya", cat="books",
    ),
]


async def run_seed() -> None:
    # ── Phase 1: Upload all images to S3 ─────────────────────────────────
    total_images = sum(len(p["seeds"]) for p in CATALOG)
    print(f"\n{'='*62}")
    print(f"  S3 Image Upload — {total_images} images for {len(CATALOG)} products")
    print(f"  Bucket : {settings.S3_BUCKET_NAME}")
    print(f"  Region : {settings.AWS_REGION}")
    print(f"{'='*62}\n")

    image_map: dict[str, list[str]] = {}
    for i, p in enumerate(CATALOG, 1):
        print(f"  [{i:02d}/{len(CATALOG)}] {p['title'][:50]}")
        urls = []
        for idx, seed in enumerate(p["seeds"]):
            url = upload_image(seed, f"image {idx + 1}")
            urls.append(url)
        image_map[p["slug"]] = urls

    print(f"\nOK All images uploaded.\n")

    # ── Phase 2: Wipe DB and re-seed ─────────────────────────────────────
    print("Clearing database ...")
    async with AsyncSessionLocal() as db:
        for model in [Review, OrderItem, Order, Product, Category, User]:
            await db.execute(delete(model))
        await db.commit()
    print("OK All tables cleared.\n")

    async with AsyncSessionLocal() as db:
        # Users
        pw = hash_password("Test1234!")
        admin = User(id=uuid.uuid4(), email="admin@marketplace.dev",
                     hashed_password=pw, full_name="Admin User",
                     role="admin", is_active=True, is_verified=True)
        ravi  = User(id=uuid.uuid4(), email="ravi@seller.dev",
                     hashed_password=pw, full_name="Ravi Sharma",
                     role="seller", is_active=True, is_verified=True)
        priya = User(id=uuid.uuid4(), email="priya@seller.dev",
                     hashed_password=pw, full_name="Priya Nair",
                     role="seller", is_active=True, is_verified=True)
        amit  = User(id=uuid.uuid4(), email="amit@buyer.dev",
                     hashed_password=pw, full_name="Amit Verma",
                     role="buyer", is_active=True, is_verified=True)
        sneha = User(id=uuid.uuid4(), email="sneha@buyer.dev",
                     hashed_password=pw, full_name="Sneha Patel",
                     role="buyer", is_active=True, is_verified=True)
        rohan = User(id=uuid.uuid4(), email="rohan@buyer.dev",
                     hashed_password=pw, full_name="Rohan Mehta",
                     role="buyer", is_active=True, is_verified=True)
        db.add_all([admin, ravi, priya, amit, sneha, rohan])
        await db.flush()
        sellers = {"ravi": ravi, "priya": priya}
        print("OK Users (6)")

        # Top-level categories
        electronics = Category(id=uuid.uuid4(), name="Electronics",
                               slug="electronics", sort_order=1,
                               description="Gadgets, devices and accessories")
        fashion     = Category(id=uuid.uuid4(), name="Fashion",
                               slug="fashion", sort_order=2,
                               description="Clothing, footwear and accessories")
        home        = Category(id=uuid.uuid4(), name="Home & Kitchen",
                               slug="home-kitchen", sort_order=3,
                               description="Appliances, cookware and decor")
        books       = Category(id=uuid.uuid4(), name="Books",
                               slug="books", sort_order=4,
                               description="Fiction, non-fiction and textbooks")
        sports      = Category(id=uuid.uuid4(), name="Sports & Fitness",
                               slug="sports-fitness", sort_order=5,
                               description="Equipment, apparel and accessories")
        db.add_all([electronics, fashion, home, books, sports])
        await db.flush()

        # Sub-categories
        phones  = Category(id=uuid.uuid4(), name="Smartphones",
                           slug="smartphones", parent_id=electronics.id, sort_order=1)
        laptops = Category(id=uuid.uuid4(), name="Laptops",
                           slug="laptops", parent_id=electronics.id, sort_order=2)
        audio   = Category(id=uuid.uuid4(), name="Audio",
                           slug="audio", parent_id=electronics.id, sort_order=3)
        mens    = Category(id=uuid.uuid4(), name="Men's Clothing",
                           slug="mens-clothing", parent_id=fashion.id, sort_order=1)
        womens  = Category(id=uuid.uuid4(), name="Women's Clothing",
                           slug="womens-clothing", parent_id=fashion.id, sort_order=2)
        db.add_all([phones, laptops, audio, mens, womens])
        await db.flush()

        cats = {
            "electronics": electronics, "fashion": fashion,
            "home": home, "books": books, "sports": sports,
            "phones": phones, "laptops": laptops,
            "audio": audio, "mens": mens, "womens": womens,
        }
        print("OK Categories (10 -- 5 top-level, 5 sub-categories)")

        # Products
        product_objs: list[Product] = []
        for p in CATALOG:
            obj = Product(
                id=uuid.uuid4(),
                title=p["title"],
                slug=p["slug"],
                description=p["desc"],
                price=p["price"],
                compare_at_price=p.get("compare"),
                stock=p["stock"],
                sku=p["sku"],
                status="active",
                seller_id=sellers[p["seller"]].id,
                category_id=cats[p["cat"]].id,
                images=image_map[p["slug"]],
                tags=p["tags"],
            )
            product_objs.append(obj)
        db.add_all(product_objs)
        await db.flush()

        by_slug = {p.slug: p for p in product_objs}
        print(f"OK Products ({len(product_objs)}) — all with S3 images")

        # Orders — helper computes totals from items
        def build_order(buyer, item_specs, status, rz_suffix, address):
            subtotal = sum(prod.price * qty for prod, qty in item_specs)
            shipping = Decimal("0") if subtotal > 500 else Decimal("50")
            tax      = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
            total    = subtotal + shipping + tax
            paid_at  = datetime.utcnow() if status in ("paid", "delivered") else None
            return Order(
                id=uuid.uuid4(),
                buyer_id=buyer.id,
                status=status,
                razorpay_order_id=f"order_seed_{rz_suffix}",
                razorpay_payment_id=f"pay_seed_{rz_suffix}",
                subtotal=subtotal,
                shipping_amount=shipping,
                tax_amount=tax,
                total=total,
                shipping_address=address,
                paid_at=paid_at,
            )

        addr_amit = {
            "full_name": "Amit Verma", "phone": "9876543210",
            "line1": "42, MG Road", "city": "Bengaluru",
            "state": "Karnataka", "pincode": "560001", "country": "India",
        }
        addr_sneha = {
            "full_name": "Sneha Patel", "phone": "9123456789",
            "line1": "12 Juhu Tara Road", "city": "Mumbai",
            "state": "Maharashtra", "pincode": "400049", "country": "India",
        }
        addr_rohan = {
            "full_name": "Rohan Mehta", "phone": "9988776655",
            "line1": "7B Connaught Place", "city": "New Delhi",
            "state": "Delhi", "pincode": "110001", "country": "India",
        }

        orders_spec = [
            (build_order(amit, [
                (by_slug["oneplus-nord-ce-3-lite-5g"], 1),
                (by_slug["boat-airdopes-141-tws"], 1),
            ], "paid", "001", addr_amit),
            [(by_slug["oneplus-nord-ce-3-lite-5g"], 1),
             (by_slug["boat-airdopes-141-tws"], 1)]),

            (build_order(amit, [
                (by_slug["atomic-habits-james-clear"], 2),
            ], "delivered", "002", addr_amit),
            [(by_slug["atomic-habits-james-clear"], 2)]),

            (build_order(sneha, [
                (by_slug["biba-womens-anarkali-kurta"], 1),
                (by_slug["fabindia-cotton-kurti-set"], 1),
            ], "processing", "003", addr_sneha),
            [(by_slug["biba-womens-anarkali-kurta"], 1),
             (by_slug["fabindia-cotton-kurti-set"], 1)]),

            (build_order(rohan, [
                (by_slug["lenovo-ideapad-slim-3"], 1),
            ], "shipped", "004", addr_rohan),
            [(by_slug["lenovo-ideapad-slim-3"], 1)]),

            (build_order(sneha, [
                (by_slug["philips-hd9252-air-fryer"], 1),
                (by_slug["prestige-svachh-kadai-3l"], 1),
            ], "pending", "005", addr_sneha),
            [(by_slug["philips-hd9252-air-fryer"], 1),
             (by_slug["prestige-svachh-kadai-3l"], 1)]),
        ]

        for order, item_specs in orders_spec:
            db.add(order)
            await db.flush()
            for prod, qty in item_specs:
                db.add(OrderItem(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    product_id=prod.id,
                    quantity=qty,
                    unit_price=prod.price,
                    product_title=prod.title,
                    product_image=prod.images[0] if prod.images else None,
                ))
        print(f"OK Orders (5) with items")

        # Reviews
        reviews = [
            Review(id=uuid.uuid4(),
                   product_id=by_slug["oneplus-nord-ce-3-lite-5g"].id,
                   user_id=amit.id, rating=5,
                   title="Excellent phone for the price",
                   body=(
                       "Battery lasts all day, camera is superb in daylight. "
                       "5G is fast, display colours are vivid. "
                       "Highly recommended under ₹20k."
                   ),
                   is_verified_purchase=True, helpful_count=12),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["oneplus-nord-ce-3-lite-5g"].id,
                   user_id=sneha.id, rating=4,
                   title="Good but slight heating during gaming",
                   body=(
                       "Overall great phone. Slight warmth during BGMI sessions. "
                       "Camera and battery are top notch for this price range."
                   ),
                   is_verified_purchase=False, helpful_count=5),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["boat-airdopes-141-tws"].id,
                   user_id=rohan.id, rating=5,
                   title="Best TWS under ₹1500",
                   body=(
                       "Sound quality is surprisingly good. "
                       "Call quality with ENx mic is crystal clear. "
                       "42H total battery is legit — tested it myself."
                   ),
                   is_verified_purchase=True, helpful_count=8),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["lenovo-ideapad-slim-3"].id,
                   user_id=sneha.id, rating=4,
                   title="Solid budget laptop",
                   body=(
                       "Ryzen 5 handles daily tasks and light coding easily. "
                       "SSD is snappy. Display could be brighter but acceptable indoors. "
                       "Good buy for the price."
                   ),
                   is_verified_purchase=False, helpful_count=3),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["skullcandy-hesh-anc"].id,
                   user_id=rohan.id, rating=4,
                   title="Great ANC at this price point",
                   body=(
                       "ANC is effective on flights and in busy cafes. "
                       "22H battery delivers as advertised. "
                       "Slight bass boost but overall balanced and comfortable."
                   ),
                   is_verified_purchase=False, helpful_count=6),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["atomic-habits-james-clear"].id,
                   user_id=amit.id, rating=5,
                   title="Changed my perspective — literally",
                   body=(
                       "I've read dozens of self-help books and this one actually sticks. "
                       "Practical system, not just motivation. "
                       "The 1% better every day concept is powerful and measurable."
                   ),
                   is_verified_purchase=True, helpful_count=21),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["prestige-svachh-kadai-3l"].id,
                   user_id=sneha.id, rating=5,
                   title="Perfect kadai, induction works flawlessly",
                   body=(
                       "Even heating, very easy to clean, lid fits perfectly. "
                       "Hard anodised coating still holding up after months of daily use. "
                       "Worth every rupee."
                   ),
                   is_verified_purchase=True, helpful_count=9),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["philips-hd9252-air-fryer"].id,
                   user_id=amit.id, rating=5,
                   title="Game changer for healthy cooking",
                   body=(
                       "Makes crispy food with almost no oil. Very easy to clean. "
                       "The 13 presets are all genuinely useful. "
                       "4.1L is perfect for a family of 3."
                   ),
                   is_verified_purchase=False, helpful_count=14),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["biba-womens-anarkali-kurta"].id,
                   user_id=rohan.id, rating=4,
                   title="Beautiful fabric, true to size",
                   body=(
                       "Ordered L for my wife — perfect fit. "
                       "The floral print looks exactly like the photos, colours are vibrant. "
                       "Slight delay in delivery but the product is lovely."
                   ),
                   is_verified_purchase=False, helpful_count=4),

            Review(id=uuid.uuid4(),
                   product_id=by_slug["wildcraft-yoga-mat-6mm"].id,
                   user_id=sneha.id, rating=5,
                   title="Excellent grip, good thickness",
                   body=(
                       "The anti-slip surface is real — doesn't shift even during hot yoga. "
                       "6mm is the right thickness for knee support. "
                       "Carry strap is a nice bonus."
                   ),
                   is_verified_purchase=False, helpful_count=7),
        ]
        db.add_all(reviews)
        await db.commit()
        print(f"OK Reviews ({len(reviews)})")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print("  Seed complete!")
    print(f"{'='*62}")
    print(f"\n  Products  : {len(CATALOG)} (all with real S3 images)")
    print(f"  Images    : {total_images} uploaded to s3://{settings.S3_BUCKET_NAME}")
    print( "  Orders    : 5 (paid, delivered, processing, shipped, pending)")
    print( "  Reviews   : 10")
    print( "\n  Login credentials -- all passwords: Test1234!")
    print( "  Email                        Role      Notes")
    print( "  " + "-"*58)
    print( "  admin@marketplace.dev        admin     Full access")
    print( "  ravi@seller.dev              seller    Electronics + Sports (8 products)")
    print( "  priya@seller.dev             seller    Fashion + Home + Books (6 products)")
    print( "  amit@buyer.dev               buyer     2 orders (paid, delivered)")
    print( "  sneha@buyer.dev              buyer     2 orders (processing, pending)")
    print( "  rohan@buyer.dev              buyer     1 order (shipped)")


if __name__ == "__main__":
    asyncio.run(run_seed())
