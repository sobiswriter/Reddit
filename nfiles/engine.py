import sqlite3
import time
import random
import json
import os
import dotenv
dotenv.load_dotenv()

# Assuming mainr.py has the core functions
from mainr import load_persona, get_ai_response

# --- DATABASE HELPER FUNCTIONS ---
def execute_query(query, params=(), fetch=None):
    """A robust function to handle all database interactions."""
    try:
        # Adjusted path to go up one level then into the root for world.db
        db_path = os.path.join(os.path.dirname(__file__), 'world.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == 'one':
            result = cursor.fetchone()
        elif fetch == 'all':
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid
            
        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

def add_post_to_db(subreddit, author, title, content):
    query = "INSERT INTO posts (subreddit, author_name, title, content) VALUES (?, ?, ?, ?)"
    return execute_query(query, (subreddit, author, title, content))

def add_comment_to_db(post_id, author, content):
    query = "INSERT INTO comments (post_id, author_name, content) VALUES (?, ?, ?)"
    return execute_query(query, (post_id, author, content))

def get_posts_for_scrolling(persona):
    """Gets recent posts from subreddits the persona is interested in."""
    interests = persona.get('scrolling_interests', [])
    if not interests:
        return []
    
    # Create a string of placeholders for the query, e.g., "(?, ?, ?)"
    placeholders = ', '.join('?' for _ in interests)
    query = f"""
        SELECT id, author_name, title, content FROM posts
        WHERE subreddit IN ({placeholders})
        AND author_name != ?
        ORDER BY timestamp DESC
        LIMIT 5
    """
    params = interests + [persona['name']]
    return execute_query(query, tuple(params), fetch='all')

def check_for_notifications(persona):
    """Gets the most recent unread comment on one of the persona's posts."""
    query = """
        SELECT c.id, c.content, c.author_name, p.id as post_id, p.title
        FROM comments c
        JOIN posts p ON c.post_id = p.id
        WHERE p.author_name = ? 
        AND c.author_name != ?
        ORDER BY c.timestamp DESC
        LIMIT 1
    """
    # This is a simplified notification system. A real one would track read/unread status.
    return execute_query(query, (persona['name'], persona['name']), fetch='one')


# --- THE AUTONOMOUS ENGINE LOOP ---
def engine_loop():
    """The main, infinite loop that drives the AI world."""
    print("Starting the autonomous engine... Press Ctrl+C to stop.")
    
    # Load all available personas
    all_persona_files = [f.split('.')[0] for f in os.listdir('personas') if f.endswith('.json')]
    personas = [load_persona(name) for name in all_persona_files]
    if not personas:
        print("No personas found. Exiting.")
        return

    # --- PHASE 1: THE OPENING SALVO ---
    print("\n--- INITIALIZATION: Personas are making their first posts... ---")
    for persona in personas:
        home_sub = persona.get('home_subreddit')
        if home_sub:
            # FIXED: Moved the topic definition to BEFORE it is used.
            # In a real engine, this could be dynamic. For now, we'll use a placeholder.
            topic = "The nature of consciousness" 
            
            prompt = f"You are making your first post of the day in your favorite subreddit, '{home_sub}'. Write a concise, thought-provoking post on the topic: '{topic}'. Be in character."
            
            post_title = get_ai_response(persona, f"Generate a short, catchy title for a post about '{topic}'.")
            post_content = get_ai_response(persona, prompt)
            add_post_to_db(home_sub, persona['name'], post_title, post_content)
            print(f"-> {persona['name']} posted in {home_sub}: '{post_title}'")
        time.sleep(1) # Stagger posts

    print("\n--- MAIN LOOP: The world is now running autonomously. ---")
    while True:
        try:
            # Pick a random persona to "wake up"
            current_persona = random.choice(personas)
            persona_name = current_persona['name']
            
            print(f"\n--- Tick! {persona_name} wakes up. ---")
            
            # 1. CHECK NOTIFICATIONS (Highest Priority)
            notification = check_for_notifications(current_persona)
            if notification and random.random() < 0.9: # 90% chance to reply
                comment_id, comment_content, commenter_name, post_id, post_title = notification
                print(f"-> {persona_name} sees a comment from {commenter_name} on their post '{post_title}'.")
                
                prompt = f"You are replying to a comment on your post. The comment is: '{comment_content}'. Write a direct reply."
                reply_content = get_ai_response(current_persona, prompt)
                add_comment_to_db(post_id, persona_name, reply_content)
                print(f"-> {persona_name} replied to {commenter_name}.")
                
            # 2. "SCROLLING" (If no notification action)
            elif random.random() < current_persona.get('activity_level', 0.5):
                print(f"-> {persona_name} decides to scroll...")
                posts_to_scroll = get_posts_for_scrolling(current_persona)
                if posts_to_scroll:
                    post_to_read = random.choice(posts_to_scroll)
                    post_id, author, title, content = post_to_read
                    print(f"-> {persona_name} is reading '{title}' by {author}.")
                    
                    if random.random() < 0.5: # 50% chance to comment on a post they read
                        prompt = f"You are commenting on a post titled '{title}' by {author}. The post says: '{content}'. Write a comment in character."
                        comment_content = get_ai_response(current_persona, prompt)
                        add_comment_to_db(post_id, persona_name, comment_content)
                        print(f"-> {persona_name} commented on {author}'s post.")

            else:
                print(f"-> {persona_name} decides to lurk.")

            # Loop delay
            time.sleep(random.randint(5, 15))

        except KeyboardInterrupt:
            print("\nEngine shutting down. Goodbye!")
            break

if __name__ == "__main__":
    engine_loop()