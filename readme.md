# 🤖 Telegram Cleaner Agent

An AI-assisted Telegram channel management system built with **Python, Telethon, SQLite, and Google Gemini**. It monitors channel memberships, tracks pending join requests, sends reminders, and supports channel cleanup through a Telegram bot.

## ✨ Features

- 📡 Monitor Telegram channel memberships.
- 🔔 Receive notifications about newly detected public channels.
- ⏰ Get reminders after eight days of membership.
- 🚪 Leave channels through the Telegram bot.
- 🟡 Track pending private-channel join requests.
- 🤖 Use Google Gemini for AI-assisted decisions.
- 📊 Manage pending, active, and left channels through an interactive dashboard.
- 🗄️ Store channel records locally using SQLite.

## 🛠️ Tech Stack

- Python
- Telethon
- Google Gemini API
- SQLite
- Telegram Bot

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

Obtain your credentials from:

- Telegram API: https://my.telegram.org/
- Telegram bot: https://t.me/BotFather
- Gemini API: https://aistudio.google.com/

Create a `.env` file using the variable names required by the project's `config.py`. Add your Telegram API credentials, bot token, and Gemini API key.

**Never commit your credentials or Telegram session files to GitHub.**

### 5. Run the application

```bash
python main.py
```

Follow any Telegram authentication prompts. Then open your bot in Telegram and send `/start` to access the dashboard and register for notifications.

Keep the application running for monitoring and reminders to work.

## 🧠 How It Works

The system follows an agentic workflow:

**Observe → Decide → Execute → Verify**

Python monitors Telegram and manages database records, while Gemini assists with supported decisions. Python tools perform the actual Telegram operations.

## 🔒 Security

- Keep API credentials and bot tokens private.
- Never upload `.env`, session files, or your local database.
- Review cleanup actions carefully.
- Use your own Telegram account and credentials.

## 🔮 Future Improvements

- Persistent task planning and recovery.
- Agent decision logs and performance metrics.
- Improved error handling and automated tests.
- Enhanced dashboard and user preferences.

## ⚖️ Disclaimer

This project is intended for educational and research purposes. Users are responsible for protecting their accounts and complying with Telegram's terms.

## 👩‍💻 Author

**ANGEL SEBASTIAN**

GitHub: https://github.com/AngelSebastIAN026
