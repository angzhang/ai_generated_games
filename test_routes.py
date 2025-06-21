import pytest
from flask import url_for
from database import db, User

class TestRoutes:
    """Test Flask application routes."""
    
    def test_home_redirects_to_login(self, client):
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_login_get(self, client):
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_login_post_success(self, client, app, sample_user):
        with app.app_context():
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'TestPass123!'
            })
            assert response.status_code == 302
            assert '/game' in response.location
    
    def test_login_post_invalid_credentials(self, client, app, sample_user):
        with app.app_context():
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpassword'
            })
            assert response.status_code == 200
            assert b'Invalid credentials' in response.data
    
    def test_login_post_nonexistent_user(self, client):
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'password123'
        })
        assert response.status_code == 200
        assert b'Invalid credentials' in response.data
    
    def test_login_with_email(self, client, app, sample_user):
        with app.app_context():
            response = client.post('/login', data={
                'username': 'test@example.com',
                'password': 'TestPass123!'
            })
            assert response.status_code == 302
            assert '/game' in response.location
    
    def test_signup_get(self, client):
        response = client.get('/signup')
        assert response.status_code == 200
        assert b'signup' in response.data.lower()
    
    def test_signup_post_success(self, client, app):
        with app.app_context():
            response = client.post('/signup', data={
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'NewPass123!'
            })
            assert response.status_code == 302
            assert '/login' in response.location
            
            # Verify user was created
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'newuser@example.com'
    
    def test_signup_post_duplicate_username(self, client, app, sample_user):
        with app.app_context():
            response = client.post('/signup', data={
                'username': 'testuser',  # Same as sample_user
                'email': 'different@example.com',
                'password': 'NewPass123!'
            })
            assert response.status_code == 200
            assert b'Username or email already exists' in response.data
            # Check that form values are preserved
            assert b'value="testuser"' in response.data
            assert b'value="different@example.com"' in response.data
    
    def test_signup_post_duplicate_email(self, client, app, sample_user):
        with app.app_context():
            response = client.post('/signup', data={
                'username': 'differentuser',
                'email': 'test@example.com',  # Same as sample_user
                'password': 'NewPass123!'
            })
            assert response.status_code == 200
            assert b'Username or email already exists' in response.data
    
    def test_signup_post_invalid_password(self, client):
        response = client.post('/signup', data={
            'username': 'weakpassuser',
            'email': 'weak@example.com',
            'password': 'weak'  # Invalid password
        })
        assert response.status_code == 200
        assert b'Password error:' in response.data
        # Check that username and email are preserved in form
        assert b'value="weakpassuser"' in response.data
        assert b'value="weak@example.com"' in response.data
    
    def test_signup_post_password_no_uppercase(self, client):
        response = client.post('/signup', data={
            'username': 'noupperuser',
            'email': 'noupper@example.com',
            'password': 'lowercase123!'
        })
        assert response.status_code == 200
        assert b'uppercase letter' in response.data
    
    def test_forgot_password_get(self, client):
        response = client.get('/forgot-password')
        assert response.status_code == 200
        assert b'forgot' in response.data.lower()
    
    def test_forgot_password_post_existing_user(self, client, app, sample_user):
        with app.app_context():
            response = client.post('/forgot-password', data={
                'email': 'test@example.com'
            })
            assert response.status_code == 302
            assert '/login' in response.location
            
            # Verify password was reset
            user = User.query.filter_by(email='test@example.com').first()
            assert user.verify_password('newpassword123') is True
    
    def test_forgot_password_post_nonexistent_user(self, client):
        response = client.post('/forgot-password', data={
            'email': 'nonexistent@example.com'
        })
        assert response.status_code == 200
        assert b'No user with that email found' in response.data
    
    def test_account_get_without_login(self, client):
        response = client.get('/account')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_account_get_with_login(self, client, app, sample_user):
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.get('/account')
            assert response.status_code == 200
            assert b'account' in response.data.lower()
    
    def test_account_post_change_password_success(self, client, app, sample_user):
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.post('/account', data={
                'old_password': 'TestPass123!',
                'new_password': 'NewPass456!',
                'confirm_password': 'NewPass456!'
            })
            assert response.status_code == 200
            assert b'Password changed successfully' in response.data
            
            # Verify password was changed
            user = db.session.get(User, sample_user.id)
            assert user.verify_password('NewPass456!') is True
    
    def test_account_post_wrong_old_password(self, client, app, sample_user):
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.post('/account', data={
                'old_password': 'WrongOldPass',
                'new_password': 'NewPass456!',
                'confirm_password': 'NewPass456!'
            })
            assert response.status_code == 200
            assert b'Old password is incorrect' in response.data
    
    def test_account_post_password_mismatch(self, client, app, sample_user):
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.post('/account', data={
                'old_password': 'TestPass123!',
                'new_password': 'NewPass456!',
                'confirm_password': 'DifferentPass456!'
            })
            assert response.status_code == 200
            assert b'New passwords do not match' in response.data
    
    def test_account_post_invalid_new_password(self, client, app, sample_user):
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.post('/account', data={
                'old_password': 'TestPass123!',
                'new_password': 'weak',  # Invalid password
                'confirm_password': 'weak'
            })
            assert response.status_code == 200
            assert b'Password error:' in response.data
    
    def test_logout(self, client, app, sample_user):
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.get('/logout')
            assert response.status_code == 302
            assert '/login' in response.location
            
            # Verify session was cleared
            with client.session_transaction() as sess:
                assert 'user_id' not in sess

