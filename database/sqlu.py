# In setup_database.py
import sqlite3

def create_database():
    conn = sqlite3.connect('world.db')
    cursor = conn.cursor()
    
    # Create the 'posts' table (unchanged)
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
    print("'posts' table is up to date.")

    # UPDATED: Added the 'is_read' column to the 'comments' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            parent_comment_id INTEGER,
            is_read INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        );
    ''')
    print("'comments' table has been updated with 'is_read' status.")

    conn.commit()
    conn.close()
    print("\nDatabase 'world.db' is set up and ready!")

if __name__ == "__main__":
    create_database()