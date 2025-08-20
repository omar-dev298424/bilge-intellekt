import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.error import BadRequest

# --- BOT TOKEN ---
TOKEN = "7981599020:AAGRhaJZbvMQ1n9Y7qrnBDKWYZcsVX3FV88" 

# --- Conversation States ---
VEZIYYET_IMTAHAN_SECIMI, VEZIYYET_SUAL_GOZLEME, VEZIYYET_TESDIQ_GOZLEME, VEZIYYET_CEDVEL_SECIMI = range(4)

# --- Dynamic Step Generation for Admission Exams ---
def fenni_addimlar_yaradan(fenn_kodu, fenn_adi, novbeti_addim):
    max_qapali, max_aciq = 22, 5
    qapali_duz_acari, qapali_sehv_acari = f"{fenn_kodu}_qapali_duz", f"{fenn_kodu}_qapali_sehv"
    kodlashdirma_acari, cedvel_acari = f"{fenn_kodu}_kodlashdirma", f"{fenn_kodu}_cedvel_secimleri"
    
    return {
        f'{fenn_kodu}_qapali_duz': {'sorğu': f"{fenn_adi} fənnindən qapalı tipli düz cavabların sayını daxil edin.", 'max_deyer': max_qapali, 'yoxlama_novu': 'tam_eded', 'veri_acari': qapali_duz_acari, 'novbeti_addim': f'{fenn_kodu}_qapali_sehv'},
        f'{fenn_kodu}_qapali_sehv': {'sorğu': f"{fenn_adi} fənnindən qapalı tipli səhv cavabların sayını daxil edin.", 'max_deyer': max_qapali, 'yoxlama_novu': 'tam_eded_sehv', 'veri_acari': qapali_sehv_acari, 'novbeti_addim': f'{fenn_kodu}_kodlashdirma'},
        f'{fenn_kodu}_kodlashdirma': {'sorğu': f"{fenn_adi} fənnindən açıq tipli düz cavabların sayını qeyd edin.", 'max_deyer': max_aciq, 'yoxlama_novu': 'tam_eded', 'veri_acari': kodlashdirma_acari, 'novbeti_addim': f'{fenn_kodu}_cedvel'},
        f'{fenn_kodu}_cedvel': {'sorğu': f"{fenn_adi} fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['28', '29', '30'], 'veri_acari': cedvel_acari, 'novbeti_addim': novbeti_addim},
    }

qebul_fenn_strukturu = {
    'qebul_1_kimya': [('riyaziyyat', 'Riyaziyyat'), ('fizika', 'Fizika'), ('kimya', 'Kimya')],
    'qebul_1_informatika': [('riyaziyyat', 'Riyaziyyat'), ('fizika', 'Fizika'), ('informatika', 'İnformatika')],
    'qebul_2': [('riyaziyyat', 'Riyaziyyat'), ('cografiya', 'Coğrafiya'), ('tarix', 'Tarix')],
    'qebul_3_dt': [('az_dili', 'Azərbaycan dili'), ('tarix', 'Tarix'), ('edebiyyat', 'Ədəbiyyat')],
    'qebul_3_tc': [('az_dili', 'Azərbaycan dili'), ('tarix', 'Tarix'), ('cografiya', 'Coğrafiya')],
    'qebul_4': [('biologiya', 'Biologiya'), ('kimya', 'Kimya'), ('fizika', 'Fizika')]
}

ADDIMLAR = {
    'buraxilis_9_kohne': {
        'ingilis_qapali': {'sorğu': "İngilis dili fənnindən qapalı suallara verdiyiniz doğru cavabların sayını daxil edin.", 'max_deyer': 26, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'ingilis_qapali', 'novbeti_addim': 'ingilis_cedvel'},
        'ingilis_cedvel': {'sorğu': "İngilis dili fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['6', '28', '29', '30'], 'veri_acari': 'ingilis_cedvel_secimleri', 'novbeti_addim': 'az_dili_qapali'},
        'az_dili_qapali': {'sorğu': "Azərbaycan dili fənnindən qapalı suallara verdiyiniz doğru cavabların sayını daxil edin.", 'max_deyer': 26, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'az_dili_qapali', 'novbeti_addim': 'az_dili_cedvel'},
        'az_dili_cedvel': {'sorğu': "Azərbaycan dili fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['49', '50', '59', '60'], 'veri_acari': 'az_dili_cedvel_secimleri', 'novbeti_addim': 'riyaziyyat_qapali'},
        'riyaziyyat_qapali': {'sorğu': "Riyaziyyat fənnindən qapalı düz cavabların sayını daxil edin.", 'max_deyer': 15, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'riyaziyyat_qapali', 'novbeti_addim': 'riyaziyyat_kodlashdirma'},
        'riyaziyyat_kodlashdirma': {'sorğu': "Riyaziyyat fənnindən açıq kodlaşdırılabilən düz cavabların sayını qeyd edin.", 'max_deyer': 6, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'riyaziyyat_kodlashdirma', 'novbeti_addim': 'riyaziyyat_cedvel'},
        'riyaziyyat_cedvel': {'sorğu': "Riyaziyyat fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['82', '83', '84', '85'], 'veri_acari': 'riyaziyyat_cedvel_secimleri', 'novbeti_addim': 'son_hesablama'},
    },
    'buraxilis_9_2025': {
        'ingilis_qapali': {'sorğu': "Xarici dil fənnindən qapalı tipli düzgün cavabların sayını daxil edin.", 'max_deyer': 22, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'ingilis_qapali', 'novbeti_addim': 'ingilis_kodlashdirma'},
        'ingilis_kodlashdirma': {'sorğu': "Xarici dil fənnindən açıq kodlaşdırılabilən düz cavabların sayını qeyd edin.\n*Qeyd: 0.5 aralıqla daxil edə bilərsiniz.*", 'max_deyer': 3, 'yoxlama_novu': 'kesr_eded', 'veri_acari': 'ingilis_kodlashdirma', 'novbeti_addim': 'ingilis_esse'},
        'ingilis_esse': {'sorğu': "Xarici dil fənnindən esse dəyərini qeyd edin.\n*Qeyd: Esse 0.5 aralıqla maksimum 5 bal kimi dəyərləndirilə bilər.*", 'max_deyer': 5, 'yoxlama_novu': 'kesr_eded', 'veri_acari': 'ingilis_esse', 'novbeti_addim': 'az_dili_qapali'},
        'az_dili_qapali': {'sorğu': "Ana dili fənnindən düzgün cavabların sayını daxil edin.", 'max_deyer': 26, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'az_dili_qapali', 'novbeti_addim': 'az_dili_cedvel'},
        'az_dili_cedvel': {'sorğu': "Ana dili fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['45', '46', '55', '56'], 'veri_acari': 'az_dili_cedvel_secimleri', 'novbeti_addim': 'riyaziyyat_qapali'},
        'riyaziyyat_qapali': {'sorğu': "Riyaziyyat fənnindən qapalı düz cavabların sayını daxil edin.", 'max_deyer': 15, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'riyaziyyat_qapali', 'novbeti_addim': 'riyaziyyat_kodlashdirma'},
        'riyaziyyat_kodlashdirma': {'sorğu': "Riyaziyyat fənnindən açıq kodlaşdırıla bilən düz cavabların sayını qeyd edin.", 'max_deyer': 6, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'riyaziyyat_kodlashdirma', 'novbeti_addim': 'riyaziyyat_cedvel'},
        'riyaziyyat_cedvel': {'sorğu': "Riyaziyyat fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['78', '79', '80', '81'], 'veri_acari': 'riyaziyyat_cedvel_secimleri', 'novbeti_addim': 'son_hesablama'},
    },
    'buraxilis_11': {
        'ingilis_qapali': {'sorğu': "Xarici dil fənnindən düzgün cavabların sayını daxil edin.", 'max_deyer': 23, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'ingilis_qapali', 'novbeti_addim': 'ingilis_cedvel'},
        'ingilis_cedvel': {'sorğu': "Xarici dil fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['4', '5', '6', '27', '28', '29', '30'], 'veri_acari': 'ingilis_cedvel_secimleri', 'novbeti_addim': 'az_dili_qapali'},
        'az_dili_qapali': {'sorğu': "Azərbaycan dili fənnindən düzgün cavabların sayını daxil edin.", 'max_deyer': 20, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'az_dili_qapali', 'novbeti_addim': 'az_dili_cedvel'},
        'az_dili_cedvel': {'sorğu': "Azərbaycan dili fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['46', '47', '48', '49', '50', '56', '57', '58', '59', '60'], 'veri_acari': 'az_dili_cedvel_secimleri', 'novbeti_addim': 'riyaziyyat_qapali'},
        'riyaziyyat_qapali': {'sorğu': "Riyaziyyat fənnindən qapalı düz cavabların sayını daxil edin.", 'max_deyer': 13, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'riyaziyyat_qapali', 'novbeti_addim': 'riyaziyyat_kodlashdirma'},
        'riyaziyyat_kodlashdirma': {'sorğu': "Riyaziyyat fənnindən açıq kodlaşdırıla bilən düz cavabların sayını qeyd edin.", 'max_deyer': 5, 'yoxlama_novu': 'tam_eded', 'veri_acari': 'riyaziyyat_kodlashdirma', 'novbeti_addim': 'riyaziyyat_cedvel'},
        'riyaziyyat_cedvel': {'sorğu': "Riyaziyyat fənnindən yazılı düz cavablarınızı seçin:", 'suallar': ['79', '80', '81', '82', '83', '84', '85'], 'veri_acari': 'riyaziyyat_cedvel_secimleri', 'novbeti_addim': 'son_hesablama'},
    }
}

for qrup_kodu, fenn_siyahisi in qebul_fenn_strukturu.items():
    ADDIMLAR[qrup_kodu] = {}
    for i, (fenn_kodu, fenn_adi) in enumerate(fenn_siyahisi):
        novbeti_addim = fenn_siyahisi[i+1][0] + "_qapali_duz" if i + 1 < len(fenn_siyahisi) else 'son_hesablama'
        start_num = 28 + i * 30
        cedvel_suallari = [str(start_num), str(start_num+1), str(start_num+2)]
        
        fenn_addimlari = fenni_addimlar_yaradan(fenn_kodu, fenn_adi, novbeti_addim)
        fenn_addimlari[f'{fenn_kodu}_cedvel']['suallar'] = cedvel_suallari
        ADDIMLAR[qrup_kodu].update(fenn_addimlari)

# --- Logging ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
async def addim_yadda_saxla(context: ContextTypes.DEFAULT_TYPE, addim: str):
    addim_tarixcesi = context.user_data.get('addim_tarixcesi', [])
    if not addim_tarixcesi or addim_tarixcesi[-1] != addim:
        addim_tarixcesi.append(addim)
        context.user_data['addim_tarixcesi'] = addim_tarixcesi

# --- Core Bot Functions ---
async def ana_menyunu_goster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🎓 Buraxılış", callback_data='meny_buraxilish'), InlineKeyboardButton("🏛️ Qəbul", callback_data='meny_qebul')],
        [InlineKeyboardButton("ℹ️ İstifadə Təlimatı", callback_data='meny_telimat')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mesaj_metni = "Salam! 👋 DİM imtahan nəticələrini hesablamaq üçün imtahan növünü seçin:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=mesaj_metni, reply_markup=reply_markup)
    else:
        await update.effective_chat.send_message(text=mesaj_metni, reply_markup=reply_markup)
        
    return VEZIYYET_IMTAHAN_SECIMI

async def istifade_telimatini_goster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    telimat_metni = (
        "ℹ️ *Botdan Necə İstifadə Etməli?*\n\n"
        "Bu bot DİM imtahan nəticələrini sürətli və dəqiq hesablamaq üçün yaradılıb.\n\n"
        "*Əsas Addımlar:*\n"
        "1️⃣ *İmtahanı Seçin:* `/start` və ya `/clean` əmri ilə ana menyuya qayıdın. 'Qəbul' və ya 'Buraxılış' düymələrindən birini seçərək öz imtahan növünüzü təyin edin.\n\n"
        "2️⃣ *Məlumatları Daxil Edin:* Botun sizə göstərdiyi suallara uyğun olaraq nəticələrinizi (düz, səhv, bal və s.) yazıb göndərin.\n\n"
        "3️⃣ *Nəticəni Əldə Edin:* Bütün məlumatları təsdiqlədikdən sonra bot yekun balınızı dərhal hesablayıb göstərəcək.\n\n"
        "--- \n"
        "*İdarəetmə Düymələri və Əmrlər:*\n\n"
        "↩️ *Geri:* Proses zamanı bir əvvəlki addıma qayıtmaq üçün istifadə olunur.\n\n"
        "✏️ *Düzəliş et:* Daxil etdiyiniz son rəqəmi yenidən yazmaq üçün istifadə olunur.\n\n"
        "❌ *Ləğv et:* Hesablama prosesini tamamilə dayandırıb avtomatik olaraq ana menyuya qayıtmaq üçün istifadə olunur.\n\n"
        "🧹 `/clean` *əmri:* Söhbət pəncərəsini təmizləyib botu yenidən başlamaq üçün bu əmri yazıb göndərin.\n\n"
        "Uğurlar!"
    )
    keyboard = [[InlineKeyboardButton("↩️ Ana Səhifəyə Qayıt", callback_data='meny_ana')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=telimat_metni, reply_markup=reply_markup, parse_mode='Markdown')
    return VEZIYYET_IMTAHAN_SECIMI

async def buraxilis_sinif_secimini_goster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await addim_yadda_saxla(context, 'meny_ana')
    keyboard = [
        [InlineKeyboardButton("11-ci sinif", callback_data='imtahan_buraxilis_11')],
        [InlineKeyboardButton("9-cu sinif (2025 modeli)", callback_data='imtahan_buraxilis_9_2025')],
        [InlineKeyboardButton("9-cu sinif (Köhnə model)", callback_data='imtahan_buraxilis_9_kohne')],
        [InlineKeyboardButton("↩️ Geri", callback_data='geri')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Zəhmət olmasa, buraxılış imtahanı üçün sinfi seçin:", reply_markup=reply_markup)
    return VEZIYYET_IMTAHAN_SECIMI

async def qebul_qrup_secimini_goster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await addim_yadda_saxla(context, 'meny_ana')
    keyboard = [
        [InlineKeyboardButton("I Qrup", callback_data='meny_qebul_1_altqrup'), InlineKeyboardButton("II Qrup", callback_data='imtahan_qebul_2')],
        [InlineKeyboardButton("III Qrup", callback_data='meny_qebul_3_altqrup'), InlineKeyboardButton("IV Qrup", callback_data='imtahan_qebul_4')],
        [InlineKeyboardButton("↩️ Geri", callback_data='geri')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Zəhmət olmasa, qəbul imtahanı üçün qrupu seçin:", reply_markup=reply_markup)
    return VEZIYYET_IMTAHAN_SECIMI

async def qebul_altqrup_secimini_goster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    secim_tipi = query.data.split('meny_')[1]
    prompt_text, keyboard_buttons = "", []
    
    await addim_yadda_saxla(context, 'meny_qebul')

    if secim_tipi == 'qebul_1_altqrup':
        prompt_text = "Zəhmət olmasa, I qrup üçün alt-qrupunuzu (3-cü fənn) seçin:"
        keyboard_buttons = [InlineKeyboardButton("Kimya", callback_data='imtahan_qebul_1_kimya'), InlineKeyboardButton("İnformatika", callback_data='imtahan_qebul_1_informatika')]
    elif secim_tipi == 'qebul_3_altqrup':
        prompt_text = "Zəhmət olmasa, III qrup üçün alt-qrupunuzu seçin:"
        keyboard_buttons = [InlineKeyboardButton("DT altqrupu", callback_data='imtahan_qebul_3_dt'), InlineKeyboardButton("TC altqrupu", callback_data='imtahan_qebul_3_tc')]
    
    keyboard = [keyboard_buttons, [InlineKeyboardButton("↩️ Geri", callback_data='geri')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=prompt_text, reply_markup=reply_markup)
    return VEZIYYET_IMTAHAN_SECIMI

async def imtahan_axinini_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    imtahan_tipi = query.data.split('imtahan_')[1]
    context.user_data['imtahan_tipi'] = imtahan_tipi
    
    ilk_addim = ""
    if imtahan_tipi.startswith('buraxilis'):
        await addim_yadda_saxla(context, 'meny_buraxilish')
        ilk_addim = 'ingilis_qapali'
    elif imtahan_tipi.startswith('qebul'):
        if '_' in imtahan_tipi.split('qebul_')[1]:
             await addim_yadda_saxla(context, f"meny_{imtahan_tipi.rsplit('_', 1)[0]}_altqrup")
        else:
             await addim_yadda_saxla(context, 'meny_qebul')
        ilk_fenn_kodu = qebul_fenn_strukturu[imtahan_tipi][0][0]
        ilk_addim = f"{ilk_fenn_kodu}_qapali_duz"
    
    return await novbeti_suali_sorus(update, context, addim_adi=ilk_addim)

async def novbeti_suali_sorus(update: Update, context: ContextTypes.DEFAULT_TYPE, addim_adi: str | None = None) -> int:
    query = update.callback_query
    mesaj = None

    if not addim_adi:
        await query.answer()
        addim_adi = query.data

    await addim_yadda_saxla(context, context.user_data.get('cari_addim', 'meny_ana'))
    context.user_data['cari_addim'] = addim_adi
    imtahan_tipi = context.user_data['imtahan_tipi']
    addim_melumati = ADDIMLAR[imtahan_tipi][addim_adi]
    
    keyboard = [[InlineKeyboardButton("↩️ Geri", callback_data='geri'), InlineKeyboardButton("❌ Prosesi Ləğv et", callback_data='legv_et')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mesaj_metni = addim_melumati['sorğu']
    if addim_melumati.get('yoxlama_novu') != 'tam_eded_sehv':
         mesaj_metni += f"\n(Maksimum dəyər: {addim_melumati['max_deyer']})"

    if query and query.message:
        mesaj = await query.edit_message_text(text=mesaj_metni, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        mesaj = await context.bot.send_message(chat_id=update.effective_chat.id, text=mesaj_metni, reply_markup=reply_markup, parse_mode='Markdown')
    
    context.user_data['son_bot_mesaji_id'] = mesaj.message_id
    return VEZIYYET_SUAL_GOZLEME

async def daxil_edilen_metni_yoxla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    son_bot_mesaji_id = context.user_data.pop('son_bot_mesaji_id', None)
    
    try:
        await update.message.delete()
        if son_bot_mesaji_id:
            await context.bot.delete_message(chat_id, son_bot_mesaji_id)
    except BadRequest:
        logger.info("Silinəcək mesaj tapılmadı.")

    daxil_edilen = update.message.text.replace(',', '.')
    addim_adi = context.user_data['cari_addim']
    imtahan_tipi = context.user_data['imtahan_tipi']
    addim_melumati = ADDIMLAR[imtahan_tipi][addim_adi]
    max_deyer = addim_melumati['max_deyer']
    yoxlama_novu = addim_melumati['yoxlama_novu']
    
    is_valid, temp_deyer, error_msg = False, None, "Daxil etdiyiniz məlumat düzgün deyil."
    
    try:
        if yoxlama_novu == 'tam_eded_sehv':
            sehv_sayi = int(daxil_edilen)
            duz_sayi_acari = addim_melumati['veri_acari'].replace('_sehv', '_duz')
            duz_sayi = context.user_data.get(duz_sayi_acari)
            if sehv_sayi >= 0 and duz_sayi is not None and (duz_sayi + sehv_sayi) <= max_deyer:
                is_valid, temp_deyer = True, sehv_sayi
            else:
                error_msg = f"Düz və səhv saylarının cəmi {max_deyer}-dən çox ola bilməz. Siz {duz_sayi} düz qeyd etmisiniz."
        else:
            deyer = float(daxil_edilen)
            if 0 <= deyer <= max_deyer:
                if yoxlama_novu == 'tam_eded' and deyer.is_integer(): is_valid, temp_deyer = True, int(deyer)
                elif yoxlama_novu == 'kesr_eded' and (deyer * 2).is_integer(): is_valid, temp_deyer = True, deyer
    except (ValueError, IndexError): is_valid = False

    if not is_valid:
        await context.bot.send_message(chat_id=chat_id, text=error_msg)
        return await novbeti_suali_sorus(update, context, addim_adi=addim_adi)
    
    context.user_data['temp_deyer'] = temp_deyer
    
    keyboard = [
        [InlineKeyboardButton("❌ Ləğv et", callback_data='legv_et')],
        [InlineKeyboardButton("✏️ Düzəliş et", callback_data=addim_adi), InlineKeyboardButton("✅ Təsdiq et", callback_data=f"tesdiq_{addim_adi}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    təsdiq_mesaji = await context.bot.send_message(chat_id=chat_id, text=f"Daxil etdiyiniz məlumat: *{temp_deyer}*\nBu məlumat doğrudurmu?", reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['son_bot_mesaji_id'] = təsdiq_mesaji.message_id
    return VEZIYYET_TESDIQ_GOZLEME

async def daxil_edilen_reqemi_tesdiqle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    addim_adi = query.data.replace('tesdiq_', '')
    imtahan_tipi = context.user_data['imtahan_tipi']
    addim_melumati = ADDIMLAR[imtahan_tipi][addim_adi]
    context.user_data[addim_melumati['veri_acari']] = context.user_data.pop('temp_deyer')
    novbeti_addim_adi = addim_melumati['novbeti_addim']
    
    if 'cedvel' in novbeti_addim_adi:
        return await ballandirma_cedvelini_goster(update, context, addim_adi=novbeti_addim_adi)
    elif novbeti_addim_adi == 'son_hesablama':
        return await netice_hesabla_ve_goster(update, context)
    else:
        return await novbeti_suali_sorus(update, context, addim_adi=novbeti_addim_adi)

async def ballandirma_cedvelini_goster(update: Update, context: ContextTypes.DEFAULT_TYPE, addim_adi: str | None = None) -> int:
    query = update.callback_query
    if query: await query.answer()
    
    if not addim_adi: addim_adi = context.user_data['cari_addim']
    await addim_yadda_saxla(context, context.user_data.get('cari_addim', ''))
    context.user_data['cari_addim'] = addim_adi

    imtahan_tipi = context.user_data['imtahan_tipi']
    addim_melumati = ADDIMLAR[imtahan_tipi][addim_adi]
    secimler = context.user_data.get(addim_melumati['veri_acari'], {})
    
    keyboard, basliq = [], f"{addim_melumati['sorğu']}\n\n*Qeyd:* Səhv seçimi sualın nömrəsinə toxunaraq sıfırlaya bilərsiniz."
    
    for sual_nomresi in addim_melumati['suallar']:
        sira = [InlineKeyboardButton(f"{sual_nomresi}. 👉", callback_data=f"cedvel_sifirla_{sual_nomresi}")]
        for deyer_metn, deyer_data in [('0', '0'), ('1/3', '0.3333'), ('1/2', '0.5'), ('2/3', '0.6667'), ('1', '1')]:
            text = f"✅ {deyer_metn}" if secimler.get(sual_nomresi) == deyer_data else deyer_metn
            sira.append(InlineKeyboardButton(text, callback_data=f"cedvel_secim_{sual_nomresi}_{deyer_data}"))
        keyboard.append(sira)
    
    keyboard.append([
        InlineKeyboardButton("↩️ Geri", callback_data='geri'),
        InlineKeyboardButton("❌ Ləğv et", callback_data='legv_et'),
        InlineKeyboardButton("✅ Təsdiq et", callback_data='tesdiq_cedvel')
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query and query.message:
        mesaj = await query.edit_message_text(text=basliq, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        mesaj = await update.effective_chat.send_message(text=basliq, reply_markup=reply_markup, parse_mode='Markdown')
        
    context.user_data['son_bot_mesaji_id'] = mesaj.message_id
    return VEZIYYET_CEDVEL_SECIMI

async def cedvel_secimini_isle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    addim_adi = context.user_data['cari_addim']
    imtahan_tipi = context.user_data['imtahan_tipi']
    addim_melumati = ADDIMLAR[imtahan_tipi][addim_adi]
    veri_acari = addim_melumati['veri_acari']
    hisseler = query.data.split('_')
    hereket, sual_nomresi = hisseler[1], hisseler[2]
    secimler = context.user_data.get(veri_acari, {})
    
    if hereket == 'secim': secimler[sual_nomresi] = hisseler[3]
    elif hereket == 'sifirla' and sual_nomresi in secimler: del secimler[sual_nomresi]
    context.user_data[veri_acari] = secimler
    return await ballandirma_cedvelini_goster(update, context)
    
async def cedveli_tesdiqle_ve_davam_et(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    cari_addim_adi = context.user_data['cari_addim']
    imtahan_tipi = context.user_data['imtahan_tipi']
    addim_melumati = ADDIMLAR[imtahan_tipi][cari_addim_adi]
    novbeti_addim_adi = addim_melumati['novbeti_addim']

    if novbeti_addim_adi == 'son_hesablama': return await netice_hesabla_ve_goster(update, context)
    else: return await novbeti_suali_sorus(update, context, addim_adi=novbeti_addim_adi)

# --- Calculation Functions ---
def fenn_bali_hesabla(data, fenn_kodu):
    Dq = data.get(f'{fenn_kodu}_qapali_duz', 0)
    Yq = data.get(f'{fenn_kodu}_qapali_sehv', 0)
    Dkod = data.get(f'{fenn_kodu}_kodlashdirma', 0)
    Dyazili = sum(float(v) for v in data.get(f'{fenn_kodu}_cedvel_secimleri', {}).values())
    NBq = max(0, (Dq - Yq / 4) * (100 / 33))
    NBa = max(0, (Dkod + 2 * Dyazili) * (100 / 33))
    return NBq + NBa

async def netice_hesabla_ve_goster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = context.user_data
    imtahan_tipi = data['imtahan_tipi']
    netice_metni = ""
    qrup_emsallari = {
        'qebul_1_kimya': {'fennler': [('riyaziyyat', 'Riyaziyyat', '🧮'), ('fizika', 'Fizika', '🔬'), ('kimya', 'Kimya', '🧪')], 'emsallar': [1.5, 1.5, 1.0]},
        'qebul_1_informatika': {'fennler': [('riyaziyyat', 'Riyaziyyat', '🧮'), ('fizika', 'Fizika', '🔬'), ('informatika', 'İnformatika', '💻')], 'emsallar': [1.5, 1.5, 1.0]},
        'qebul_2': {'fennler': [('riyaziyyat', 'Riyaziyyat', '🧮'), ('cografiya', 'Coğrafiya', '🌍'), ('tarix', 'Tarix', '📜')], 'emsallar': [1.5, 1.5, 1.0]},
        'qebul_3_dt': {'fennler': [('az_dili', 'Azərbaycan dili', '🇦🇿'), ('tarix', 'Tarix', '📜'), ('edebiyyat', 'Ədəbiyyat', '📚')], 'emsallar': [1.5, 1.5, 1.0]},
        'qebul_3_tc': {'fennler': [('az_dili', 'Azərbaycan dili', '🇦🇿'), ('tarix', 'Tarix', '📜'), ('cografiya', 'Coğrafiya', '🌍')], 'emsallar': [1.0, 1.5, 1.5]},
        'qebul_4': {'fennler': [('biologiya', 'Biologiya', '🧬'), ('kimya', 'Kimya', '🧪'), ('fizika', 'Fizika', '🔬')], 'emsallar': [1.5, 1.5, 1.0]}
    }
    try:
        if imtahan_tipi.startswith('qebul'):
            qrup_info = qrup_emsallari[imtahan_tipi]
            yekun_ballar = [max(0, fenn_bali_hesabla(data, fk) * emsal) for fk, emsal in zip([f[0] for f in qrup_info['fennler']], qrup_info['emsallar'])]
            total_bal = sum(yekun_ballar)
            qrup_adi = imtahan_tipi.replace('qebul_', '').replace('_', ' ').upper()
            netice_metni = f"🎉 *Nəticəniz ({qrup_adi})* 🎉\n"
            for i, (_, fenn_adi, emoji) in enumerate(qrup_info['fennler']):
                netice_metni += f"\n{emoji} *{fenn_adi}:* {yekun_ballar[i]:.1f} bal\n"
            netice_metni += f"\n-------------------------------------\n🏆 *ÜMUMİ BAL:* {total_bal:.1f}"
        
        elif imtahan_tipi.startswith('buraxilis'):
            bal_az = bal_ingilis = bal_riyaziyyat = 0.0
            if imtahan_tipi == 'buraxilis_11':
                bal_az = ((2 * sum(float(v) for v in data.get('az_dili_cedvel_secimleri', {}).values()) + data.get('az_dili_qapali', 0)) * 5) / 2
                bal_ingilis = (100 / 37) * (2 * sum(float(v) for v in data.get('ingilis_cedvel_secimleri', {}).values()) + data.get('ingilis_qapali', 0))
                bal_riyaziyyat = (25 / 8) * (2 * sum(float(v) for v in data.get('riyaziyyat_cedvel_secimleri', {}).values()) + data.get('riyaziyyat_qapali', 0) + data.get('riyaziyyat_kodlashdirma', 0))
            else:
                bal_az = ((2 * sum(float(v) for v in data.get('az_dili_cedvel_secimleri', {}).values()) + data.get('az_dili_qapali', 0)) * 100) / 34
                bal_riyaziyyat = ((2 * sum(float(v) for v in data.get('riyaziyyat_cedvel_secimleri', {}).values()) + data.get('riyaziyyat_kodlashdirma', 0) + data.get('riyaziyyat_qapali', 0)) * 100) / 29
                if imtahan_tipi == 'buraxilis_9_2025':
                    bal_ingilis_raw = ((data.get('ingilis_esse', 0) + data.get('ingilis_kodlashdirma', 0) + data.get('ingilis_qapali', 0)) * 100) / 30
                    bal_ingilis = min(100.0, bal_ingilis_raw)
                else:
                    bal_ingilis = ((2 * sum(float(v) for v in data.get('ingilis_cedvel_secimleri', {}).values()) + data.get('ingilis_qapali', 0)) * 100) / 34
            
            total_bal = bal_az + bal_ingilis + bal_riyaziyyat
            imtahan_basligi = imtahan_tipi.replace('_', ' ').replace('buraxilis ', '').title()
            netice_metni = (f"🎉 *Nəticəniz ({imtahan_basligi})* 🎉\n"
                            f"\n🇦🇿 *Ana dili:* {bal_az:.1f} bal\n"
                            f"\n🇬🇧 *Xarici dil:* {bal_ingilis:.1f} bal\n"
                            f"\n🧮 *Riyaziyyat:* {bal_riyaziyyat:.1f} bal\n"
                            f"\n-------------------------------------\n🏆 *ÜMUMİ BAL:* {total_bal:.1f}")
    except Exception as e:
        logger.error(f"Hesablama zamanı xəta baş verdi: {e}")
        netice_metni = "Nəticələri hesablayarkən xəta baş verdi. Zəhmət olmasa, /start ilə yenidən cəhd edin."
    
    keyboard = [[InlineKeyboardButton("🏠 Ana Səhifə", callback_data='meny_ana')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=netice_metni, parse_mode='Markdown', reply_markup=reply_markup)
    context.user_data.clear()
    return VEZIYYET_IMTAHAN_SECIMI

# --- Navigation and Command Functions ---
async def prosesi_legv_et(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    return await ana_menyunu_goster(update, context)

async def geri_get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    addim_tarixcesi = context.user_data.get('addim_tarixcesi', [])
    
    if context.user_data.get('cari_addim') in addim_tarixcesi:
        addim_tarixcesi.pop()

    if addim_tarixcesi:
        evvelki_addim = addim_tarixcesi.pop()
        context.user_data['addim_tarixcesi'] = addim_tarixcesi

        if evvelki_addim == 'meny_ana': return await ana_menyunu_goster(update, context)
        elif evvelki_addim == 'meny_buraxilish': return await buraxilis_sinif_secimini_goster(update, context)
        elif evvelki_addim == 'meny_qebul': return await qebul_qrup_secimini_goster(update, context)
        elif evvelki_addim.endswith('_altqrup'): return await qebul_altqrup_secimini_goster(update, context)
        elif 'cedvel' in evvelki_addim: return await ballandirma_cedvelini_goster(update, context, addim_adi=evvelki_addim)
        else: return await novbeti_suali_sorus(update, context, addim_adi=evvelki_addim)
    
    return await ana_menyunu_goster(update, context)

async def lazimsiz_mesaji_sil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.delete()
    except BadRequest:
        logger.info("Silinəcək lazımsız mesaj tapılmadı.")

async def temizle_ve_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Söhbət tarixçəsini təmizləyir və botu yenidən başladır."""
    chat_id = update.effective_chat.id
    current_message_id = update.message.message_id
    
    logger.info(f"'{chat_id}' üçün /clean əmri ilə ekran təmizləmə prosesi başlanır...")

    for i in range(100): # Son 100 mesajı silməyə cəhd edir
        message_id_to_delete = current_message_id - i
        
        if message_id_to_delete <= 0:
            break
        
        try:
            await context.bot.delete_message(chat_id, message_id_to_delete)
        except BadRequest:
            logger.warning(f"Mesaj {message_id_to_delete} silinə bilmədi (çox köhnə və ya mövcud deyil).")
        except Exception as e:
            logger.error(f"Mesaj silinərkən gözlənilməz xəta: {e}")
            break

    logger.info("Ekran təmizləndi. Ana menyu göstərilir.")
    
    return await ana_menyunu_goster(update, context)

# --- Main Bot Setup ---
def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', ana_menyunu_goster),
            CommandHandler('clean', temizle_ve_baslat) # 'clean' sözü əvəzinə /clean əmri
        ],
        states={
            VEZIYYET_IMTAHAN_SECIMI: [
                CallbackQueryHandler(buraxilis_sinif_secimini_goster, pattern='^meny_buraxilish$'),
                CallbackQueryHandler(qebul_qrup_secimini_goster, pattern='^meny_qebul$'),
                CallbackQueryHandler(qebul_altqrup_secimini_goster, pattern=r'^meny_qebul_[13]_altqrup$'),
                CallbackQueryHandler(imtahan_axinini_baslat, pattern='^imtahan_'),
                CallbackQueryHandler(ana_menyunu_goster, pattern='^meny_ana$'),
                CallbackQueryHandler(istifade_telimatini_goster, pattern='^meny_telimat$'),
                CallbackQueryHandler(geri_get, pattern='^geri$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lazimsiz_mesaji_sil),
            ],
            VEZIYYET_SUAL_GOZLEME: [
                CallbackQueryHandler(geri_get, pattern='^geri$'),
                CallbackQueryHandler(prosesi_legv_et, pattern='^legv_et$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, daxil_edilen_metni_yoxla),
            ],
            VEZIYYET_TESDIQ_GOZLEME: [
                CallbackQueryHandler(daxil_edilen_reqemi_tesdiqle, pattern='^tesdiq_'),
                CallbackQueryHandler(novbeti_suali_sorus, pattern=f'^(?!tesdiq_|legv_et|geri).*$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lazimsiz_mesaji_sil),
            ],
            VEZIYYET_CEDVEL_SECIMI: [
                CallbackQueryHandler(cedvel_secimini_isle, pattern='^cedvel_'),
                CallbackQueryHandler(cedveli_tesdiqle_ve_davam_et, pattern='^tesdiq_cedvel$'),
                CallbackQueryHandler(geri_get, pattern='^geri$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lazimsiz_mesaji_sil),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(prosesi_legv_et, pattern='^legv_et$'),
            CommandHandler('clean', temizle_ve_baslat), # 'clean' sözü əvəzinə /clean əmri
            CommandHandler('start', ana_menyunu_goster)
        ],
        persistent=False, name="imtahan_sohbeti"
    )

    application.add_handler(conv_handler)
    
    print("Bot işə düşdü...")
    application.run_polling()

if __name__ == "__main__":
    main()
