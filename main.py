import requests  
import json  
import os  
from datetime import datetime, timedelta, timezone  
import time  

TELEGRAM_TOKEN = "8730145684:AAH29y9Y3ERZ3XSnr0LbaTehYB88cBrPUs4"  
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

def send_message(chat_id, text, reply_markup=None):  
    try:  
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        requests.post(  
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",  
            data=data,  
            timeout=10  
        )  
    except Exception as e:  
        print("خطأ ارسال: " + str(e))  

def send_message_to_channel(channel_id, text):
    """ارسال رسالة للقناة"""
    try:  
        requests.post(  
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",  
            data={"chat_id": channel_id, "text": text, "parse_mode": "HTML"},  
            timeout=10  
        )  
    except Exception as e:  
        print("خطأ ارسال للقناة: " + str(e))

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

def get_user_info(user_id):
    """الحصول على معلومات المستخدم"""
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getChat",
            params={"chat_id": user_id},
            timeout=10
        )
        if r.json().get("ok"):
            user = r.json()["result"]
            name = user.get("first_name", "")
            if user.get("last_name"):
                name += " " + user.get("last_name")
            username = user.get("username", "")
            return name, username
    except:
        pass
    return "غير معروف", ""

def activate_subscription(target_user, channel_id, days, db):
    """تفعيل الاشتراك"""
    now = datetime.now(timezone.utc)  
    expire = now + timedelta(days=days)  

    # تحديد نوع الاشتراك
    if days == 15:
        sub_type = "تجريبي"
        emoji = "🆓"
    elif days == 30:
        sub_type = "شهري"
        emoji = "📅"
    elif days == 90:
        sub_type = "ربع سنوي"
        emoji = "💎"
    else:
        sub_type = "مخصص"
        emoji = "⭐"

    db[target_user] = {  
        "channel_id": channel_id,  
        "start_date": now.strftime("%Y-%m-%d %H:%M"),  
        "expire_date": expire.strftime("%Y-%m-%d %H:%M"),
        "subscription_days": days,
        "subscription_type": sub_type,
        "notified_3days": False,  
        "notified_1day": False,  
        "active": True  
    }  
    save_db(db)

    # الحصول على معلومات المستخدم
    user_name, username = get_user_info(target_user)
    username_text = f"@{username}" if username else "لا يوجد"

    # رسالة للأدمن
    send_message(ADMIN_ID,  
        f"✅ <b>تم تفعيل الاشتراك بنجاح</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{emoji} نوع الاشتراك: <b>{sub_type}</b>\n"
        f"👤 الاسم: <b>{user_name}</b>\n"
        f"🆔 المعرف: {username_text}\n"
        f"🔢 الآيدي: <code>{target_user}</code>\n"  
        f"📅 البداية: {now.strftime('%Y-%m-%d')}\n"  
        f"⏰ الانتهاء: {expire.strftime('%Y-%m-%d')}\n"  
        f"📆 المدة: {days} يوم\n"
        f"━━━━━━━━━━━━━━━")  

    # رسالة للمستخدم في الخاص
    send_message(target_user,  
        f"🎉 <b>مرحباً {user_name}!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{emoji} <b>تم تفعيل اشتراكك {sub_type}</b>\n\n"
        f"✅ الاشتراك فعال لمدة <b>{days} يوم</b>\n"  
        f"📅 تاريخ البداية: <b>{now.strftime('%Y-%m-%d')}</b>\n"
        f"⏰ تاريخ الانتهاء: <b>{expire.strftime('%Y-%m-%d')}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔔 سيتم تذكيرك قبل انتهاء الاشتراك\n"
        f"💬 للدعم تواصل مع المشرف\n\n"
        f"© <i>#مستر_سكالب</i>")  

    # رسالة في القناة
    send_message_to_channel(channel_id,
        f"🎊 <b>مشترك جديد!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👋 مرحباً بـ <b>{user_name}</b>\n"
        f"{emoji} اشتراك <b>{sub_type}</b> - {days} يوم\n"
        f"━━━━━━━━━━━━━━━\n"
        f"© <i>#مستر_سكالب</i>")

