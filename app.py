from flask import Flask, request, jsonify, render_template
import json

from static.python.add import addition
from static.python.genarray import gen_array

app = Flask(__name__)

@app.route('/_add_numbers')
def add_numbers():
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    result = addition(a, b)
    return jsonify(result=result)

@app.route('/_random/')
def generate():
    scale = request.args.get('scale', 0, type=int)
    gendata = json.loads(gen_array(scale))
    return jsonify(result=gendata)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/d3test')
def d3test():
    return render_template('d3test.html')

@app.route('/heatmap')
def heatmap():
    return render_template('heat.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=50050)
