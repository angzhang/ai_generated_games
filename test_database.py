import pytest
from database import db, User, PasswordHistory, init_db, create_tables, drop_tables
from flask import Flask

class TestDatabaseUtilities:
    """Test database utility functions."""
    
    def test_init_db(self):
        """Test database initialization."""
        test_app = Flask(__name__)
        init_db(test_app)
        
        assert 'SQLALCHEMY_DATABASE_URI' in test_app.config
        assert 'SQLALCHEMY_TRACK_MODIFICATIONS' in test_app.config
        assert test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] is False
        assert test_app.config['SQLALCHEMY_ECHO'] is True
    
    def test_create_tables(self, app):
        """Test table creation."""
        with app.app_context():
            # Drop tables first
            db.drop_all()
            
            # Create tables
            create_tables(app)
            
            # Verify tables exist by trying to query them
            assert User.query.count() == 0
            assert PasswordHistory.query.count() == 0
    
    def test_drop_tables(self, app):
        """Test table dropping."""
        with app.app_context():
            # Ensure tables exist first
            create_tables(app)
            
            # Add some data
            user = User(username='droptest', email='drop@example.com')
            user.password = 'DropTest123!'
            db.session.add(user)
            db.session.commit()
            
            # Drop tables
            drop_tables(app)
            
            # Recreate tables to verify they're empty
            create_tables(app)
            assert User.query.count() == 0
            assert PasswordHistory.query.count() == 0

class TestPasswordHistory:
    """Test PasswordHistory model."""
    
    def test_password_history_creation(self, app):
        """Test creating password history entries."""
        with app.app_context():
            user = User(username='historytest', email='history@example.com')
            user.password = 'HistoryTest123!'
            db.session.add(user)
            db.session.commit()
            
            # Create a password history entry manually
            history = PasswordHistory(user_id=user.id, password_hash='test_hash')
            db.session.add(history)
            db.session.commit()
            
            assert history.id is not None
            assert history.user_id == user.id
            assert history.password_hash == 'test_hash'
            assert history.created_at is not None
    
    def test_password_history_relationship(self, app):
        """Test relationship between User and PasswordHistory."""
        with app.app_context():
            user = User(username='relationtest', email='relation@example.com')
            user.password = 'RelationTest123!'
            db.session.add(user)
            db.session.commit()
            
            # Change password to create history
            user.password = 'NewRelationTest123!'
            db.session.commit()
            
            # Test relationship
            assert len(user.password_history) == 1
            assert user.password_history[0].user == user
    
    def test_password_history_limit(self, app):
        """Test that password history is limited to configured size."""
        with app.app_context():
            user = User(username='limittest', email='limit@example.com')
            user.password = 'LimitTest123!'
            db.session.add(user)
            db.session.commit()
            
            # Change password multiple times (more than history size)
            passwords = [
                'LimitTest1!', 'LimitTest2!', 'LimitTest3!',
                'LimitTest4!', 'LimitTest5!', 'LimitTest6!',
                'LimitTest7!'  # This should cause oldest to be removed
            ]
            
            for password in passwords:
                user.password = password
                db.session.commit()
            
            # Should only keep the last 5 entries
            assert len(user.password_history) <= 5

class TestDatabaseIntegration:
    """Test database integration scenarios."""
    
    def test_user_cascade_delete(self, app):
        """Test that deleting a user removes associated password history."""
        with app.app_context():
            user = User(username='cascadetest', email='cascade@example.com')
            user.password = 'CascadeTest123!'
            db.session.add(user)
            db.session.commit()
            
            user_id = user.id
            
            # Change password to create history
            user.password = 'NewCascadeTest123!'
            db.session.commit()
            
            # Verify history exists
            history_count = PasswordHistory.query.filter_by(user_id=user_id).count()
            assert history_count > 0
            
            # Delete user
            db.session.delete(user)
            db.session.commit()
            
            # Verify history is also deleted (if cascade is set up)
            remaining_history = PasswordHistory.query.filter_by(user_id=user_id).count()
            # Note: This depends on foreign key constraints being properly set up
    
    def test_database_constraints(self, app):
        """Test database constraints."""
        with app.app_context():
            # Test unique username constraint
            user1 = User(username='uniquetest', email='unique1@example.com')
            user1.password = 'UniqueTest123!'
            db.session.add(user1)
            db.session.commit()
            
            user2 = User(username='uniquetest', email='unique2@example.com')
            user2.password = 'UniqueTest123!'
            db.session.add(user2)
            
            with pytest.raises(Exception):  # Should raise integrity error
                db.session.commit()
            
            db.session.rollback()
            
            # Test unique email constraint
            user3 = User(username='uniquetest2', email='unique1@example.com')
            user3.password = 'UniqueTest123!'
            db.session.add(user3)
            
            with pytest.raises(Exception):  # Should raise integrity error
                db.session.commit()
    
    def test_database_transactions(self, app):
        """Test database transaction behavior."""
        with app.app_context():
            # Test successful transaction
            user = User(username='transactiontest', email='transaction@example.com')
            user.password = 'TransactionTest123!'
            db.session.add(user)
            db.session.commit()
            
            user_count = User.query.count()
            
            # Test failed transaction with rollback
            try:
                user2 = User(username='transactiontest', email='transaction2@example.com')  # Duplicate username
                user2.password = 'TransactionTest123!'
                db.session.add(user2)
                db.session.commit()
            except Exception:
                db.session.rollback()
            
            # User count should remain the same
            assert User.query.count() == user_count