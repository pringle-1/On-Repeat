"""
On Repeat 12DTP Social Music Website/Application

A social music site that allows users to:
- Create an account
- Customise their account and profile with profile pictures and custom user bios
- Review albums
- Comment on reviews
- Reply to comments
- Edit and delete their reviews, comments, and replies

Created by Fibitius Chan
"""

# Essential internal and external imports to ensure the app functions as intended

# Internal library imports for database access, file handling, and generating secure random values
import sqlite3
import os
import secrets

# External imports to support the app's functionality:
# date: accurately get the current date for accounts, comments, and replies
# Flask: route creation, page rendering, form handling, session creation, and error handling
# Werkzeug security: secure password hashing and checking
# Secure filename: safely processes the names of uploaded profile pictures
# Load dotenv: loads environment variables
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, g, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Setting up the application

# Create the Flask app instance
app = Flask(__name__)

# Load environment variables from .env file into the app
load_dotenv()

# Use SECRET_KEY from environment if it exists
# Otherwise generate a random key for the application run
# Used to securely sign session data
secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Set important app settings in variables
# DATABASE stores the name of the SQLite file
DATABASE = 'onrepeat.db'
# ALLOWED_EXTENSIONS contains the file types users can upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Set the secret key to securely store sessions
app.config['SECRET_KEY'] = secret_key

# Load word filter lists

# Open bannedwords.txt and store each banned word in a list
# strip() removes whitespace or newlines and lower() makes it so that the words are banned
# regardless of capitalisation
with open('bannedwords.txt', 'r', encoding='utf-8') as f:
    BANNED_WORDS = [line.strip().lower() for line in f]

# Open badpasswords.txt and store each bad password in a list
# Users cannot register with or update their passwords to these passwords as they are too common
with open('badpasswords.txt', 'r', encoding='utf-8') as f:
    BAD_PASSWORDS = [line.strip() for line in f]

# Database functionality

def get_db():
    """Create or reuse the database connection"""
    # Check if a database connection has already been established
    if 'db' not in g:
        # Create a connection to the database file
        g.db = sqlite3.connect(DATABASE)
        # Allow access to database rows using column names
        g.db.row_factory = sqlite3.Row
    return g.db


def allowed_file(filename):
    """Check whether a profile picture has an allowed extension"""
    # Ensure that the filename contains an extension (a dot)
    # which is in ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.teardown_appcontext
def close_db(_error):
    """Close the database connection after a request"""
    db = g.pop('db', None)
    # Close the connection if one was opened
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    """Function to pull data from the database with queries in SQL"""
    # Execute the query
    cur = get_db().execute(query, args)
    # Fetch all rows returned by query
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# Account registration

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle account registration"""
    # SQL statement to create a new account using the user's inputted values
    register_sql = """INSERT INTO User (username, password, date_joined) VALUES (?, ?, ?)"""
    # Process if the user submits it
    if request.method == 'POST':
        # Retrieve the user inputted values from the form
        username = request.form['username']
        password = request.form['password']
        # Ensure the username is long enough
        if len(username) < 3:
            return render_template("register.html",
                                   username=username,
                                   error="Username must be at least 3 characters!")
        # Ensure the username isn't too long
        if len(username) > 20:
            return render_template("register.html",
                                    username=username,
                                    error="Username must be 20 characters or less!")
        # Ensure the username doesn't contain spaces
        if ' ' in username:
            return render_template("register.html",
                                    username=username,
                                    error="Username cannot contain spaces!")
        # Ensure the username doesn't contain any values in the list of banned words
        if any(word in username.casefold() for word in BANNED_WORDS):
            return render_template("register.html",
                                    username=username,
                                    error="That username is not allowed!")
        # Ensure the password is long enough
        if len(password) < 8:
            return render_template("register.html",
                                    username=username,
                                    error="Password must be at least 8 characters!")
        # Ensure the password isn't any of the values in the list of bad passwords
        if password in BAD_PASSWORDS:
            return render_template("register.html",
                                    username=username,
                                    error="Weak password, choose a stronger one!")
        # Hash the password before storing it in the database
        # The user's inputted plaintext is never stored
        hashed_password = generate_password_hash(password)
        db = get_db()
        # Ensure the username isn't already taken
        existing = query_db("SELECT * FROM User WHERE LOWER(username) = LOWER(?)",
                                                                        (username,),
                                                                        one=True)
        # Return the appropriate error if the username is already taken
        if existing:
            return render_template("register.html",
                                    username=username,
                                    error="Username already taken!")
        # Add the new user to the database
        db.execute(register_sql, (username, hashed_password, date.today().strftime('%d/%m/%Y')))
        db.commit()
        # Redirect the user to the login page after successful registration
        return redirect(url_for('login'))
    return render_template("register.html")

# Login

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user logins"""
    if request.method == 'POST':
        # Retrieve the values entered into the form by the user
        username = request.form['username']
        password = request.form['password']
        user_sql = """SELECT * FROM User WHERE LOWER(username) = LOWER(?)"""
        user = query_db(user_sql, (username,), one=True)
        # Return the appropriate error if the user isn't found
        if user is None:
            return render_template("login.html", username=username, error="User not found!")
        # Ensure the inputted password matches the stored hashed password for the inputted username
        if not check_password_hash(user['password'], password):
            return render_template("login.html", username=username, error="Incorrect password!")
        # Store the user's ID in the session
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        # Redirect the user to the home page after successful login
        return redirect(url_for('home'))
    return render_template("login.html")