def process_callback(callback_query, db):
    """معالجة ضغط الأزرار"""
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    
    if chat_id != ADMIN_ID:
        return

    # استخراج البيانات من callback_data
    # Format: add_USERID_CHANNELID_DAYS
    if data.startswith("add_"):
        parts = data.split("_")
        if len(parts) == 4:
            target_user = parts[1]
            channel_id = parts[2]
            days = int(parts[3])
            
            activate_subscription(target_user, channel_id, days, db)
            
            # تحديث الرسالة
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                    data={
                        "chat_id": chat_id,
                        "message_id": message["message_id"],
                        "text": f"✅ تم تفعيل الاشتراك لـ {days} يوم",
                        "parse_mode": "HTML"
                    },
                    timeout=10
                )
            except:
                pass

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
                "⚠️ <b>الصيغة الصحيحة:</b>\n"
                "/add USER_ID CHANNEL_ID\n\n"
                "<b>مثال:</b>\n"
                "/add 123456789 -1001234567890")  
            return  

        target_user = parts[1]  
        channel_id = parts[2]

        # إنشاء أزرار اختيار المدة
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🆓 15 يوم (تجريبي)", "callback_data": f"add_{target_user}_{channel_id}_15"}
                ],
                [
                    {"text": "📅 30 يوم (شهري)", "callback_data": f"add_{target_user}_{channel_id}_30"}
                ],
                [
                    {"text": "💎 90 يوم (ربع سنوي)", "callback_data": f"add_{target_user}_{channel_id}_90"}
                ]
            ]
        }

        send_message(ADMIN_ID,
            f"🎯 <b>اختر مدة الاشتراك:</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 المستخدم: <code>{target_user}</code>\n"
            f"📢 القناة: <code>{channel_id}</code>",
            reply_markup=keyboard)

    elif text.startswith("/remove"):  
        parts = text.split()  
        if len(parts) < 2:  
            send_message(ADMIN_ID, "⚠️ الصيغة: /remove USER_ID")  
            return  

        target_user = parts[1]  
        if target_user in db:
            user_name, username = get_user_info(target_user)
            channel_id = db[target_user]["channel_id"]  
            db[target_user]["active"] = False  
            save_db(db)  
            kick_user(channel_id, target_user)  
            send_message(ADMIN_ID, 
                f"✅ <b>تم إلغاء الاشتراك</b>\n"
                f"👤 {user_name}\n"
                f"🔢 <code>{target_user}</code>\n"
                f"🚪 تم طرده من القناة")  
            send_message(target_user,  
                f"❌ <b>تم إلغاء اشتراكك</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"للتجديد تواصل مع المشرف\n\n"
                f"© <i>#مستر_سكالب</i>")  
        else:  
            send_message(ADMIN_ID, "⚠️ المستخدم غير موجود في القاعدة")  

    elif text.startswith("/renew"):  
        parts = text.split()  
        if len(parts) < 2:  
            send_message(ADMIN_ID, "⚠️ الصيغة: /renew USER_ID")  
            return  

        target_user = parts[1]  
        if target_user in db:
            # إنشاء أزرار اختيار مدة التجديد
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🆓 15 يوم", "callback_data": f"renew_{target_user}_15"}
                    ],
                    [
                        {"text": "📅 30 يوم", "callback_data": f"renew_{target_user}_30"}
                    ],
                    [
                        {"text": "💎 90 يوم", "callback_data": f"renew_{target_user}_90"}
                    ]
                ]
            }

            user_name, username = get_user_info(target_user)
            send_message(ADMIN_ID,
                f"🔄 <b>اختر مدة التجديد:</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 {user_name}\n"
                f"🔢 <code>{target_user}</code>",
                reply_markup=keyboard)
        else:  
            send_message(ADMIN_ID, "⚠️ المستخدم غير موجود")  

    elif text == "/list":  
        if not db:  
            send_message(ADMIN_ID, "📭 لا يوجد مشتركين حالياً")  
            return  

        msg = "📋 <b>قائمة المشتركين:</b>\n━━━━━━━━━━━━━━━\n"  
        now = datetime.now(timezone.utc)
        active_count = 0
        expired_count = 0
        
        for uid, info in db.items():  
            expire = datetime.strptime(info["expire_date"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)  
            days_left = (expire - now).days
            sub_type = info.get("subscription_type", "عادي")
            
            if info["active"] and days_left > 0:
                status = "✅ فعال"
                active_count += 1
            else:
                status = "❌ منتهي"
                expired_count += 1
                
            user_name, username = get_user_info(uid)
            msg += f"\n👤 {user_name}\n"
            msg += f"🔢 <code>{uid}</code>\n"
            msg += f"📊 {status} | {sub_type} | متبقي {days_left} يوم\n"
            msg += f"━━━━━━━━━━━━━━━\n"

        msg += f"\n📊 <b>الإحصائيات:</b>\n"
        msg += f"✅ فعال: {active_count}\n"
        msg += f"❌ منتهي: {expired_count}\n"
        msg += f"📈 المجموع: {len(db)}"

        send_message(ADMIN_ID, msg)  

    elif text == "/help":  
        send_message(ADMIN_ID,  
            "🤖 <b>أوامر البوت:</b>\n"  
            "━━━━━━━━━━━━━━━\n\n"
            "➕ <b>/add USER_ID CHANNEL_ID</b>\n"
            "   تفعيل مشترك جديد مع خيارات المدة\n\n"
            "➖ <b>/remove USER_ID</b>\n"
            "   إلغاء اشتراك وطرد من القناة\n\n"
            "🔄 <b>/renew USER_ID</b>\n"
            "   تجديد الاشتراك مع خيارات المدة\n\n"
            "📋 <b>/list</b>\n"
            "   عرض كل المشتركين مع التفاصيل\n\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 <b>مدد الاشتراك المتاحة:</b>\n"
            "🆓 15 يوم - تجريبي\n"
            "📅 30 يوم - شهري\n"
            "💎 90 يوم - ربع سنوي\n\n"
            "© <i>#مستر_سكالب</i>")

# معالجة التجديد عبر الأزرار
def process_renew_callback(callback_query, db):
    """معالجة تجديد الاشتراك"""
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    
    if chat_id != ADMIN_ID:
        return

    if data.startswith("renew_"):
        parts = data.split("_")
        if len(parts) == 3:
            target_user = parts[1]
            days = int(parts[2])
            
            if target_user in db:
                now = datetime.now(timezone.utc)  
                expire = now + timedelta(days=days)
                
                # تحديد نوع الاشتراك
                if days == 15:
                    sub_type = "تجريبي"
                    emoji = "🆓"
                elif days == 30:
                    sub_type = "شهري"
                    emoji = "📅"
                elif days == 90:
                    sub_type = "ربع سنوي"
                    emoji = "💎"
                else:
                    sub_type = "مخصص"
                    emoji = "⭐"
                
                db[target_user]["expire_date"] = expire.strftime("%Y-%m-%d %H:%M")  
                db[target_user]["notified_3days"] = False  
                db[target_user]["notified_1day"] = False  
                db[target_user]["active"] = True
                db[target_user]["subscription_days"] = days
                db[target_user]["subscription_type"] = sub_type
                save_db(db)

                user_name, username = get_user_info(target_user)

                send_message(ADMIN_ID,  
                    f"✅ <b>تم تجديد الاشتراك</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{emoji} نوع الاشتراك: <b>{sub_type}</b>\n"
                    f"👤 {user_name}\n"
                    f"🔢 <code>{target_user}</code>\n"
                    f"⏰ الانتهاء الجديد: {expire.strftime('%Y-%m-%d')}\n"
                    f"📆 المدة: {days} يوم")  

                send_message(target_user,  
                    f"🎉 <b>تم تجديد اشتراكك!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{emoji} <b>اشتراك {sub_type}</b>\n"
                    f"⏰ ينتهي بتاريخ: <b>{expire.strftime('%Y-%m-%d')}</b>\n"
                    f"📆 المدة: <b>{days} يوم</b>\n\n"
                    f"© <i>#مستر_سكالب</i>")
                
                # تحديث الرسالة
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                        data={
                            "chat_id": chat_id,
                            "message_id": message["message_id"],
                            "text": f"✅ تم تجديد الاشتراك لـ {days} يوم",
                            "parse_mode": "HTML"
                        },
                        timeout=10
                    )
                except:
                    pass

