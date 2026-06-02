"""On Repeat 12DTP Social Music Website/Application
A site that allows users to review albums, comment on reviews, and reply to comments"""

# Import models
from flask import Flask, render_template, request, redirect, url_for, session, g, abort
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
# Create app instance and secret key
app = Flask(__name__)
app.secret_key = 'onrepeatsecretkey'

DATABASE = 'onrepeat.db'

# Open and read bannedwords.txt and badpasswords.txt
with open('bannedwords.txt', 'r') as f:
    BANNED_WORDS = [line.strip().lower() for line in f]
with open('badpasswords.txt', 'r') as f:
    BAD_PASSWORDS = [line.strip() for line in f]

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
        username = request.form['username'].lower()
        password = request.form['password']
        if len(username) < 3:
            return render_template("register.html", error="Username must be at least 3 characters!")
        if len(username) > 20:
            return render_template("register.html", error="Username must be 20 characters or less!")
        if ' ' in username:
            return render_template("register.html", error="Username cannot contain spaces!")
        if any(word in username.lower() for word in BANNED_WORDS):
            return render_template("register.html", error="That username is not allowed!")
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters!")
        if password in BAD_PASSWORDS:
            return render_template("register.html", error="Weak password, choose a stronger one!")
        if request.form['password'] != request.form['confirm_password']:
            return render_template("register.html", error="Passwords do not match!")
        hashed_password = generate_password_hash(password)
        db = get_db()
        try:
            db.execute('INSERT INTO User (username, password, date_joined) VALUES (?, ?, ?)', (username, hashed_password, date.today().strftime('%d/%m/%Y')))
            db.commit()
            return redirect(url_for('login'))
        except:
            return render_template("register.html", error="Username already taken!")
    return render_template("register.html")

# Route for login (page)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        user = query_db('SELECT * FROM user WHERE username = ?', (username,), one=True)
        if user is None:
            return render_template("login.html", error="User not found!")
        if not check_password_hash(user['password'], password):
            return render_template("login.html", error="Incorrect password!")
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        return redirect(url_for('home'))
    return render_template("login.html")

# Route for logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Error 404 handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# Make the data of the current logged in user available to all templates
@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = query_db("SELECT * FROM User WHERE user_id = ?", (session['user_id'],), one=True)
    return dict(current_user=user)

# Route for index (home) page
@app.route('/')
def home():
    # Run SQL query to get albums and all their details
    sql = """SELECT * FROM album;"""
    albums = query_db(sql)
    return render_template("index.html", active_page="home", albums=albums)

# Route for albums page
@app.route('/albums')
def albums():
    # Run SQL query to get albums and all their details
    sql = """SELECT * FROM album;"""
    albums = query_db(sql)
    return render_template("albums.html", active_page="albums", albums=albums)

# Route for one album's page
@app.route('/album/<int:id>')
def album(id):
    # Only one album from its ID
    sql = """SELECT * FROM album WHERE album_id = ?;"""
    album = query_db(sql,(id,),True)
    if album is None:
        abort(404)
    return render_template("album.html", album=album)

@app.route('/album/<int:id>/review', methods=['GET', 'POST'])
def review(id):
    sql = """SELECT * FROM Album WHERE album_id = ?;"""
    album = query_db(sql,(id,),True)
    if album is None:
        abort(404)
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("review.html", album=album)

# Route for artists page
@app.route('/artists')
def artists():
    # Run SQL query to get artists and all their details
    sql = """SELECT * FROM artist;"""
    artists = query_db(sql)
    return render_template("artists.html", active_page="artists", artists=artists)

# Route for one artist's page
@app.route('/artist/<int:id>')
def artist(id):
    # Only one artist from its ID
    sql = """SELECT * FROM artist WHERE artist_id = ?;"""
    artist = query_db(sql,(id,),True)
    if artist is None:
        abort(404)
    albums = query_db("SELECT * FROM Album WHERE artist_id = ?", (id,))
    return render_template("artist.html", artist=artist, albums=albums)

# Route for my profile page
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("profile.html", active_page="profile")

# Run statement
if __name__ == "__main__":
    app.run(debug=True)
