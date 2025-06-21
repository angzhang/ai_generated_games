from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime, timedelta

# Initialize SQLAlchemy without binding to app
db = SQLAlchemy()

class PasswordError(Exception):
    """Custom exception for password validation errors"""
    pass

class PasswordPolicy:
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*(),.?\":{}|<>"
    MAX_REPEATED_CHARS = 3
    COMMON_PASSWORDS_FILE = "common_passwords.txt"  # You would need to create/download this file
    PASSWORD_HISTORY_SIZE = 5
    PASSWORD_MIN_AGE_DAYS = 1
    PASSWORD_MAX_AGE_DAYS = 90

    @classmethod
    def validate_password(cls, password, user=None):
        """
        Validate password against security policy
        Returns (bool, str) tuple - (is_valid, error_message)
        """
        try:
            if not cls.MIN_LENGTH <= len(password) <= cls.MAX_LENGTH:
                raise PasswordError(
                    f"Password must be between {cls.MIN_LENGTH} and {cls.MAX_LENGTH} characters"
                )

            if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
                raise PasswordError("Password must contain at least one uppercase letter")

            if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
                raise PasswordError("Password must contain at least one lowercase letter")

            if cls.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
                raise PasswordError("Password must contain at least one number")

            if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
                raise PasswordError(f"Password must contain at least one special character from {cls.SPECIAL_CHARS}")

            # Check for repeated characters
            for i in range(len(password) - cls.MAX_REPEATED_CHARS + 1):
                if len(set(password[i:i + cls.MAX_REPEATED_CHARS])) == 1:
                    raise PasswordError(f"Password cannot contain {cls.MAX_REPEATED_CHARS} or more repeated characters")

            # If user is provided, check password history
            if user:
                if user.check_password_history(password):
                    raise PasswordError("Password cannot be the same as any of your last 5 passwords")

                if user.password_last_changed:
                    days_since_change = (datetime.utcnow() - user.password_last_changed).days
                    if days_since_change < cls.PASSWORD_MIN_AGE_DAYS:
                        raise PasswordError(f"Password cannot be changed more than once every {cls.PASSWORD_MIN_AGE_DAYS} day(s)")

            return True, ""
        except PasswordError as e:
            return False, str(e)

def init_db(app):
    """Initialize the database with the app"""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flaskuser:flaskpass@db/flaskdb'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True
    db.init_app(app)

class PasswordHistory(db.Model):
    """Store password history for users"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    password_last_changed = db.Column(db.DateTime, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime)
    is_locked = db.Column(db.Boolean, default=False)
    password_history = db.relationship('PasswordHistory', backref='user', lazy=True)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        """Set password with enhanced security"""
        # Validate password
        is_valid, error_message = PasswordPolicy.validate_password(password, self)
        if not is_valid:
            raise PasswordError(error_message)

        # Use stronger hashing parameters
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256:260000',  # Use PBKDF2 with SHA256 and 260000 iterations
            salt_length=16  # Use a 16-byte salt
        )

        # Add to password history
        if hasattr(self, 'id') and self.id is not None:  # Only if user already exists in database
            history = PasswordHistory(user_id=self.id, password_hash=self.password_hash)
            db.session.add(history)
            
            # Keep only last N passwords
            old_histories = PasswordHistory.query.filter_by(user_id=self.id)\
                .order_by(PasswordHistory.created_at.desc())\
                .offset(PasswordPolicy.PASSWORD_HISTORY_SIZE).all()
            for old in old_histories:
                db.session.delete(old)

        self.password_last_changed = datetime.utcnow()
        self.failed_login_attempts = 0
        self.is_locked = False

    def verify_password(self, password):
        """Verify password with account lockout"""
        if self.is_locked:
            if self.last_failed_login and \
               datetime.utcnow() - self.last_failed_login < timedelta(minutes=30):
                return False
            self.is_locked = False

        if check_password_hash(self.password_hash, password):
            self.failed_login_attempts = 0
            return True
        
        self.failed_login_attempts += 1
        self.last_failed_login = datetime.utcnow()
        if self.failed_login_attempts >= 5:  # Lock after 5 failed attempts
            self.is_locked = True
        db.session.commit()
        return False

    def check_password_history(self, new_password):
        """Check if password exists in user's password history"""
        for history in self.password_history:
            if check_password_hash(history.password_hash, new_password):
                return True
        return False

    @staticmethod
    def get_by_username_or_email(username_or_email):
        """Get user by username or email"""
        return User.query.filter(
            (User.username == username_or_email) | 
            (User.email == username_or_email)
        ).first()

    def check_password_expiration(self):
        """Check if password has expired"""
        if not self.password_last_changed:
            return True
        days_since_change = (datetime.utcnow() - self.password_last_changed).days
        return days_since_change >= PasswordPolicy.PASSWORD_MAX_AGE_DAYS

def create_tables(app):
    """Create all database tables"""
    with app.app_context():
        db.create_all()

def drop_tables(app):
    """Drop all database tables"""
    with app.app_context():
        db.drop_all() 