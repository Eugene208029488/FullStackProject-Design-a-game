#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging

import webapp2
from google.appengine.api import mail, app_identity
from google.appengine.ext import ndb

from api import TicTacToeApi

from models import User, Game


class SendReminderEmail_all(webapp2.RequestHandler):

    def get(self):
        """Send a reminder email to each User with incomplete games.
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()

        games = Game.query(Game.game_over == False)

        for game in games:
            # send email to user with email address and their turn to play
            users = User.query(User.email != None, User.name == game.next_turn)
            for user in users:

                subject = 'This is a reminder!'
                body = (
                    'Hello {}, it is your turn.  Please complete your '
                    'Tic Tac Toe with gameid = {} !'.format(
                        user.name, game.key.urlsafe()))
                # This will send test emails, the arguments to send_mail are:
                # from, to, subject, body
                mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                               user.email,
                               subject,
                               body)
                # logging.info(body)


class SendReminderEmail(webapp2.RequestHandler):

    def post(self):
        """Turn notification reminder email.
           Will be called called from a taskqueue"""

        app_id = app_identity.get_application_id()

        user_key = ndb.Key(urlsafe=self.request.get('user_id'))

        subject = 'This is a reminder!'
        body = (
            'Hello {}, it is your turn.  Please complete your '
            'Tic Tac Toe with gameid = {} !'.format(
                user_key.get().name, self.request.get('game_id')))

        # This will send test emails, the arguments to send_mail are:
        # from, to, subject, body
        mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                       user_key.get().email,
                       subject,
                       body)
        # logging.info(body)


class UpdateRanking(webapp2.RequestHandler):

    def post(self):
        """Update player rankings.
           Will be called from task queue"""
        TicTacToeApi._get_winning_percentage(self.request.get('player'))
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail_all),
    ('/tasks/update_ranking', UpdateRanking),
    ('/tasks/send_reminder', SendReminderEmail),
], debug=True)
