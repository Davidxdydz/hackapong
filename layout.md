## Beerpong match website called Hackapong


This website is made for needing a quick and easy way to organize a beerpong match.

## Functionality
- each team starts with 1200 elo
- winning or losing a match changes the elo of both playing teams
- scheduled matchmaking
- responsive design optimized for mobile
- persistent data
- modern, colorful design, with modern and smooth animations
- any number of team members per team can be logged in at the same time

## Pages
These pages are accessible via a navbar

- Leaderboard:
    - show all teams sorted by elo, display their elo, number of wins and losses, and win rate
    - clicking on a team name leads to the team page

- Team page:
    - show team name, elo, number of wins and losses, and win rate
    - show list of all matches played by this team
    - show chart of the elo changes over time

- Schedule page:
    - show all scheduled matches, as well as the teams that are playing in them (clicking on a team name leads to the team page)
    - on top, show the current running match, or no match if none is running
    - when logged in, highlight the team that the user is playing for

- Login page:
    - login: username and password
    - register: username, password, confirm password

- Game page:
    - state dependent
    - state: not active: show search for match button
    - button clicked > state: searching
    - two teams searching > state of both: matched > match is scheduled, see scheduling, teams are pinged
    - state: matched: display countdown to end of running game
    - event: game ended > next teams (if exist) are set to state: confirm_ready
    - if there is no running game, directly go to state: confirm_ready
    - state: confirm_ready: show confirmation page: 3 min timer, indicator if other team is ready, and if self is ready. Button on the bottom to confirm ready, disabled when already confirmed. client to server: confirm ready, this updates the state to state: ready, which also pings the other team to update their confirmation page
    - both teams confirmed ready > state of both: in game
    - state: in game: show countdown to end of game, and button for "done"
    - button clicked > state: done
    - both teams in state done or timer expired > state of both: submit
    - submit: display submit page: two inputs for cups hit by each team, both teams must submit both scores. submit button
    - submit button clicked > state: submitted
    - both teams in state submitted > if both submitted scores are different, message "scores are different, please submit again" and go to state: submit. if same: both teams go to state: not active, ping to redirect to win/lose page with the result, server updates elo
    
## Implementation
- think about what makes sense
- dumb app with single state on server:
    - when state changes, just send ping to all affected clients containing the target url. when the client receives the ping, it fetches the new state from the server at the given url
    - the server decides which page to server to a logged in/logged out team based on their state

## Team state and matchmaking control flow
- logged in and not logged in is the same as logged in or different team if it depends on the team (e.g. team page can only be edited by logged in team)
- states as defined in the game page

## Scheduling


## Matches
- 12 minutes per match, with 3 minute break in between