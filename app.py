import logging
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import db, User, init_db, create_tables, PasswordError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database
init_db(app)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        logger.debug(f"Login attempt for username/email: {username}")
        password = request.form['password']
        user = User.get_by_username_or_email(username)
        if user and user.verify_password(password):
            session['user_id'] = user.id
            logger.info(f"User {username} logged in successfully.")
            flash('Logged in successfully!')
            return redirect(url_for('games'))
        else:
            logger.warning(f"Failed login attempt for username/email: {username}")
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.get_by_username_or_email(username) or User.get_by_username_or_email(email):
            flash('Username or email already exists')
            return render_template('signup.html', username=username, email=email)
        
        try:
            new_user = User(username=username, email=email)
            new_user.password = password  # This will hash the password
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please log in.')
            return redirect(url_for('login'))
        except PasswordError as e:
            flash(f'Password error: {str(e)}')
            return render_template('signup.html', username=username, email=email)
        except Exception as e:
            flash('An error occurred during signup. Please try again.')
            logger.error(f"Signup error: {str(e)}")
            return render_template('signup.html', username=username, email=email)
    return render_template('signup.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # For demo: reset password to 'newpassword123' and inform user
            user.password = 'newpassword123'
            db.session.commit()
            flash('Password reset! Your new password is "newpassword123". Please log in and change it.')
            return redirect(url_for('login'))
        else:
            flash('No user with that email found.')
    return render_template('forgot_password.html')

@app.route('/account')
def account():
    # Redirect old account route to new profile route
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to access your profile.')
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        flash('Please log in to change your password.')
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if not user.verify_password(old_password):
            flash('Old password is incorrect.')
        elif new_password != confirm_password:
            flash('New passwords do not match.')
        else:
            try:
                user.password = new_password
                db.session.commit()
                flash('Password changed successfully!')
                return redirect(url_for('profile'))
            except PasswordError as e:
                flash(f'Password error: {str(e)}')
    
    return render_template('change_password.html')

@app.route('/games')
def games():
    if 'user_id' not in session:
        flash('Please log in to play games.')
        return redirect(url_for('login'))
    return render_template('games.html')

@app.route('/game/sky-fighter')
def sky_fighter():
    if 'user_id' not in session:
        flash('Please log in to play the game.')
        return redirect(url_for('login'))
    return render_template('sky_fighter.html')

@app.route('/game/tetris')
def tetris():
    if 'user_id' not in session:
        flash('Please log in to play the game.')
        return redirect(url_for('login'))
    return render_template('tetris.html')

@app.route('/game/battle-city')
def battle_city():
    if 'user_id' not in session:
        flash('Please log in to play the game.')
        return redirect(url_for('login'))
    return render_template('battle_city.html')

@app.route('/game')
def game():
    # Redirect old game route to new games menu
    return redirect(url_for('games'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!')
    return redirect(url_for('login'))

if __name__ == '__main__':
    create_tables(app)
    app.run(host='0.0.0.0', debug=True) 