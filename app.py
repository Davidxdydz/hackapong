from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from db import db, init_db, Team, Match
from datetime import datetime, timedelta
import eventlet
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!' # In a real app, this should be an environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hackapong.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app, async_mode='eventlet')

# Initialize DB
init_db(app)

@app.before_request
def load_logged_in_user():
    from flask import g
    team_id = session.get('team_id')
    if team_id is None:
        g.user = None
    else:
        g.user = Team.query.get(team_id)

@app.route('/')
def index():
    teams = Team.query.order_by(Team.elo.desc()).all()
    return render_template('index.html', teams=teams)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if 'register' in request.form:
            username = request.form['username']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            if password != confirm_password:
                flash('Passwords do not match')
                return redirect(url_for('login'))
            
            if Team.query.filter_by(name=username).first():
                flash('Team name already exists')
                return redirect(url_for('login'))
            
            new_team = Team(name=username, password=password)
            db.session.add(new_team)
            db.session.commit()
            session['team_id'] = new_team.id
            return redirect(url_for('game'))
            
        else: # Login
            username = request.form['username']
            password = request.form['password']
            team = Team.query.filter_by(name=username).first()
            
            if team and team.password == password:
                session['team_id'] = team.id
                return redirect(url_for('game'))
            else:
                flash('Invalid username or password')
                return redirect(url_for('login'))
                
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('team_id', None)
    return redirect(url_for('index'))

@app.route('/game')
def game():
    if 'team_id' not in session:
        return redirect(url_for('login'))
    
    team = Team.query.get(session['team_id'])
    if not team:
        session.pop('team_id', None)
        return redirect(url_for('login'))
    
    match = None
    current_running_match = None
    
    if team.current_match_id:
        match = Match.query.get(team.current_match_id)
        
    # Get opponent if in a match
    opponent = None
    if match:
        if match.team1_id == team.id:
            opponent = match.team2
        else:
            opponent = match.team1
        
    # If we are MATCHED (waiting in queue), we need to know when the current game ends
    if team.state == 'MATCHED':
        current_running_match = Match.query.filter_by(status='ACTIVE').first()
        
    return render_template('game.html', team=team, match=match, current_running_match=current_running_match, opponent=opponent)

@app.route('/schedule')
def schedule():
    matches = Match.query.filter(Match.status != 'COMPLETED').order_by(Match.scheduled_time).all()
    current_match = Match.query.filter_by(status='ACTIVE').first()
    return render_template('schedule.html', matches=matches, current_match=current_match)

def get_elo_history(team_id):
    """
    Replays all completed matches to calculate the Elo history for a specific team.
    Returns a list of dicts: [{'date': 'YYYY-MM-DD', 'elo': 1200}, ...]
    """
    # Get all completed matches, ordered by time
    matches = Match.query.filter_by(status='COMPLETED').order_by(Match.end_time).all()
    
    # Initialize all teams with default Elo
    teams = Team.query.all()
    team_elos = {t.id: 1200 for t in teams}
    
    # History for the target team
    history = [{'date': 'Start', 'elo': 1200}]
    
    for match in matches:
        # Calculate Elo change for this match
        ra = team_elos.get(match.team1_id, 1200)
        rb = team_elos.get(match.team2_id, 1200)
        
        k = 30
        ea = 1 / (1 + 10 ** ((rb - ra) / 400))
        eb = 1 / (1 + 10 ** ((ra - rb) / 400))
        
        sa = 1 if match.score1 > match.score2 else 0
        sb = 1 if match.score2 > match.score1 else 0
        
        new_ra = ra + k * (sa - ea)
        new_rb = rb + k * (sb - eb)
        
        # Update current Elos
        team_elos[match.team1_id] = new_ra
        team_elos[match.team2_id] = new_rb
        
        # If this match involved our target team, record the new Elo
        if match.team1_id == team_id:
            history.append({
                'date': match.end_time.strftime('%Y-%m-%d %H:%M'),
                'elo': int(new_ra)
            })
        elif match.team2_id == team_id:
            history.append({
                'date': match.end_time.strftime('%Y-%m-%d %H:%M'),
                'elo': int(new_rb)
            })
            
    return history

@app.route('/team/<int:team_id>')
def team_detail(team_id):
    team = Team.query.get_or_404(team_id)
    matches = Match.query.filter(
        ((Match.team1_id == team_id) | (Match.team2_id == team_id)) &
        (Match.status == 'COMPLETED')
    ).order_by(Match.end_time.desc()).all()
    
    elo_history = get_elo_history(team_id)
    
    return render_template('team.html', team=team, matches=matches, elo_history=elo_history)

