#!/usr/bin/env python
# -*- coding: utf-8 -*-

# general imports
import os
import sys
import logging

from utils import *

# logging to file
myPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../')
logPath = os.path.join(myPath, 'log/mmojunkies.log')
logging.basicConfig(
    filename=logPath,
    format='%(asctime)s %(levelname)-7s %(message)s',
    datefmt='%Y-%d-%m %H:%M:%S',
    level=logging.INFO)

# make logging available during initialization
log = logging.getLogger(__name__)
log.info("[System] MMOJunkies system is starting up")

# flask imports
try:
    from flask import *
except ImportError:
    log.error("[System] Please install flask")
    sys.exit(2)

try:
    from flask_compress import Compress
except ImportError:
    log.error("[System] Please install the flask extension: Flask-Compress")
    sys.exit(2)

# optional imports
try:
    import uwsgi
except ImportError:
    logging.warning("[System] Unable to import the uwsgi library.")

# setup flask app
app = Flask(__name__)

# setup logging
log = app.logger

# enable output compression
Compress(app)

# configure runtime variables
app.config['scriptPath'] = os.path.dirname(os.path.realpath(__file__))

# load configuration file
try:
    os.environ['MMOJUNKIES_CFG']
    log.info("[System] Loading config from: %s" % os.environ['MMOJUNKIES_CFG'])
except KeyError:
    log.warning("[System] Loading config from dist/mmojunkies.cfg.example "
                "because MMOJUNKIES_CFG environment variable is not set.")
    os.environ['MMOJUNKIES_CFG'] = "../dist/mmojunkies.cfg.example"

try:
    app.config.from_envvar('MMOJUNKIES_CFG', silent=False)
except RuntimeError as e:
    log.error(e)
    sys.exit(2)

# setup logging
with app.test_request_context():
    if app.debug:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)
        from logging.handlers import SMTPHandler
        mail_handler = SMTPHandler(app.config['EMAILSERVER'],
                                   app.config['EMAILFROM'],
                                   app.config['ADMINS'],
                                   current_app.name + ' failed!')
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

# initialize stuff
app.config['mmojunkesConfig'] = YamlConfig(os.path.join(
    app.config['scriptPath'], "../config/mmojunkies.yml")).get_values()
if not len(app.config['APPSECRET']):
    log.warning("[System] Generating random secret_key. All older cookies "
                "will be invalid, but i will NOT work with multiple "
                "processes (WSGI).")
    app.secret_key = os.urandom(24)
else:
    app.secret_key = app.config['APPSECRET']

# flask error handlers
@app.errorhandler(400)
def error_bad_request(error):
    log.warning("[System] 400 Bad Request: %s" % (request.path))
    return redirect(url_for('index'))


@app.errorhandler(401)
def error_unauthorized_request(error):
    log.warning("[System] 401 Page not found: %s" % (request.path))
    return redirect(url_for('index'))


@app.errorhandler(403)
def error_forbidden_request(error):
    log.warning("[System] 403 Page not found: %s" % (request.path))
    return redirect(url_for('index'))


@app.errorhandler(404)
def error_not_found(error):
    log.warning("[System] 404 Page not found: %s" % (request.path))
    return redirect(url_for('index'))


@app.errorhandler(500)
def error_internal_server_error(error):
    flash(gettext("The server encountered an internal error, probably a bug "
                  "in the program. The administration was automatically "
                  "informed of this problem."), 'error')
    log.warning("[System] 500 Internal error: %s" % (request.path))
    return index()

# basic app routes
# @app.teardown_appcontext
# def shutdown_session(exception=None):
#     db_session.remove()
#
# @app.before_request
# def before_request():
#     pass
#
# @app.after_request
# def add_header(response):
#     response.cache_control.max_age = 2
#     response.cache_control.min_fresh = 1
#     return response

# main routes
# TODO robots.txt and sitemap.xml integration? pre-render with phantom?

# main index
@app.route('/')
def index():
    return jsonify({'RESULT': "OK"})

# OAuth part
#  https://flask-oauthlib.readthedocs.io/en/latest/client.html#facebook-oauth
@app.route('/oauth-authorized')
def oauth_authorized():
    next_url = request.args.get('next') or url_for('index')
    resp = twitter.authorized_response()
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)

    session['twitter_token'] = (
        resp['oauth_token'],
        resp['oauth_token_secret']
    )
    session['twitter_user'] = resp['screen_name']

    flash('You were signed in as %s' % resp['screen_name'])
    return redirect(next_url)


@app.route('/login/twitter')
def twitter_login():
    return twitter.authorize(callback=url_for('oauth_authorized',
                                              next=request.args.get('next') or request.referrer or None))

@app.route('/login/facebook')
def facebook_login():
    facebook = oauth.remote_app('facebook',
        base_url='https://graph.facebook.com/',
        request_token_url=None,
        access_token_url='/oauth/access_token',
        authorize_url='https://www.facebook.com/dialog/oauth',
        consumer_key=FACEBOOK_APP_ID,
        consumer_secret=FACEBOOK_APP_SECRET,
        request_token_params={'scope': 'email'}
    )