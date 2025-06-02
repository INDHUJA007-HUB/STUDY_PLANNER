import streamlit as st
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import hashlib
import time

# Configure the page
st.set_page_config(
    page_title="Smart Task Manager Pro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .task-card {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        background-color: #f8f9fa;
    }
    .completed-task {
        opacity: 0.6;
        border-left-color: #28a745 !important;
    }
    .high-priority {
        border-left-color: #dc3545 !important;
    }
    .medium-priority {
        border-left-color: #ffc107 !important;
    }
    .low-priority {
        border-left-color: #28a745 !important;
    }
    .streak-badge {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        text-align: center;
        font-size: 0.9rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .goal-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .habit-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    .kanban-column {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem;
        min-height: 400px;
    }
    .kanban-task {
        background-color: white;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# --- Enhanced Database Setup ---
def init_db():
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    
    # Users table with additional fields
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        email TEXT,
        created_date DATE,
        timezone TEXT DEFAULT 'UTC',
        theme TEXT DEFAULT 'light'
    )''')
    
    # Enhanced tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        category TEXT,
        priority TEXT DEFAULT 'medium',
        completed BOOLEAN DEFAULT 0,
        date TEXT,
        time_slot TEXT,
        estimated_duration INTEGER DEFAULT 60,
        actual_duration INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        tags TEXT,
        recurring TEXT DEFAULT 'none',
        parent_task_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Categories table
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        color TEXT,
        icon TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Goals table
    c.execute('''CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        target_date DATE,
        progress REAL DEFAULT 0,
        completed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Habits table
    c.execute('''CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        description TEXT,
        frequency TEXT,
        streak INTEGER DEFAULT 0,
        best_streak INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Habit tracking
    c.execute('''CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER,
        date TEXT,
        completed BOOLEAN,
        notes TEXT,
        FOREIGN KEY (habit_id) REFERENCES habits (id)
    )''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# --- Security Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

# --- Enhanced Authentication Functions ---
def register_user(username, password, email):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    try:
        hashed_pw = hash_password(password)
        c.execute("INSERT INTO users (username, password, email, created_date) VALUES (?, ?, ?, ?)", 
                 (username, hashed_pw, email, date.today().isoformat()))
        conn.commit()
        
        # Create default categories
        user_id = c.lastrowid
        default_categories = [
            ('Work', '#1f77b4', '💼'),
            ('Personal', '#ff7f0e', '👤'),
            ('Health', '#2ca02c', '🏥'),
            ('Learning', '#d62728', '📚'),
            ('Hobbies', '#9467bd', '🎨')
        ]
        
        for name, color, icon in default_categories:
            c.execute("INSERT INTO categories (user_id, name, color, icon) VALUES (?, ?, ?, ?)",
                     (user_id, name, color, icon))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and verify_password(password, user[2]):
        return user
    return None

# --- Enhanced Task Functions ---
def get_tasks(user_id, selected_date=None, category=None, priority=None):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    
    query = "SELECT * FROM tasks WHERE user_id = ?"
    params = [user_id]
    
    if selected_date:
        query += " AND date = ?"
        params.append(selected_date)
    
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
    
    if priority and priority != "All":
        query += " AND priority = ?"
        params.append(priority)
    
    query += " ORDER BY time_slot, priority DESC"
    
    c.execute(query, params)
    tasks = c.fetchall()
    conn.close()
    return tasks

def add_task(user_id, title, description, category, priority, date_, time_slot, estimated_duration, tags, recurring="none"):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("""INSERT INTO tasks 
                 (user_id, title, description, category, priority, date, time_slot, estimated_duration, tags, recurring) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
              (user_id, title, description, category, priority, date_, time_slot, estimated_duration, tags, recurring))
    conn.commit()
    conn.close()

def complete_task(task_id, actual_duration=None):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET completed=1, completed_at=?, actual_duration=? WHERE id=?", 
              (datetime.now().isoformat(), actual_duration, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def get_categories(user_id):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("SELECT * FROM categories WHERE user_id = ?", (user_id,))
    categories = c.fetchall()
    conn.close()
    return categories

def get_productivity_stats(user_id, days=7):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    c.execute("""
        SELECT date, 
               COUNT(*) as total_tasks,
               SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_tasks,
               SUM(estimated_duration) as planned_time,
               SUM(CASE WHEN actual_duration IS NOT NULL THEN actual_duration ELSE 0 END) as actual_time
        FROM tasks 
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date
    """, (user_id, start_date.isoformat(), end_date.isoformat()))
    
    stats = c.fetchall()
    conn.close()
    return stats

def get_streak_data(user_id):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    
    c.execute("""
        SELECT date, 
               CASE WHEN COUNT(*) > 0 AND SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) > 0 
                    THEN 1 ELSE 0 END as productive_day
        FROM tasks 
        WHERE user_id = ? 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT 30
    """, (user_id,))
    
    days = c.fetchall()
    conn.close()
    
    current_streak = 0
    for day_data in days:
        if day_data[1] == 1:
            current_streak += 1
        else:
            break
    
    return current_streak

# --- Goal Functions ---
def add_goal(user_id, title, description, target_date):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("INSERT INTO goals (user_id, title, description, target_date) VALUES (?, ?, ?, ?)",
              (user_id, title, description, target_date))
    conn.commit()
    conn.close()

def get_goals(user_id):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("SELECT * FROM goals WHERE user_id = ? ORDER BY target_date", (user_id,))
    goals = c.fetchall()
    conn.close()
    return goals

def update_goal_progress(goal_id, progress):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    completed = 1 if progress >= 100 else 0
    c.execute("UPDATE goals SET progress = ?, completed = ? WHERE id = ?", (progress, completed, goal_id))
    conn.commit()
    conn.close()

def delete_goal(goal_id):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("DELETE FROM goals WHERE id=?", (goal_id,))
    conn.commit()
    conn.close()

# --- Habit Tracking Functions ---
def add_habit(user_id, name, description, frequency):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("INSERT INTO habits (user_id, name, description, frequency) VALUES (?, ?, ?, ?)",
              (user_id, name, description, frequency))
    conn.commit()
    conn.close()

def get_habits(user_id):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("SELECT * FROM habits WHERE user_id = ?", (user_id,))
    habits = c.fetchall()
    conn.close()
    return habits

def log_habit(habit_id, date_str, completed, notes=""):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    
    # Check if already logged for today
    c.execute("SELECT * FROM habit_logs WHERE habit_id = ? AND date = ?", (habit_id, date_str))
    existing = c.fetchone()
    
    if existing:
        c.execute("UPDATE habit_logs SET completed = ?, notes = ? WHERE habit_id = ? AND date = ?",
                  (completed, notes, habit_id, date_str))
    else:
        c.execute("INSERT INTO habit_logs (habit_id, date, completed, notes) VALUES (?, ?, ?, ?)",
                  (habit_id, date_str, completed, notes))
    
    # Update streak
    if completed:
        c.execute("UPDATE habits SET streak = streak + 1 WHERE id = ?", (habit_id,))
        c.execute("UPDATE habits SET best_streak = MAX(best_streak, streak) WHERE id = ?", (habit_id,))
    else:
        c.execute("UPDATE habits SET streak = 0 WHERE id = ?", (habit_id,))
    
    conn.commit()
    conn.close()

def get_habit_log(habit_id, date_str):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("SELECT * FROM habit_logs WHERE habit_id = ? AND date = ?", (habit_id, date_str))
    log = c.fetchone()
    conn.close()
    return log

def delete_habit(habit_id):
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    c.execute("DELETE FROM habit_logs WHERE habit_id = ?", (habit_id,))
    c.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()

# --- AI-Powered Recommendations ---
def get_smart_recommendations(user_id):
    recommendations = []
    
    conn = sqlite3.connect('smart_taskmanager.db')
    c = conn.cursor()
    
    # Check for overdue tasks
    c.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND date < ? AND completed = 0",
              (user_id, date.today().isoformat()))
    overdue_count = c.fetchone()[0]
    
    if overdue_count > 0:
        recommendations.append({
            "type": "warning",
            "title": "⚠️ Overdue Tasks Alert",
            "message": f"You have {overdue_count} overdue tasks. Consider rescheduling or breaking them into smaller chunks.",
            "action": "Review overdue tasks"
        })
    
    # Check for productivity patterns
    stats = get_productivity_stats(user_id, 7)
    if stats:
        total_tasks = sum(row[1] for row in stats)
        completed_tasks = sum(row[2] for row in stats)
        avg_completion = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        if avg_completion < 0.6:
            recommendations.append({
                "type": "tip",
                "title": "💡 Productivity Boost",
                "message": f"Your completion rate is {avg_completion:.1%}. Try breaking tasks into smaller, manageable chunks.",
                "action": "Optimize task planning"
            })
        elif avg_completion > 0.8:
            recommendations.append({
                "type": "success",
                "title": "🎉 Great Performance!",
                "message": f"Excellent completion rate of {avg_completion:.1%}! Keep up the great work!",
                "action": "Maintain momentum"
            })
    
    # Time management suggestions
    c.execute("""SELECT AVG(actual_duration), AVG(estimated_duration) 
                 FROM tasks WHERE user_id = ? AND completed = 1 AND actual_duration IS NOT NULL""",
              (user_id,))
    time_data = c.fetchone()
    
    if time_data[0] and time_data[1] and time_data[0] > time_data[1] * 1.5:
        recommendations.append({
            "type": "insight",
            "title": "⏰ Time Estimation",
            "message": "You're consistently underestimating task duration. Consider adding buffer time.",
            "action": "Improve time estimates"
        })
    
    conn.close()
    return recommendations

# --- Page Functions ---
def show_login():
    st.markdown('<h1 class="main-header">🎯 Smart Task Manager Pro</h1>', unsafe_allow_html=True)
    
    # Feature highlights
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📊 **Smart Analytics**\nTrack productivity patterns")
    with col2:
        st.info("🎯 **Goal Management**\nSet and achieve big goals")
    with col3:
        st.info("🔄 **Habit Tracking**\nBuild lasting habits")
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        st.subheader("Welcome Back!")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns(2)
            with col1:
                login_button = st.form_submit_button("Login", use_container_width=True)
            with col2:
                demo_button = st.form_submit_button("Try Demo", use_container_width=True)
            
            if login_button:
                if username and password:
                    user = login_user(username, password)
                    if user:
                        st.session_state.user_id = user[0]
                        st.session_state.username = user[1]
                        st.session_state.page = 'dashboard'
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.error("❌ Please enter both username and password")
            
            if demo_button:
                # Create demo user if not exists
                demo_user = login_user("demo", "demo123")
                if not demo_user:
                    register_user("demo", "demo123", "demo@example.com")
                    demo_user = login_user("demo", "demo123")
                
                st.session_state.user_id = demo_user[0]
                st.session_state.username = demo_user[1]
                st.session_state.page = 'dashboard'
                st.success("Welcome to demo mode!")
                st.rerun()
    
    with tab2:
        st.subheader("Join Smart Task Manager Pro")
        with st.form("register_form"):
            new_username = st.text_input("Username", placeholder="Choose a unique username")
            new_email = st.text_input("Email", placeholder="your.email@example.com")
            new_password = st.text_input("Password", type="password", placeholder="Create a strong password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            register_button = st.form_submit_button("Create Account", use_container_width=True)
            
            if register_button:
                if new_username and new_email and new_password and confirm_password:
                    if new_password == confirm_password:
                        if register_user(new_username, new_password, new_email):
                            st.success("✅ Account created successfully! Please login.")
                        else:
                            st.error("❌ Username already exists")
                    else:
                        st.error("❌ Passwords don't match")
                else:
                    st.error("❌ Please fill all fields")

def show_dashboard():
    # Header with user info and navigation
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        st.markdown(f"### 👋 Welcome, {st.session_state.username}!")
    
    with col2:
        # Navigation tabs
        tab_selected = st.selectbox("Navigate to:", 
            ["📋 Tasks", "📊 Analytics", "🎯 Goals", "🔄 Habits", "⚙️ Settings"],
            key="main_nav"
        )
    
    with col3:
        col_streak, col_logout = st.columns(2)
        with col_streak:
            streak = get_streak_data(st.session_state.user_id)
            st.markdown(f'<div class="streak-badge">🔥 {streak} days</div>', unsafe_allow_html=True)
        with col_logout:
            if st.button("Logout"):
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.page = 'login'
                st.rerun()
    
    st.divider()
    
    # Route to different pages based on selection
    if tab_selected == "📋 Tasks":
        show_task_manager()
    elif tab_selected == "📊 Analytics":
        show_analytics()
    elif tab_selected == "🎯 Goals":
        show_goals()
    elif tab_selected == "🔄 Habits":
        show_habits()
    elif tab_selected == "⚙️ Settings":
        show_settings()

def show_task_manager():
    # Smart recommendations
    recommendations = get_smart_recommendations(st.session_state.user_id)
    if recommendations:
        st.subheader("🤖 Smart Recommendations")
        for rec in recommendations:
            if rec["type"] == "warning":
                st.warning(f"**{rec['title']}**: {rec['message']}")
            elif rec["type"] == "tip":
                st.info(f"**{rec['title']}**: {rec['message']}")
            elif rec["type"] == "success":
                st.success(f"**{rec['title']}**: {rec['message']}")
            else:
                st.info(f"**{rec['title']}**: {rec['message']}")
    
    # Filters and date selection
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        selected_date = st.date_input("📅 Select Date", value=date.today())
        selected_date_str = selected_date.isoformat()
    
    with col2:
        categories = get_categories(st.session_state.user_id)
        category_options = ["All"] + [cat[2] for cat in categories]
        selected_category = st.selectbox("🏷️ Category", category_options)
    
    with col3:
        priority_filter = st.selectbox("⚡ Priority", ["All", "high", "medium", "low"])
    
    with col4:
        view_mode = st.selectbox("👁️ View", ["List", "Kanban"])
    
    # Add new task section
    with st.expander("➕ Add New Task", expanded=False):
        with st.form("add_task_form"):
            task_col1, task_col2 = st.columns(2)
            
            with task_col1:
                task_title = st.text_input("Task Title*", placeholder="What needs to be done?")
                task_description = st.text_area("Description", placeholder="Add details...")
                task_category = st.selectbox("Category", [cat[2] for cat in categories])
            
            with task_col2:
                task_priority = st.selectbox("Priority", ["high", "medium", "low"], index=1)
                time_slots = [
                    "06:00-07:00", "07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00",
                    "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00",
                    "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00", "22:00-23:00"
                ]
                time_slot = st.selectbox("Time Slot", time_slots)
                estimated_duration = st.number_input("Estimated Duration (minutes)", value=60, min_value=15, step=15)
            
            task_tags = st.text_input("Tags", placeholder="work, urgent, meeting (comma separated)")
            task_recurring = st.selectbox("Recurring", ["none", "daily", "weekly", "monthly"])
            
            add_button = st.form_submit_button("🎯 Add Task", use_container_width=True)
            
            if add_button:
                if task_title:
                    add_task(st.session_state.user_id, task_title, task_description, task_category, 
                            task_priority, selected_date_str, time_slot, estimated_duration, task_tags, task_recurring)
                    st.success("✅ Task added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Please enter a task title")
    
    # Display tasks based on view mode
    st.subheader(f"📅 Tasks for {selected_date.strftime('%B %d, %Y')}")
    
    tasks = get_tasks(st.session_state.user_id, selected_date_str, 
                     selected_category if selected_category != "All" else None,
                     priority_filter if priority_filter != "All" else None)
    
    if view_mode == "List":
        show_tasks_list(tasks)
    else:
        show_tasks_kanban(tasks)

def show_tasks_list(tasks):
    if tasks:
        for task in tasks:
            task_id, user_id, title, description, category, priority, completed, task_date, time_slot, est_duration, actual_duration, created_at, completed_at, tags, recurring, parent_task_id = task
            
            # Task card styling based on priority and completion
            card_class = "task-card"
            if completed:
                card_class += " completed-task"
            else:
                card_class += f" {priority}-priority"
            
            with st.container():
                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns([5, 2, 1, 1])
                
                with col1:
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[priority]
                    if completed:
                        st.markdown(f"~~{priority_emoji} **{title}**~~ ✅")
                        if description:
                            st.markdown(f"*{description}*")
                    else:
                        st.markdown(f"{priority_emoji} **{title}**")
                        if description:
                            st.markdown(f"*{description}*")
                    
                    if tags:
                        tag_list = [tag.strip() for tag in tags.split(',')]
                        tag_str = " ".join([f"`{tag}`" for tag in tag_list])
                        st.markdown(tag_str)
                
                with col2:
                    st.write(f"🕐 {time_slot}")
                    st.write(f"⏱️ {est_duration}min")
                    if category:
                        st.write(f"🏷️ {category}")
                
                with col3:
                    if not completed:
                        if st.button("✅", key=f"complete_{task_id}", help="Complete Task"):
                            complete_task(task_id, est_duration)
                            st.rerun()
                
                with col4:
                    if st.button("🗑️", key=f"delete_{task_id}", help="Delete Task"):
                        delete_task(task_id)
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
                            # Add these lines to complete the show_tasks_list function (after the last line in your code):

                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📝 No tasks found for the selected criteria. Add your first task above!")


def show_tasks_kanban(tasks):
    """Display tasks in Kanban board format"""
    col1, col2, col3 = st.columns(3)
    
    # Separate tasks by status
    todo_tasks = [t for t in tasks if not t[6]]  # not completed
    in_progress_tasks = []  # You can add logic for in-progress status
    completed_tasks = [t for t in tasks if t[6]]  # completed
    
    with col1:
        st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
        st.subheader("📝 To Do")
        for task in todo_tasks:
            st.markdown(f'''
            <div class="kanban-task">
                <strong>{task[2]}</strong><br>
                <small>🕐 {task[7]} | ⏱️ {task[9]}min</small>
            </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
        st.subheader("🔄 In Progress")
        for task in in_progress_tasks:
            st.markdown(f'''
            <div class="kanban-task">
                <strong>{task[2]}</strong><br>
                <small>🕐 {task[7]} | ⏱️ {task[9]}min</small>
            </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
        st.subheader("✅ Completed")
        for task in completed_tasks:
            st.markdown(f'''
            <div class="kanban-task">
                <strong>{task[2]}</strong><br>
                <small>🕐 {task[7]} | ⏱️ {task[9]}min</small>
            </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def show_analytics():
    """Display analytics and productivity insights"""
    st.subheader("📊 Productivity Analytics")
    
    # Get productivity stats
    stats = get_productivity_stats(st.session_state.user_id, 7)
    
    if stats:
        # Create charts
        dates = [s[0] for s in stats]
        total_tasks = [s[1] for s in stats]
        completed_tasks = [s[2] for s in stats]
        
        df = pd.DataFrame({
            'Date': dates,
            'Total Tasks': total_tasks,
            'Completed Tasks': completed_tasks
        })
        
        fig = px.bar(df, x='Date', y=['Total Tasks', 'Completed Tasks'],
                    title='Daily Task Completion')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📈 No data available yet. Complete some tasks to see your analytics!")


def show_goals():
    """Display and manage goals"""
    st.subheader("🎯 Goal Management")
    
    # Add new goal
    with st.expander("➕ Add New Goal"):
        with st.form("add_goal_form"):
            goal_title = st.text_input("Goal Title")
            goal_description = st.text_area("Description")
            target_date = st.date_input("Target Date")
            
            if st.form_submit_button("Add Goal"):
                if goal_title:
                    add_goal(st.session_state.user_id, goal_title, goal_description, target_date.isoformat())
                    st.success("Goal added!")
                    st.rerun()
    
    # Display goals
    goals = get_goals(st.session_state.user_id)
    for goal in goals:
        with st.container():
            st.markdown(f'''
            <div class="goal-card">
                <h4>{goal[2]}</h4>
                <p>{goal[3]}</p>
                <small>Target: {goal[4]} | Progress: {goal[5]:.1f}%</small>
            </div>
            ''', unsafe_allow_html=True)


def show_habits():
    """Display and manage habits"""
    st.subheader("🔄 Habit Tracking")
    
    # Add new habit
    with st.expander("➕ Add New Habit"):
        with st.form("add_habit_form"):
            habit_name = st.text_input("Habit Name")
            habit_description = st.text_area("Description")
            frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"])
            
            if st.form_submit_button("Add Habit"):
                if habit_name:
                    add_habit(st.session_state.user_id, habit_name, habit_description, frequency)
                    st.success("Habit added!")
                    st.rerun()
    
    # Display habits
    habits = get_habits(st.session_state.user_id)
    for habit in habits:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f'''
                <div class="habit-card">
                    <h4>{habit[2]}</h4>
                    <p>{habit[3]}</p>
                    <small>Streak: {habit[5]} days | Best: {habit[6]} days</small>
                </div>
                ''', unsafe_allow_html=True)
            with col2:
                if st.button("✅", key=f"habit_complete_{habit[0]}"):
                    log_habit(habit[0], date.today().isoformat(), True)
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"habit_delete_{habit[0]}"):
                    delete_habit(habit[0])
                    st.rerun()


def show_settings():
    """Display user settings"""
    st.subheader("⚙️ Settings")
    
    st.info("🚧 Settings panel coming soon!")
    st.write("Future features:")
    st.write("- Theme customization")
    st.write("- Notification preferences")
    st.write("- Data export/import")
    st.write("- Account management")


# Main application logic
def main():
    if st.session_state.page == 'login':
        show_login()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()