"""On Repeat 12DTP Social Music Website/Application
A site that allows users to review albums, comment on reviews, and reply to comments
Created by Fibitius Chan"""


# Internal imports
import sqlite3
import os
import secrets


# External imports
from flask import Flask, render_template, request, redirect, url_for, session, g, abort
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv


# Create app instance and randomized secret key in hexcode
app = Flask(__name__)
load_dotenv()
secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))


# Set variables for the database, allowed profile picture extensions, and the app's secret key
DATABASE = 'onrepeat.db'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['SECRET_KEY'] = secret_key

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


# Check that uploaded profile picture files have an allowed file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
    register_sql = """INSERT INTO User (username, password, date_joined) VALUES (?, ?, ?)"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if len(username) < 3:
            return render_template("register.html", username=username, error="Username must be at least 3 characters!")
        if len(username) > 20:
            return render_template("register.html", username=username, error="Username must be 20 characters or less!")
        if ' ' in username:
            return render_template("register.html", username=username, error="Username cannot contain spaces!")
        if any(word in username.casefold() for word in BANNED_WORDS):
            return render_template("register.html", username=username, error="That username is not allowed!")
        if len(password) < 8:
            return render_template("register.html", username=username, error="Password must be at least 8 characters!")
        if password in BAD_PASSWORDS:
            return render_template("register.html", username=username, error="Weak password, choose a stronger one!")
        hashed_password = generate_password_hash(password)
        db = get_db()
        existing = query_db("SELECT * FROM User WHERE LOWER(username) = LOWER(?)", (username,), one=True)
        if existing:
            return render_template("register.html", username=username, error="Username already taken!")
        db.execute(register_sql, (username, hashed_password, date.today().strftime('%d/%m/%Y')))
        db.commit()
        return redirect(url_for('login'))
    return render_template("register.html")


# Route for login (page)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = query_db('SELECT * FROM user WHERE LOWER(username) = LOWER(?)', (username,), one=True)
        if user is None:
            return render_template("login.html", username=username, error="User not found!")
        if not check_password_hash(user['password'], password):
            return render_template("login.html", username=username, error="Incorrect password!")
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        return redirect(url_for('home'))
    return render_template("login.html")


# Route for logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# Error 403 handler custom page
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


# Error 404 handler custom page
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
@app.route('/album/<int:album_id>')
def album(album_id):
    # Only one album from its ID
    sql = """SELECT * FROM album JOIN Artist ON Album.artist_id = Artist.artist_id WHERE album_id = ?;"""
    average_rating_sql = """SELECT AVG(rating) AS average_rating FROM Review WHERE album_id = ?;"""
    album = query_db(sql, (album_id,), True)
    average = query_db(average_rating_sql, (album_id,), one=True)
    average_rating = average['average_rating']
    if album is None:
        abort(404)
    if average_rating is not None:
        average_rating = round(average_rating, 1)
    return render_template("album.html", album=album, average_rating=average_rating)


# Route to write an album review
@app.route('/album/<int:album_id>/review', methods=['GET', 'POST'])
def review(album_id):
    sql = """SELECT * FROM Album JOIN Artist ON Album.artist_id = Artist.artist_id WHERE album_id = ?;"""
    average_rating_sql = """SELECT AVG(rating) AS average_rating FROM Review WHERE album_id = ?;"""
    average = query_db(average_rating_sql, (album_id,), one=True)
    average_rating = average['average_rating']
    album = query_db(sql, (album_id,), True)
    review_sql = """INSERT INTO Review (user_id, album_id, rating, review_text, review_date) VALUES (?, ?, ?, ?, ?)"""
    if album is None:
        abort(404)
    if average_rating is not None:
        average_rating = round(average_rating, 1)
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        rating = float(request.form['rating'])
        review_text = request.form['review_text']
        if any(word in review_text.lower() for word in BANNED_WORDS):
            return render_template("reviewer.html",
                                   album=album,
                                   average_rating=average_rating,
                                   rating=rating,
                                   review_text=review_text,
                                   error="Your review contains words that are not allowed!")
        if rating < 0.1 or rating > 10:
            return render_template("reviewer.html", album=album, error="Rating must be between 0.1 and 10.0!")
        db = get_db()
        try:
            db.execute(review_sql, (session['user_id'], album_id, rating, review_text, date.today().strftime('%d/%m/%Y')))
            db.commit()
            return redirect(url_for('reviews', album_id=album_id))
        except sqlite3.IntegrityError:
            return render_template("reviewer.html", album=album, error="You have already reviewed this album!")
    return render_template("reviewer.html", album=album, average_rating=average_rating, review=review)


# Route for all reviews page
@app.route('/reviews')
def all_reviews():
    review_sql = """
    SELECT
        Review.*,
        User.username,
        user.profile_picture,
        Album.album_title,
        Album.album_cover,
        Artist.artist_name,
        COUNT(Comment.comment_id) AS comment_count
    FROM Review
    JOIN User ON Review.user_id = User.user_id
    JOIN Album ON Review.album_id = Album.album_id
    JOIN Artist ON Album.artist_id = Artist.artist_id
    LEFT JOIN Comment ON Review.review_id = Comment.review_id
    GROUP BY Review.review_id
    ORDER BY comment_count DESC;
    """
    reviews = query_db(review_sql)
    return render_template("all_reviews.html", active_page="all_reviews", reviews=reviews)


# Route to read the reviews for one album
@app.route('/album/<int:album_id>/reviews')
def reviews(album_id):
    sql = """SELECT Review.*,
                User.username,
                User.profile_picture
             FROM Review
             JOIN User
             ON Review.user_id = User.user_id
             WHERE album_id = ?
             ORDER BY review_id DESC;"""
    album_sql = """SELECT * FROM Album WHERE album_id = ?;"""
    album = query_db(album_sql, (album_id,), True)
    reviews = query_db(sql, (album_id,))
    if album is None:
        abort(404)
    return render_template("reviews.html", album=album, reviews=reviews)


# Route for one review's page
@app.route("/review/<int:review_id>", methods=['GET', 'POST'])
def review_page(review_id):
    # Only one review from its ID
    sql = """SELECT
                Review.*,
                User.username,
                User.profile_picture,
                Album.album_title,
                Album.album_cover,
                Artist.artist_id,
                Artist.artist_name
            FROM review
            JOIN User
            ON Review.user_id = User.user_id
            JOIN Album ON Review.album_id = Album.album_id
            JOIN Artist ON Album.artist_id = Artist.artist_id
            WHERE review_id = ?;"""
    comment_sql = """SELECT
                        Comment.*,
                        User.username,
                        User.profile_picture
                    FROM Comment
                    JOIN User ON Comment.user_id = User.user_id
                    WHERE review_id = ?
                    ORDER BY comment_id DESC;"""
    reply_sql = """SELECT
                    Reply.*,
                    User.username,
                    User.profile_picture
                FROM Reply
                JOIN User ON Reply.user_id = User.user_id
                WHERE comment_id = ?
                ORDER BY reply_id ASC;"""
    review = query_db(sql, (review_id,), True)
    if review is None:
        abort(404)
    comments = query_db(comment_sql, (review_id,))
    comment_list = []
    for comment in comments:
        comment_data = dict(comment)
        comment_data['replies'] = query_db(reply_sql, (comment['comment_id'],))
        comment_list.append(comment_data)
    comments = comment_list
    if request.method == 'POST':
        if 'user_id' not in session:
            return redirect(url_for('login'))
        comment_text = request.form['comment_text']
        if any(word in comment_text.lower() for word in BANNED_WORDS):
            return render_template("review.html", review=review, comments=comments, comment_text=comment_text, comment_error="Your comment contains words that are not allowed!")
        db = get_db()
        db.execute('INSERT INTO COMMENT (user_id, review_id, comment_text, comment_date) VALUES (?, ?, ?, ?)', (session['user_id'], review_id, comment_text, date.today().strftime('%d/%m/%Y')))
        db.commit()
        return redirect(url_for('review_page', review_id=review_id))
    return render_template("review.html", review=review, comments=comments)


# Route for writing replies to comments
@app.route('/comment/<int:comment_id>/reply', methods=['POST'])
def reply_to_comment(comment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comment_sql = """SELECT * FROM Comment WHERE comment_id = ?"""
    comment = query_db(comment_sql, (comment_id,), one=True)
    reply_sql = """INSERT INTO Reply (user_id, comment_id, reply_text, reply_date) VALUES (?, ?, ?, ?)"""
    if comment is None:
        abort(404)
    reply_text = request.form['reply_text']
    if any(word in reply_text.lower() for word in BANNED_WORDS):
        review_sql = """SELECT Review.*, User.username, User.profile_picture, Album.album_title, Album.album_cover, Artist.artist_id, Artist.artist_name
                 FROM Review
                 JOIN User ON Review.user_id = User.user_id
                 JOIN Album ON Review.album_id = Album.album_id
                 JOIN Artist ON Album.artist_id = Artist.artist_id
                 WHERE review_id = ?;"""
        all_comment_sql = """SELECT Comment.*, User.username, User.profile_picture
                           FROM Comment
                           JOIN User ON Comment.user_id = User.user_id
                           WHERE review_id = ?
                           ORDER BY comment_id DESC;"""
        reply_sql = """SELECT Reply.*, User.username, User.profile_picture
                      FROM Reply
                      JOIN User ON Reply.user_id = User.user_id
                      WHERE comment_id = ?
                      ORDER BY reply_id ASC;"""
        review = query_db(review_sql, (comment['review_id'],), True)
        comments = query_db(all_comment_sql, (comment['review_id'],))
        comment_list = []
        for current_comment in comments:
            comment_data = dict(current_comment)
            comment_data['replies'] = query_db(reply_sql, (current_comment['comment_id'],))
            comment_list.append(comment_data)
        comments = comment_list
        return render_template("review.html",
                               review=review,
                               comments=comments,
                               reply_text=reply_text,
                               reply_comment_id=comment_id,
                               reply_error="Your reply contains words that are not allowed!")
    db = get_db()
    db.execute(reply_sql, (session['user_id'], comment_id, reply_text, date.today().strftime('%d/%m/%Y')))
    db.commit()
    return redirect(url_for('review_page', review_id=comment['review_id']))


# Route for editing a review
@app.route('/review/<int:review_id>/edit', methods=['GET', 'POST'])
def edit_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    review_sql = """SELECT
                        Review.*,
                        Album.album_title,
                        Album.album_cover,
                        Album.release_year,
                        Artist.artist_name
                    FROM Review
                    JOIN Album ON Review.album_id = Album.album_id
                    JOIN Artist ON Album.artist_id = Artist.artist_id
                    WHERE review_id = ?"""
    review = query_db(review_sql, (review_id,), True)
    edit_sql = """UPDATE Review SET rating = ?, review_text = ? WHERE review_id = ?"""
    if review is None:
        abort(404)
    if review['user_id'] != session['user_id']:
        abort(403)
    average_rating_sql = """SELECT AVG(rating) AS average_rating FROM Review WHERE album_id = ?"""
    average = query_db(average_rating_sql, (review['album_id'],), True)
    average_rating = average['average_rating']
    if average_rating is not None:
        average_rating = round(average_rating, 1)
    if request.method == 'POST':
        rating = float(request.form['rating'])
        review_text = request.form['review_text']
        if rating < 0.1 or rating > 10.0:
            return render_template("edit_review.html", review=review, average_rating=average_rating, error="Rating must be between 0.1 and 10.0!")
        db = get_db()
        db.execute(edit_sql, (rating, review_text, review_id))
        db.commit()
        return redirect(url_for('review_page', review_id=review_id))
    return render_template("edit_review.html", review=review, average_rating=average_rating)


# Route for deleting a review
@app.route('/review/<int:review_id>/delete', methods=['POST'])
def delete_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    review_sql = """SELECT * FROM Review WHERE review_id = ?"""
    review = query_db(review_sql, (review_id,),True)
    delete_sql = """DELETE FROM Review WHERE review_id = ?"""
    comment_delete_sql = """DELETE FROM Comment WHERE review_id = ?"""
    if review is None:
        abort(404)
    if review['user_id'] != session['user_id']:
        abort(403)
    db = get_db()
    db.execute(comment_delete_sql, (review_id,))
    db.execute(delete_sql, (review_id,))
    db.commit()
    return redirect(url_for('reviews', album_id=review['album_id']))


# Route for deleting a comment
@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comment_sql = """SELECT * FROM Comment WHERE comment_id = ?"""
    comment = query_db(comment_sql, (comment_id,), one=True)
    delete_sql = """DELETE FROM Comment WHERE comment_id = ?"""
    reply_delete_sql = """DELETE FROM Reply WHERE comment_id = ?"""
    if comment is None:
        abort(404)
    if comment['user_id'] != session['user_id']:
        abort(403)
    db = get_db()
    db.execute(reply_delete_sql, (comment_id,))
    db.execute(delete_sql, (comment_id,))
    db.commit()
    return redirect(url_for('review_page', review_id=comment['review_id']))


# Route for deleting a reply
@app.route('/reply/<int:reply_id>/delete', methods=['POST'])
def delete_reply(reply_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    reply_sql = """SELECT * FROM Reply WHERE reply_id = ?"""
    reply = query_db(reply_sql, (reply_id,), one=True)
    if reply is None:
        abort(404)
    delete_sql = """DELETE FROM Reply WHERE reply_id = ?"""
    comment_sql = """SELECT review_id FROM Comment WHERE comment_id = ?"""
    comment = query_db(comment_sql, (reply['comment_id'],), one=True)
    if reply['user_id'] != session['user_id']:
        abort(403)
    db = get_db()
    db.execute(delete_sql, (reply_id,))
    db.commit()
    return redirect(url_for('review_page', review_id=comment['review_id']))


# Route for artists page
@app.route('/artists')
def artists():
    # Run SQL query to get artists and all their details
    sql = """SELECT * FROM artist;"""
    artists = query_db(sql)
    return render_template("artists.html", active_page="artists", artists=artists)


# Route for one artist's page
@app.route('/artist/<int:artist_id>')
def artist(artist_id):
    # Only one artist from its ID
    artist_sql = """SELECT * FROM artist WHERE artist_id = ?;"""
    artist = query_db(artist_sql, (artist_id,), True)
    album_sql = """SELECT * FROM Album WHERE artist_id = ?"""
    if artist is None:
        abort(404)
    albums = query_db(album_sql, (artist_id,))
    return render_template("artist.html", artist=artist, albums=albums)


# Route for my profile page
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    sql = """SELECT Review.*, Album.album_title, Album.album_cover FROM Review JOIN Album ON Review.album_id = Album.album_id WHERE Review.user_id = ? ORDER BY Review.review_date DESC"""
    reviews = query_db(sql, (session['user_id'],))
    return render_template("profile.html", active_page="profile", reviews=reviews)


# Route for editing my profile
@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_sql = """SELECT * FROM User WHERE user_id = ?"""
    user = query_db(user_sql, (session['user_id'],), one=True)
    edit_sql = """UPDATE User SET username = ?, user_bio = ?, profile_picture = ? WHERE user_id = ?"""
    edit_password_sql = """UPDATE User SET username = ?, user_bio = ?, password = ?, profile_picture = ? WHERE user_id = ?"""
    if user is None:
        abort(404)
    if request.method == 'POST':
        username = request.form['username']
        bio = request.form['bio']
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        profile_picture = request.files['profile_picture']
        profile_filename = user['profile_picture']
        if any(word in bio.lower() for word in BANNED_WORDS):
            return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Your bio contains words that are not allowed!")
        if len(username) < 3:
            return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Username must be at least 3 characters!")
        if len(username) > 20:
            return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Username must be 20 characters or less!")
        if ' ' in username:
            return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Username cannot contain spaces!")
        if any(word in username.lower() for word in BANNED_WORDS):
            return render_template("edit_profile.html", user=user, username=username, bio=bio, error="That username is not allowed!")
        takenusernamesql = """SELECT * FROM User WHERE LOWER(username) = LOWER(?) AND user_id != ?"""
        takenusername = query_db(takenusernamesql, (username, session['user_id']), one=True)
        if takenusername:
            return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Username already taken!")
        if current_password or new_password:
            if not current_password or not new_password:
                return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Enter both your current and new password!")
            if not check_password_hash(user['password'], current_password):
                return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Current password is incorrect!")
            if new_password == current_password:
                return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Your new password cannot be the same as your current password!")
            if len(new_password) < 8:
                return render_template("edit_profile.html", user=user, username=username, bio=bio, error="New password must be at least 8 characters!")
            if new_password in BAD_PASSWORDS:
                return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Weak password, choose a stronger one!")
            hashed_password = generate_password_hash(new_password)
        if profile_picture and profile_picture.filename:
            if not allowed_file(profile_picture.filename):
                return render_template("edit_profile.html", user=user, username=username, bio=bio, error="Profile picture must be a PNG, JPG, JPEG, GIF, or WEBP file!")
            filename = secure_filename(profile_picture.filename)
            extension = filename.rsplit('.', 1)[1].lower()
            new_filename = f"profile_{session['user_id']}.{extension}"
            filepath = os.path.join('static', 'images', new_filename)
            profile_picture.save(filepath)
            old_filename = user['profile_picture']
            if old_filename.startswith(f"profile_{session['user_id']}.") and old_filename != new_filename:
                old_filepath = os.path.join('static', 'images', old_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            profile_filename = new_filename
        db = get_db()
        if current_password or new_password:
            db.execute(edit_password_sql, (username, bio, hashed_password, profile_filename, session['user_id']))
        else:
            db.execute(edit_sql, (username, bio, profile_filename, session['user_id']))
        db.commit()
        session['username'] = username
        return redirect(url_for('profile'))
    return render_template("edit_profile.html", user=user)


# Route for clearing profile picture
@app.route('/profile/edit/clear-picture', methods=['POST'])
def clear_profile_picture():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_sql = """SELECT profile_picture FROM User WHERE user_id = ?"""
    user = query_db(user_sql, (session['user_id'],), one=True)
    update_sql = """UPDATE User SET profile_picture = ? WHERE user_id = ?"""
    if user is None:
        abort(404)
    old_filename = user['profile_picture']
    if old_filename.startswith(f"profile_{session['user_id']}."):
        old_filepath = os.path.join('static', 'images', old_filename)
        if os.path.exists(old_filepath):
            os.remove(old_filepath)
    db = get_db()
    db.execute(update_sql, ('profile_placeholder.png', session['user_id']))
    db.commit()
    return redirect(url_for('edit_profile'))


# Route for other user profiles
@app.route('/user/<int:user_id>')
def user(user_id):
    sql = """SELECT * FROM User WHERE user_id = ?;"""
    review_sql = """SELECT
                        Review.*,
                        Album.album_title,
                        Album.album_cover
                    FROM Review
                    JOIN Album ON Review.album_id = Album.album_id
                    WHERE Review.user_id = ?
                    ORDER BY Review.review_date DESC;"""
    user = query_db(sql, (user_id,), True)
    reviews = query_db(review_sql, (user_id,))
    if user is None:
        abort(404)
    return render_template("user.html", user=user, reviews=reviews)


# Run statement
if __name__ == "__main__":
    app.run(debug=True)

