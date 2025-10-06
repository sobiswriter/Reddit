import sqlite3

def create_database():
    """Connects to the database and creates the necessary tables if they don't exist."""
    
    # This will create the 'world.db' file if it doesn't already exist
    conn = sqlite3.connect('world.db')
    cursor = conn.cursor()

    # --- Create the 'posts' table ---
    # This table will store the main topic of each thread.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subreddit TEXT NOT NULL,
            author_name TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    print("'posts' table created or already exists.")

    # --- Create the 'comments' table ---
    # This table will store all replies.
    # 'post_id' links a comment to its main post.
    # 'parent_comment_id' allows for nested replies (a reply to another reply).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            parent_comment_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        );
    ''')
    print("'comments' table created or already exists.")

    conn.commit()
    conn.close()
    print("\nDatabase 'world.db' is set up and ready!")

if __name__ == "__main__":
    create_database()