# Logout

@app.route('/logout')
def logout():
    """Log the current user out"""
    # Remove all information from the current session
    session.clear()
    # Redirect the user to the home page after successful logout
    return redirect(url_for('home'))

# Error handlers

# This page displays when the user doesn't have correct access permissions
@app.errorhandler(403)
def forbidden(_error):
    """Handle 403 handler custom page"""
    return render_template("403.html"), 403


# This page displays when the user goes to a page that doesn't exist
@app.errorhandler(404)
def page_not_found(_error):
    """Error 404 handler custom page"""
    return render_template("404.html"), 404

# Template context

@app.context_processor
def inject_user():
    """Make current user data available to all templates"""
    user = None
    # Checks if a user ID is stored in the current session
    if 'user_id' in session:
        # Retrieve that user's data from the database
        user = query_db("SELECT * FROM User WHERE user_id = ?", (session['user_id'],), one=True)
    # User is available to templates as current_user
    return dict(current_user=user)

# Home page

@app.route('/')
def home():
    """Display the home page"""
    # Retrieve all albums and their details from the database
    sql = """SELECT * FROM album;"""
    albums = query_db(sql)
    # Displays the home page with album data passed to the home HTML template
    return render_template("index.html", active_page="home", albums=albums)

# Albums

@app.route('/albums')
def albums():
    """Route for albums page"""
    # Retrieve all albums and their details from the database
    sql = """SELECT * FROM album;"""
    albums = query_db(sql)
    # Displays the albums page with album data passed to the albums page HTML template
    return render_template("albums.html", active_page="albums", albums=albums)


@app.route('/album/<int:album_id>')
def album(album_id):
    """Route for individual album pages"""
    # Retrieve the album and its artists using SQL JOIN
    sql = """SELECT *
             FROM album
             JOIN Artist ON Album.artist_id = Artist.artist_id
             WHERE album_id = ?;"""
    # Calculate the average rating for the selected album
    average_rating_sql = """SELECT AVG(rating) AS average_rating FROM Review WHERE album_id = ?;"""
    # Retrieve album information and its average rating
    album = query_db(sql, (album_id,), True)
    # Display the custom error 404 handler page if the album doesn't exist
    if album is None:
        abort(404)
    average = query_db(average_rating_sql, (album_id,), one=True)
    average_rating = average['average_rating']
    # Round the average rating to one decimal place
    if average_rating is not None:
        average_rating = round(average_rating, 1)
    return render_template("album.html", album=album, average_rating=average_rating)

# Review creation

