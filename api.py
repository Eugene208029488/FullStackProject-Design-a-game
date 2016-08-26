# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""

import random
import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, Score, Ranking
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, RankForms, HistoryForm, HistoryForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))


@endpoints.api(name='tic_tac_toe', version='v1')
class TicTacToeApi(remote.Service):

    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
            request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        player1 = User.query(User.name == request.player1).get()
        if not player1:
            raise endpoints.NotFoundException(
                'Player1 does not exist!')
        player2 = User.query(User.name == request.player2).get()
        if not player2:
            raise endpoints.NotFoundException(
                'Player2 does not exist!')

        # randomize who gets the 1st turn
        next_turn = random.randint(1, 2)
        if next_turn == 1:
            next_turn_name = player1.name
        else:
            next_turn_name = player2.name

        # reset the tic tac toe board
        board = [' '] * 9

        # create a new game record in datastore
        game = Game.new_game(player1.key, player2.key,
                             next_turn_name, board)

        return game.to_form('{} will have the first move'
                            .format(next_turn_name))

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/cancel',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self, request):
        """Cancel an active game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        if game.game_over:
            raise endpoints.NotFoundException('Cannot cancel completed game')
        else:
            game.key.delete()
            return StringMessage(message='Game cancelled!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        # Checks if game is complete
        if game.game_over:
            return game.to_form('Game already over!')

        # Checks if it is the right player's turn
        if game.next_turn != request.player:
            return game.to_form('It is {} turn to play'.format(game.next_turn))

        # Checks if the move entered is valid
        if (request.move < 0 or request.move > 8):
            return game.to_form('Move should be from 0 to 8 only')

        # Checks if the move entered is already taken
        if (game.board[request.move] != ' '):
            return game.to_form('Position already taken.')

        msg = ''
        # Game logic.  update the board and check if player wins.
        if request.player == game.player1.get().name:
            game.board[request.move] = 'O'
            next_turn = game.player2
            if self.isWinner(game.board, 'O'):
                game.end_game(game.player1, game.player2, 'win')
                msg = '{} win!'.format(game.player1.get().name)
        else:
            game.board[request.move] = 'X'
            next_turn = game.player1
            if self.isWinner(game.board, 'X'):
                game.end_game(game.player2, game.player1, 'win')
                msg = '{} win!'.format(game.player2.get().name)

        # if no winner found check if there's a tie or who has the next turn
        if msg.find('win') == -1:  # no winner found yet
            if self.isTie(game.board):
                game.end_game(game.player1, game.player2, 'tie')
                msg = 'Tie!'
            else:
                game.next_turn = next_turn.get().name
                msg = '{} turn'.format(game.next_turn)
                # Turn notification system.  Add a task to the task queue to
                # notify the User's opponent turn
                taskqueue.add(params={'user_id': next_turn.urlsafe(),
                                      'game_id': game.key.urlsafe()},
                              url='/tasks/send_reminder')

        # Game history tracking.
        intCtr = len(game.history) + 1
        history = {'seq': intCtr, 'player': request.player,
                   'move': request.move, 'result': msg}
        game.history.append(history)
        game.put()

        return game.to_form(msg)

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual User's games"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        games = Game.query(ndb.AND(ndb.OR(Game.player1 == user.key,
                                          Game.player2 == user.key),
                                   Game.game_over == False))
        return GameForms(items=[game.to_form('') for game in games])

    @endpoints.method(response_message=RankForms,
                      path='ranking',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return all ranking sort by winning percent"""
        return RankForms(items=[rank.to_form() for rank in Ranking
                                .query().order(-Ranking.winning_percent)])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=HistoryForms,
                      path='game/{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return game history."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        if game:
            # logging.info(game.history)
            items = []
            for history in game.history:
                items.append(HistoryForm(sequence=history['seq'],
                                         player=history[
                                             'player'], move=history['move'],
                                         result=history['result']))
            # logging.info(items)
            return HistoryForms(items=items)
        else:
            raise endpoints.NotFoundException('Game not found!')

    @staticmethod
    def _get_winning_percentage(player_name):
        """Populates ranking entity based on players winning %"""

        user = User.query(User.name == player_name).get()
        if user:
            total_win = float(
                len(Score.query(Score.user == user.key, Score.result == 'win')
                    .fetch()))
            total_lose = float(
                len(Score.query(Score.user == user.key, Score.result == 'lose')
                    .fetch()))
            total_tie = float(
                len(Score.query(Score.user == user.key, Score.result == 'tie')
                    .fetch()))
            # tie counts for 1/2 win and 1/2 lose
            winning_per = ((total_win + (total_tie / 2)) /
                           (total_win + total_lose + total_tie))

            # logging.info(total_win)
            # logging.info(total_lose)
            # logging.info(total_tie)
            # logging.info(winning_per)

            ranking = Ranking.query(Ranking.user == user.key).get()
            if ranking:
                ranking.winning_percent = winning_per
                ranking.put()
            else:
                ranking = Ranking(user=user.key,
                                  winning_percent=winning_per)
                ranking.put()

    def isWinner(self, bo, le):
        # Given a board and a player’s letter, this function returns True if
        # that player has won.
        return (  # across the top
            (bo[6] == le and bo[7] == le and bo[8] == le) or
            # across the middle
            (bo[3] == le and bo[4] == le and bo[5] == le) or
            # across the bottom
            (bo[0] == le and bo[1] == le and bo[2] == le) or
            # down the left side
            (bo[6] == le and bo[3] == le and bo[0] == le) or
            # down the middle
            (bo[7] == le and bo[4] == le and bo[1] == le) or
            # down the right side
            (bo[8] == le and bo[5] == le and bo[2] == le) or
            # diagonal
            (bo[6] == le and bo[4] == le and bo[2] == le) or
            # diagonal
            (bo[8] == le and bo[4] == le and bo[0] == le))

    def isTie(self, bo):
        # if all grid are not empty then it is a tie.
        return (bo[0] != ' ' and bo[1] != ' ' and bo[2] != ' ' and
                bo[3] != ' ' and bo[4] != ' ' and bo[5] != ' ' and
                bo[6] != ' ' and bo[7] != ' ' and bo[8] != ' ')


api = endpoints.api_server([TicTacToeApi])
