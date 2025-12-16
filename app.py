from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.static_folder = 'public/static'
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'public/static/audio'

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local development fallback - use absolute path to avoid OneDrive issues
    instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    db_path = os.path.join(instance_dir, 'playlisthub.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

db = SQLAlchemy(app)

GENRES = ['Pop', 'Hip-Hop', 'Rock', 'Electronic', 'R&B', 'Country', 'Jazz', 'Classical', 'Indie', 'K-Pop']
ALLOWED_EXTENSIONS = {'mp3'}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    plain_password = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    playlists = db.relationship('Playlist', backref='author')
    votes = db.relationship('Vote', backref='user')

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    songs = db.Column(db.Text, nullable=True)
    genre = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    votes = db.relationship('Vote', backref='playlist')

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    value = db.Column(db.Integer, nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

with app.app_context():
    db.create_all()
    users = User.query.all()
    for user in users:
        if user.password and not user.password.startswith('pbkdf2'):
            user.password = generate_password_hash(user.password)
            print("Hashed existing password:", user.password)
            db.session.commit()
    
    if User.query.count() == 0:
        import random
        import string
        for i in range(3):
            username = ''.join(random.choices(string.ascii_lowercase, k=8))
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            hashed = generate_password_hash(password)
            print("Created hashed password for demo user:", hashed)
            demo_user = User(username=username, password=hashed, plain_password=password)
            db.session.add(demo_user)
        db.session.commit()

def get_vote_count(playlist):
    result = db.session.query(db.func.sum(Vote.value)).filter_by(playlist_id=playlist.id).scalar()
    if result is not None:
        return result
    else:
        return 0

def get_user_vote(playlist_id):
    if 'user_id' not in session:
        return 0
    vote = Vote.query.filter_by(user_id=session['user_id'], playlist_id=playlist_id).first()
    if vote:
        return vote.value
    else:
        return 0

def is_logged_in():
    if 'user_id' in session:
        return True
    else:
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_genre_folder(genre):
    genre_map = {
        'Pop': 'pop',
        'Hip-Hop': 'hiphop',
        'Rock': 'rock',
        'Electronic': 'electronic',
        'R&B': 'rb',
        'Country': 'country',
        'Jazz': 'jazz',
        'Classical': 'classical',
        'Indie': 'indie',
        'K-Pop': 'kpop'
    }
    return genre_map.get(genre, 'pop')

def get_current_user_id():
    return session.get('user_id')

@app.route('/')
def home():
    genre_filter = request.args.get('genre', '')
    search_text = request.args.get('search', '')
    
    all_playlists = Playlist.query.order_by(Playlist.created_at.desc()).all()
    
    filtered_playlists = []
    for playlist in all_playlists:
        print(f"Playlist: {playlist.title}, Genre: {playlist.genre}")
        should_include = True
        if genre_filter:
            if playlist.genre.strip().lower() != genre_filter.strip().lower():
                should_include = False
        if search_text:
            if search_text.lower() not in playlist.title.lower():
                should_include = False
        if should_include:
            filtered_playlists.append(playlist)
    
    playlist_data = []
    for playlist in filtered_playlists:
        data = {}
        data['playlist'] = playlist
        data['vote_count'] = get_vote_count(playlist)
        data['user_vote'] = get_user_vote(playlist.id)
        playlist_data.append(data)
    
    return render_template('home.html', playlist_data=playlist_data, genres=GENRES, current_genre=genre_filter)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    username = request.form['username']
    password = request.form['password']
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return render_template('signup.html', error='Username already exists')
    
    hashed_password = generate_password_hash(password)
    print("Hashed password for new user:", hashed_password)
    new_user = User(username=username, password=hashed_password, plain_password=password)
    db.session.add(new_user)
    db.session.commit()
    
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        user = None
        if is_logged_in():
            user = User.query.get(get_current_user_id())
        all_users = User.query.all()
        users = []
        for u in all_users:
            if u.username and u.username.lower() == 'kanye_lover3000':
                continue
            users.append({
                'username': u.username,
                'plain_password': u.plain_password
            })
        return render_template('login.html', user=user, users=users)
    
    username = request.form['username']
    password = request.form['password']
    
    user = User.query.filter_by(username=username).first()
    
    if user:
        if check_password_hash(user.password, password) or user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))
    
    # Rebuild users list for display on failed login, excluding Kanye_Lover3000
    all_users = User.query.all()
    users = []
    for u in all_users:
        if u.username and u.username.lower() == 'kanye_lover3000':
            continue
        users.append({
            'username': u.username,
            'plain_password': u.plain_password
        })
    return render_template('login.html', error='Invalid username or password', users=users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/create', methods=['GET', 'POST'])
def create_playlist():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('create.html', genres=GENRES)
    
    title = request.form['title']
    description = request.form['description']
    songs = request.form.get('songs', '')
    genre = request.form['genre']
    
    new_playlist = Playlist(
        title=title,
        description=description,
        songs=songs,
        genre=genre,
        user_id=get_current_user_id()
    )
    db.session.add(new_playlist)
    db.session.commit()
    
    return redirect(url_for('home'))

@app.route('/playlist/<int:id>')
def view_playlist(id):
    playlist = Playlist.query.get_or_404(id)
    
    songs_text = playlist.songs
    songs_lines = songs_text.split('\n')
    songs_list = []
    for song in songs_lines:
        song = song.strip()
        if song:
            songs_list.append(song)
    
    comments = Comment.query.filter_by(playlist_id=id).order_by(Comment.created_at.desc()).all()
    
    return render_template(
        'playlist.html',
        playlist=playlist,
        vote_count=get_vote_count(playlist),
        user_vote=get_user_vote(id),
        songs_list=songs_list,
        comments=comments
    )

@app.route('/vote/<int:playlist_id>/<value>', methods=['POST'])
def vote(playlist_id, value):
    try:
        value = int(value)
        if not is_logged_in():
            return jsonify({'error': 'Not logged in'}), 401
        
        if value != 1 and value != -1:
            return jsonify({'error': 'Invalid vote'}), 400
        
        playlist = Playlist.query.get(playlist_id)
        if not playlist:
            return jsonify({'error': 'Playlist not found'}), 404
        
        user_id = get_current_user_id()
        # Fetch all votes for this user/playlist to ensure we keep at most one
        user_votes = Vote.query.filter_by(user_id=user_id, playlist_id=playlist_id).all()
        existing_vote = user_votes[0] if user_votes else None
        
        # Remove any extra duplicate rows if they exist
        if len(user_votes) > 1:
            for dup in user_votes[1:]:
                db.session.delete(dup)
        
        if existing_vote:
            if existing_vote.value == value:
                # Same vote clicked again: keep as-is (no change)
                pass
            else:
                # Opposite vote clicked: remove current vote only (net change of 1)
                db.session.delete(existing_vote)
        else:
            # No vote yet: create one
            new_vote = Vote(user_id=user_id, playlist_id=playlist_id, value=value)
            db.session.add(new_vote)
        
        db.session.commit()
        
        # Expire all objects to ensure fresh data
        db.session.expire_all()
        
        # Re-query playlist to get fresh data
        playlist = Playlist.query.get(playlist_id)
        
        # Recalculate vote count with fresh query
        response_data = {}
        response_data['vote_count'] = get_vote_count(playlist)
        response_data['user_vote'] = get_user_vote(playlist_id)
        
        return jsonify(response_data)
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/add_song/<int:playlist_id>', methods=['POST'])
def add_song(playlist_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    playlist = Playlist.query.get_or_404(playlist_id)
    
    if playlist.user_id != get_current_user_id():
        return redirect(url_for('home'))
    
    artist = request.form['artist'].strip()
    song_title = request.form['song_title'].strip()
    
    if artist and song_title:
        new_song = artist + ' - ' + song_title
        
        # Handle file upload if provided
        if 'music_file' in request.files:
            file = request.files['music_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = f"{artist} - {song_title}.mp3"
                # Use secure_filename but preserve the format
                filename = secure_filename(filename).replace('_', ' ')
                
                genre_folder = get_genre_folder(playlist.genre)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], genre_folder)
                
                os.makedirs(upload_path, exist_ok=True)
                
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)
        
        if playlist.songs:
            playlist.songs = playlist.songs + '\n' + new_song
        else:
            playlist.songs = new_song
        
        db.session.commit()
    
    return redirect(url_for('view_playlist', id=playlist_id))

