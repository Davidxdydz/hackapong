# Hackapong Requirements & Control Flow

## Overview
Hackapong is a web-based beerpong match organizer with an Elo rating system, scheduling, and real-time state updates.

## Data Models

### Team
- `id`: Integer, Primary Key
- `name`: String, Unique
- `password`: String (Plaintext as requested)
- `elo`: Integer (Default: 1200)
- `wins`: Integer (Default: 0)
- `losses`: Integer (Default: 0)
- `state`: Enum/String (NOT_ACTIVE, SEARCHING, MATCHED, CONFIRM_READY, READY, IN_GAME, DONE, SUBMIT, SUBMITTED)
- `current_match_id`: Foreign Key (nullable)

### Match
- `id`: Integer, Primary Key
- `team1_id`: Foreign Key
- `team2_id`: Foreign Key
- `score1`: Integer (nullable)
- `score2`: Integer (nullable)
- `start_time`: DateTime (nullable)
- `end_time`: DateTime (nullable)
- `status`: Enum/String (SCHEDULED, ACTIVE, COMPLETED)
- `scheduled_time`: DateTime (for queueing/scheduling)

## Control Flow & State Machine (Game Page)

The server maintains the state of each team. Clients poll or receive push notifications (WebSockets) to refresh the page/state.

1.  **NOT_ACTIVE**
    -   **View**: "Find Match" button.
    -   **Action**: User clicks "Find Match".
    -   **Transition**: Team state -> `SEARCHING`.

2.  **SEARCHING**
    -   **View**: "Searching for opponent..." spinner/text.
    -   **Logic**: Server looks for another team in `SEARCHING`.
    -   **Transition**: When opponent found -> Create `Match` (Scheduled), Team state (both) -> `MATCHED`.

3.  **MATCHED**
    -   **View**: Display countdown to start of match (if waiting for previous match to finish) or immediate transition.
    -   **Logic**: System checks if a game slot is free. Matches are 12 mins + 3 mins break.
    -   **Transition**: When slot available -> Team state (both) -> `CONFIRM_READY`.

4.  **CONFIRM_READY**
    -   **View**: 3-minute timer. "I am Ready" button. Indicators for Self and Opponent readiness.
    -   **Action**: User clicks "I am Ready".
    -   **Transition**: Team state -> `READY`.
    -   **Logic**: If timer expires and not ready -> Match cancelled/forfeit? (Assume reset to NOT_ACTIVE for now).

5.  **READY**
    -   **View**: Waiting for opponent...
    -   **Transition**: When both teams `READY` -> Team state (both) -> `IN_GAME`. Match status -> `ACTIVE`.

6.  **IN_GAME**
    -   **View**: Game timer (countdown). "Done" button.
    -   **Action**: User clicks "Done" (game finished early) OR Timer expires.
    -   **Transition**: Team state -> `DONE`.

7.  **DONE**
    -   **View**: Waiting for other team...
    -   **Transition**: When both teams `DONE` (or timer expired for both) -> Team state (both) -> `SUBMIT`.

8.  **SUBMIT**
    -   **View**: Form to enter cups hit by Team 1 and Team 2. Submit button.
    -   **Action**: User submits scores.
    -   **Transition**: Team state -> `SUBMITTED`. Store temp score.

9.  **SUBMITTED**
    -   **View**: Waiting for opponent confirmation...
    -   **Logic**:
        -   If both submitted:
            -   Compare scores.
            -   **If Mismatch**: Team state (both) -> `SUBMIT` (with error message).
            -   **If Match**:
                -   Update Elo, Wins, Losses.
                -   Set Match status -> `COMPLETED`.
                -   Team state (both) -> `NOT_ACTIVE`.
                -   Redirect/Notify users of result.

## Pages & Routing

-   `/`: Landing/Leaderboard (or redirect to Game if logged in?) -> Let's make `/` the Leaderboard.
-   `/login`: Login/Register.
-   `/game`: Main action page. Renders differently based on `Team.state`.
-   `/schedule`: List of scheduled matches.
-   `/team/<team_id>`: Team stats and history.
-   `/rules`: (Optional, good for completeness).

## Technical Stack
-   **Backend**: Flask
-   **Database**: SQLite (via SQLAlchemy)
-   **Real-time**: Flask-SocketIO (for state updates/pings)
-   **Frontend**: Jinja2 Templates + Tailwind CSS (CDN) + Vanilla JS (SocketIO client).
