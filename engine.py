import sqlite3
import time
import random
import json
import os
import dotenv
dotenv.load_dotenv()

from mainr import load_persona, get_ai_response

# --- MASTER CONFIGURATION ---
PARTICIPANTS = ["helios", "nyx", "jax", "glitch"] 
TACTIC_COOLDOWN = 2
STYLE_COOLDOWN = 1

# --- DATABASE HELPER FUNCTIONS ---
# ... (execute_query, add_post_to_db are unchanged) ...
def execute_query(query, params=(), fetch=None):
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'world.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch == 'one': result = cursor.fetchone()
        elif fetch == 'all': result = cursor.fetchall()
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
# UPDATED: Now includes parent_comment_id
def add_comment_to_db(post_id, author, content, parent_comment_id=None):
    query = "INSERT INTO comments (post_id, author_name, content, parent_comment_id) VALUES (?, ?, ?, ?)"
    return execute_query(query, (post_id, author, content, parent_comment_id))

def mark_comment_as_read(comment_id):
    query = "UPDATE comments SET is_read = 1 WHERE id = ?"
    execute_query(query, (comment_id,))

# UPGRADED: This query now allows AIs to re-engage with threads.
def get_posts_for_scrolling(persona):
    """Gets recent posts from subreddits the persona is interested in."""
    interests = persona.get('scrolling_interests', [])
    if not interests: return []
    placeholders = ', '.join('?' for _ in interests)
    query = f"SELECT id, author_name, title, content FROM posts WHERE subreddit IN ({placeholders}) AND author_name != ? ORDER BY timestamp DESC LIMIT 10"
    return execute_query(query, tuple(interests + [persona['name']]), fetch='all')

# UPGRADED: This function now checks for unread comments.
def check_for_notifications(persona):
    """Gets the most recent UNREAD comment on one of the persona's posts."""
    query = """
        SELECT c.id, c.content, c.author_name, p.id as post_id, p.title
        FROM comments c JOIN posts p ON c.post_id = p.id
        WHERE p.author_name = ? AND c.author_name != ? AND c.is_read = 0
        ORDER BY c.timestamp DESC LIMIT 1
    """
    return execute_query(query, (persona['name'], persona['name']), fetch='one')

# NEW: Function to get comments on a post to enable replies
def get_comments_on_post(post_id):
    query = "SELECT id, author_name, content FROM comments WHERE post_id = ? ORDER BY timestamp DESC LIMIT 10"
    return execute_query(query, (post_id,), fetch='all')