# SocketIO Events
@socketio.on('connect')
def handle_connect():
    if 'team_id' in session:
        join_room(f"team_{session['team_id']}")

@socketio.on('find_match')
def handle_find_match():
    if 'team_id' not in session:
        return
    
    team = Team.query.get(session['team_id'])
    if team.state == 'NOT_ACTIVE':
        team.state = 'SEARCHING'
        db.session.commit()
        emit('state_change', {'state': 'SEARCHING'}, room=f"team_{team.id}")
        matchmaking_logic()

@socketio.on('cancel_search')
def handle_cancel_search():
    if 'team_id' not in session:
        return
    
    team = Team.query.get(session['team_id'])
    if team.state == 'SEARCHING':
        team.state = 'NOT_ACTIVE'
        db.session.commit()
        emit('state_change', {'state': 'NOT_ACTIVE'}, room=f"team_{team.id}")

@socketio.on('confirm_ready')
def handle_confirm_ready():
    if 'team_id' not in session:
        return
        
    team = Team.query.get(session['team_id'])
    if team.state == 'CONFIRM_READY':
        team.state = 'READY'
        db.session.commit()
        emit('state_change', {'state': 'READY'}, room=f"team_{team.id}")
        check_match_start(team.current_match_id)

@socketio.on('game_done')
def handle_game_done():
    if 'team_id' not in session:
        return
    
    team = Team.query.get(session['team_id'])
    if team.state == 'IN_GAME':
        team.state = 'DONE'
        db.session.commit()
        emit('state_change', {'state': 'DONE'}, room=f"team_{team.id}")
        check_game_end(team.current_match_id)

@socketio.on('submit_score')
def handle_submit_score(data):
    if 'team_id' not in session:
        return
    
    team = Team.query.get(session['team_id'])
    if team.state in ['DONE', 'SUBMIT']: # Allow submit from DONE if other team is slow, or SUBMIT
        score1 = int(data.get('score1'))
        score2 = int(data.get('score2'))
        
        # Store temporary score in the match object? Or just check if both submitted?
        # For simplicity, let's assume we trust the first submission or wait for both?
        # The requirement says: "both teams must submit both scores... if different... please submit again"
        
        match = Match.query.get(team.current_match_id)
        
        # We need a place to store the submitted scores temporarily.
        # Since the Match model has score1 and score2, we can use them, but we need to know WHO submitted WHAT.
        # Let's add a temporary storage or just use the session/memory for this simple app?
        # Or better, let's use the Match model but be careful.
        # Actually, let's add 'submission_team1' and 'submission_team2' to the Match model or just handle it in logic.
        # Given the constraints, let's just assume we store it in the match if it's empty, or compare if it's there.
        # But wait, we need to know if *this* team submitted.
        
        team.state = 'SUBMITTED'
        # We can store the submitted score in a temporary dict in memory for this demo
        if not hasattr(app, 'pending_scores'):
            app.pending_scores = {}
        
        app.pending_scores[f"{match.id}_{team.id}"] = (score1, score2)
        
        db.session.commit()
        emit('state_change', {'state': 'SUBMITTED'}, room=f"team_{team.id}")
        check_score_submission(match.id)

def matchmaking_logic():
    searching_teams = Team.query.filter_by(state='SEARCHING').all()
    if len(searching_teams) >= 2:
        team1 = searching_teams[0]
        team2 = searching_teams[1]
        
        match = Match(team1_id=team1.id, team2_id=team2.id, status='SCHEDULED')
        db.session.add(match)
        db.session.commit()
        
        team1.state = 'MATCHED'
        team2.state = 'MATCHED'
        team1.current_match_id = match.id
        team2.current_match_id = match.id
        db.session.commit()
        
        emit('state_change', {'state': 'MATCHED'}, room=f"team_{team1.id}")
        emit('state_change', {'state': 'MATCHED'}, room=f"team_{team2.id}")
        
        # Check if they can start immediately (if no active match)
        active_match = Match.query.filter_by(status='ACTIVE').first()
        if not active_match:
            start_confirmation(match.id)

def start_confirmation(match_id):
    match = Match.query.get(match_id)
    team1 = Team.query.get(match.team1_id)
    team2 = Team.query.get(match.team2_id)
    
    team1.state = 'CONFIRM_READY'
    team2.state = 'CONFIRM_READY'
    db.session.commit()
    
    emit('state_change', {'state': 'CONFIRM_READY'}, room=f"team_{team1.id}")
    emit('state_change', {'state': 'CONFIRM_READY'}, room=f"team_{team2.id}")