@app.route('/album/<int:album_id>/review', methods=['GET', 'POST'])
def review(album_id):
    """Route for review creation"""
    # Retrieve the selected album and its artist
    sql = """SELECT *
             FROM Album
             JOIN Artist ON Album.artist_id = Artist.artist_id
             WHERE album_id = ?;"""
    # Calculate the average rating for the selected album
    average_rating_sql = """SELECT AVG(rating) AS average_rating FROM Review WHERE album_id = ?;"""
    # Retrieve the value for the album's average rating and the album's details
    average = query_db(average_rating_sql, (album_id,), one=True)
    average_rating = average['average_rating']
    album = query_db(sql, (album_id,), True)
    # SQL query to add the new review to the database
    review_sql = """INSERT INTO Review (user_id,
                                        album_id,
                                        rating,
                                        review_text,
                                        review_date)
                                VALUES (?, ?, ?, ?, ?)"""
    # Display the custom error 404 handler page if the album doesn't exist
    if album is None:
        abort(404)
    # Round the average rating to one decimal place
    if average_rating is not None:
        average_rating = round(average_rating, 1)
    # Prevent review creation if the user isn't logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        rating = float(request.form['rating'])
        review_text = request.form['review_text']
        # Prevent review creation if the review contains banned words
        if any(word in review_text.lower() for word in BANNED_WORDS):
            return render_template("reviewer.html",
                                   album=album,
                                   average_rating=average_rating,
                                   rating=rating,
                                   review_text=review_text,
                                   error="Your review contains words that are not allowed!")
        # Ensure the number rating is within the allowed range
        if rating < 0.1 or rating > 10:
            return render_template("reviewer.html",
                                    album=album,
                                    error="Rating must be between 0.1 and 10.0!")
        db = get_db()
        try:
            # Add the new review to the database
            db.execute(review_sql,
                       (session['user_id'],
                       album_id,
                       rating,
                       review_text,
                       date.today().strftime('%d/%m/%Y')))
            db.commit()
            # Redirect the user to the album's reviews after successful review creation
            return redirect(url_for('reviews', album_id=album_id))
        except sqlite3.IntegrityError:
            # Return the appropriate error if the user has already reviewed the album
            return render_template("reviewer.html",
                                    album=album,
                                    average_rating=average_rating,
                                    rating=rating,
                                    review_text=review_text,
                                    error="You have already reviewed this album!")
    return render_template("reviewer.html", album=album, average_rating=average_rating)

# All reviews

@app.route('/reviews')
def all_reviews():
    """Route for all reviews page"""
    # Retrieve reviews and their details
    review_sql = """
    SELECT
        Review.*,
        User.username,
        User.profile_picture,
        Album.album_title,
        Album.album_cover,
        Artist.artist_name,
        COUNT(DISTINCT Comment.comment_id)
        + COUNT(DISTINCT Reply.reply_id) AS interaction_count
    FROM Review
    JOIN User ON Review.user_id = User.user_id
    JOIN Album ON Review.album_id = Album.album_id
    JOIN Artist ON Album.artist_id = Artist.artist_id
    LEFT JOIN Comment ON Review.review_id = Comment.review_id
    LEFT JOIN Reply ON Comment.comment_id = Reply.comment_id
    GROUP BY Review.review_id
    ORDER BY interaction_count DESC;
    """
    # Execute the query
    reviews = query_db(review_sql)
    return render_template("all_reviews.html", active_page="all_reviews", reviews=reviews)

# Reviews for one album

@app.route('/album/<int:album_id>/reviews')
def reviews(album_id):
    """Route to read the reviews for one album"""
    # Retrieve all reviews for one album
    sql = """SELECT Review.*,
                User.username,
                User.profile_picture
             FROM Review
             JOIN User
             ON Review.user_id = User.user_id
             WHERE album_id = ?
             ORDER BY review_id DESC;"""
    # Retrieve the details for one album
    album_sql = """SELECT * FROM Album WHERE album_id = ?;"""
    album = query_db(album_sql, (album_id,), True)
    # Retrieve all reviews for one album
    reviews = query_db(sql, (album_id,))
    # Display the custom error 404 handler page if the album doesn't exist
    if album is None:
        abort(404)
    return render_template("reviews.html", album=album, reviews=reviews)

# Individual reviews and comments

