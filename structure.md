```
# Hackapong Project Structure

```
hackapong/
├── app.py              # Main Flask application entry point, routes, and socket events
├── db.py               # Database configuration and SQLAlchemy models
├── requirements.txt    # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css   # Custom CSS (Tailwind will be loaded via CDN)
│   └── js/
│   │   └── main.js     # Client-side logic (SocketIO handling, state updates)
└── templates/
    ├── base.html       # Base HTML template (includes Tailwind CDN, SocketIO script)
    ├── index.html      # Leaderboard page (Home)
    ├── login.html      # Login and Registration page
    ├── game.html       # Main Game page (Dynamic content based on state)
    ├── schedule.html   # Schedule page
    ├── team.html       # Team details page
    └── rules.html      # Rules page
```

## Key Files Description

-   **app.py**: Handles all HTTP routes and WebSocket events. Contains the game logic and state transitions.
-   **db.py**: Defines `Team` and `Match` models. Handles DB initialization.
-   **templates/game.html**: This will be the most complex template, likely using Jinja2 conditionals or JavaScript to show different UI elements based on the team's state.
-   **static/js/main.js**: Connects to the SocketIO server, listens for 'state_change' events, and reloads the page or updates the DOM when the server pushes an update.
