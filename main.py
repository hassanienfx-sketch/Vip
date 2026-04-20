import requests
import json
import os
from datetime import datetime, timedelta, timezone
import time

TELEGRAM_TOKEN = "8260071605:AAEoqDEUkXxmIlVBm8h327kuW1WvXpAZZtI"

# ✅ قائمة المديرين (يمكن إضافة أكثر من مدير)
ADMIN_IDS = ["8553520344", "7903475836"]

DB_FILE = "subscribers.json"


# ─────────────────────────────────────────
#  دوال مساعدة
# ─────────────────────────────────────────

def is_admin(user_id):
    """التحقق إذا كان المستخدم مديراً"""
    return str(user_id) in ADMIN_IDS


def send_to_all_admins(text, reply_markup=None):
    """إرسال رسالة لجميع المديرين"""
    for admin_id in ADMIN_IDS:
        send_message(admin_id, text, reply_markup)


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


def approve_join_request(channel_id, user_id):
    """الموافقة على طلب انضمام المستخدم للقناة"""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/approveChatJoinRequest",
            data={"chat_id": channel_id, "user_id": user_id},
            timeout=10
        )
        return r.json().get("ok", False)
    except Exception as e:
        print("خطأ قبول الطلب: " + str(e))
        return False


def decline_join_request(channel_id, user_id):
    """رفض طلب انضمام المستخدم للقناة"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/declineChatJoinRequest",
            data={"chat_id": channel_id, "user_id": user_id},
            timeout=10
        )
    except Exception as e:
        print("خطأ رفض الطلب: " + str(e))


def process_join_request(join_request, db):
    """معالجة طلبات الانضمام للقناة تلقائياً"""
    user = join_request.get("from", {})
    user_id = str(user.get("id", ""))
    channel_id = str(join_request.get("chat", {}).get("id", ""))

    # جلب اسم المستخدم
    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    user_name = (first_name + " " + last_name).strip() or "بدون اسم"
    username = user.get("username", "")
    username_text = f"@{username}" if username else "لا يوجد معرف"

    # فحص هل المستخدم لديه اشتراك نشط في هذه القناة
    now = datetime.now(timezone.utc)
    subscriber = db.get(user_id)

    if subscriber and subscriber.get("active") and str(subscriber.get("channel_id")) == channel_id:
        expire = datetime.strptime(subscriber["expire_date"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        if expire > now:
            # ✅ لديه اشتراك نشط — قبول تلقائي
            success = approve_join_request(channel_id, user_id)
            if success:
                sub_type = subscriber.get("subscription_type", "عادي")
                days_left = (expire - now).days

                # رسالة للمستخدم عند القبول
                send_message(user_id,
                    f"✅ <b>تم قبول طلبك في القناة!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 مرحباً <b>{user_name}</b>\n"
                    f"📊 نوع اشتراكك: <b>{sub_type}</b>\n"
                    f"⏰ ينتهي بتاريخ: <b>{expire.strftime('%Y-%m-%d')}</b>\n"
                    f"📆 متبقي: <b>{days_left} يوم</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"© <i>#مستر_سكالب</i>",
                    reply_markup=get_admin_buttons()
                )

                # إشعار للمديرين
                send_to_all_admins(
                    f"🔔 <b>قبول تلقائي لطلب انضمام</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 الاسم: <b>{user_name}</b>\n"
                    f"🆔 المعرف: {username_text}\n"
                    f"🔢 الآيدي: <code>{user_id}</code>\n"
                    f"📢 القناة: <code>{channel_id}</code>\n"
                    f"📊 الاشتراك: {sub_type} | متبقي {days_left} يوم\n"
                    f"━━━━━━━━━━━━━━━"
                )
            return

    # ❌ لا يوجد اشتراك نشط — رفض ومعالجة
    # نرفض الطلب ونخبر المديرين
    decline_join_request(channel_id, user_id)
    send_to_all_admins(
        f"⛔ <b>طلب انضمام مرفوض (لا اشتراك)</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 الاسم: <b>{user_name}</b>\n"
        f"🆔 المعرف: {username_text}\n"
        f"🔢 الآيدي: <code>{user_id}</code>\n"
        f"📢 القناة: <code>{channel_id}</code>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💡 لتفعيله استخدم:\n"
        f"<code>/add {user_id} {channel_id}</code>"
    )


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


def get_admin_buttons():
    """إرجاع أزرار التواصل مع كل مشرف بشكل منفصل"""
    buttons = []
    for i, admin_id in enumerate(ADMIN_IDS):
        buttons.append([{
            "text": f"👨‍💼 تواصل مع المشرف {i + 1}",
            "url": f"tg://user?id={admin_id}"
        }])
    return {"inline_keyboard": buttons}


def create_invite_link(channel_id, user_id):
    """إنشاء رابط دعوة خاص للمستخدم (استخدام واحد فقط)"""
    try:
        expire_date = int(time.time()) + 86400  # ينتهي بعد 24 ساعة
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/createChatInviteLink",
            data={
                "chat_id": channel_id,
                "member_limit": 1,
                "expire_date": expire_date,
                "creates_join_request": False
            },
            timeout=10
        )
        result = r.json()
        if result.get("ok"):
            return result["result"]["invite_link"]
    except Exception as e:
        print("خطأ إنشاء رابط: " + str(e))
    return None


def get_sub_info(days):
    """إرجاع نوع وإيموجي الاشتراك حسب عدد الأيام"""
    if days == 15:
        return "تجريبي", "🆓"
    elif days == 30:
        return "شهري", "📅"
    elif days == 90:
        return "ربع سنوي", "💎"
    else:
        return "مخصص", "⭐"


# ─────────────────────────────────────────
#  تفعيل الاشتراك
# ─────────────────────────────────────────

def activate_subscription(target_user, channel_id, days, db):
    """تفعيل الاشتراك"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=days)
    sub_type, emoji = get_sub_info(days)

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

    user_name, username = get_user_info(target_user)
    username_text = f"@{username}" if username else "لا يوجد"

    # رسالة لجميع المديرين
    send_to_all_admins(
        f"✅ <b>تم تفعيل الاشتراك بنجاح</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{emoji} نوع الاشتراك: <b>{sub_type}</b>\n"
        f"👤 الاسم: <b>{user_name}</b>\n"
        f"🆔 المعرف: {username_text}\n"
        f"🔢 الآيدي: <code>{target_user}</code>\n"
        f"📅 البداية: {now.strftime('%Y-%m-%d')}\n"
        f"⏰ الانتهاء: {expire.strftime('%Y-%m-%d')}\n"
        f"📆 المدة: {days} يوم\n"
        f"━━━━━━━━━━━━━━━"
    )

    # رسالة للمستخدم مع رابط الدخول وأزرار المشرفين
    invite_link = create_invite_link(channel_id, target_user)

    if invite_link:
        user_keyboard = {
            "inline_keyboard": [
                [{"text": "📢 انضم للقناة الآن", "url": invite_link}]
            ] + get_admin_buttons()["inline_keyboard"]
        }
        send_message(target_user,
            f"🎉 <b>مرحباً {user_name}!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{emoji} <b>تم تفعيل اشتراكك {sub_type}</b>\n\n"
            f"✅ الاشتراك فعال لمدة <b>{days} يوم</b>\n"
            f"📅 تاريخ البداية: <b>{now.strftime('%Y-%m-%d')}</b>\n"
            f"⏰ تاريخ الانتهاء: <b>{expire.strftime('%Y-%m-%d')}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👇 اضغط الزر أدناه للدخول للقناة مباشرة\n"
            f"⚠️ الرابط صالح لمرة واحدة فقط خلال 24 ساعة\n\n"
            f"© <i>#مستر_سكالب</i>",
            reply_markup=user_keyboard
        )
    else:
        send_message(target_user,
            f"🎉 <b>مرحباً {user_name}!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{emoji} <b>تم تفعيل اشتراكك {sub_type}</b>\n\n"
            f"✅ الاشتراك فعال لمدة <b>{days} يوم</b>\n"
            f"📅 تاريخ البداية: <b>{now.strftime('%Y-%m-%d')}</b>\n"
            f"⏰ تاريخ الانتهاء: <b>{expire.strftime('%Y-%m-%d')}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔔 سيتم تذكيرك قبل انتهاء الاشتراك\n\n"
            f"© <i>#مستر_سكالب</i>",
            reply_markup=get_admin_buttons()
        )

    # رسالة في القناة
    send_message_to_channel(channel_id,
        f"🎊 <b>مشترك جديد!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👋 مرحباً بـ <b>{user_name}</b>\n"
        f"{emoji} اشتراك <b>{sub_type}</b> - {days} يوم\n"
        f"━━━━━━━━━━━━━━━\n"
        f"© <i>#مستر_سكالب</i>"
    )