@app.route("/review/<int:review_id>", methods=['GET', 'POST'])
def review_page(review_id):
    """Route for one review's page"""
    # Retrieve the details for one review
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
    # Retrieve the comments under the one review
    comment_sql = """SELECT
                        Comment.*,
                        User.username,
                        User.profile_picture
                    FROM Comment
                    JOIN User ON Comment.user_id = User.user_id
                    WHERE review_id = ?
                    ORDER BY comment_id DESC;"""
    # Retrieve the replies under one comment
    reply_sql = """SELECT
                    Reply.*,
                    User.username,
                    User.profile_picture
                FROM Reply
                JOIN User ON Reply.user_id = User.user_id
                WHERE comment_id = ?
                ORDER BY reply_id ASC;"""
    review = query_db(sql, (review_id,), True)
    # Display the custom error 404 handler page if the review doesn't exist
    if review is None:
        abort(404)
    comments = query_db(comment_sql, (review_id,))
    # Create a new list so each comment can have its replies attached to it
    comment_list = []
    for comment in comments:
        # Convert database row into dictionary
        comment_data = dict(comment)
        comment_data['replies'] = query_db(reply_sql, (comment['comment_id'],))
        # Add completed comment to list
        comment_list.append(comment_data)
    comments = comment_list
    if request.method == 'POST':
        # Prevent comment being posted if the user isn't logged in
        if 'user_id' not in session:
            return redirect(url_for('login'))
        comment_text = request.form['comment_text']
        # Prevent comment being posted if the comment contains banned words
        if any(word in comment_text.lower() for word in BANNED_WORDS):
            return render_template("review.html",
                                review=review,
                                comments=comments,
                                comment_text=comment_text,
                                comment_error="Your comment contains words that are not allowed!")
        db = get_db()
        # Add the new comment to the database
        db.execute(
            'INSERT INTO COMMENT '
            '(user_id, review_id, comment_text, comment_date) '
            'VALUES (?, ?, ?, ?)',
            (session['user_id'], review_id, comment_text, date.today().strftime('%d/%m/%Y'))
        )
        db.commit()
        # Redirect the user to the individual review page after successful comment posting
        return redirect(url_for('review_page', review_id=review_id))
    return render_template("review.html", review=review, comments=comments)

# Replies