@app.route('/delete_song/<int:playlist_id>/<int:song_index>', methods=['POST'])
def delete_song(playlist_id, song_index):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    playlist = Playlist.query.get_or_404(playlist_id)
    
    if playlist.user_id != get_current_user_id():
        return redirect(url_for('home'))
    
    songs_lines = playlist.songs.split('\n')
    songs_list = []
    for song in songs_lines:
        song = song.strip()
        if song:
            songs_list.append(song)
    
    if song_index >= 0 and song_index < len(songs_list):
        songs_list.pop(song_index)
        playlist.songs = '\n'.join(songs_list)
        db.session.commit()
    
    return redirect(url_for('view_playlist', id=playlist_id))

@app.route('/profile')
def profile():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user = User.query.get(get_current_user_id())
    user_playlists = Playlist.query.filter_by(user_id=get_current_user_id()).all()
    
    playlist_data = []
    for playlist in user_playlists:
        data = {}
        data['playlist'] = playlist
        data['vote_count'] = get_vote_count(playlist)
        playlist_data.append(data)
    
    return render_template('profile.html', user=user, playlist_data=playlist_data)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_playlist(id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    playlist = Playlist.query.get_or_404(id)
    
    if playlist.user_id != get_current_user_id():
        return redirect(url_for('home'))
    
    Vote.query.filter_by(playlist_id=id).delete()
    Comment.query.filter_by(playlist_id=id).delete()
    db.session.delete(playlist)
    db.session.commit()
    
    return redirect(url_for('profile'))

@app.route('/add_comment/<int:playlist_id>', methods=['POST'])
def add_comment(playlist_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    playlist = Playlist.query.get_or_404(playlist_id)
    comment_text = request.form.get('comment', '').strip()
    
    if not comment_text:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Comment cannot be empty'}), 400
        return redirect(url_for('view_playlist', id=playlist_id))
    
    new_comment = Comment(
        user_id=get_current_user_id(),
        username=session['username'],
        comment=comment_text,
        playlist_id=playlist_id
    )
    db.session.add(new_comment)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'id': new_comment.id,
            'username': new_comment.username,
            'comment': new_comment.comment,
            'created_at': new_comment.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'updated': False,
            'playlist_id': playlist_id
        })
    
    return redirect(url_for('view_playlist', id=playlist_id))

