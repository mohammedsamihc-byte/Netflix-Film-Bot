import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError
from pymongo import MongoClient

# ------------------------------------------------------------------
# CONFIGURAZIONE
# ------------------------------------------------------------------
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])  # admin principale (owner), non rimovibile
MONGO_URI = os.environ["MONGO_URI"]

STARS_PRICE = 50  # prezzo in Telegram Stars per saltare l'iscrizione obbligatoria

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------------
client = MongoClient(MONGO_URI)
db = client["filmbot"]
videos = db["videos"]
required_channels = db["required_channels"]
admins_col = db["admins"]
paid_bypass = db["paid_bypass"]
users_col = db["users"]

# ------------------------------------------------------------------
# TRADUZIONI
# ------------------------------------------------------------------
TEXTS = {
    "it": {
        "welcome": "Ciao! Scrivimi il codice del film che vuoi ricevere.",
        "not_authorized": "Non sei autorizzato a fare questo.",
        "video_needs_code": "Manda il video con una didascalia = codice, es. FILM01",
        "video_saved": "Video salvato con codice: {code}",
        "code_not_found": "Codice non trovato. Controlla e riprova.",
        "need_subscribe": "Per usare il bot devi iscriverti a:\n{channels}\n\nOppure sblocca l'accesso pagando {stars} Stelle Telegram.",
        "pay_button": "Paga {stars} Stelle per sbloccare",
        "payment_success": "Pagamento ricevuto! Ora puoi usare il bot senza iscriverti ai canali.",
        "channel_added": "Aggiunto: ora e' obbligatorio iscriversi a {channel}.\nRicorda: devo essere ADMIN in quel canale/gruppo.",
        "channel_removed": "Rimosso: {channel} non e' piu' obbligatorio.",
        "channel_list_empty": "Nessun canale/gruppo obbligatorio impostato.",
        "channel_list": "Obbligatori:\n{list}",
        "usage_addchannel": "Uso: /addchannel @nomecanale",
        "usage_removechannel": "Uso: /removechannel @nomecanale",
        "admin_added": "Aggiunto come admin: {uid}",
        "admin_removed": "Rimosso come admin: {uid}",
        "admin_list_empty": "Nessun admin aggiuntivo (oltre a te).",
        "admin_list": "Admin aggiuntivi:\n{list}",
        "usage_addadmin": "Uso: /addadmin ID_TELEGRAM",
        "owner_only": "Solo l'admin principale puo' fare questo.",
        "admin_help": (
            "Comandi admin disponibili:\n"
            "/addchannel @canale - aggiunge iscrizione obbligatoria\n"
            "/removechannel @canale - rimuove l'obbligo\n"
            "/listchannels - elenco canali obbligatori\n"
            "/addadmin ID - aggiunge un admin (solo owner)\n"
            "/removeadmin ID - rimuove un admin (solo owner)\n"
            "/listadmins - elenco admin (solo owner)\n"
            "Manda un video con didascalia = codice per salvarlo."
        ),
    },
    "en": {
        "welcome": "Hi! Send me the code of the movie you want.",
        "not_authorized": "You are not authorized to do this.",
        "video_needs_code": "Send the video with a caption = code, e.g. FILM01",
        "video_saved": "Video saved with code: {code}",
        "code_not_found": "Code not found. Check and try again.",
        "need_subscribe": "To use the bot you must join:\n{channels}\n\nOr unlock access by paying {stars} Telegram Stars.",
        "pay_button": "Pay {stars} Stars to unlock",
        "payment_success": "Payment received! You can now use the bot without joining the channels.",
        "channel_added": "Added: joining {channel} is now required.\nRemember: I must be admin in that channel/group.",
        "channel_removed": "Removed: {channel} is no longer required.",
        "channel_list_empty": "No required channel/group set.",
        "channel_list": "Required:\n{list}",
        "usage_addchannel": "Usage: /addchannel @channelname",
        "usage_removechannel": "Usage: /removechannel @channelname",
        "admin_added": "Added as admin: {uid}",
        "admin_removed": "Removed as admin: {uid}",
        "admin_list_empty": "No extra admins (besides you).",
        "admin_list": "Extra admins:\n{list}",
        "usage_addadmin": "Usage: /addadmin TELEGRAM_ID",
        "owner_only": "Only the main admin can do this.",
        "admin_help": (
            "Available admin commands:\n"
            "/addchannel @channel - require joining a channel\n"
            "/removechannel @channel - remove the requirement\n"
            "/listchannels - list required channels\n"
            "/addadmin ID - add an admin (owner only)\n"
            "/removeadmin ID - remove an admin (owner only)\n"
            "/listadmins - list admins (owner only)\n"
            "Send a video with caption = code to save it."
        ),
    },
    "fr": {
        "welcome": "Salut ! Envoie-moi le code du film que tu veux.",
        "not_authorized": "Tu n'es pas autorise a faire ca.",
        "video_needs_code": "Envoie la video avec une legende = code, ex. FILM01",
        "video_saved": "Video enregistree avec le code : {code}",
        "code_not_found": "Code introuvable. Verifie et reessaie.",
        "need_subscribe": "Pour utiliser le bot tu dois rejoindre :\n{channels}\n\nOu debloque l'acces en payant {stars} Etoiles Telegram.",
        "pay_button": "Payer {stars} Etoiles pour debloquer",
        "payment_success": "Paiement recu ! Tu peux maintenant utiliser le bot sans rejoindre les canaux.",
        "channel_added": "Ajoute : rejoindre {channel} est maintenant obligatoire.\nRappel : je dois etre admin dans ce canal/groupe.",
        "channel_removed": "Supprime : {channel} n'est plus obligatoire.",
        "channel_list_empty": "Aucun canal/groupe obligatoire defini.",
        "channel_list": "Obligatoires :\n{list}",
        "usage_addchannel": "Usage : /addchannel @nomcanal",
        "usage_removechannel": "Usage : /removechannel @nomcanal",
        "admin_added": "Ajoute comme admin : {uid}",
        "admin_removed": "Supprime comme admin : {uid}",
        "admin_list_empty": "Aucun admin supplementaire (a part toi).",
        "admin_list": "Admins supplementaires :\n{list}",
        "usage_addadmin": "Usage : /addadmin ID_TELEGRAM",
        "owner_only": "Seul l'admin principal peut faire ca.",
        "admin_help": (
            "Commandes admin disponibles :\n"
            "/addchannel @canal - rend l'inscription obligatoire\n"
            "/removechannel @canal - supprime l'obligation\n"
            "/listchannels - liste des canaux obligatoires\n"
            "/addadmin ID - ajoute un admin (owner seulement)\n"
            "/removeadmin ID - supprime un admin (owner seulement)\n"
            "/listadmins - liste des admins (owner seulement)\n"
            "Envoie une video avec legende = code pour l'enregistrer."
        ),
    },
    "ar": {
        "welcome": "مرحباً! أرسل لي كود الفيلم الذي تريده.",
        "not_authorized": "غير مصرح لك بفعل هذا.",
        "video_needs_code": "أرسل الفيديو مع تعليق = الكود، مثال FILM01",
        "video_saved": "تم حفظ الفيديو بالكود: {code}",
        "code_not_found": "الكود غير موجود. تحقق وحاول مرة أخرى.",
        "need_subscribe": "لاستخدام البوت يجب عليك الانضمام إلى:\n{channels}\n\nأو افتح الوصول بدفع {stars} نجمة تيليجرام.",
        "pay_button": "ادفع {stars} نجمة لفتح الوصول",
        "payment_success": "تم استلام الدفع! يمكنك الآن استخدام البوت دون الانضمام للقنوات.",
        "channel_added": "تمت الإضافة: الانضمام إلى {channel} أصبح إلزامياً.\nملاحظة: يجب أن أكون مشرفاً في تلك القناة/المجموعة.",
        "channel_removed": "تمت الإزالة: {channel} لم يعد إلزامياً.",
        "channel_list_empty": "لا توجد قناة/مجموعة إلزامية محددة.",
        "channel_list": "الإلزامية:\n{list}",
        "usage_addchannel": "الاستخدام: /addchannel @اسم_القناة",
        "usage_removechannel": "الاستخدام: /removechannel @اسم_القناة",
        "admin_added": "تمت الإضافة كمشرف: {uid}",
        "admin_removed": "تمت الإزالة كمشرف: {uid}",
        "admin_list_empty": "لا يوجد مشرفون إضافيون.",
        "admin_list": "المشرفون الإضافيون:\n{list}",
        "usage_addadmin": "الاستخدام: /addadmin ID_TELEGRAM",
        "owner_only": "فقط المشرف الرئيسي يمكنه فعل هذا.",
        "admin_help": (
            "أوامر المشرف المتاحة:\n"
            "/addchannel @قناة - يجعل الانضمام إلزامياً\n"
            "/removechannel @قناة - يزيل الإلزام\n"
            "/listchannels - قائمة القنوات الإلزامية\n"
            "/addadmin ID - إضافة مشرف (المالك فقط)\n"
            "/removeadmin ID - إزالة مشرف (المالك فقط)\n"
            "/listadmins - قائمة المشرفين (المالك فقط)\n"
            "أرسل فيديو مع تعليق = كود لحفظه."
        ),
    },
}


