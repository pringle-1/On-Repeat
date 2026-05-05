# Import models
from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
# Create app instance and secret key
app = Flask(__name__)
app.secret_key = 'onrepeatsecretkey'

DATABASE = 'onrepeat.db'

# Database connection function
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

# Close database connection after every request
@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Function to pull data from the database with SQL queries
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# Route for index (home) page
@app.route('/')
def home():
    header_py="home"
    return render_template("index.html", header=header_py)

# Route for albums page
@app.route('/albums')
def albums():
    # Run SQL query to get albums and all their details
    sql = """
                SELECT *
                FROM album;
          """
    
    albums = query_db(sql)
    header_py="albums"
    return render_template("albums.html", header=header_py, albums=albums, request=request)

# Route for artists page
@app.route('/artists')
def artists():
    header_py="artists"
    return render_template("artists.html", header=header_py)

# Route for my profile page
@app.route('/profile')
def profile():
    header_py="profile"
    return render_template("profile.html", header=header_py)

# Run statement
if __name__ == "__main__":
    app.run(debug=True)
