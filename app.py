import os
from flask import (Flask, redirect, url_for, session, request,
                    render_template, g)
from flask.ext.login import (LoginManager, login_required, login_user,
                                logout_user, current_user)
from flask.ext.sqlalchemy import SQLAlchemy
from flask_oauth import OAuth


FACEBOOK_APP_ID = os.environ['FACEBOOK_APP_ID']
FACEBOOK_APP_SECRET = os.environ['FACEBOOK_APP_SECRET']


app = Flask(__name__)
app.debug = True
app.secret_key = os.environ['APP_SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'


##############################################################################
##                                  Models                                  ##
##############################################################################
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    social_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)

    def __init__(self, name, social_id, email=None):
        self.name = name
        self.social_id = social_id
        self.email = email

    def is_authenticated(self):
        return True
 
    def is_active(self):
        return True
 
    def is_anonymous(self):
        return False
 
    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return "<User %r>" %(self.name)


##############################################################################
##                                  Login                                   ##
##############################################################################
oauth = OAuth()
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = '.login'

facebook = oauth.remote_app('facebook',
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    consumer_key=FACEBOOK_APP_ID,
    consumer_secret=FACEBOOK_APP_SECRET,
    request_token_params={'scope': 'email'}
)

@login_manager.unauthorized_handler
def unauthorized():
    return "You can't access this."

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user

@app.route('/login-facebook/authorized')
@facebook.authorized_handler
def facebook_authorized(resp):
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['oauth_token'] = (resp['access_token'], '')
    me = facebook.get('/me').data
    user = User.query.filter_by(social_id=me['id']).first()
    print user
    if user is not None:
        login_user(user)
        return redirect(url_for('.user'))
    else:
        if "email" in me:
            user = User(me['name'], me['id'], me['email'])
        else:
            user = User(me['name'], me['id'])
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('.user'))


@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get('oauth_token')


##############################################################################
##                                  Routes                                  ##
##############################################################################
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/me')
@login_required
def user():
    return render_template('user.html', user=current_user)

@app.route('/login-facebook')
def login():
    if current_user.is_anonymous():
        return facebook.authorize(callback=url_for('facebook_authorized',
            next=request.args.get('next') or request.referrer or None,
            _external=True))
    return redirect(url_for('.user'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('.index'))

if __name__ == '__main__':
    db.create_all()
    app.run(port=3000)
