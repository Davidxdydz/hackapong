from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Plaintext as requested
    elo = db.Column(db.Integer, default=1200)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    state = db.Column(db.String(20), default='NOT_ACTIVE') # NOT_ACTIVE, SEARCHING, MATCHED, CONFIRM_READY, READY, IN_GAME, DONE, SUBMIT, SUBMITTED
    current_match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'elo': self.elo,
            'wins': self.wins,
            'losses': self.losses,
            'state': self.state,
            'current_match_id': self.current_match_id
        }

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    score1 = db.Column(db.Integer, nullable=True)
    score2 = db.Column(db.Integer, nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='SCHEDULED') # SCHEDULED, ACTIVE, COMPLETED
    scheduled_time = db.Column(db.DateTime, default=datetime.utcnow)

    team1 = db.relationship('Team', foreign_keys=[team1_id], backref='matches_as_team1')
    team2 = db.relationship('Team', foreign_keys=[team2_id], backref='matches_as_team2')

def init_db(app):
    with app.app_context():
        db.create_all()
