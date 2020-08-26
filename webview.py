from flask import Flask, render_template
from optionhunting import TDApi
app = Flask(__name__)

@app.route('/')
def data():
    
    return render_template('data.html')