# ─────────────────────────────────────────
#  معالجة الأزرار
# ─────────────────────────────────────────

def process_callback(callback_query, db):
    """معالجة ضغط أزرار التفعيل"""
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not is_admin(chat_id):
        return

    if data.startswith("add_"):
        parts = data.split("_")
        if len(parts) == 4:
            target_user = parts[1]
            channel_id = parts[2]
            days = int(parts[3])

            activate_subscription(target_user, channel_id, days, db)

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


def process_renew_callback(callback_query, db):
    """معالجة تجديد الاشتراك عبر الأزرار"""
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not is_admin(chat_id):
        return

    if data.startswith("renew_"):
        parts = data.split("_")
        if len(parts) == 3:
            target_user = parts[1]
            days = int(parts[2])

            if target_user in db:
                now = datetime.now(timezone.utc)
                expire = now + timedelta(days=days)
                sub_type, emoji = get_sub_info(days)

                db[target_user]["expire_date"] = expire.strftime("%Y-%m-%d %H:%M")
                db[target_user]["notified_3days"] = False
                db[target_user]["notified_1day"] = False
                db[target_user]["active"] = True
                db[target_user]["subscription_days"] = days
                db[target_user]["subscription_type"] = sub_type
                save_db(db)

                user_name, username = get_user_info(target_user)

                # إشعار لجميع المديرين
                send_to_all_admins(
                    f"✅ <b>تم تجديد الاشتراك</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{emoji} نوع الاشتراك: <b>{sub_type}</b>\n"
                    f"👤 {user_name}\n"
                    f"🔢 <code>{target_user}</code>\n"
                    f"⏰ الانتهاء الجديد: {expire.strftime('%Y-%m-%d')}\n"
                    f"📆 المدة: {days} يوم"
                )

                send_message(target_user,
                    f"🎉 <b>تم تجديد اشتراكك!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{emoji} <b>اشتراك {sub_type}</b>\n"
                    f"⏰ ينتهي بتاريخ: <b>{expire.strftime('%Y-%m-%d')}</b>\n"
                    f"📆 المدة: <b>{days} يوم</b>\n\n"
                    f"© <i>#مستر_سكالب</i>",
                    reply_markup=get_admin_buttons()
                )

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


