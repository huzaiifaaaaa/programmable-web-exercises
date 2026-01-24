from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return """Welcome to the Internet Age Calculatron!
            Usage:
                /add/<number_1>/<number_2>/  -> addition
                /sub/<number_1>/<number_2>/  -> subtraction
                /mul/<number_1>/<number_2>/  -> multiplication
                /div/<number_1>/<number_2>/  -> division

            Note: numbers must be floats (e.g. 3.0, 4.5)
        """

@app.route("/add/<float:number_1>/<float:number_2>/")
def plus(number_1, number_2):
    result = number_1 + number_2
    return f"{result}"

@app.route("/sub/<float:number_1>/<float:number_2>/")
def minus(number_1, number_2):
    result = number_1 - number_2
    return f"{result}"


@app.route("/mul/<float:number_1>/<float:number_2>/")
def mult(number_1, number_2):
    result = number_1 * number_2
    return f"{result}"

@app.route("/div/<float:number_1>/<float:number_2>/")
def div(number_1, number_2):
    if number_2 == 0.0:
        return "NaN"
    result = number_1 / number_2
    return f"{result}"

if __name__ == "__main__":
    app.run(debug=True)
