from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from werkzeug.routing import BaseConverter
from werkzeug.exceptions import NotFound

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
api = Api(app)

class Product(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    handle = db.Column(db.String(64),unique=True,nullable=False)
    weight = db.Column(db.Float,nullable=False)
    price = db.Column(db.Float,nullable=False)
    in_storage = db.relationship("StorageItem",back_populates="product")

class StorageItem(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    qty = db.Column(db.Integer,nullable=False)
    location = db.Column(db.String(64),nullable=False)
    product_id = db.Column(db.Integer,db.ForeignKey("product.id"),nullable=False)
    product = db.relationship("Product",back_populates="in_storage")

class ProductConverter(BaseConverter):
    def to_python(self, value):
        product = Product.query.filter_by(handle=value).first()
        if product is None:
            raise NotFound()
        return product

    def to_url(self, value):
        return value.handle

app.url_map.converters["product"] = ProductConverter

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

        return product_list

    def post(self):
        if not request.is_json:
            return Response(status=415)

        data = request.json
        if not all(
            k in data
            for k in ("handle", "weight", "price")
        ):
            return Response("Incomplete request - missing fields",status=400)

        handle = data["handle"]
        weight = data["weight"]
        price = data["price"]

        try:
            weight = float(weight)
            price = float(price)
        except (ValueError, TypeError):
            return Response("Weight and price must be numbers",status=400)

        existing = Product.query.filter_by(handle=handle).first()

        if existing:
            return Response("Handle already exists",status=409)

        product = Product(
            handle=handle,
            weight=weight,
            price=price
        )

        db.session.add(product)
        db.session.commit()

        return Response(status=201,
            headers={
                "Location": api.url_for(
                    ProductItem,
                    product=product
                )
            }
        )

class ProductItem(Resource):
    def get(self, product):
        return {
            "handle": product.handle,
            "weight": product.weight,
            "price": product.price
        }, 200

api.add_resource(ProductCollection,"/api/products/")
api.add_resource(ProductItem,"/api/products/<product:product>/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