def get_lang_raw(user_id):
    doc = users_col.find_one({"user_id": user_id})
    return doc.get("lang") if doc else None


def get_lang(user_id):
    return get_lang_raw(user_id) or "en"


def set_lang(user_id, lang):
    users_col.update_one({"user_id": user_id}, {"$set": {"lang": lang}}, upsert=True)


def t(user_id, key, **kwargs):
    lang = get_lang(user_id)
    text = TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"][key])
    return text.format(**kwargs) if kwargs else text


def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    return admins_col.find_one({"user_id": user_id}) is not None


def get_required_channels():
    return [d["channel_id"] for d in required_channels.find()]


async def user_is_subscribed(context, user_id):
    missing = []
    for channel in get_required_channels():
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ("left", "kicked"):
                missing.append(channel)
        except TelegramError:
            missing.append(channel)
    return missing


# ------------------------------------------------------------------
# LINGUA
# ------------------------------------------------------------------
LANG_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Italiano", callback_data="lang_it"),
        InlineKeyboardButton("English", callback_data="lang_en"),
    ],
    [
        InlineKeyboardButton("Francais", callback_data="lang_fr"),
        InlineKeyboardButton("Arabic", callback_data="lang_ar"),
    ],
])

CHOOSE_LANG_MSG = "Scegli la lingua / Choose language / Choisissez la langue / Ikhtar al-lugha"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_lang_raw(user_id) is None:
        await update.message.reply_text(CHOOSE_LANG_MSG, reply_markup=LANG_BUTTONS)
    else:
        await update.message.reply_text(t(user_id, "welcome"))


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CHOOSE_LANG_MSG, reply_markup=LANG_BUTTONS)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("lang_"):
        lang = query.data.split("_")[1]
        set_lang(user_id, lang)
        await query.edit_message_text(t(user_id, "welcome"))

    elif query.data == "pay_stars":
        prices = [LabeledPrice("Accesso permanente", STARS_PRICE)]
        await context.bot.send_invoice(
            chat_id=user_id,
            title="Sblocca accesso",
            description=f"Sblocca l'accesso permanente al bot per {STARS_PRICE} Stelle",
            payload="bypass_channels",
            provider_token="",
            currency="XTR",
            prices=prices,
        )