@app.route('/comment/<int:comment_id>/reply', methods=['POST'])
def reply_to_comment(comment_id):
    """Route for writing replies to comments"""
    # Prevent reply posting if the user isn't logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Retrieve the comment being replied to and its details
    comment_sql = """SELECT * FROM Comment WHERE comment_id = ?"""
    comment = query_db(comment_sql, (comment_id,), one=True)
    # SQL statement to insert a new reply into the database
    reply_sql = """INSERT INTO Reply (user_id,
                                      comment_id,
                                      reply_text,
                                      reply_date)
                   VALUES (?, ?, ?, ?)"""
    # Display the custom error 404 handler page if the comment doesn't exist
    if comment is None:
        abort(404)
    # Prevent reply posting if the reply contains banned words
    reply_text = request.form['reply_text']
    if any(word in reply_text.lower() for word in BANNED_WORDS):
        # If the review contains banned words, retrieve the review and its comments again
        # so that the error message can be displayed
        review_sql = """SELECT Review.*,
                               User.username,
                               User.profile_picture,
                               Album.album_title,
                               Album.album_cover,
                               Artist.artist_id,
                               Artist.artist_name
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
        # Retrieve the review that has the comment being replied to
        review = query_db(review_sql, (comment['review_id'],), True)
        # Retrieve all other comments that the review has
        comments = query_db(all_comment_sql, (comment['review_id'],))
        # Create a list containing the comments and all their replies
        comment_list = []
        for current_comment in comments:
            comment_data = dict(current_comment)
            comment_data['replies'] = query_db(reply_sql, (current_comment['comment_id'],))
            comment_list.append(comment_data)
        comments = comment_list
        # Redirect the user to the individual review page
        return render_template("review.html",
                               review=review,
                               comments=comments,
                               reply_text=reply_text,
                               reply_comment_id=comment_id,
                               reply_error="Your reply contains words that are not allowed!")
    db = get_db()
    db.execute(
        reply_sql,
        (
            session['user_id'],
            comment_id,
            reply_text,
            date.today().strftime('%d/%m/%Y')
        )
    )
    db.commit()
    return redirect(url_for('review_page', review_id=comment['review_id']))

# Edit review

@app.route('/review/<int:review_id>/edit', methods=['GET', 'POST'])
def edit_review(review_id):
    """Route for review editing"""
    # Prevent review editing if the user isn't logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # SQL query to retrieve review and album details
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
    # SQL query to update the review details
    edit_sql = """UPDATE Review SET rating = ?, review_text = ? WHERE review_id = ?"""
    # Display the custom error 404 handler page if the review doesn't exist
    if review is None:
        abort(404)
    # Display the custom error 403 handler page if the user isn't the review creator
    if review['user_id'] != session['user_id']:
        abort(403)
    # Calculate the average rating of the album
    average_rating_sql = """SELECT AVG(rating) AS average_rating FROM Review WHERE album_id = ?"""
    average = query_db(average_rating_sql, (review['album_id'],), True)
    average_rating = average['average_rating']
    if average_rating is not None:
        average_rating = round(average_rating, 1)
    if request.method == 'POST':
        rating = float(request.form['rating'])
        review_text = request.form['review_text']
        # Prevent review updating if the review contains banned words
        if any(word in review_text.lower() for word in BANNED_WORDS):
            return render_template("edit_review.html",
                                review=review,
                                average_rating=average_rating,
                                review_text=review_text,
                                rating=rating,
                                error="Your edited review contains words that are not allowed!")
        # Ensure the number rating is within the allowed range
        if rating < 0.1 or rating > 10.0:
            return render_template("edit_review.html",
                                   review=review,
                                   average_rating=average_rating,
                                   error="Rating must be between 0.1 and 10.0!")
        # Update the review details stored in the database
        db = get_db()
        db.execute(edit_sql, (rating, review_text, review_id))
        db.commit()
        return redirect(url_for('review_page', review_id=review_id))
    return render_template("edit_review.html", review=review, average_rating=average_rating)

# Delete review

@app.route('/review/<int:review_id>/delete', methods=['POST'])
def delete_review(review_id):
    """Route for review deletion"""
    # Prevent review deletion if the user isn't logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # SQL query to retrieve review details
    review_sql = """SELECT * FROM Review WHERE review_id = ?"""
    review = query_db(review_sql, (review_id,), True)
    # SQL query to delete the review and any comments or replies it has
    delete_sql = """DELETE FROM Review WHERE review_id = ?"""
    reply_delete_sql = """DELETE FROM Reply
                          WHERE comment_id
                          IN (SELECT comment_id
                              FROM Comment
                              WHERE review_id = ?)"""
    comment_delete_sql = """DELETE FROM Comment WHERE review_id = ?"""
    # Display the custom error 404 handler page if the review doesn't exist
    if review is None:
        abort(404)
    # Display the custom error 403 handler page if the current user ID
    # doesn't match the reviewer's user ID
    if review['user_id'] != session['user_id']:
        abort(403)
    db = get_db()
    # Delete replies first as they depend on the comment they're under
    db.execute(reply_delete_sql, (review_id,))
    # Delete comments next after their replies have been deleted
    db.execute(comment_delete_sql, (review_id,))
    # Delete the review last after both their comments and replies have been deleted
    db.execute(delete_sql, (review_id,))
    db.commit()
    return redirect(url_for('reviews', album_id=review['album_id']))

# Delete comment

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    """Route for comment deletion"""
    # Prevent comment deletion if the user isn't logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # SQL query to retrieve the comment and its details
    comment_sql = """SELECT * FROM Comment WHERE comment_id = ?"""
    comment = query_db(comment_sql, (comment_id,), one=True)
    # SQL queries to delete the comment and its replies
    delete_sql = """DELETE FROM Comment WHERE comment_id = ?"""
    reply_delete_sql = """DELETE FROM Reply WHERE comment_id = ?"""
    # Display the custom error 404 handler page if the comment doesn't exist
    if comment is None:
        abort(404)
    # Display the custom error 403 handler page if the current user ID
    # doesn't match the commenter's user ID
    if comment['user_id'] != session['user_id']:
        abort(403)
    db = get_db()
    # Delete replies first as they belong to the comment
    db.execute(reply_delete_sql, (comment_id,))
    # Delete the comment after replies
    db.execute(delete_sql, (comment_id,))
    db.commit()
    return redirect(url_for('review_page', review_id=comment['review_id']))

# Delete reply

@app.route('/reply/<int:reply_id>/delete', methods=['POST'])
def delete_reply(reply_id):
    """Route for reply deletion"""
    # Prevent reply deletion if the user isn't logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # SQL query to retrieve the reply and its details
    reply_sql = """SELECT * FROM Reply WHERE reply_id = ?"""
    reply = query_db(reply_sql, (reply_id,), one=True)
    # Display the custom error 404 handler page if the reply doesn't exist
    if reply is None:
        abort(404)
    # SQL query to delete the reply
    delete_sql = """DELETE FROM Reply WHERE reply_id = ?"""
    # Retrieve the review ID so the user can be
    # redirected to the correct page after successful deletion
    comment_sql = """SELECT review_id FROM Comment WHERE comment_id = ?"""
    comment = query_db(comment_sql, (reply['comment_id'],), one=True)
    # Display the custom error 403 handler page if the current user ID
    # doesn't match the replier's user ID
    if reply['user_id'] != session['user_id']:
        abort(403)
    db = get_db()
    # Delete the reply
    db.execute(delete_sql, (reply_id,))
    db.commit()
    return redirect(url_for('review_page', review_id=comment['review_id']))

# Artists

@app.route('/artists')
def artists():
    """Route for page that displays all artists"""
    # SQL query to get artists and all their details from the database
    sql = """SELECT * FROM artist;"""
    artists = query_db(sql)
    # Display the all artists page
    return render_template("artists.html", active_page="artists", artists=artists)


@app.route('/artist/<int:artist_id>')
def artist(artist_id):
    """Route for one artist's page"""
    # SQL query to retrieve details for the selected artist
    artist_sql = """SELECT * FROM artist WHERE artist_id = ?;"""
    artist = query_db(artist_sql, (artist_id,), True)
    # Retrieve the albums made by the selected artist
    album_sql = """SELECT * FROM Album WHERE artist_id = ?"""
    # Display the custom error 404 handler page if the artist doesn't exist
    if artist is None:
        abort(404)
    albums = query_db(album_sql, (artist_id,))
    # Display the artist's page
    return render_template("artist.html", artist=artist, albums=albums)

