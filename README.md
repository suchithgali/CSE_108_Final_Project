# PlaylistHub

A web application for creating, sharing, and voting on music playlists. Built with Flask, this app allows users to sign up, create playlists, vote on others' playlists, and play music directly in the browser.

## Features

- **User Authentication**: Secure signup and login with hashed passwords.
- **Playlist Management**: Create playlists with songs, descriptions, and genres.
- **Voting System**: Upvote and downvote playlists with a toggle-based system.
- **Music Playback**: Integrated audio player that streams MP3 files based on playlist genre.
- **Responsive UI**: Clean, modern interface with voting buttons and music controls.

## Technologies Used

- **Backend**: Flask (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **Security**: Werkzeug for password hashing
- **Audio**: HTML5 Audio API for playback

## Installation

1. **Clone or Download** the project files.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the App**:
   ```bash
   python app.py
   ```

4. **Access**: Open `http://127.0.0.1:5000/` in your browser.

## Usage

- **Signup/Login**: Create an account or log in with test accounts shown on the login page.
- **Home Page**: Browse playlists, vote with ▲ and ▼ buttons.
- **Create Playlist**: Add title, description, genre (no songs input needed—songs are predefined).
- **Playlist View**: Click on a playlist to view songs and play music.
- **Voting**: Click upvote/downvote to toggle votes. Buttons highlight when voted.

## Project Structure

- `app.py`: Main Flask application with routes and logic.
- `templates/`: HTML templates for pages.
- `static/`: CSS, JS, and audio files.
- `instance/`: SQLite database.
- `requirements.txt`: Python dependencies.

## Audio Files

MP3 files are organized by genre in `static/audio/{genre}/`. The app dynamically loads songs based on the playlist's genre.

## Security Notes

- Passwords are hashed with salt using Werkzeug.
- User input is handled securely.
- Demo accounts are created for testing.
