#!/usr/bin/env python3
"""
PlaylistHub Database Migration Script
Run this after setting up your PostgreSQL database
"""

import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Setup Flask app first
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database models (copied from app.py)
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

def migrate_database():
    """Migrate data from SQLite to PostgreSQL"""

    print("=== PlaylistHub Database Migration ===\n")

    # Check DATABASE_URL
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not set!")
        print("Set it with: export DATABASE_URL='your_postgresql_connection_string'")
        return False

    print(f"✅ Using database: {db_url.replace(db_url.split('@')[0], '***:***')}")

    # Setup Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db = SQLAlchemy(app)

    try:
        with app.app_context():
            print("🔄 Creating tables...")
            db.create_all()
            print("✅ Tables created")

            print("📥 Migrating data...")

            # Migrate users
            users_data = [
                (1, 'hwkzrbmv', 'pbkdf2:sha256:600000$MVzPVw7JQxNqrhQ0$baff7d851c4289c190cc80fc06736cc8708c4ef071236dfb0b76dab0a8d04cda', 'C0J2CvYdYl'),
                (2, 'jlovhyrj', 'pbkdf2:sha256:600000$u1KPe1eUIyDFGW8H$b1ee14e26e749bd1a150b4f304a5aec1b16b1f8332fcf4d0952e02099670ac13', 'WhHk05gjRT'),
                (3, 'bzcyiiwp', 'pbkdf2:sha256:600000$CxP2Hagn12CAva85$c68a248267dc1b148ce813dc032b4ea62d2924c23b52667e7d28008e6d332409', 'Yiq7CNBnrm'),
                (4, 'kanye_Lover3000', 'pbkdf2:sha256:600000$sVJLNVe3Phinnn55$73d741a1cb492a81e26086c33cf0a0dc8d4bb1819fa4fed3332f3bda19e5f38b', 'password123')
            ]

            for user_data in users_data:
                user = User(id=user_data[0], username=user_data[1], password=user_data[2], plain_password=user_data[3])
                db.session.add(user)
            print("✅ Users migrated")

            # Migrate playlists
            playlists_data = [
                (1, 'Christmas Songs', 'festive playlist for the holidays', 'Brenda Lee - Rocking Around the Christmas Tree\nWham! - Last Christmas\nMichael Bublé - It\'s Beginning To Look A Lot Like Christmas', 'Pop', 1),
                (2, 'R&B Music', 'nice R&B', 'The Weeknd - Blinding Lights\nKendrick Lamar, SZA - All the Stars', 'R&B', 2),
                (3, 'K-Pop playlist', 'nice kpop songs', 'BIGBANG - BANG BANG BANG\nG-DRAGON - POWER', 'K-Pop', 3),
                (4, 'Kanye is Awesome!!', 'Kanye Only!!', 'Kanye West - Flashing Lights\nKanye West - Good Morning\nKanye West - I Wonder', 'Pop', 4),
                (5, 'Kid Cudi', 'Super cool!!', 'Kid Cudi - Pursuit of Happiness', 'Pop', 4)
            ]

            for playlist_data in playlists_data:
                playlist = Playlist(id=playlist_data[0], title=playlist_data[1], description=playlist_data[2],
                                  songs=playlist_data[3], genre=playlist_data[4], user_id=playlist_data[5])
                db.session.add(playlist)
            print("✅ Playlists migrated")

            # Migrate votes
            votes_data = [
                (1, 2, 1, 1),
                (2, 3, 2, -1),
                (4, 4, 1, 1),
                (5, 4, 2, 1),
                (7, 1, 5, 1)
            ]

            for vote_data in votes_data:
                vote = Vote(id=vote_data[0], user_id=vote_data[1], playlist_id=vote_data[2], value=vote_data[3])
                db.session.add(vote)
            print("✅ Votes migrated")

            # Migrate comments
            comments_data = [
                (1, 1, 'kanye_Lover3000', 'Great Playlist!!', 2),
                (2, 1, 'kanye_Lover3000', 'woahhh', 3),
                (3, 1, 'kanye_Lover3000', 'Kanye is so coool!', 4),
                (4, 4, 'kanye_Lover3000', 'Kanye is awesome!!!', 4),
                (5, 4, 'kanye_Lover3000', 'Love this Guy!!', 5)
            ]

            for comment_data in comments_data:
                comment = Comment(id=comment_data[0], user_id=comment_data[1], username=comment_data[2],
                                comment=comment_data[3], playlist_id=comment_data[4])
                db.session.add(comment)
            print("✅ Comments migrated")

            db.session.commit()
            print("\n🎉 Migration completed successfully!")
            print("📊 Data summary:")
            print(f"   - {len(users_data)} users")
            print(f"   - {len(playlists_data)} playlists")
            print(f"   - {len(votes_data)} votes")
            print(f"   - {len(comments_data)} comments")

            return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)