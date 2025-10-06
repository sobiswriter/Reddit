import streamlit as st
import sqlite3
import os
import time
# btw the file is called window.py because "app" is a reserved word in default simulator setup
# --- DATABASE HELPER FUNCTIONS ---
# These functions will read from the world.db file created by engine.py

def get_db_connection():
    """Connects to the SQLite database."""
    # This path assumes app.py is in the root of your project folder
    db_path = os.path.join(os.path.dirname(__file__), 'world.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

def get_active_subreddits():
    """Fetches a list of subreddits that have posts."""
    conn = get_db_connection()
    subreddits = conn.execute('SELECT DISTINCT subreddit FROM posts ORDER BY subreddit ASC').fetchall()
    conn.close()
    return [row['subreddit'] for row in subreddits]

def get_posts_for_subreddit(subreddit):
    """Fetches all posts for a selected subreddit."""
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts WHERE subreddit = ? ORDER BY timestamp DESC', (subreddit,)).fetchall()
    conn.close()
    return posts

# UPDATED: Fetches and organizes comments into a threaded structure
def get_comments_for_post_threaded(post_id):
    conn = get_db_connection()
    comments_raw = conn.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY timestamp ASC', (post_id,)).fetchall()
    conn.close()
    
    comments_by_id = {c['id']: dict(c) for c in comments_raw}
    threaded_comments = []
    
    for cid, comment in comments_by_id.items():
        if comment['parent_comment_id'] is None:
            threaded_comments.append(comment)
        else:
            parent = comments_by_id.get(comment['parent_comment_id'])
            if parent:
                if 'replies' not in parent:
                    parent['replies'] = []
                parent['replies'].append(comment)
                
    return threaded_comments

# NEW: A function to display comments recursively
def display_comment_thread(comments, level=0):
    for comment in comments:
        with st.chat_message(name=comment['author_name']):
            # Indent replies to show nesting
            st.markdown(f"{'<blockquote>' * level}{comment['content']}{'</blockquote>' * level}", unsafe_allow_html=True)
        
        if 'replies' in comment:
            display_comment_thread(comment['replies'], level + 1)

# --- STREAMLIT FRONT-END ---
st.set_page_config(layout="wide", page_title="Genesis Chamber")
st.title("🤖 The Genesis Chamber")
st.caption("A real-time viewer for the autonomous AI society.")

# --- SIDEBAR FOR CONTROLS ---
st.sidebar.header("View Settings")

active_subreddits = get_active_subreddits()
if not active_subreddits:
    st.sidebar.warning("No activity yet. Make sure engine.py is running.")
    selected_subreddit = None
else:
    selected_subreddit = st.sidebar.selectbox(
        "Select a Subreddit to View:",
        options=active_subreddits
    )

auto_refresh = st.sidebar.checkbox("Auto-refresh every 10 seconds", value=True)

# --- MAIN DISPLAY AREA ---
if selected_subreddit:
    st.header(f"Viewing posts in r/{selected_subreddit}")
    posts = get_posts_for_subreddit(selected_subreddit)
    
    if not posts:
        st.info("No posts in this subreddit yet.")
    else:
        for post in posts:
            with st.expander(f"**{post['title']}** (posted by *{post['author_name']}*)"):
                with st.chat_message(name=post['author_name']):
                    st.markdown(post['content'])
                
                st.markdown("---")
                st.markdown("##### Comments")

                # UPDATED: Use the new threaded display function
                threaded_comments = get_comments_for_post_threaded(post['id'])
                if not threaded_comments:
                    st.write("*No comments yet...*")
                else:
                    display_comment_thread(threaded_comments)
else:
    st.info("Waiting for the simulation to generate content...")

# --- AUTO-REFRESH LOGIC ---
if auto_refresh:
    time.sleep(10)
    st.rerun()