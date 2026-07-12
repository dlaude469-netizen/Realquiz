"""
GOKU QUIZ SOLVER BOT v2.0
========================
Multi-Admin Quiz Solver with Beautiful Display System
Ready for Railway Deployment
"""

import os
import sys
import time
import threading
import logging
import random
from datetime import datetime
from flask import Flask
from threading import Thread
import telebot
from telebot import types
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 8080))

# Validate
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not set")
    sys.exit(1)

# Flask app for keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Goku Quiz Solver Bot v2.0"

def run_flask():
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask error: {e}")

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()
    logger.info("✅ Flask Keep-Alive started")

# ================================
# ADMIN CONFIGURATION
# ================================

ADMIN_LIST = {
    "8739344756"
    "9876543210"

}

# ================================
# GLOBAL DATA
# ================================

bot = telebot.TeleBot(BOT_TOKEN)
active_sessions = {}  # {user_id: session_data}
user_login_state = {}  # {user_id: {"email": "", "password": ""}}

# ================================
# SESSION MANAGEMENT
# ================================

class QuizSession:
    def __init__(self, admin_id, admin_info):
        self.admin_id = admin_id
        self.admin_name = admin_info["name"]
        self.admin_email = admin_info["email"]
        self.tier = admin_info["tier"]
        self.login_time = datetime.now()
        self.quizzes_completed = 0
        self.total_questions = 0
        self.correct_answers = 0
        self.quiz_history = []
        self.is_running = False
        self.current_quiz = None

def create_session(user_id, admin_id):
    """Create new session for admin"""
    admin_info = ADMIN_LIST.get(admin_id)
    if not admin_info:
        return None
    
    session = QuizSession(admin_id, admin_info)
    active_sessions[user_id] = session
    return session

# ================================
# DISPLAY FORMATTING
# ================================

def header(title):
    """Create header display"""
    return f"""
╔{'═'*58}╗
║{title.center(58)}║
╚{'═'*58}╝
"""

def box(content, title=""):
    """Create box display"""
    if title:
        lines = f"┌{'─'*58}┐\n"
        lines += f"│ {title.ljust(56)} │\n"
        lines += f"├{'─'*58}┤\n"
    else:
        lines = f"┌{'─'*58}┐\n"
    
    for line in content.split('\n'):
        if line:
            lines += f"│ {line.ljust(56)} │\n"
    
    lines += f"└{'─'*58}┘"
    return lines

def progress_bar(current, total, length=40):
    """Create progress bar"""
    filled = int((current / total) * length)
    bar = "█" * filled + "░" * (length - filled)
    percent = (current / total) * 100
    return f"[{bar}] {current}/{total} ({percent:.0f}%)"

# ================================
# COMMAND HANDLERS
# ================================

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    
    welcome = header("🚀 GOKU QUIZ SOLVER BOT v2.0")
    welcome += f"""
👋 Welcome {message.from_user.first_name}!

This is an advanced quiz solving bot with:
✅ Multi-Admin Support
✅ Beautiful Display System
✅ Session Management
✅ Statistics Tracking

Use /help for commands
Use /login to start quizzing!
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔐 Login", callback_data="login"),
        types.InlineKeyboardButton("❓ Help", callback_data="help")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Status", callback_data="status"),
        types.InlineKeyboardButton("📈 Stats", callback_data="stats")
    )
    
    bot.send_message(user_id, welcome, reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = """
📋 COMMAND HELP

/start - Welcome & Menu
/help - This help message
/login - Login to quiz system
/status - Check your status
/stats - View your statistics

🎮 BUTTONS:
🔐 Login - Select admin & login
▶️ Start Quiz - Begin quiz session
📊 Status - Check system status
📈 Stats - View quiz history
❓ Help - Get help

🎯 HOW TO USE:
1. Click "🔐 Login" button
2. Select your admin profile
3. Enter credentials
4. Click "▶️ Start Quiz"
5. Complete quizzes
6. View results

