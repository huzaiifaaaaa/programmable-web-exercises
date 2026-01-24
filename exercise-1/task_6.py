from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///task_6.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(64), unique=True, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    in_storage = db.relationship("StorageItem", back_populates="product")

class StorageItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qty = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(64), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    product = db.relationship("Product", back_populates="in_storage")

@app.route("/products/add/", methods=["POST"])
def add_product():
    if not request.is_json:
        return "Content type should be JSON!", 415

    data = request.json
    if not all(field in data for field in ("handle", "weight", "price")):
        return "Missing required fields!", 400

    handle = data["handle"]
    weight = data["weight"]
    price = data["price"]

    try:
        weight = float(weight)
        price = float(price)
    except (ValueError, TypeError):
        return "Weight and price should be numbers!", 400

    existing = Product.query.filter_by(handle=handle).first()
    if existing:
        return "Handle already exists!", 409

    product = Product(handle=handle, weight=weight, price=price)
    db.session.add(product)
    db.session.commit()
    return "", 201

@app.route("/storage/<product_handle>/add/", methods=["POST"])
def add_to_storage(product_handle):
    if not request.is_json:
        return "Content type should be JSON!", 415

    data = request.json
    if not all(field in data for field in ("location", "qty")):
        return "Missing required fields!", 400

    location = data["location"]
    qty = data["qty"]

    try:
        qty = int(qty)
    except (ValueError, TypeError):
        return "Qty should be integer!", 400

    product = Product.query.filter_by(handle=product_handle).first()
    if not product:
        return "Product not found!", 404

    storage_item = StorageItem(location=location, qty=qty, product=product)
    db.session.add(storage_item)
    db.session.commit()
    return "", 201

@app.route("/storage/", methods=["GET"])
def get_inventory():
    products = Product.query.all()
    inventory_list = []

    for p in products:
        item = {"handle": p.handle, 
                "weight": p.weight, 
                "price": p.price, 
                "inventory": [[s.location, s.qty] for s in p.in_storage]
            }
        inventory_list.append(item)
    return jsonify(inventory_list), 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