def check_match_start(match_id):
    match = Match.query.get(match_id)
    team1 = Team.query.get(match.team1_id)
    team2 = Team.query.get(match.team2_id)
    
    if team1.state == 'READY' and team2.state == 'READY':
        team1.state = 'IN_GAME'
        team2.state = 'IN_GAME'
        match.status = 'ACTIVE'
        match.start_time = datetime.utcnow()
        db.session.commit()
        
        emit('state_change', {'state': 'IN_GAME'}, room=f"team_{team1.id}")
        emit('state_change', {'state': 'IN_GAME'}, room=f"team_{team2.id}")

def check_game_end(match_id):
    match = Match.query.get(match_id)
    team1 = Team.query.get(match.team1_id)
    team2 = Team.query.get(match.team2_id)
    
    # If both are DONE, move to SUBMIT
    if team1.state == 'DONE' and team2.state == 'DONE':
        team1.state = 'SUBMIT'
        team2.state = 'SUBMIT'
        db.session.commit()
        emit('state_change', {'state': 'SUBMIT'}, room=f"team_{team1.id}")
        emit('state_change', {'state': 'SUBMIT'}, room=f"team_{team2.id}")

def check_score_submission(match_id):
    match = Match.query.get(match_id)
    team1 = Team.query.get(match.team1_id)
    team2 = Team.query.get(match.team2_id)

    # Check if both teams have submitted scores
    team1_submitted_key = f"{match.id}_{team1.id}"
    team2_submitted_key = f"{match.id}_{team2.id}"

    if team1_submitted_key in app.pending_scores and team2_submitted_key in app.pending_scores:
        score1_t1, score2_t1 = app.pending_scores[team1_submitted_key]
        score1_t2, score2_t2 = app.pending_scores[team2_submitted_key]

        # Check if scores match (team1's score1 should match team2's score2, and vice versa)
        if score1_t1 == score1_t2 and score2_t1 == score2_t2:
            # Scores match, finalize the match
            match.score1 = score1_t1
            match.score2 = score2_t1
            match.status = 'COMPLETED'
            match.end_time = datetime.utcnow()
            db.session.commit()

            # Update Elo ratings and team stats
            update_elo(team1, team2, match.score1, match.score2)
            db.session.commit()

            team1.state = 'NOT_ACTIVE'
            team2.state = 'NOT_ACTIVE'
            team1.current_match_id = None
            team2.current_match_id = None
            db.session.commit()

            emit('state_change', {'state': 'COMPLETED', 'match_id': match.id}, room=f"team_{team1.id}")
            emit('state_change', {'state': 'COMPLETED', 'match_id': match.id}, room=f"team_{team2.id}")

            # Clear pending scores for this match
            del app.pending_scores[team1_submitted_key]
            del app.pending_scores[team2_submitted_key]

            # Check for next match
            next_match = Match.query.filter_by(status='SCHEDULED').order_by(Match.scheduled_time).first()
            if next_match:
                start_confirmation(next_match.id)
                
        else:
            # Scores mismatch
            # Reset both to SUBMIT
            team1.state = 'SUBMIT'
            team2.state = 'SUBMIT'
            db.session.commit()
            
            # Clear pending for this match so they can try again
            del app.pending_scores[team1_submitted_key]
            del app.pending_scores[team2_submitted_key]
            
            emit('state_change', {'state': 'SUBMIT', 'error': 'Scores did not match! Please talk to your opponent and submit again.'}, room=f"team_{team1.id}")
            emit('state_change', {'state': 'SUBMIT', 'error': 'Scores did not match! Please talk to your opponent and submit again.'}, room=f"team_{team2.id}")
            

def update_elo(team1, team2, score1, score2):
    # Simple Elo implementation
    # Winner gets points, loser loses points
    k = 32
    r1 = 10 ** (team1.elo / 400)
    r2 = 10 ** (team2.elo / 400)
    e1 = r1 / (r1 + r2)
    e2 = r2 / (r1 + r2)
    
    if score1 > score2: # Team 1 won
        s1 = 1
        s2 = 0
        team1.wins += 1
        team2.losses += 1
    else: # Team 2 won
        s1 = 0
        s2 = 1
        team1.losses += 1
        team2.wins += 1
        
    team1.elo = int(team1.elo + k * (s1 - e1))
    team2.elo = int(team2.elo + k * (s2 - e2))

if __name__ == '__main__':
    socketio.run(app, debug=True, port = 443, host='0.0.0.0', certfile='/etc/letsencrypt/live/hackapong.ddns.net/cert.pem', keyfile='/etc/letsencrypt/live/hackapong.ddns.net/privkey.pem')