# ------------------------------------------------------------------
# PAGAMENTI (TELEGRAM STARS)
# ------------------------------------------------------------------
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    paid_bypass.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
    await update.message.reply_text(t(user_id, "payment_success"))


# ------------------------------------------------------------------
# UTENTE: RICHIESTA CODICE
# ------------------------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    has_paid = paid_bypass.find_one({"user_id": user_id}) is not None

    if not has_paid:
        missing = await user_is_subscribed(context, user_id)
        if missing:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    t(user_id, "pay_button", stars=STARS_PRICE),
                    callback_data="pay_stars",
                )]]
            )
            await update.message.reply_text(
                t(user_id, "need_subscribe", channels="\n".join(missing), stars=STARS_PRICE),
                reply_markup=keyboard,
            )
            return

    code = update.message.text.strip().upper()
    result = videos.find_one({"code": code})

    if result:
        await update.message.reply_video(result["file_id"])
    else:
        await update.message.reply_text(t(user_id, "code_not_found"))


# ------------------------------------------------------------------
# ADMIN: VIDEO E CODICI
# ------------------------------------------------------------------
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, "not_authorized"))
        return
    if not update.message.caption:
        await update.message.reply_text(t(user_id, "video_needs_code"))
        return
    code = update.message.caption.strip().upper()
    file_id = update.message.video.file_id
    videos.update_one({"code": code}, {"$set": {"file_id": file_id}}, upsert=True)
    await update.message.reply_text(t(user_id, "video_saved", code=code))