⚠️ FEATURES:
✅ 3 Quizzes per session
✅ 5-8 Questions per quiz
✅ Multiple categories
✅ Difficulty levels
✅ Session tracking
✅ Beautiful displays
"""
    
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
    )
    
    bot.send_message(message.chat.id, help_text, reply_markup=markup)

# ================================
# CALLBACK HANDLERS
# ================================

@bot.callback_query_handler(func=lambda call: call.data == "login")
def login_callback(call):
    user_id = call.from_user.id
    
    msg = header("🔐 SELECT ADMIN ACCOUNT")
    msg += "\nChoose your profile:\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for admin_id, info in ADMIN_LIST.items():
        tier_icon = "👑" if info["tier"] == "OWNER" else "⭐"
        btn_text = f"{tier_icon} {info['name']} - {info['email']}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"select_admin_{admin_id}"))
    
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu"))
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_admin_"))
def select_admin_callback(call):
    user_id = call.from_user.id
    admin_id = call.data.split("_")[-1]
    
    # Create session
    session = create_session(user_id, admin_id)
    if not session:
        bot.answer_callback_query(call.id, "❌ Admin not found!", show_alert=True)
        return
    
    # Login display
    msg = header("✅ LOGIN SUCCESSFUL")
    msg += f"""
👤 Admin: {session.admin_name}
📧 Email: {session.admin_email}
🎫 Tier: {session.tier}
⏰ Login: {session.login_time.strftime('%H:%M:%S')}

Ready to start quizzing? 🎯
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("▶️ Start Quiz", callback_data="start_quiz"),
        types.InlineKeyboardButton("📊 Status", callback_data="session_status")
    )
    markup.add(
        types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
    )
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "start_quiz")
def start_quiz_callback(call):
    user_id = call.from_user.id
    session = active_sessions.get(user_id)
    
    if not session:
        bot.answer_callback_query(call.id, "❌ Not logged in!", show_alert=True)
        return
    
    session.is_running = True
    
    # Start quiz message
    msg = header("📝 QUIZ SESSION STARTING")
    msg += f"""
👤 Admin: {session.admin_name}
📊 Session Quizzes: 3
❓ Questions: 5-8 per quiz
⏳ Duration: ~2 minutes

Starting first quiz... ⏳
"""
    
    sent_msg = bot.send_message(call.message.chat.id, msg)
    
    # Run quizzes
    run_quizzes(call.message.chat.id, session, sent_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "session_status")
def session_status_callback(call):
    user_id = call.from_user.id
    session = active_sessions.get(user_id)
    
    if not session:
        bot.answer_callback_query(call.id, "❌ No active session!", show_alert=True)
        return
    
    msg = header(f"📊 SESSION STATUS - {session.admin_name}")
    
    if session.total_questions == 0:
        msg += "\n📭 No quizzes completed yet!"
    else:
        accuracy = (session.correct_answers / session.total_questions) * 100
        msg += f"""
🎯 PERFORMANCE:
├─ Quizzes: {session.quizzes_completed}/3
├─ Questions: {session.total_questions}
├─ Correct: {session.correct_answers}
├─ Wrong: {session.total_questions - session.correct_answers}
└─ Accuracy: {accuracy:.1f}%
"""
    
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
    )
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "status")
def status_callback(call):
    msg = header("✅ BOT STATUS")
    msg += f"""
🤖 Status: ONLINE ✅
👥 Active Sessions: {len(active_sessions)}
📊 Version: 2.0

Server: Railway
Framework: Telebot
Display: Enhanced
"""
    
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
    )
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats_callback(call):
    user_id = call.from_user.id
    session = active_sessions.get(user_id)
    
    if not session or session.total_questions == 0:
        msg = "📭 No quiz statistics yet!\n\nStart a quiz session first."
    else:
        accuracy = (session.correct_answers / session.total_questions) * 100
        
        if accuracy >= 80:
            rating = "🌟 EXCELLENT"
        elif accuracy >= 60:
            rating = "👍 GOOD"
        else:
            rating = "📚 NEEDS IMPROVEMENT"
        
        msg = header(f"📈 STATISTICS - {session.admin_name}")
        msg += f"""
🎯 OVERALL STATS:
├─ Quizzes Completed: {session.quizzes_completed}
├─ Total Questions: {session.total_questions}
├─ Correct Answers: {session.correct_answers}
├─ Wrong Answers: {session.total_questions - session.correct_answers}
├─ Accuracy: {accuracy:.1f}%
└─ Rating: {rating}
"""
    
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
    )
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_menu")
def back_menu_callback(call):
    user_id = call.from_user.id
    
    msg = header("🎮 MAIN MENU")
    msg += "\nSelect an option:\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔐 Login", callback_data="login"),
        types.InlineKeyboardButton("❓ Help", callback_data="help")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Status", callback_data="status"),
        types.InlineKeyboardButton("📈 Stats", callback_data="stats")
    )
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