# ─────────────────────────────────────────
#  معالجة الرسائل (أوامر المديرين)
# ─────────────────────────────────────────

def process_message(message, db):
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "")
    user_id = str(message.get("from", {}).get("id", ""))

    # تجاهل أي شخص ليس مديراً
    if not is_admin(user_id):
        return

    if text.startswith("/add"):
        parts = text.split()
        if len(parts) < 3:
            send_message(chat_id,
                "⚠️ <b>الصيغة الصحيحة:</b>\n"
                "/add USER_ID CHANNEL_ID\n\n"
                "<b>مثال:</b>\n"
                "/add 123456789 -1001234567890")
            return

        target_user = parts[1]
        channel_id = parts[2]

        keyboard = {
            "inline_keyboard": [
                [{"text": "🆓 15 يوم (تجريبي)", "callback_data": f"add_{target_user}_{channel_id}_15"}],
                [{"text": "📅 30 يوم (شهري)",    "callback_data": f"add_{target_user}_{channel_id}_30"}],
                [{"text": "💎 90 يوم (ربع سنوي)", "callback_data": f"add_{target_user}_{channel_id}_90"}]
            ]
        }
        send_message(chat_id,
            f"🎯 <b>اختر مدة الاشتراك:</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 المستخدم: <code>{target_user}</code>\n"
            f"📢 القناة: <code>{channel_id}</code>",
            reply_markup=keyboard
        )

    elif text.startswith("/remove"):
        parts = text.split()
        if len(parts) < 2:
            send_message(chat_id, "⚠️ الصيغة: /remove USER_ID")
            return

        target_user = parts[1]
        if target_user in db:
            user_name, username = get_user_info(target_user)
            channel_id = db[target_user]["channel_id"]
            db[target_user]["active"] = False
            save_db(db)
            kick_user(channel_id, target_user)
            send_message(chat_id,
                f"✅ <b>تم إلغاء الاشتراك</b>\n"
                f"👤 {user_name}\n"
                f"🔢 <code>{target_user}</code>\n"
                f"🚪 تم طرده من القناة")
            send_message(target_user,
                f"❌ <b>تم إلغاء اشتراكك</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"للتجديد تواصل مع المشرف\n\n"
                f"© <i>#مستر_سكالب</i>",
                reply_markup=get_admin_buttons()
            )
        else:
            send_message(chat_id, "⚠️ المستخدم غير موجود في القاعدة")

    elif text.startswith("/renew"):
        parts = text.split()
        if len(parts) < 2:
            send_message(chat_id, "⚠️ الصيغة: /renew USER_ID")
            return

        target_user = parts[1]
        if target_user in db:
            user_name, username = get_user_info(target_user)
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🆓 15 يوم", "callback_data": f"renew_{target_user}_15"}],
                    [{"text": "📅 30 يوم", "callback_data": f"renew_{target_user}_30"}],
                    [{"text": "💎 90 يوم", "callback_data": f"renew_{target_user}_90"}]
                ]
            }
            send_message(chat_id,
                f"🔄 <b>اختر مدة التجديد:</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 {user_name}\n"
                f"🔢 <code>{target_user}</code>",
                reply_markup=keyboard
            )
        else:
            send_message(chat_id, "⚠️ المستخدم غير موجود")

    elif text == "/list":
        if not db:
            send_message(chat_id, "📭 لا يوجد مشتركين حالياً")
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

            user_name, _ = get_user_info(uid)
            msg += f"\n👤 {user_name}\n"
            msg += f"🔢 <code>{uid}</code>\n"
            msg += f"📊 {status} | {sub_type} | متبقي {days_left} يوم\n"
            msg += f"━━━━━━━━━━━━━━━\n"

        msg += (
            f"\n📊 <b>الإحصائيات:</b>\n"
            f"✅ فعال: {active_count}\n"
            f"❌ منتهي: {expired_count}\n"
            f"📈 المجموع: {len(db)}"
        )
        send_message(chat_id, msg)

    elif text == "/help":
        send_message(chat_id,
            "🤖 <b>أوامر البوت:</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "➕ <b>/add USER_ID CHANNEL_ID</b>\n"
            "   تفعيل مشترك جديد مع خيارات المدة\n\n"
            "➖ <b>/remove USER_ID</b>\n"
            "   إلغاء اشتراك وطرد من القناة\n\n"
            "🔄 <b>/renew USER_ID</b>\n"
            "   تجديد الاشتراك مع خيارات المدة\n\n"
            "📋 <b>/list</b>\n"
            "   عرض كل المشتركين م
