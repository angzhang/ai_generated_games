import pytest
from datetime import datetime, timedelta
from database import db, User, PasswordHistory, PasswordPolicy, PasswordError
from werkzeug.security import check_password_hash

class TestPasswordPolicy:
    """Test password policy validation."""
    
    def test_valid_password(self):
        is_valid, message = PasswordPolicy.validate_password("ValidPass123!")
        assert is_valid is True
        assert message == ""
    
    def test_password_too_short(self):
        is_valid, message = PasswordPolicy.validate_password("Short1!")
        assert is_valid is False
        assert "between 8 and 128 characters" in message
    
    def test_password_too_long(self):
        long_password = "a" * 129
        is_valid, message = PasswordPolicy.validate_password(long_password)
        assert is_valid is False
        assert "between 8 and 128 characters" in message
    
    def test_password_no_uppercase(self):
        is_valid, message = PasswordPolicy.validate_password("lowercase123!")
        assert is_valid is False
        assert "uppercase letter" in message
    
    def test_password_no_lowercase(self):
        is_valid, message = PasswordPolicy.validate_password("UPPERCASE123!")
        assert is_valid is False
        assert "lowercase letter" in message
    
    def test_password_no_numbers(self):
        is_valid, message = PasswordPolicy.validate_password("NoNumbers!")
        assert is_valid is False
        assert "number" in message
    
    def test_password_no_special_chars(self):
        is_valid, message = PasswordPolicy.validate_password("NoSpecial123")
        assert is_valid is False
        assert "special character" in message
    
    def test_password_repeated_chars(self):
        is_valid, message = PasswordPolicy.validate_password("Aaaaa123!")
        assert is_valid is False
        assert "repeated characters" in message

class TestUser:
    """Test User model functionality."""
    
    def test_user_creation(self, app):
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.password = 'ValidPass123!'
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.password_hash is not None
            assert user.password_last_changed is not None
    
    def test_password_hashing(self, app):
        with app.app_context():
            user = User(username='hashtest', email='hash@example.com')
            password = 'TestHash123!'
            user.password = password
            
            assert user.password_hash != password
            assert check_password_hash(user.password_hash, password)
    
    def test_password_verification_success(self, app, sample_user):
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            assert user.verify_password('TestPass123!') is True
            assert user.failed_login_attempts == 0
    
    def test_password_verification_failure(self, app, sample_user):
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            assert user.verify_password('WrongPassword') is False
            assert user.failed_login_attempts == 1
    
    def test_account_lockout(self, app, sample_user):
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            
            # Simulate 5 failed login attempts
            for i in range(5):
                user.verify_password('WrongPassword')
            
            assert user.is_locked is True
            assert user.failed_login_attempts == 5
            
            # Even with correct password, should fail when locked
            assert user.verify_password('TestPass123!') is False
    
    def test_account_unlock_after_timeout(self, app, sample_user):
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            
            # Lock the account
            for i in range(5):
                user.verify_password('WrongPassword')
            
            # Simulate time passing (more than 30 minutes)
            user.last_failed_login = datetime.utcnow() - timedelta(minutes=31)
            db.session.commit()
            
            # Should unlock and allow correct password
            assert user.verify_password('TestPass123!') is True
            assert user.is_locked is False
    
    def test_get_by_username_or_email(self, app, sample_user):
        with app.app_context():
            # Test finding by username
            user_by_username = User.get_by_username_or_email('testuser')
            assert user_by_username is not None
            assert user_by_username.username == 'testuser'
            
            # Test finding by email
            user_by_email = User.get_by_username_or_email('test@example.com')
            assert user_by_email is not None
            assert user_by_email.email == 'test@example.com'
            
            # Test not found
            user_not_found = User.get_by_username_or_email('nonexistent')
            assert user_not_found is None
    
    def test_password_not_readable(self, app):
        with app.app_context():
            user = User(username='readtest', email='read@example.com')
            user.password = 'TestRead123!'
            
            with pytest.raises(AttributeError):
                _ = user.password
    
    def test_invalid_password_raises_error(self, app):
        with app.app_context():
            user = User(username='errortest', email='error@example.com')
            
            with pytest.raises(PasswordError):
                user.password = 'weak'
    
    def test_password_history_creation(self, app):
        with app.app_context():
            user = User(username='historytest', email='history@example.com')
            user.password = 'FirstPass123!'
            db.session.add(user)
            db.session.commit()
            
            # Change password
            user.password = 'SecondPass123!'
            db.session.commit()
            
            # Check password history
            assert len(user.password_history) == 1
            assert user.check_password_history('FirstPass123!') is True
            assert user.check_password_history('SecondPass123!') is False  # Current password not in history
    
    def test_password_history_prevents_reuse(self, app):
        with app.app_context():
            user = User(username='reusetest', email='reuse@example.com')
            user.password = 'FirstPass123!'
            db.session.add(user)
            db.session.commit()
            
            # Try to reuse the same password
            with pytest.raises(PasswordError, match="same as any of your last"):
                user.password = 'FirstPass123!'
    
    def test_check_password_expiration(self, app):
        with app.app_context():
            user = User(username='expiretest', email='expire@example.com')
            user.password = 'ExpireTest123!'
            
            # Fresh password should not be expired
            assert user.check_password_expiration() is False
            
            # Set password change date to more than 90 days ago
            user.password_last_changed = datetime.utcnow() - timedelta(days=91)
            assert user.check_password_expiration() is True
            
            # Test user with no password_last_changed
            user.password_last_changed = None
            assert user.check_password_expiration() is True