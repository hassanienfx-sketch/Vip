import requests
import json
import os
from datetime import datetime, timedelta, timezone
import time

TELEGRAM_TOKEN = "ضع_توكن_البوت_الجديد_هنا"
ADMIN_ID = "8553520344"
DB_FILE = "subscribers.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def send_message(chat_id, text):
    try:
        requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print("خطأ ارسال: " + str(e))

def kick_user(channel_id, user_id):
    try:
        requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/banChatMember",
            data={"chat_id": channel_id, "user_id": user_id},
            timeout=10
        )
        time.sleep(1)
        requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/unbanChatMember",
            data={"chat_id": channel_id, "user_id": user_id},
            timeout=10
        )
    except Exception as e:
        print("خطأ طرد: " + str(e))

def handle_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/getUpdates",
            params=params, timeout=35
        )
        return r.json()
    except:
        return {"ok": False, "result": []}

def process_message(message, db):
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "")
    user_id = str(message.get("from", {}).get("id", ""))

    if user_id != ADMIN_ID:
        return

    if text.startswith("/add"):
        parts = text.split()
        if len(parts) < 3:
            send_message(ADMIN_ID,
                "⚠️ الصيغة الصحيحة:\n/add USER_ID CHANNEL_ID\n\nمثال:\n/add 123456789 -1001234567890")
            return

        target_user = parts[1]
        channel_id = parts[2]
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=30)

        db[target_user] = {
            "channel_id": channel_id,
            "start_date": now.strftime("%Y-%m-%d %H:%M"),
            "expire_date": expire.strftime("%Y-%m-%d %H:%M"),
            "notified_3days": False,
            "notified_1day": False,
            "active": True
        }
        save_db(db)

        send_message(ADMIN_ID,
            f"✅ <b>تم تفعيل الاشتراك</b>\n"
            f"👤 المستخدم: <code>{target_user}</code>\n"
            f"📅 البداية: {now.strftime('%Y-%m-%d')}\n"
            f"⏰ الانتهاء: {expire.strftime('%Y-%m-%d')}\n"
            f"📆 المدة: 30 يوم")

        send_message(target_user,
            f"🎉 <b>مرحباً! تم تفعيل اشتراكك</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ اشتراكك فعال لمدة <b>30 يوم</b>\n"
            f"📅 ينتهي بتاريخ: <b>{expire.strftime('%Y-%m-%d')}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"© <i>#مستر_سكالب</i>")

    elif text.startswith("/remove"):
        parts = text.split()
        if len(parts) < 2:
            send_message(ADMIN_ID, "⚠️ الصيغة: /remove USER_ID")
            return

        target_user = parts[1]
        if target_user in db:
            channel_id = db[target_user]["channel_id"]
            db[target_user]["active"] = False
            save_db(db)
            kick_user(channel_id, target_user)
            send_message(ADMIN_ID, f"✅ تم إلغاء اشتراك {target_user} وطرده من القناة")
            send_message(target_user,
                "❌ <b>تم إلغاء اشتراكك</b>\n"
                "للتجديد تواصل مع المشرف\n"
                "© <i>#مستر_سكالب</i>")
        else:
            send_message(ADMIN_ID, "⚠️ المستخدم غير موجود في القاعدة")

    elif text.startswith("/renew"):
        parts = text.split()
        if len(parts) < 2:
            send_message(ADMIN_ID, "⚠️ الصيغة: /renew USER_ID")
            return

        target_user = parts[1]
        if target_user in db:
            now = datetime.now(timezone.utc)
            expire = now + timedelta(days=30)
            db[target_user]["expire_date"] = expire.strftime("%Y-%m-%d %H:%M")
            db[target_user]["notified_3days"] = False
            db[target_user]["notified_1day"] = False
            db[target_user]["active"] = True
            save_db(db)

            send_message(ADMIN_ID,
                f"✅ تم تجديد اشتراك {target_user}\n"
                f"⏰ الانتهاء الجديد: {expire.strftime('%Y-%m-%d')}")

            send_message(target_user,
                f"🎉 <b>تم تجديد اشتراكك!</b>\n"
                f"⏰ ينتهي بتاريخ: <b>{expire.strftime('%Y-%m-%d')}</b>\n"
                f"© <i>#مستر_سكالب</i>")
        else:
            send_message(ADMIN_ID, "⚠️ المستخدم غير موجود")

    elif text == "/list":
        if not db:
            send_message(ADMIN_ID, "📭 لا يوجد مشتركين حالياً")
            return

        msg = "📋 <b>قائمة المشتركين:</b>\n━━━━━━━━━━━━━━━\n"
        now = datetime.now(timezone.utc)
        for uid, info in db.items():
            expire = datetime.strptime(info["expire_date"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            days_left = (expire - now).days
            status = "✅ فعال" if info["active"] and days_left > 0 else "❌ منتهي"
            msg += f"👤 <code>{uid}</code> | {status} | متبقي {days_left} يوم\n"

        send_message(ADMIN_ID, msg)

    elif text == "/help":
        send_message(ADMIN_ID,
            "🤖 <b>اوامر البوت:</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "/add USER_ID CHANNEL_ID\n➡️ تفعيل مشترك جديد\n\n"
            "/remove USER_ID\n➡️ إلغاء اشتراك وطرد\n\n"
            "/renew USER_ID\n➡️ تجديد 30 يوم\n\n"
            "/list\n➡️ عرض كل المشتركين\n\n"
            "━━━━━━━━━━━━━━━\n"
            "© <i>#مستر_سكالب</i>")

def check_expiry(db):
    now = datetime.now(timezone.utc)
    changed = False

    for user_id, info in db.items():
        if not info.get("active", False):
            continue

        expire = datetime.strptime(info["expire_date"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        days_left = (expire - now).days

        if days_left <= 3 and not info.get("notified_3days", False):
            send_message(user_id,
                f"⚠️ <b>تنبيه: اشتراكك ينتهي قريباً</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"⏰ متبقي <b>{days_left} أيام</b> فقط\n"
                f"📅 تاريخ الانتهاء: {expire.strftime('%Y-%m-%d')}\n"
                f"💬 تواصل مع المشرف للتجديد\n"
                f"━━━━━━━━━━━━━━━\n"
                f"© <i>#مستر_سكالب</i>")
            db[user_id]["notified_3days"] = True
            changed = True

        if days_left <= 1 and not info.get("notified_1day", False):
            send_message(user_id,
                f"🚨 <b>آخر تذكير! اشتراكك ينتهي غداً</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📅 ينتهي: {expire.strftime('%Y-%m-%d')}\n"
                f"⚡ جدد الآن قبل فوات الأوان\n"
                f"━━━━━━━━━━━━━━━\n"
                f"© <i>#مستر_سكالب</i>")
            db[user_id]["notified_1day"] = True
            changed = True

        if days_left <= 0 and info.get("active", False):
            db[user_id]["active"] = False
            kick_user(info["channel_id"], user_id)
            send_message(user_id,
                "❌ <b>انتهى اشتراكك</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "تم إزالتك من القناة\n"
                "💬 تواصل مع المشرف للتجديد\n"
                "━━━━━━━━━━━━━━━\n"
                "© <i>#مستر_سكالب</i>")
            send_message(ADMIN_ID,
                f"🔔 انتهى اشتراك المستخدم: <code>{user_id}</code>\n"
                f"تم طرده تلقائياً من القناة")
            changed = True

    if changed:
        save_db(db)

print("✅ بوت الاشتراكات يعمل...")
send_message(ADMIN_ID,
    "✅ <b>بوت الاشتراكات شغال</b>\n"
    "اكتب /help لعرض الاوامر")

offset = None
last_check = time.time()

while True:
    try:
        updates = handle_updates(offset)
        if updates.get("ok"):
            for update in updates["result"]:
                offset = update["update_id"] + 1
                if "message" in update:
                    db = load_db()
                    process_message(update["message"], db)

        if time.time() - last_check > 3600:
            db = load_db()
            check_expiry(db)
            last_check = time.time()

    except Exception as e:
        print("❌ خطأ: " + str(e))
        time.sleep(5)
