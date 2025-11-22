from app import app, db, Team, Match

with app.app_context():
    # Reset all teams to NOT_ACTIVE
    teams = Team.query.all()
    for team in teams:
        team.state = 'NOT_ACTIVE'
        team.current_match_id = None
        
    # Mark all ACTIVE matches as COMPLETED (or delete them if you prefer, but completing is safer for history)
    # Actually, let's just delete ACTIVE matches to clean up the queue
    active_matches = Match.query.filter_by(status='ACTIVE').all()
    for match in active_matches:
        db.session.delete(match)
        
    # Also delete SCHEDULED matches
    scheduled_matches = Match.query.filter_by(status='SCHEDULED').all()
    for match in scheduled_matches:
        db.session.delete(match)
        
    db.session.commit()
    print("State reset successfully.")
