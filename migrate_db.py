import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime

# Local SQLite app for reading
local_app = Flask(__name__)
local_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/suchithgali/C++ Files/CSE_108/final_project/instance/playlisthub.db'
local_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
local_db = SQLAlchemy(local_app)

# Remote PostgreSQL app for writing
remote_app = Flask(__name__)
postgres_url = os.getenv('POSTGRES_URL')
if not postgres_url:
    print("POSTGRES_URL environment variable not set!")
    exit(1)
remote_app.config['SQLALCHEMY_DATABASE_URI'] = postgres_url
remote_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
remote_db = SQLAlchemy(remote_app)

# Define models for both databases
class User(local_db.Model):
    id = local_db.Column(local_db.Integer, primary_key=True)
    username = local_db.Column(local_db.String(80), unique=True, nullable=False)
    password = local_db.Column(local_db.String(200), nullable=False)
    plain_password = local_db.Column(local_db.String(200), nullable=True)
    created_at = local_db.Column(local_db.DateTime, default=datetime.utcnow)
    playlists = local_db.relationship('Playlist', backref='author')
    votes = local_db.relationship('Vote', backref='user')

class Playlist(local_db.Model):
    id = local_db.Column(local_db.Integer, primary_key=True)
    title = local_db.Column(local_db.String(100), nullable=False)
    description = local_db.Column(local_db.Text)
    songs = local_db.Column(local_db.Text, nullable=True)
    genre = local_db.Column(local_db.String(50), nullable=False)
    user_id = local_db.Column(local_db.Integer, local_db.ForeignKey('user.id'), nullable=False)
    created_at = local_db.Column(local_db.DateTime, default=datetime.utcnow)
    votes = local_db.relationship('Vote', backref='playlist')

class Vote(local_db.Model):
    id = local_db.Column(local_db.Integer, primary_key=True)
    user_id = local_db.Column(local_db.Integer, local_db.ForeignKey('user.id'), nullable=False)
    playlist_id = local_db.Column(local_db.Integer, local_db.ForeignKey('playlist.id'), nullable=False)
    value = local_db.Column(local_db.Integer, nullable=False)

# Remote models
class RemoteUser(remote_db.Model):
    __tablename__ = 'user'
    id = remote_db.Column(remote_db.Integer, primary_key=True)
    username = remote_db.Column(remote_db.String(80), unique=True, nullable=False)
    password = remote_db.Column(remote_db.String(200), nullable=False)
    plain_password = remote_db.Column(remote_db.String(200), nullable=True)
    created_at = remote_db.Column(remote_db.DateTime, default=datetime.utcnow)
    playlists = remote_db.relationship('RemotePlaylist', backref='author')
    votes = remote_db.relationship('RemoteVote', backref='user')

class RemotePlaylist(remote_db.Model):
    __tablename__ = 'playlist'
    id = remote_db.Column(remote_db.Integer, primary_key=True)
    title = remote_db.Column(remote_db.String(100), nullable=False)
    description = remote_db.Column(remote_db.Text)
    songs = remote_db.Column(remote_db.Text, nullable=True)
    genre = remote_db.Column(remote_db.String(50), nullable=False)
    user_id = remote_db.Column(remote_db.Integer, remote_db.ForeignKey('user.id'), nullable=False)
    created_at = remote_db.Column(remote_db.DateTime, default=datetime.utcnow)
    votes = remote_db.relationship('RemoteVote', backref='playlist')

class RemoteVote(remote_db.Model):
    __tablename__ = 'vote'
    id = remote_db.Column(remote_db.Integer, primary_key=True)
    user_id = remote_db.Column(remote_db.Integer, remote_db.ForeignKey('user.id'), nullable=False)
    playlist_id = remote_db.Column(remote_db.Integer, remote_db.ForeignKey('playlist.id'), nullable=False)
    value = remote_db.Column(remote_db.Integer, nullable=False)

def migrate_data():
    with local_app.app_context():
        print("Reading data from local SQLite database...")

        # Get all users
        users = User.query.all()
        print(f"Found {len(users)} users")

        # Get all playlists
        playlists = Playlist.query.all()
        print(f"Found {len(playlists)} playlists")

        # Get all votes
        votes = Vote.query.all()
        print(f"Found {len(votes)} votes")

    with remote_app.app_context():
        print("Creating tables in PostgreSQL...")
        remote_db.create_all()

        print("Migrating users...")
        for user in users:
            # Skip if user already exists
            if RemoteUser.query.filter_by(username=user.username).first():
                print(f"User {user.username} already exists, skipping...")
                continue

            remote_user = RemoteUser(
                username=user.username,
                password=user.password,
                plain_password=user.plain_password,
                created_at=user.created_at
            )
            remote_db.session.add(remote_user)

        remote_db.session.commit()

        # Create a mapping of old user IDs to new user IDs
        user_id_map = {}
        for user in users:
            remote_user = RemoteUser.query.filter_by(username=user.username).first()
            if remote_user:
                user_id_map[user.id] = remote_user.id

        print("Migrating playlists...")
        for playlist in playlists:
            new_user_id = user_id_map.get(playlist.user_id)
            if not new_user_id:
                print(f"Could not find new user ID for playlist {playlist.title}, skipping...")
                continue

            remote_playlist = RemotePlaylist(
                title=playlist.title,
                description=playlist.description,
                songs=playlist.songs,
                genre=playlist.genre,
                user_id=new_user_id,
                created_at=playlist.created_at
            )
            remote_db.session.add(remote_playlist)

        remote_db.session.commit()

        # Create a mapping of old playlist IDs to new playlist IDs
        playlist_id_map = {}
        for playlist in playlists:
            # Find the corresponding remote playlist
            remote_playlist = RemotePlaylist.query.filter_by(
                title=playlist.title,
                user_id=user_id_map.get(playlist.user_id)
            ).first()
            if remote_playlist:
                playlist_id_map[playlist.id] = remote_playlist.id

        print("Migrating votes...")
        for vote in votes:
            new_user_id = user_id_map.get(vote.user_id)
            new_playlist_id = playlist_id_map.get(vote.playlist_id)

            if not new_user_id or not new_playlist_id:
                print(f"Could not map IDs for vote, skipping...")
                continue

            remote_vote = RemoteVote(
                user_id=new_user_id,
                playlist_id=new_playlist_id,
                value=vote.value
            )
            remote_db.session.add(remote_vote)

        remote_db.session.commit()

    print("Migration completed successfully!")

if __name__ == '__main__':
    migrate_data()