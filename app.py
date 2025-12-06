from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.static_folder = 'public/static'
app.secret_key = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///playlisthub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

GENRES = ['Pop', 'Hip-Hop', 'Rock', 'Electronic', 'R&B', 'Country', 'Jazz', 'Classical', 'Indie', 'K-Pop']

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
            user_dict = {}
            user_dict['username'] = u.username
            user_dict['password'] = u.password
            user_dict['plain_password'] = u.plain_password
            users.append(user_dict)
        return render_template('login.html', user=user, users=users)
    
    username = request.form['username']
    password = request.form['password']
    
    user = User.query.filter_by(username=username).first()
    
    if user:
        if check_password_hash(user.password, password) or user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))
    
    all_users = User.query.all()
    users = []
    for u in all_users:
        user_dict = {}
        user_dict['username'] = u.username
        user_dict['password'] = u.password
        user_dict['plain_password'] = u.plain_password
        users.append(user_dict)
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
    
    return render_template(
        'playlist.html',
        playlist=playlist,
        vote_count=get_vote_count(playlist),
        user_vote=get_user_vote(id),
        songs_list=songs_list
    )

@app.route('/vote/<int:playlist_id>/<value>', methods=['POST'])
def vote(playlist_id, value):
    value = int(value)
    if not is_logged_in():
        return jsonify({'error': 'Not logged in'}), 401
    
    if value != 1 and value != -1:
        return jsonify({'error': 'Invalid vote'}), 400
    
    user_id = get_current_user_id()
    existing_vote = Vote.query.filter_by(user_id=user_id, playlist_id=playlist_id).first()
    
    if existing_vote:
        if existing_vote.value == value:
            db.session.delete(existing_vote)
        else:
            existing_vote.value = value
    else:
        new_vote = Vote(user_id=user_id, playlist_id=playlist_id, value=value)
        db.session.add(new_vote)
    
    db.session.commit()
    
    playlist = Playlist.query.get(playlist_id)
    
    response_data = {}
    response_data['vote_count'] = get_vote_count(playlist)
    response_data['user_vote'] = get_user_vote(playlist_id)
    
    return jsonify(response_data)

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
    db.session.delete(playlist)
    db.session.commit()
    
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=True)