# On Repeat 12DTP

 On Repeat is a social music website created for 12DTP. Users can browse albums and artists, write reviews, and interact with other users through comments and replies.

 **Created by Fibitius Chan**

 ## Features

 - Create and customise an account
- Add a profile picture and user bio
- Browse albums and artists
- Rate albums from 0.1 to 10.0
- Write, edit and delete reviews
- Comment on reviews and reply to comments
- Edit and delete your own comments and replies
- View other users' profiles and reviews

 ## Built With

 - Python
- Flask
- SQLite
- HTML/CSS
- Jinja2
- Werkzeug
- python-dotenv

 ## Running the Project

 Install the required packages:

```
pip install flask werkzeug python-dotenv
```

 Create a `.env` file in the project folder and add:

```
SECRET_KEY=your-secret-key
```

 Run the application:

```
python app.py
```

 Then open `http://127.0.0.1:5000` in your browser.

 ## Project Files

```
app.py              Main Flask application
onrepeat.db         SQLite database
bannedwords.txt     List of banned words
badpasswords.txt    List of commonly used passwords
templates/          HTML templates
static/             CSS, images and profile pictures
```

 ## Security

 The application includes password hashing, parameterised SQL queries, user session management, content filtering, secure file handling and permission checks for editing and deleting user content.

 ## Author

 **Fibitius Chan**

 12DTP — On Repeat