def check_expiry(db):  
    now = datetime.now(timezone.utc)  
    changed = False  

    for user_id, info in db.items():  
        if not info.get("active", False):  
            continue  

        expire = datetime.strptime(info["expire_date"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)  
        days_left = (expire - now).days
        sub_type = info.get("subscription_type", "عادي")

        if days_left <= 3 and not info.get("notified_3days", False):  
            send_message(user_id,  
                f"⚠️ <b>تنبيه: اشتراكك ينتهي قريباً</b>\n"  
                f"━━━━━━━━━━━━━━━\n"
                f"📊 نوع الاشتراك: <b>{sub_type}</b>\n"
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
                f"📊 نوع الاشتراك: <b>{sub_type}</b>\n"
                f"📅 ينتهي: {expire.strftime('%Y-%m-%d')}\n"  
                f"⚡ جدد الآن قبل فوات الأوان\n"  
                f"━━━━━━━━━━━━━━━\n"  
                f"© <i>#مستر_سكالب</i>")  
            db[user_id]["notified_1day"] = True  
            changed = True  

        if days_left <= 0 and info.get("active", False):  
            db[user_id]["active"] = False  
            kick_user(info["channel_id"], user_id)
            
            user_name, username = get_user_info(user_id)
            
            send_message(user_id,  
                "❌ <b>انتهى اشتراكك</b>\n"  
                "━━━━━━━━━━━━━━━\n"  
                "تم إزالتك من القناة\n"  
                "💬 تواصل مع المشرف للتجديد\n"  
                "━━━━━━━━━━━━━━━\n"  
                "© <i>#مستر_سكالب</i>")  
            send_message(ADMIN_ID,  
                f"🔔 <b>انتهى اشتراك:</b>\n"
                f"👤 {user_name}\n"
                f"🔢 <code>{user_id}</code>\n"
                f"🚪 تم طرده تلقائياً من القناة")  
            changed = True  

    if changed:  
        save_db(db)  

print("✅ بوت الاشتراكات يعمل...")  
send_message(ADMIN_ID,  
    "✅ <b>بوت الاشتراكات شغال</b>\n"
    "━━━━━━━━━━━━━━━\n"
    "اكتب /help لعرض الأوامر\n\n"
    "© <i>#مستر_سكالب</i>")  

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
                elif "callback_query" in update:
                    db = load_db()
                    callback_data = update["callback_query"].get("data", "")
                    if callback_data.startswith("add_"):
                        process_callback(update["callback_query"], db)
                    elif callback_data.startswith("renew_"):
                        process_renew_callback(update["callback_query"], db)

        if time.time() - last_check > 3600:  
            db = load_db()  
            check_expiry(db)  
            last_check = time.time()  

    except Exception as e:  
        print("❌ خطأ: " + str(e))  
        time.sleep(5)        parts = text.split()
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