# ------------------------------------------------------------------
# ADMIN: CANALI/GRUPPI OBBLIGATORI
# ------------------------------------------------------------------
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, "not_authorized"))
        return
    if not context.args:
        await update.message.reply_text(t(user_id, "usage_addchannel"))
        return
    channel = context.args[0]
    required_channels.update_one({"channel_id": channel}, {"$set": {"channel_id": channel}}, upsert=True)
    await update.message.reply_text(t(user_id, "channel_added", channel=channel))


async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, "not_authorized"))
        return
    if not context.args:
        await update.message.reply_text(t(user_id, "usage_removechannel"))
        return
    channel = context.args[0]
    required_channels.delete_one({"channel_id": channel})
    await update.message.reply_text(t(user_id, "channel_removed", channel=channel))


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, "not_authorized"))
        return
    channels = get_required_channels()
    if not channels:
        await update.message.reply_text(t(user_id, "channel_list_empty"))
    else:
        await update.message.reply_text(t(user_id, "channel_list", list="\n".join(channels)))


# ------------------------------------------------------------------
# OWNER: GESTIONE ALTRI ADMIN
# ------------------------------------------------------------------
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text(t(user_id, "owner_only"))
        return
    if not context.args:
        await update.message.reply_text(t(user_id, "usage_addadmin"))
        return
    try:
        new_admin_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(t(user_id, "usage_addadmin"))
        return
    admins_col.update_one({"user_id": new_admin_id}, {"$set": {"user_id": new_admin_id}}, upsert=True)
    await update.message.reply_text(t(user_id, "admin_added", uid=new_admin_id))


async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text(t(user_id, "owner_only"))
        return
    if not context.args:
        await update.message.reply_text(t(user_id, "usage_addadmin"))
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(t(user_id, "usage_addadmin"))
        return
    admins_col.delete_one({"user_id": target_id})
    await update.message.reply_text(t(user_id, "admin_removed", uid=target_id))


async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text(t(user_id, "owner_only"))
        return
    admins = [str(d["user_id"]) for d in admins_col.find()]
    if not admins:
        await update.message.reply_text(t(user_id, "admin_list_empty"))
    else:
        await update.message.reply_text(t(user_id, "admin_list", list="\n".join(admins)))


async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, "not_authorized"))
        return
    await update.message.reply_text(t(user_id, "admin_help"))


# ------------------------------------------------------------------
# AVVIO BOT
# ------------------------------------------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("adminhelp", admin_help))

    app.add_handler(CommandHandler("addchannel", add_channel))
    app.add_handler(CommandHandler("removechannel", remove_channel))
    app.add_handler(CommandHandler("listchannels", list_channels))

    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("listadmins", list_admins))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot avviato...")
    app.run_polling()


if __name__ == "__main__":
    main()
