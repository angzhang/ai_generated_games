import pytest
import tempfile
import os
from app import app as flask_app
from database import db, User, PasswordHistory, create_tables, drop_tables

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Use SQLite for testing instead of MySQL
    db_fd, db_path = tempfile.mkstemp()
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    with flask_app.app_context():
        create_tables(flask_app)
        
    yield flask_app
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.password = 'TestPass123!'
        db.session.add(user)
        db.session.commit()
        return user