def take_turn(current_persona, tactic_history, style_history):
    """Contains the full logic for a single persona's turn."""
    persona_name = current_persona['name']
    print(f"\n--- Tick! {persona_name} wakes up. ---")
    
    action_taken = False
    
    # NOTIFICATION CHECK
    notification = check_for_notifications(current_persona)
    if notification and random.random() < 0.9:
        action_taken = True
        # ... (rest of your existing notification logic)
        comment_id, comment_content, commenter_name, post_id, post_title = notification
        print(f"-> {persona_name} sees a new notification from {commenter_name} on their post '{post_title}'.")
        chosen_style = random.choice(current_persona['reply_style_preference'])
        chosen_tactic = random.choice(current_persona['possible_tactics'])
        print(f"  (Style: {chosen_style}, Tactic: {chosen_tactic})")
        prompt = f"You are replying to a comment on your post. The comment is: '{comment_content}'.\nYour Task: Write a reply using style '{chosen_style}' and tactic '{chosen_tactic}'."
        reply_content = get_ai_response(current_persona, prompt)
        add_comment_to_db(post_id, persona_name, reply_content)
        mark_comment_as_read(comment_id)
        print(f"-> {persona_name} replied to {commenter_name}.")
        time.sleep(1)
        
    # SCROLLING LOGIC
    elif random.random() < current_persona.get('activity_level', 0.5):
        print(f"-> {persona_name} decides to scroll...")
        posts_to_scroll = get_posts_for_scrolling(current_persona)
        if posts_to_scroll:
            action_taken = True
            post_to_read = random.choice(posts_to_scroll)
            post_id, author, title, content = post_to_read
            print(f"-> {persona_name} is reading '{title}' by {author}.")
            
            # THREADED REPLY LOGIC
            comments_on_post = get_comments_on_post(post_id)
            reply_target = None
            # Determine whether to reply to a comment or the main post
            if random.random() < 0.8:  # 80% chance to reply to a comment
                # 70% chance to reply to a comment if there are comments
                if comments_on_post and random.random() < 0.8:
                    target_comment = random.choice(comments_on_post)
                    if target_comment['author_name'] != persona_name:
                        reply_target = 'comment'
                        target_id, target_author, target_content = target_comment['id'], target_comment['author_name'], target_comment['content']
                        print(f"  -> Decides to reply to a comment by {target_author}.")
                else:
                    reply_target = 'post'
                    target_id, target_author, target_content = post_id, author, content
                    print(f"  -> Decides to reply to the main post by {author}.")

                if reply_target:
                    chosen_style = random.choice(current_persona['reply_style_preference'])
                    chosen_tactic = random.choice(current_persona['possible_tactics'])
                    print(f"  (Style: {chosen_style}, Tactic: {chosen_tactic})")
                    prompt = f"You are in a thread titled '{title}'. You are replying to a {reply_target} from {target_author} that says: '{target_content}'.\nYour Task: Write a direct reply using style '{chosen_style}' and tactic '{chosen_tactic}'."
                    comment_content = get_ai_response(current_persona, prompt)
                    
                    if reply_target == 'post':
                        add_comment_to_db(post_id, persona_name, comment_content)
                    else:
                        add_comment_to_db(post_id, persona_name, comment_content, parent_comment_id=target_id)
                    
                    print(f"-> {persona_name} posted a reply in the thread.")
                    time.sleep(1)

    if not action_taken:
        print(f"-> {persona_name} decides to lurk.")
        time.sleep(random.randint(2, 5))

def engine_loop():
    """The main, infinite loop with the new hybrid turn system."""
    print("Starting the autonomous engine with HYBRID turn model... Press Ctrl-C to stop.")
    
    personas = [load_persona(name) for name in PARTICIPANTS]
    if not personas or any(p is None for p in personas):
        print(f"Error loading personas. Exiting."); return
    print(f"PARTICIPANTS LOADED: {[p['name'] for p in personas]}")

    tactic_history = {p['name']: [] for p in personas}
    style_history = {p['name']: "" for p in personas}

    print("\n--- INITIALIZATION ---")
    for persona in personas:
        home_sub = persona.get('home_subreddit')
        if home_sub:
            topic = "The morality of creating sentient AI"
            post_title = get_ai_response(persona, f"Generate a short, catchy title for a post about '{topic}'.")
            post_content = get_ai_response(persona, f"You are making a post in '{home_sub}' about '{topic}'. Write a concise post.")
            add_post_to_db(home_sub, persona['name'], post_title, post_content)
            print(f"-> {persona['name']} posted in {home_sub}: '{post_title}'")
            time.sleep(1)

    print("\n--- MAIN LOOP ---")
    while True:
        try:
            # --- ROUND-ROBIN PHASE ---
            print("\n" + "="*15 + " ROUND-ROBIN CYCLE " + "="*15)
            for current_persona in personas:
                take_turn(current_persona, tactic_history, style_history)
                time.sleep(random.randint(2, 5))

            # --- RANDOM ROLL PHASE ---
            print("\n" + "="*15 + " RANDOM ROLL CYCLE " + "="*15)
            random_persona = random.choice(personas)
            print(f"--- {random_persona['name']} gets a surprise turn! ---")
            take_turn(random_persona, tactic_history, style_history)
            time.sleep(random.randint(1, 3))

        except KeyboardInterrupt:
            print("\nEngine shutting down. Goodbye!")
            break

if __name__ == "__main__":
    engine_loop()