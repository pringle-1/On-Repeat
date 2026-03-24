# Import models
from flask import Flask, g, render_template, request
import sqlite3
# Create app instance
app = Flask(__name__)
# Route for index (home) page
@app.route('/')
# Define function that runs when route is served
def home ():
    header_py="home"
    return render_template("index.html", header=header_py)
# Run statement
if __name__ == "__main__":
    app.run(debug=True)