import streamlit as st
import sqlite3
import os
import time

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

def get_comments_for_post(post_id):
    """Fetches all comments for a specific post, ordered by time."""
    conn = get_db_connection()
    comments = conn.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY timestamp ASC', (post_id,)).fetchall()
    conn.close()
    return comments

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
            # Using an expander for each post creates a clean, Reddit-like thread view
            with st.expander(f"**{post['title']}** (posted by *{post['author_name']}*)"):
                # Display the main post content
                with st.chat_message(name=post['author_name']):
                    st.markdown(post['content'])
                
                st.markdown("---")
                st.markdown("##### Comments")

                # Display comments for this post
                comments = get_comments_for_post(post['id'])
                if not comments:
                    st.write("*No comments yet...*")
                else:
                    for comment in comments:
                        with st.chat_message(name=comment['author_name']):
                            st.markdown(comment['content'])
else:
    st.info("Waiting for the simulation to generate content...")

# --- AUTO-REFRESH LOGIC ---
if auto_refresh:
    time.sleep(10)
    st.rerun()