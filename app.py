"""On Repeat 12DTP Social Music Website/Application
A site that allows users to review albums, comment on reviews, and reply to comments
Fibitius Chan"""

# Import models
from flask import Flask, render_template, request, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash
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

# Route for register (account creation) page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username=request.form['username']
        password=request.form['password']
        hashed_password = generate_password_hash
        db = get_db
        try:
            db.execute('INSERT INTO User (username, password) VALUES (?, ?)', (username, hashed_password))
            db.commit()
            return redirect(url_for('login'))
        except:
            return render_template("register.html", error="Username already taken!")
    return render_template

# Route for login (page)
@app.route('/login')
def login():
    return render_template("login.html")

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
    return render_template("albums.html", header=header_py, albums=albums)

# Route for one album's page
@app.route('/album/<int:id>')
def album(id):
    # Only one album from its ID
    sql = """
                SELECT *
                FROM album
                WHERE album_id = ?;
          """
    album = query_db(sql,(id,),True)
    return render_template("album.html", album=album)
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