# ================================
# QUIZ EXECUTION
# ================================

def run_quizzes(chat_id, session, msg_id):
    """Run quiz session"""
    categories = ["General Knowledge", "Science", "History", "Technology", "Sports"]
    difficulties = ["Easy", "Medium", "Hard"]
    
    for quiz_num in range(1, 4):  # 3 quizzes
        if not session.is_running:
            break
        
        category = random.choice(categories)
        difficulty = random.choice(difficulties)
        num_questions = random.randint(5, 8)
        
        # Quiz start
        quiz_msg = header(f"📖 QUIZ #{quiz_num}")
        quiz_msg += f"""
Category: {category}
Difficulty: {difficulty}
Questions: {num_questions}

Starting...
"""
        
        bot.send_message(chat_id, quiz_msg)
        
        # Simulate questions
        quiz_correct = 0
        
        for q in range(1, num_questions + 1):
            is_correct = random.choice([True, True, True, False])  # 75% correct
            
            if is_correct:
                quiz_correct += 1
                session.correct_answers += 1
            
            session.total_questions += 1
            time.sleep(0.5)
        
        # Quiz completion display
        accuracy = (quiz_correct / num_questions) * 100
        
        result_msg = header(f"✅ QUIZ #{quiz_num} COMPLETED")
        result_msg += f"""
Category: {category}
Difficulty: {difficulty}
Correct: {quiz_correct}/{num_questions}
Accuracy: {accuracy:.1f}%

{progress_bar(quiz_correct, num_questions)}
"""
        
        if accuracy >= 80:
            result_msg += "\n🌟 EXCELLENT PERFORMANCE!"
        elif accuracy >= 60:
            result_msg += "\n👍 GOOD JOB!"
        else:
            result_msg += "\n📚 KEEP PRACTICING!"
        
        bot.send_message(chat_id, result_msg)
        
        session.quiz_history.append({
            "quiz": quiz_num,
            "category": category,
            "difficulty": difficulty,
            "correct": quiz_correct,
            "total": num_questions,
            "accuracy": accuracy
        })
        
        session.quizzes_completed += 1
        
        if quiz_num < 3:
            time.sleep(1)
    
    # Session complete
    if session.total_questions > 0:
        overall_accuracy = (session.correct_answers / session.total_questions) * 100
        
        final_msg = header("🎉 SESSION COMPLETE")
        final_msg += f"""
Admin: {session.admin_name}
Quizzes: {session.quizzes_completed}/3
Total Questions: {session.total_questions}
Correct: {session.correct_answers}
Overall Accuracy: {overall_accuracy:.1f}%

{progress_bar(session.correct_answers, session.total_questions)}

✅ All quizzes finished!
"""
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📈 View Stats", callback_data="stats"),
            types.InlineKeyboardButton("▶️ New Session", callback_data="login")
        )
        markup.add(
            types.InlineKeyboardButton("⬅️ Menu", callback_data="back_menu")
        )
        
        bot.send_message(chat_id, final_msg, reply_markup=markup)

# ================================
# STARTUP
# ================================

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("🚀 GOKU QUIZ SOLVER BOT v2.0")
    logger.info("📊 Multi-Admin Quiz System")
    logger.info("✅ Railway Ready")
    logger.info("="*60)
    
    keep_alive()
    time.sleep(1)
    
    logger.info("🤖 Bot Started!")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            logger.warning("⚠️ Timeout. Restarting...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"💥 Error: {e}")
            time.sleep(30)
