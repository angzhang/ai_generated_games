
CREATE TABLE user (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(150) NOT NULL, 
	email VARCHAR(150) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	password_last_changed DATETIME, 
	failed_login_attempts INTEGER, 
	last_failed_login DATETIME, 
	is_locked BOOL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
)

;


CREATE TABLE password_history (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
)

;

