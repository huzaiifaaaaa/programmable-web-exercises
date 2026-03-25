from flask import Flask, request, Response
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
    in_storage = db.relationship("StorageItem", back_populates="product")

class StorageItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qty = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(64), nullable=False)
    product_id = db.Column(db.Integer,db.ForeignKey("product.id"),nullable=False)
    product = db.relationship("Product",back_populates="in_storage")

class ProductItem(Resource):
    def get(self, handle):
        return Response(status=501)

class ProductCollection(Resource):
    def get(self):
        products = Product.query.all()
        return [{
                "handle": p.handle,
                "weight": p.weight,
                "price": p.price
            }
            for p in products
        ], 200

    def post(self):
        if not request.is_json:
            return Response("Request content type must be JSON",status=415)

        data = request.json
        if not all(k in data for k in ("handle", "weight", "price")):
            return Response("Incomplete request -missing fields",status=400)

        handle = data["handle"]
        try:
            weight = float(data["weight"])
            price = float(data["price"])
        except (ValueError, TypeError):
            return Response("Weight and price must be numbers", status=400)

        if Product.query.filter_by(handle=handle).first():
            return Response("Handle already exists",status=409)

        product = Product(
            handle=handle,
            weight=weight,
            price=price
        )

        db.session.add(product)
        db.session.commit()

        return Response(
            status=201,
            headers={"Location": api.url_for(
                    ProductItem,
                    handle=handle
                )
            }
        )

api.add_resource(ProductCollection, "/api/products/")
api.add_resource(ProductItem,"/api/products/<string:handle>/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
