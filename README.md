# 🍽️ Fridge Chef Bot — Telegram Bot

A smart Telegram bot that generates recipes from your ingredients — either typed or from a photo of your fridge!

---

## ✨ Features

- 📝 **Text input** — type ingredients, get 3 recipes instantly
- 📸 **Photo input** — snap your fridge, AI identifies ingredients automatically
- 🥗 **Dietary filters** — Vegetarian, Vegan, Halal, Kosher, Gluten-Free
- 📅 **5-Day Meal Plan** — full week planned from your ingredients
- ⭐ **Save Favourites** — bookmark recipes you love
- ⚡ **Fast** — responses in under 5 seconds

---

## 🚀 Setup (5 minutes)

### Step 1 — Get your Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. `My Fridge Chef`)
4. Choose a username ending in `bot` (e.g. `myfridgechef_bot`)
5. Copy the token BotFather gives you

### Step 2 — Get your Free Gemini API Key

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **Create API Key**
4. Copy the key

### Step 3 — Configure the bot

```bash
# Clone or download this folder, then:
cd fridge_bot

# Copy the example env file
cp .env.example .env

# Open .env and fill in your keys:
# TELEGRAM_TOKEN=your_token_here
# GEMINI_API_KEY=your_key_here
```

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5 — Run the bot

```bash
python bot.py
```

That's it! 🎉 Open Telegram and start chatting with your bot.

---

## 💬 How to Use

| Action | What to do |
|--------|-----------|
| Get recipes from text | Send: `eggs, cheese, tomatoes, garlic` |
| Get recipes from photo | Send a photo of your fridge |
| Set dietary preference | `/diet` |
| View saved favourites | `/favourites` |
| Clear session | `/clear` |
| Help | `/help` |

---

## 💰 Cost

| Service | Cost |
|---------|------|
| Telegram Bot API | ✅ Always Free |
| Google Gemini API | ✅ Free (1,500 requests/day) |
| SQLite database | ✅ Always Free |
| Running locally | ✅ Free |
| Hosting on Render.com | ✅ Free tier available |

**Total cost to run: $0** 🎉

---

## 🌐 Deploy Free on Render.com (Optional)

1. Push this folder to a GitHub repo
2. Go to [render.com](https://render.com) and create a free account
3. New → Web Service → connect your GitHub repo
4. Set environment variables (TELEGRAM_TOKEN, GEMINI_API_KEY)
5. Build command: `pip install -r requirements.txt`
6. Start command: `python bot.py`
7. Deploy! Your bot runs 24/7 for free.

---

## 📁 File Structure

```
fridge_bot/
├── bot.py           # Main bot logic
├── database.py      # SQLite database handler
├── config.py        # Configuration loader
├── requirements.txt # Python dependencies
├── .env.example     # Environment template
└── README.md        # This file
```