# Current user profile

@app.route('/profile')
def profile():
    """Route for my profile page"""
    # The user must be logged in to view their profile
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # SQL query to retrieve the user's review details and
    # the covers and titles of the albums they've reviewed
    sql = """SELECT Review.*,
                    Album.album_title,
                    Album.album_cover
             FROM Review
             JOIN Album ON Review.album_id = Album.album_id
             WHERE Review.user_id = ?
             ORDER BY Review.review_date DESC"""
    reviews = query_db(sql, (session['user_id'],))
    # Display the user's profile page
    return render_template("profile.html", active_page="profile", reviews=reviews)

# Edit profile

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    """Route for profile editing"""
    # Prevent profile editing if the user isn't logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # SQL query to retrieve the user's details
    user_sql = """SELECT * FROM User WHERE user_id = ?"""
    user = query_db(user_sql, (session['user_id'],), one=True)
    # SQL query for when the user doesn't update their password
    edit_sql = """UPDATE User
                  SET username = ?,
                      user_bio = ?,
                      profile_picture = ?
                  WHERE user_id = ?"""
    # SQL query for then the user updates their password
    edit_password_sql = """UPDATE User
                           SET username = ?,
                               user_bio = ?,
                               password = ?,
                               profile_picture = ?
                           WHERE user_id = ?"""
    # Display the custom error 404 handler page if the user doesn't exist
    if user is None:
        abort(404)
    if request.method == 'POST':
        # Retrieve the user inputted values from the form
        username = request.form['username']
        bio = request.form['bio']
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        profile_picture = request.files['profile_picture']
        # Keep the same profile picture if it is not updated
        profile_filename = user['profile_picture']
        # Prevent bio updating if the new bio contains banned words
        if any(word in bio.lower() for word in BANNED_WORDS):
            return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Your bio contains words that are not allowed!")
        # Ensure the username is long enough
        if len(username) < 3:
            return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Username must be at least 3 characters!")
        # Ensure the username isn't too long
        if len(username) > 20:
            return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Username must be 20 characters or less!")
        # Ensure the username doesn't contain spaces
        if ' ' in username:
            return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Username cannot contain spaces!")
        # Prevent username updating if the new username contains banned words
        if any(word in username.lower() for word in BANNED_WORDS):
            return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="That username is not allowed!")
        # SQL query to find accounts with the same username excluding the current user
        taken_username_sql = """SELECT *
                              FROM User
                              WHERE LOWER(username) = LOWER(?)
                              AND user_id != ?"""
        taken_username = query_db(taken_username_sql, (username, session['user_id']), one=True)
        # Ensure the new username isn't already taken
        if taken_username:
            return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Username already taken!")
        # Process changes if either password field is filled in
        if current_password or new_password:
            # Ensure both password fields are filled in
            if not current_password or not new_password:
                return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Enter both your current and new password!")
            # Ensure that the current password field is correct
            if not check_password_hash(user['password'], current_password):
                return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Current password is incorrect!")
            # Prevent the user from reusing the same password
            if new_password == current_password:
                return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Your new password cannot be the same as your current password!")
            # Ensure the new password is long enough
            if len(new_password) < 8:
                return render_template("edit_profile.html",
                                        user=user,
                                        username=username,
                                        bio=bio,
                                        error="New password must be at least 8 characters!")
            # Prevent password updating if it matches a value in the list of bad passwords
            if new_password in BAD_PASSWORDS:
                return render_template("edit_profile.html",
                                        user=user,
                                        username=username,
                                        bio=bio, error="Weak password, choose a stronger one!")
            # Hash the password before storing it in the database
            hashed_password = generate_password_hash(new_password)
        if profile_picture and profile_picture.filename:
            # Ensure that the extension of the uploaded file is allowed
            if not allowed_file(profile_picture.filename):
                return render_template("edit_profile.html",
                            user=user,
                            username=username,
                            bio=bio,
                            error="Profile picture must be a PNG, JPG, JPEG, GIF, or WEBP file!")
            # Create a safe version of the new filename
            filename = secure_filename(profile_picture.filename)
            # Retrieve the file extension
            extension = filename.rsplit('.', 1)[1].lower()
            # Create a new filename for the uploaded image for each user ID
            # This ensures that each user has their own profile picture file
            new_filename = f"profile_{session['user_id']}.{extension}"
            # Create the path where the profile image is stored
            filepath = os.path.join('static', 'images', new_filename)
            profile_picture.save(filepath)
            # Retrieve the name of the old profile picture
            old_filename = user['profile_picture']
            # Delete the user's previous profile picture if it exists
            profile_prefix = f"profile_{session['user_id']}."
            if old_filename.startswith(profile_prefix) and old_filename != new_filename:
                old_filepath = os.path.join('static', 'images', old_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            # Update the filename of the profile picture
            profile_filename = new_filename
        db = get_db()
        # If the password was changed, update the password value
        if current_password or new_password:
            db.execute(edit_password_sql, (username,
                                           bio,
                                           hashed_password,
                                           profile_filename,
                                           session['user_id']))
        # Otherwise, only update the changed values
        else:
            db.execute(edit_sql, (username, bio, profile_filename, session['user_id']))
        db.commit()
        # Update the username stored in the current session
        session['username'] = username
        return redirect(url_for('profile'))
    return render_template("edit_profile.html", user=user)

# Clear profile picture

@app.route('/profile/edit/clear-picture', methods=['POST'])
def clear_profile_picture():
    """Route for profile picture clearing"""
    # Prevent profile picture clearing if the user isn't logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # SQL query to retrieve the filename of the user's current profile picture
    user_sql = """SELECT profile_picture FROM User WHERE user_id = ?"""
    user = query_db(user_sql, (session['user_id'],), one=True)
    # SQL query to replace the current image with the default placeholder image
    update_sql = """UPDATE User SET profile_picture = ? WHERE user_id = ?"""
    # Display the custom error 404 page handler if the user doesn't exist
    if user is None:
        abort(404)
    # Retrieve the filename of the user's current profile picture
    old_filename = user['profile_picture']
    # Only delete files that belong to the user
    if old_filename.startswith(f"profile_{session['user_id']}."):
        old_filepath = os.path.join('static', 'images', old_filename)
        # Delete the old image file if it exists
        if os.path.exists(old_filepath):
            os.remove(old_filepath)
    db = get_db()
    # Replace the database image value with the default placeholder image
    db.execute(update_sql, ('profile_placeholder.png', session['user_id']))
    db.commit()
    # Return to the edit profile page
    return redirect(url_for('edit_profile'))

# Other user profiles

@app.route('/user/<int:user_id>')
def user(user_id):
    """Route for pages of other users"""
    # SQL query to retrieve the selected user's details
    sql = """SELECT * FROM User WHERE user_id = ?;"""
    # SQL query to retrieve all reviews written by the selected user
    review_sql = """SELECT
                        Review.*,
                        Album.album_title,
                        Album.album_cover
                    FROM Review
                    JOIN Album ON Review.album_id = Album.album_id
                    WHERE Review.user_id = ?
                    ORDER BY Review.review_date DESC;"""
    # Find the user and the user's reviews
    user = query_db(sql, (user_id,), True)
    reviews = query_db(review_sql, (user_id,))
    # Display the custom error 404 page handler if the user doesn't exist
    if user is None:
        abort(404)
    # Display the user's profile and the user's reviews
    return render_template("user.html", user=user, reviews=reviews)

# Run application

# Ensures that the server only starts when the Python file is being run
if __name__ == "__main__":
    app.run(debug=True)
