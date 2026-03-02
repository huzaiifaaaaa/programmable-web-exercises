from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
api = Api(app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(64), unique=True, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    in_storage = db.relationship("StorageItem",back_populates="product")

class StorageItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qty = db.Column(db.Integer,nullable=False)
    location = db.Column(db.String(64),nullable=False)
    product_id = db.Column(db.Integer,db.ForeignKey("product.id"),nullable=False)
    product = db.relationship("Product",back_populates="in_storage")

class ProductCollection(Resource):

    def get(self):
        products = Product.query.all()
        product_list = []
        for product in products:
            product_list.append({
                "handle": product.handle,
                "weight": product.weight,
                "price": product.price
            })

        return product_list, 200

    def post(self):
        if not request.is_json:
            return "Request content type must be JSON", 415

        data = request.json
        if not all(k in data for k in ("handle", "weight", "price")):
            return "Incomplete request - missing fields", 400

        handle = data["handle"]
        weight = data["weight"]
        price = data["price"]

        try:
            weight = float(weight)
            price = float(price)
        except (ValueError, TypeError):
            return "Weight and price must be numbers", 400

        if Product.query.filter_by(handle=handle).first():
            return "Handle already exists", 409

        product = Product(
            handle=handle,
            weight=weight,
            price=price
        )

        db.session.add(product)
        db.session.commit()
        return "", 201

api.add_resource(ProductCollection, "/api/products/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
