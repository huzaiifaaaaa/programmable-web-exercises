from datetime import datetime
from flask import Flask, Response, request
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from jsonschema import validate, ValidationError, FormatChecker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy import event
from werkzeug.exceptions import BadRequest, Conflict, NotFound, UnsupportedMediaType
from werkzeug.routing import BaseConverter

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
draft7_format_checker = FormatChecker()

db = SQLAlchemy(app)
api = Api(app)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

deployments = db.Table("deployments",
    db.Column("deployment_id", db.Integer, db.ForeignKey("deployment.id"), primary_key=True),
    db.Column("sensor_id", db.Integer, db.ForeignKey("sensor.id"), primary_key=True)
)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    altitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.String(256), nullable=True)
    sensor = db.relationship("Sensor", back_populates="location", uselist=False)

    def serialize(self, short_form=False):
        doc = {"name": self.name}
        if not short_form:
            doc.update({
                "longitude": self.longitude,
                "latitude": self.latitude,
                "altitude": self.altitude,
                "description": self.description
            })
        return doc

    def deserialize(self, doc):
        self.name = doc["name"]
        self.latitude = doc.get("latitude")
        self.longitude = doc.get("longitude")
        self.altitude = doc.get("altitude")
        self.description = doc.get("description")

class Deployment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sensors = db.relationship("Sensor", secondary=deployments, back_populates="deployments")

class Sensor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    model = db.Column(db.String(128), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), unique=True)
    location = db.relationship("Location", back_populates="sensor")
    measurements = db.relationship("Measurement", back_populates="sensor")
    deployments = db.relationship("Deployment", secondary=deployments, back_populates="sensors")

    def serialize(self):
        return {
            "name": self.name,
            "model": self.model,
            "location": self.location.name if self.location else None
        }

    def deserialize(self, doc):
        self.name = doc["name"]
        self.model = doc["model"]

    @staticmethod
    def json_schema():
        schema = {
            "type": "object",
            "properties": {
                "name": {"description": "Sensor's unique name", "type": "string"},
                "model": {"description": "Sensor's model name", "type": "string"}
            },
            "required": ["name", "model"],
            "additionalProperties": False
        }
        return schema

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey("sensor.id", ondelete="SET NULL"))
    value = db.Column(db.Float, nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    sensor = db.relationship("Sensor", back_populates="measurements")

    def serialize(self):
        return {"time": self.time.isoformat(), "value": self.value}

    def deserialize(self, data):
        self.value = float(data["value"])
        self.time = datetime.fromisoformat(data["time"])

    @staticmethod
    def json_schema():
        return {
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "time": {"type": "string", "format": "date-time"}
            },
            "required": ["value", "time"],
            "additionalProperties": False
        }

class SensorConverter(BaseConverter):
    def to_python(self, value):
        sensor = Sensor.query.filter_by(name=value).first()
        if sensor is None:
            raise NotFound
        return sensor

    def to_url(self, value):
        sensor = value
        return sensor.name

app.url_map.converters["sensor"] = SensorConverter

class SensorCollection(Resource):
    def get(self):
        return [s.serialize() for s in Sensor.query.all()]

    def post(self):
        if not request.is_json:
            raise UnsupportedMediaType
        try:
            validate(request.json, Sensor.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e
        sensor = Sensor()
        sensor.deserialize(request.json)
        try:
            db.session.add(sensor)
            db.session.commit()
        except IntegrityError as exc:
            raise Conflict(description=f"Sensor with name '{sensor.name}' already exists.") from exc
        return Response(status=201, headers={"Location": api.url_for(SensorItem, sensor=sensor)})

class SensorItem(Resource):
    def get(self, sensor):
        return sensor.serialize()

    def put(self, sensor):
        if not request.is_json:
            raise UnsupportedMediaType
        try:
            validate(request.json, Sensor.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e
        sensor.deserialize(request.json)
        try:
            db.session.add(sensor)
            db.session.commit()
        except IntegrityError as exc:
            raise Conflict(description=f"Sensor with name '{sensor.name}' already exists.") from exc
        return Response(status=204)

    def delete(self, sensor):
        db.session.delete(sensor)
        db.session.commit()
        return Response(status=204)

class MeasurementCollection(Resource):
    def post(self, sensor):
        if not request.is_json:
            raise UnsupportedMediaType
        try:
            validate(request.json, Measurement.json_schema(), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e
        m = Measurement()
        m.deserialize(request.json)
        m.sensor = sensor
        db.session.add(m)
        db.session.commit()
        return Response(status=201, headers={
            "Location": api.url_for(MeasurementItem, sensor=sensor, measurement=m.id)
        })

class MeasurementItem(Resource):
    def delete(self, sensor, measurement):
        m = Measurement.query.filter_by(id=measurement, sensor_id=sensor.id).first()
        if not m:
            raise NotFound
        db.session.delete(m)
        db.session.commit()
        return Response(status=204)

api.add_resource(SensorCollection, "/api/sensors/")
api.add_resource(SensorItem, "/api/sensors/<sensor:sensor>/")
api.add_resource(MeasurementCollection, "/api/sensors/<sensor:sensor>/measurements/")
api.add_resource(MeasurementItem, "/api/sensors/<sensor:sensor>/measurements/<int:measurement>/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
