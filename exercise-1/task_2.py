from flask import Flask, request
import math

app = Flask(__name__)

@app.route("/trig/<func>/")
def trig(func):
    if func not in ("sin", "cos", "tan"):
        return "Operation not found", 404

    angle = request.args.get("angle")
    if angle is None:
        return "Missing query parameter: angle", 400

    try:
        angle = float(angle)
    except ValueError:
        return "Invalid query parameter value(s)", 400

    unit = request.args.get("unit", "radian")
    if unit not in ("radian", "degree"):
        return "Invalid query parameter value(s)", 400

    if unit == "degree":
        angle = math.radians(angle)

    if func == "sin":
        result = math.sin(angle)
    elif func == "cos":
        result = math.cos(angle)
    else:
        result = math.tan(angle)

    return f"{result:.3f}", 200


if __name__ == "__main__":
    app.run(debug=True)
