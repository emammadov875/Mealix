import logging
import asyncio
import base64
import os
import json
import re
from io import BytesIO

import httpx
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction, ParseMode

from config import TELEGRAM_TOKEN, GEMINI_API_KEY
from database import Database

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Gemini helpers ─────────────────────────────────────────────────────────────
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
)
HEADERS = {"Content-Type": "application/json"}


async def call_gemini(parts: list, timeout: int = 30) -> str:
    payload = {"contents": [{"parts": parts}]}
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(GEMINI_URL, headers=HEADERS, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def identify_ingredients_from_image(image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    parts = [
        {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": b64,
            }
        },
        {
            "text": (
                "You are a kitchen assistant. Look at this fridge/pantry image carefully. "
                "List ALL visible food ingredients you can identify. "
                "Return ONLY a comma-separated list of ingredients, nothing else. "
                "Example: eggs, milk, cheese, tomatoes, onions"
            )
        },
    ]
    return await call_gemini(parts)


async def generate_recipes(
    ingredients: str, dietary: str = "none", favorites: list = None
) -> str:
    fav_note = ""
    if favorites:
        fav_note = f"\nThe user previously saved these favourites: {', '.join(favorites[:5])}. Try to suggest something different."

    dietary_note = f"\nDietary preference: {dietary}." if dietary != "none" else ""

    parts = [
        {
            "text": f"""You are a world-class chef and nutritionist. 
The user has these ingredients: {ingredients}{dietary_note}{fav_note}

Generate exactly 3 creative recipes using ONLY (or mostly) these ingredients.
For each recipe provide:

**Recipe Name** 🍽️
⏱️ Time: X minutes
💪 Difficulty: Easy/Medium/Hard
🔥 Calories: ~XXX kcal

**Ingredients needed:**
- list them with amounts

**Quick Steps:**
1. Step one
2. Step two
3. Step three (keep it to 4-5 steps max)

**Pro Tip:** one sentence tip

---

Make the recipes practical, delicious and varied (e.g. one quick, one hearty, one creative).
Use emojis to make it visually appealing. Keep each recipe concise but complete."""
        }
    ]
    return await call_gemini(parts)


async def generate_meal_plan(ingredients: str, dietary: str = "none") -> str:
    dietary_note = f"Dietary preference: {dietary}." if dietary != "none" else ""
    parts = [
        {
            "text": f"""You are a professional nutritionist.
Available ingredients: {ingredients}
{dietary_note}

Create a 5-day meal plan (Mon–Fri) using these ingredients.
Format:
**Day** | Breakfast | Lunch | Dinner
Keep it short, practical and nutritious. Use emojis."""
        }
    ]
    return await call_gemini(parts)


# ── Database singleton ─────────────────────────────────────────────────────────
db = Database()

# ── Keyboards ──────────────────────────────────────────────────────────────────

DIETARY_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🥗 Vegetarian", callback_data="diet_vegetarian"),
            InlineKeyboardButton("🥩 No restriction", callback_data="diet_none"),
        ],
        [
            InlineKeyboardButton("🫙 Vegan", callback_data="diet_vegan"),
            InlineKeyboardButton("🌾 Gluten-Free", callback_data="diet_gluten_free"),
        ],
        [
            InlineKeyboardButton("🕌 Halal", callback_data="diet_halal"),
            InlineKeyboardButton("✡️ Kosher", callback_data="diet_kosher"),
        ],
    ]
)

AFTER_RECIPE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("⭐ Save Favourite", callback_data="save_fav"),
            InlineKeyboardButton("🔄 New Recipes", callback_data="new_recipes"),
        ],
        [
            InlineKeyboardButton("📅 5-Day Meal Plan", callback_data="meal_plan"),
            InlineKeyboardButton("❤️ My Favourites", callback_data="show_favs"),
        ],
    ]
)


# ── Command handlers ───────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.first_name)
    await update.message.reply_text(
        f"👋 Hey *{user.first_name}*\\! I'm your personal *Fridge Chef Bot* 🍽️\n\n"
        "Just send me:\n"
        "📝 *A list of ingredients* — e\\.g\\. `eggs, cheese, tomatoes`\n"
        "📸 *A photo of your fridge* — I'll identify ingredients automatically\\!\n\n"
        "I'll instantly generate *3 delicious recipes* you can make right now\\! 🚀",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Fridge Chef Bot — Help*\n\n"
        "📝 *Send ingredients as text:*\n`eggs, milk, spinach, garlic`\n\n"
        "📸 *Send a fridge photo* — auto\\-detects ingredients\\!\n\n"
        "⚙️ *Commands:*\n"
        "/start — Welcome message\n"
        "/diet — Set dietary preference\n"
        "/favourites — View saved recipes\n"
        "/clear — Clear saved ingredients\n"
        "/help — This message",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def diet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥗 Choose your dietary preference:",
        reply_markup=DIETARY_KEYBOARD,
    )


async def favourites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    favs = db.get_favourites(uid)
    if not favs:
        await update.message.reply_text(
            "❌ You have no saved favourites yet\\.\n\n"
            "After getting recipes, tap *⭐ Save Favourite* to save them\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    text = "❤️ *Your Saved Favourites:*\n\n"
    for i, f in enumerate(favs, 1):
        text += f"{i}\\. {escape_md(f)}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🗑️ Cleared! Send me new ingredients anytime.")


