"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
import logging
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb
from google.appengine.api import taskqueue


class User(ndb.Model):

    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class Game(ndb.Model):

    """Game object"""
    player1 = ndb.KeyProperty(required=True, kind='User')
    player2 = ndb.KeyProperty(required=True, kind='User')
    next_turn = ndb.StringProperty(required=True)
    board = ndb.StringProperty(repeated=True)
    game_over = ndb.BooleanProperty(required=True, default=False)
    history = ndb.JsonProperty(repeated=True)

    @classmethod
    def new_game(cls, player1, player2, next_turn, board):
        """Creates and returns a new game"""

        game = Game(player1=player1,
                    player2=player2,
                    next_turn=next_turn,
                    board=board,
                    history=[],
                    game_over=False)
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.next_turn = self.next_turn
        form.board = self.board
        form.game_over = self.game_over
        form.message = message
        form.player1 = self.player1.get().name
        form.player2 = self.player2.get().name
        return form

    def end_game(self, winner, loser, result):
        """Ends the game -
        if result = win then winner wins and loser loses
        if result = tie then both winner and loser tie """
        self.game_over = True
        self.put()

        # logging.info(winner)  # winner is the key

        # Add the game to the score 'board'
        # Score record will create an ancestor to the user to ensure
        # strong consistency.
        if result == 'win':
            score = Score(
                user=winner, date=date.today(), result='win', parent=winner)
            score.put()
            score = Score(
                user=loser, date=date.today(), result='lose', parent=loser)
            score.put()

        else:
            score = Score(
                user=winner, date=date.today(), result='tie', parent=winner)
            score.put()
            score = Score(
                user=loser, date=date.today(), result='tie', parent=loser)
            score.put()

        # create task queue to recalculate players ranking
        taskqueue.add(params={'player': winner.get().name},
                      url='/tasks/update_ranking')
        taskqueue.add(params={'player': loser.get().name},
                      url='/tasks/update_ranking')


class Score(ndb.Model):

    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    result = ndb.StringProperty(required=True)

    def to_form(self):
        return ScoreForm(user=self.user.get().name,
                         result=self.result, date=str(self.date))


class Ranking(ndb.Model):

    """Ranking"""
    user = ndb.KeyProperty(required=True, kind='User')
    winning_percent = ndb.FloatProperty()

    def to_form(self):
        return RankForm(user=self.user.get().name,
                        winning_percent=self.winning_percent)


class GameForm(messages.Message):

    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    next_turn = messages.StringField(2, required=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    player1 = messages.StringField(5, required=True)
    player2 = messages.StringField(6, required=True)
    board = messages.StringField(7, repeated=True)


class GameForms(messages.Message):

    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):

    """Used to create a new game"""
    player1 = messages.StringField(1, required=True)
    player2 = messages.StringField(2, required=True)


class MakeMoveForm(messages.Message):

    """Used to make a move in an existing game"""
    player = messages.StringField(1, required=True)
    move = messages.IntegerField(2, required=True)


class ScoreForm(messages.Message):

    """ScoreForm for outbound Score information"""
    user = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    result = messages.StringField(3, required=True)


class ScoreForms(messages.Message):

    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class RankForm(messages.Message):

    """RankForm for outbound Rank information"""
    user = messages.StringField(1, required=True)
    winning_percent = messages.FloatField(2, required=True)


class RankForms(messages.Message):

    """Return multiple RankForm"""
    items = messages.MessageField(RankForm, 1, repeated=True)


class HistoryForm(messages.Message):

    """HistoryForm for outbound history information"""
    sequence = messages.IntegerField(1, required=True)
    player = messages.StringField(2, required=True)
    move = messages.IntegerField(3, required=True)
    result = messages.StringField(4, required=True)


class HistoryForms(messages.Message):

    """Return multiple HistoryForm"""
    items = messages.MessageField(HistoryForm, 1, repeated=True)


class StringMessage(messages.Message):

    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