class TestAuthentication:
    """Test authentication-related functionality."""
    
    def test_session_management(self, client, app, sample_user):
        with app.app_context():
            # Test login creates session
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'TestPass123!'
            }, follow_redirects=True)
            
            with client.session_transaction() as sess:
                assert 'user_id' in sess
                assert sess['user_id'] == sample_user.id
    
    def test_protected_route_access(self, client, app, sample_user):
        with app.app_context():
            # Try to access protected route without login
            response = client.get('/account')
            assert response.status_code == 302
            
            # Login and try again
            client.post('/login', data={
                'username': 'testuser',
                'password': 'TestPass123!'
            })
            
            response = client.get('/account')
            assert response.status_code == 200
    
    def test_login_with_locked_account(self, client, app, sample_user):
        with app.app_context():
            # Lock the account by making failed attempts
            user = db.session.get(User, sample_user.id)
            for i in range(5):
                user.verify_password('wrongpassword')
            
            # Try to login with correct credentials
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'TestPass123!'
            })
            assert response.status_code == 200
            assert b'Invalid credentials' in response.data

class TestGameRoutes:
    """Test game-related routes."""
    
    def test_game_requires_login(self, client):
        """Test that game page requires authentication."""
        response = client.get('/game')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_game_access_when_logged_in(self, client, app, sample_user):
        """Test that logged-in users can access the game."""
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.get('/game')
            assert response.status_code == 200
            assert b'Sky Fighter 1942' in response.data
            assert b'gameCanvas' in response.data
            assert b'startBtn' in response.data
    
    def test_game_navigation_when_logged_in(self, client, app, sample_user):
        """Test that navigation shows game link when logged in."""
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.get('/game')
            assert response.status_code == 200
            assert b'Play Game' in response.data

class TestProfileRoutes:
    """Test profile and password change routes."""
    
    def test_profile_requires_login(self, client):
        """Test that profile page requires authentication."""
        response = client.get('/profile')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_profile_access_when_logged_in(self, client, app, sample_user):
        """Test that logged-in users can access their profile."""
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.get('/profile')
            assert response.status_code == 200
            assert b'User Profile' in response.data
            assert b'testuser' in response.data  # Username should be displayed
            assert b'test@example.com' in response.data  # Email should be displayed
    
    def test_change_password_requires_login(self, client):
        """Test that change password page requires authentication."""
        response = client.get('/change-password')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_change_password_access_when_logged_in(self, client, app, sample_user):
        """Test that logged-in users can access change password page."""
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.get('/change-password')
            assert response.status_code == 200
            assert b'Change Password' in response.data
            assert b'old_password' in response.data
            assert b'new_password' in response.data
    
    def test_change_password_success(self, client, app, sample_user):
        """Test successful password change redirects to profile."""
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.post('/change-password', data={
                'old_password': 'TestPass123!',
                'new_password': 'NewPass456!',
                'confirm_password': 'NewPass456!'
            })
            assert response.status_code == 302
            assert '/profile' in response.location
    
    def test_account_redirects_to_profile(self, client, app, sample_user):
        """Test that old account route redirects to profile."""
        with app.app_context():
            # Login first
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.get('/account')
            assert response.status_code == 302
            assert '/profile' in response.location