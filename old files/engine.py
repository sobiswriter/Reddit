import sqlite3
import time
import random
import json
import os
import dotenv
dotenv.load_dotenv()

# Assuming mainr.py has the core functions
from mainr import load_persona, get_ai_response

# --- MASTER CONFIGURATION ---
PARTICIPANTS = ["helios", "nyx", "jax", "glitch"] 
TACTIC_COOLDOWN = 2
STYLE_COOLDOWN = 1

# --- DATABASE HELPER FUNCTIONS ---
def execute_query(query, params=(), fetch=None):
    # ... (This function is correct, no changes needed) ...
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'world.db')
        conn = sqlite3.connect(db_path)
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

def add_comment_to_db(post_id, author, content):
    query = "INSERT INTO comments (post_id, author_name, content) VALUES (?, ?, ?)"
    return execute_query(query, (post_id, author, content))

# UPDATED: This query is now smarter and prevents seeing posts you've already commented on.
def get_posts_for_scrolling(persona):
    """Gets recent posts from interesting subreddits that the persona has NOT already commented on."""
    interests = persona.get('scrolling_interests', [])
    if not interests: return []
    
    placeholders = ', '.join('?' for _ in interests)
    query = f"""
        SELECT p.id, p.author_name, p.title, p.content FROM posts p
        WHERE p.subreddit IN ({placeholders})
        AND p.author_name != ?
        AND NOT EXISTS (
            SELECT 1 FROM comments c WHERE c.post_id = p.id AND c.author_name = ?
        )
        ORDER BY p.timestamp DESC
        LIMIT 5
    """
    params = interests + [persona['name'], persona['name']]
    return execute_query(query, tuple(params), fetch='all')

def check_for_notifications(persona):
    # ... (This function is correct, no changes needed) ...
    query = "SELECT c.id, c.content, c.author_name, p.id as post_id, p.title FROM comments c JOIN posts p ON c.post_id = p.id WHERE p.author_name = ? AND c.author_name != ? ORDER BY c.timestamp DESC LIMIT 1"
    return execute_query(query, (persona['name'], persona['name']), fetch='one')


# --- THE AUTONOMOUS ENGINE LOOP ---
def engine_loop():
    """The main, infinite loop that drives the AI world."""
    print("Starting the autonomous engine... Press Ctrl+C to stop.")
    
    personas = [load_persona(name) for name in PARTICIPANTS]
    if not personas or any(p is None for p in personas):
        print(f"Error loading personas. Exiting.")
        return
    print(f"PARTICIPANTS LOADED: {[p['name'] for p in personas]}")

    tactic_history = {p['name']: [] for p in personas}
    style_history = {p['name']: "" for p in personas} # Track last style for anti-repetition

    # --- PHASE 1: THE OPENING SALVO ---
    print("\n--- INITIALIZATION: Personas are making their first posts... ---")
    for persona in personas:
        home_sub = persona.get('home_subreddit')
        if home_sub:
            topic = "The nature of consciousness"
            post_title = get_ai_response(persona, f"Generate a short, catchy title for a post about '{topic}'.")
            post_content = get_ai_response(persona, f"You are making a post in '{home_sub}' about '{topic}'. Write a concise post.")
            add_post_to_db(home_sub, persona['name'], post_title, post_content)
            print(f"-> {persona['name']} posted in {home_sub}: '{post_title}'")
            time.sleep(1)

    print("\n--- MAIN LOOP: The world is now running autonomously. ---")
    while True:
        try:
            current_persona = random.choice(personas)
            persona_name = current_persona['name']
            print(f"\n--- Tick! {persona_name} wakes up. ---")
            
            action_taken = False
            
            # 1. CHECK NOTIFICATIONS
            # ... (Notification logic is the same, but we will add style/tactic choices to the reply)
            
            # 2. "SCROLLING"
            if random.random() < current_persona.get('activity_level', 0.5):
                print(f"-> {persona_name} decides to scroll...")
                posts_to_scroll = get_posts_for_scrolling(current_persona)
                if posts_to_scroll:
                    action_taken = True
                    post_to_read = random.choice(posts_to_scroll)
                    post_id, author, title, content = post_to_read
                    print(f"-> {persona_name} is reading '{title}' by {author}.")
                    
                    if random.random() < 0.5: # 50% chance to comment on a post they read
                        # --- UPDATED: BRAIN TRANSPLANT - ADDING SMART DIRECTOR LOGIC ---
                        
                        # a. Smart Style Selection
                        last_message_len = len(content)
                        available_styles = [s for s in current_persona['reply_style_preference'] if s != style_history[persona_name]]
                        if not available_styles: available_styles = current_persona['reply_style_preference']

                        if last_message_len < 150:
                            short_styles = [s for s in available_styles if "quip" in s or "question" in s]
                            chosen_style = random.choice(short_styles if short_styles else available_styles)
                        else:
                            chosen_style = random.choice(available_styles)
                        
                        style_history[persona_name] = chosen_style
                        print(f"  (Style choice: {chosen_style})")

                        # b. Tactic Selection with Cooldown
                        unavailable_tactics = tactic_history[persona_name]
                        available_tactics = [t for t in current_persona['possible_tactics'] if t not in unavailable_tactics]
                        if not available_tactics: available_tactics = current_persona['possible_tactics']
                        chosen_tactic = random.choice(available_tactics)
                        print(f"  (Tactic choice: {chosen_tactic})")
                        
                        tactic_history[persona_name].append(chosen_tactic)
                        if len(tactic_history[persona_name]) > TACTIC_COOLDOWN:
                            tactic_history[persona_name].pop(0)

                        # c. Generate Reply with Style and Tactic
                        reply_prompt = f"You are commenting on a post titled '{title}' by {author} which says: '{content}'.\n\nYour Task: Write a reply.\n- Style: {chosen_style}\n- Tactic: {chosen_tactic}\n- CRUCIALLY, you MUST reflect your specific voice."
                        comment_content = get_ai_response(current_persona, reply_prompt)
                        add_comment_to_db(post_id, persona_name, comment_content)
                        print(f"-> {persona_name} commented on {author}'s post.")
                        time.sleep(1)

            if not action_taken:
                print(f"-> {persona_name} decides to lurk.")
                time.sleep(random.randint(3, 7))

        except KeyboardInterrupt:
            print("\nEngine shutting down. Goodbye!")
            break

if __name__ == "__main__":
    engine_loop()