@app.route('/edit_comment/<int:comment_id>', methods=['POST'])
def edit_comment(comment_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != get_current_user_id():
        return redirect(url_for('home'))
    
    comment_text = request.form.get('comment', '').strip()
    if comment_text:
        comment.comment = comment_text
        db.session.commit()
    
    return redirect(url_for('view_playlist', id=comment.playlist_id))

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != get_current_user_id():
        return redirect(url_for('home'))
    
    playlist_id = comment.playlist_id
    db.session.delete(comment)
    db.session.commit()
    
    return redirect(url_for('view_playlist', id=playlist_id))

@app.route('/upload_music', methods=['GET', 'POST'])
def upload_music():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('upload_music.html', genres=GENRES)
    
    if 'music_file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['music_file']
    artist = request.form.get('artist', '').strip()
    song_title = request.form.get('song_title', '').strip()
    genre = request.form.get('genre', 'Pop')
    
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if not artist or not song_title:
        flash('Please provide both artist and song title')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = f"{artist} - {song_title}.mp3"
        # Use secure_filename but preserve spaces
        filename = secure_filename(filename).replace('_', ' ')
        
        genre_folder = get_genre_folder(genre)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], genre_folder)
        
        os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        flash(f'Successfully uploaded: {artist} - {song_title}')
        return redirect(url_for('upload_music'))
    else:
        flash('Invalid file type. Please upload an MP3 file.')
        return redirect(request.url)

def add_comment(playlist_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    playlist = Playlist.query.get_or_404(playlist_id)
    comment_text = request.form.get('comment', '').strip()
    
    if comment_text:
        new_comment = Comment(
            username=session['username'],
            comment=comment_text,
            playlist_id=playlist_id
        )
        db.session.add(new_comment)
        db.session.commit()
    
    return redirect(url_for('view_playlist', id=playlist_id))

if __name__ == '__main__':
    app.run(debug=True)