# ── Message handlers ───────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    # Basic validation — must look like ingredients
    if len(text) < 3 or len(text) > 500:
        await update.message.reply_text(
            "Please send a list of ingredients, e.g.:\n`eggs, cheese, tomatoes, onion`"
        )
        return

    context.user_data["ingredients"] = text
    context.user_data["last_message_id"] = update.message.message_id
    dietary = db.get_dietary(uid) or "none"

    await update.message.chat.send_action(ChatAction.TYPING)

    thinking_msg = await update.message.reply_text("🔍 Analysing your ingredients...")

    try:
        recipes = await generate_recipes(text, dietary, db.get_favourites(uid))
        await thinking_msg.delete()
        await update.message.reply_text(
            f"🍽️ *Here are your recipes!*\n\n{recipes}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=AFTER_RECIPE_KEYBOARD,
        )
        context.user_data["last_recipes"] = recipes
    except Exception as e:
        logger.error(f"Recipe generation error: {e}")
        await thinking_msg.edit_text(
            "❌ Oops! Something went wrong. Please try again in a moment."
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.chat.send_action(ChatAction.TYPING)

    thinking_msg = await update.message.reply_text(
        "📸 Scanning your fridge... This takes a few seconds!"
    )

    try:
        # Get highest resolution photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(file.file_path)
            image_bytes = resp.content

        await thinking_msg.edit_text("🧠 Identifying ingredients...")
        ingredients = await identify_ingredients_from_image(image_bytes)
        ingredients = ingredients.strip()

        if not ingredients or len(ingredients) < 3:
            await thinking_msg.edit_text(
                "😕 Couldn't identify ingredients clearly. "
                "Please try a clearer photo or type your ingredients manually."
            )
            return

        context.user_data["ingredients"] = ingredients
        dietary = db.get_dietary(uid) or "none"

        await thinking_msg.edit_text(
            f"✅ Found: *{ingredients}*\n\n🍳 Generating recipes...",
            parse_mode=ParseMode.MARKDOWN,
        )

        recipes = await generate_recipes(ingredients, dietary, db.get_favourites(uid))

        await thinking_msg.delete()
        await update.message.reply_text(
            f"🥦 *Detected ingredients:* {ingredients}\n\n"
            f"🍽️ *Here are your recipes!*\n\n{recipes}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=AFTER_RECIPE_KEYBOARD,
        )
        context.user_data["last_recipes"] = recipes

    except Exception as e:
        logger.error(f"Photo handler error: {e}")
        await thinking_msg.edit_text(
            "❌ Couldn't process the image. Please try again or type ingredients manually."
        )


# ── Callback query handlers ────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    # ── Dietary selection ──
    if data.startswith("diet_"):
        pref = data.replace("diet_", "")
        db.set_dietary(uid, pref)
        label = pref.replace("_", " ").title()
        await query.edit_message_text(
            f"✅ Dietary preference set to *{label}*\\!\n\n"
            "Now send me your ingredients and I'll filter recipes accordingly 🍽️",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # ── Save favourite ──
    if data == "save_fav":
        recipes_text = context.user_data.get("last_recipes", "")
        if not recipes_text:
            await query.answer("No recipes to save!", show_alert=True)
            return
        # Extract first recipe name from text
        lines = recipes_text.strip().split("\n")
        recipe_name = "Unknown Recipe"
        for line in lines:
            clean = re.sub(r"[*_`#🍽️]", "", line).strip()
            if len(clean) > 3:
                recipe_name = clean[:60]
                break
        db.add_favourite(uid, recipe_name)
        await query.answer(f"⭐ Saved: {recipe_name[:30]}...", show_alert=False)
        return

    # ── New recipes ──
    if data == "new_recipes":
        ingredients = context.user_data.get("ingredients")
        if not ingredients:
            await query.edit_message_text(
                "Please send me your ingredients first! 🥦"
            )
            return
        dietary = db.get_dietary(uid) or "none"
        await query.edit_message_text("🔄 Generating new recipe ideas...")
        try:
            recipes = await generate_recipes(ingredients, dietary, db.get_favourites(uid))
            context.user_data["last_recipes"] = recipes
            await query.edit_message_text(
                f"🍽️ *Fresh recipes for you!*\n\n{recipes}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=AFTER_RECIPE_KEYBOARD,
            )
        except Exception as e:
            logger.error(e)
            await query.edit_message_text("❌ Failed to generate. Try again!")
        return

    # ── Meal plan ──
    if data == "meal_plan":
        ingredients = context.user_data.get("ingredients")
        if not ingredients:
            await query.edit_message_text("Please send ingredients first! 🥦")
            return
        dietary = db.get_dietary(uid) or "none"
        await query.edit_message_text("📅 Building your 5-day meal plan...")
        try:
            plan = await generate_meal_plan(ingredients, dietary)
            await query.edit_message_text(
                f"📅 *Your 5-Day Meal Plan*\n\n{plan}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back to Recipes", callback_data="new_recipes")]]
                ),
            )
        except Exception as e:
            logger.error(e)
            await query.edit_message_text("❌ Failed to generate plan. Try again!")
        return

    # ── Show favourites ──
    if data == "show_favs":
        favs = db.get_favourites(uid)
        if not favs:
            await query.answer("No favourites saved yet!", show_alert=True)
            return
        text = "❤️ *Your Favourites:*\n\n"
        for i, f in enumerate(favs, 1):
            text += f"{i}. {f}\n"
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="new_recipes")]]
            ),
        )
        return


# ── Utility ────────────────────────────────────────────────────────────────────

def escape_md(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("diet", diet_command))
    app.add_handler(CommandHandler("favourites", favourites_command))
    app.add_handler(CommandHandler("clear", clear_command))

    # Messages
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("🚀 Fridge Chef Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
