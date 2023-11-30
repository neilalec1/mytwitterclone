from flask import Flask, render_template, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, current_user, logout_user, login_required
from forms import RegistrationForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from forms import TweetForm
from flask_migrate import Migrate


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://mytwitterclone_user:lk0jh11H8CqMysxKqCU8psoZYwIvyIMZ@dpg-clkdedmrem5c73ah2atg-a.frankfurt-postgres.render.com/mytwitterclone' #PostGreSQL database
app.config['SECRET_KEY'] = '\xe9d\xc1\xaf\xe6\x8c\x90\xcc\xba\x9f>\xc0\x19\xb1k\x15\x07\x14(\xf0\x7fQ&\xaa'  #my not so secret key
db = SQLAlchemy(app)
migrate = Migrate(app, db)



login_manager = LoginManager(app)
login_manager.login_view = 'login'  #function name of login route

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




@app.route('/', methods=['GET', 'POST'])
def home():
     form = TweetForm()
     if form.validate_on_submit() and current_user.is_authenticated:
        tweet = Tweet(content=form.content.data, user_id=current_user.id)
        db.session.add(tweet)
        db.session.commit()
        flash('Your tweet has been posted!', 'success')
        return redirect(url_for('home'))
     tweets = Tweet.query.order_by(Tweet.date_posted.desc()).all()
     return render_template('home.html', current_user=current_user, tweets=tweets, form=form)

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    follower_count = user.followers.count()
    followee_count = user.followed.count()
    return render_template('user_profile.html', user=user,
                           follower_count=follower_count, 
                           followee_count=followee_count)

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', title='Sign Up', form=form)

@app.route("/login", methods=['GET', 'POST'], endpoint='login')
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('You have been logged in!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User not found.')
        return redirect(url_for('home'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user_profile', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are now following {}!'.format(username))
    return redirect(url_for('user_profile', username=username))

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User not found.')
        return redirect(url_for('home'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user_profile', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You have stopped following {}.'.format(username))
    return redirect(url_for('user_profile', username=username))

@app.route("/tweet/delete/<int:tweet_id>")
@login_required
def delete_tweet(tweet_id):
    tweet = Tweet.query.get_or_404(tweet_id)
    if tweet.user != current_user:
        flash('You do not have permission to delete this tweet.', 'danger')
        return redirect(url_for('home'))
    db.session.delete(tweet)
    db.session.commit()
    flash('Your tweet has been deleted!', 'success')
    return redirect(url_for('home'))




class Tweet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(280), nullable=False)  #Twitter's character limit
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User')

    def __repr__(self):
        return f"Tweet('{self.content}', '{self.date_posted}')"
    
#followers association table
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    #new fields for following functionality
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    


    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"
    
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0
    

