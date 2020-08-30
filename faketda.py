import sqlite3
from sqlite3 import Error
from account import TDAuth
from flask import Flask, request, render_template

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def data():
    print(request.form)
    return "G2G"

