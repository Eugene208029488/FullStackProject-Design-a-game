#Full Stack Nanodegree Project 6 - Design a Game

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
2.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
3.  Access it via https://tic-tac-toe-140903.appspot.com/_ah/api/explorer



##Game Description:
Tic Tac Toe is a a two players game who take turns marking the spaces in a 3×3 grid. The player who succeeds in placing three of their marks in a horizontal, vertical, or diagonal row wins the game.  Both players get a 'Tie' if there's no empty space left on the grid and no winner found.  The game will randomize who goes first.  Player makes the move by calling `make_move` endpoint and indicate the position on the grid they want to mark.  The grid position is from 0-8.  The game will return who has the next turn or if player wins or there's a tie.
Many different Tic Tac Toe games can be played by many different Users at any
given time. Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`.

##Scoring Rules
Player wins if he/she was able to successfully place 3 marks in succession either horizontally, vertically or diagonal on the 3x3 grid.  We keep track of both winner and loser in the Score kind.  Winning player gets a 'win' record and loser gets a 'lose' record created in the Score kind.  In case of a 'Tie' wherein there's no empty space left on the grid and no winner found then both players get a 'Tie' record created in the Score kind.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - index.yaml: index configuration
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

##Technology used:
1. Google App Engine
2. Google Cloud Endpoints - simplifies API development
3. Google Datastore - NoSQL document database
4. Task Queue - push queue
5. Cron Jobs

##Key Functionalities:
 - Build endpoints to create and play Tic Tac Toe
 - Setup an hourly email reminder using Cron Jobs
 - Add task queue to calculate user's winning % and notify next player turn

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will
    raise a ConflictException if a User with that user_name already exists.

 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: player1, player2
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. player1 & player2 provided must correspond to an existing user - will raise a NotFoundException if not.

 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.

 - **cancel_game**
    - Path: 'game/{urlsafe_game_key}/cancel'
    - Method: PUT
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Message confirming game cancelled.

 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, player, move
    - Returns: GameForm with new game state.
    - Description: Accepts 'player name' and 'move' and returns the updated state of the game.  If this causes the game to end, a corresponding Score entity will be created and a task added to the queue to calculate both players winning percentage.  Each player's turn and result will also be store it in the Game entity.  Lastly it will create task queue to send email reminder to notify user's opponent turn.

 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).

 - **get__user__scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms.
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

 - **get__user__games**
    - Path: 'games/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms.
    - Description: Returns all active games of the user (unordered).
    Will raise a NotFoundException if the User does not exist.

 - **get__user__rankings**
    - Path: 'ranking'
    - Method: GET
    - Parameters: None
    - Returns: RankingForms
    - Description: Returns all user and its winning percentage sorted in descending order.  Winning percentage = (total_win + (total_tie/2))/(total_games)

 - **get__game__history**
    - Path: 'game/{urlsafe_game_key}/history'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: HistoryForms
    - Description: Display the turn by turn history of the game.

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.

 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.

 - **Ranking**
    - Records player's ranking. Associated with Users model via KeyProperty.

##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, player1, player2, next_turn, board, game_over flag, message).
 - **NewGameForm**
    - Used to create a new game (player1, player2)
 - **MakeMoveForm**
    - Inbound make move form (player, move).
 - **ScoreForm**
    - Representation of a completed game's Score (user, date, result).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **RankForm**
    - Representation of a player's rank (user, winning %).
 - **RankForms**
    - Multiple RankForm container.
 - **HistoryForm**
    - Representation of a game history (sequence, player, move, result).
 - **HistoryForms**
    - Multiple HistoryForm container.
 - **StringMessage**
    - General purpose String container.