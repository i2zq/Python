import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import asyncio
import random
from datetime import datetime, timedelta
import time
import re

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ملفات التخزين
SETTINGS_FILE = "guild_settings.json"
BANK_FILE = "bank_data.json"
WARNINGS_FILE = "warnings.json"
AZKAR_FILE = "azkar.json"

# تحميل الإعدادات
def load_file(filename, default=None):
    if default is None:
        default = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

guild_settings = load_file(SETTINGS_FILE)
bank_data = load_file(BANK_FILE)
warnings_data = load_file(WARNINGS_FILE)

# قائمة الأذكار الافتراضية
default_azkar = [
    "سبحان الله وبحمده، سبحان الله العظيم",
    "لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
    "اللهم صل وسلم على نبينا محمد",
    "أستغفر الله العظيم الذي لا إله إلا هو الحي القيوم وأتوب إليه",
    "الحمد لله رب العالمين",
    "لا حول ولا قوة إلا بالله العلي العظيم",
    "سبحان الله، والحمد لله، ولا إله إلا الله، والله أكبر",
    "اللهم أعنا على ذكرك وشكرك وحسن عبادتك"
]

# قائمة الكلمات الممنوعة الافتراضية
default_banned_words = ["كلمة1", "كلمة2", "كلمة3"]

# ================================
# ✅ نظام اللوق Logs (مطور كامل)
# ================================

def get_log_channel(guild_id, log_type="general"):
    settings = guild_settings.get(str(guild_id), {})
    logs_config = settings.get("logs", {})
    
    if logs_config.get("enabled", False):
        if logs_config.get("separate_channels", False):
            return logs_config.get("channels", {}).get(log_type)
        else:
            return logs_config.get("channel")
    return None

def create_log_embed(title, description, color=0x3498db):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    return embed

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    channel_id = get_log_channel(message.guild.id, "message")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            embed = create_log_embed(
                "🗑️ رسالة محذوفة",
                f"**العضو:** {message.author.mention}\n**القناة:** {message.channel.mention}\n**المحتوى:** {message.content[:1024] if message.content else 'لا يوجد محتوى'}",
                0xe74c3c
            )
            embed.set_author(name=str(message.author), icon_url=message.author.avatar.url if message.author.avatar else None)
            await channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    
    channel_id = get_log_channel(before.guild.id, "message")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            embed = create_log_embed(
                "📝 رسالة معدلة",
                f"**العضو:** {before.author.mention}\n**القناة:** {before.channel.mention}\n**قبل:** {before.content[:500] if before.content else 'لا يوجد محتوى'}\n**بعد:** {after.content[:500] if after.content else 'لا يوجد محتوى'}",
                0xf39c12
            )
            embed.set_author(name=str(before.author), icon_url=before.author.avatar.url if before.author.avatar else None)
            await channel.send(embed=embed)

@bot.event
async def on_guild_channel_create(channel):
    channel_id = get_log_channel(channel.guild.id, "channel")
    if channel_id:
        log_channel = bot.get_channel(channel_id)
        if log_channel:
            embed = create_log_embed(
                "📢 قناة جديدة",
                f"**اسم القناة:** {channel.name}\n**النوع:** {channel.type}\n**الفئة:** {channel.category.name if channel.category else 'بدون فئة'}",
                0x2ecc71
            )
            await log_channel.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    channel_id = get_log_channel(channel.guild.id, "channel")
    if channel_id:
        log_channel = bot.get_channel(channel_id)
        if log_channel:
            embed = create_log_embed(
                "🗑️ قناة محذوفة",
                f"**اسم القناة:** {channel.name}\n**النوع:** {channel.type}\n**الفئة:** {channel.category.name if channel.category else 'بدون فئة'}",
                0xe74c3c
            )
            await log_channel.send(embed=embed)

@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        channel_id = get_log_channel(before.guild.id, "member")
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel:
                embed = create_log_embed(
                    "👤 تغيير الاسم المستعار",
                    f"**العضو:** {after.mention}\n**قبل:** {before.nick or before.name}\n**بعد:** {after.nick or after.name}",
                    0x9b59b6
                )
                embed.set_author(name=str(after), icon_url=after.avatar.url if after.avatar else None)
                await channel.send(embed=embed)

@bot.event
async def on_member_join(member):
    # نظام الترحيب
    settings = guild_settings.get(str(member.guild.id), {})
    welcome_config = settings.get("welcome", {})
    
    if welcome_config.get("enabled", False) and welcome_config.get("channel"):
        channel = bot.get_channel(welcome_config["channel"])
        if channel:
            embed = discord.Embed(
                title="🎉 مرحباً بك!",
                description=f"أهلاً وسهلاً {member.mention} في **{member.guild.name}**!\n\nأنت العضو رقم **{member.guild.member_count}**",
                color=0x2ecc71
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_footer(text=f"انضم في {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            await channel.send(embed=embed)
    
    # لوق الانضمام
    channel_id = get_log_channel(member.guild.id, "member")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            embed = create_log_embed(
                "📥 عضو جديد",
                f"**العضو:** {member.mention}\n**الحساب:** {member.name}\n**تاريخ الانضمام:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n**عدد الأعضاء:** {member.guild.member_count}",
                0x2ecc71
            )
            embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel_id = get_log_channel(member.guild.id, "member")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            embed = create_log_embed(
                "📤 عضو غادر",
                f"**العضو:** {member.mention}\n**الحساب:** {member.name}\n**تاريخ المغادرة:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n**عدد الأعضاء:** {member.guild.member_count}",
                0xe74c3c
            )
            embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
            await channel.send(embed=embed)

@bot.event
async def on_member_ban(guild, user):
    channel_id = get_log_channel(guild.id, "moderation")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            embed = create_log_embed(
                "🔨 عضو محظور",
                f"**العضو:** {user.mention}\n**الحساب:** {user.name}\n**تاريخ الحظر:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                0x992d22
            )
            embed.set_author(name=str(user), icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
            await channel.send(embed=embed)

@bot.event
async def on_member_unban(guild, user):
    channel_id = get_log_channel(guild.id, "moderation")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            embed = create_log_embed(
                "🔓 إلغاء حظر",
                f"**العضو:** {user.mention}\n**الحساب:** {user.name}\n**تاريخ إلغاء الحظر:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                0x27ae60
            )
            embed.set_author(name=str(user), icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
            await channel.send(embed=embed)

# ================================
# 🎫 نظام التذاكر Tickets (مطور كامل)
# ================================

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="إنشاء تذكرة", style=discord.ButtonStyle.primary, emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = guild_settings.get(str(interaction.guild.id), {})
        ticket_config = settings.get("tickets", {})
        
        if not ticket_config.get("enabled", False):
            await interaction.response.send_message("❌ نظام التذاكر غير مفعل!", ephemeral=True)
            return
        
        # تحقق من وجود تذكرة مسبقة
        existing_ticket = None
        for channel in interaction.guild.channels:
            if channel.name == f"ticket-{interaction.user.name.lower()}":
                existing_ticket = channel
                break
        
        if existing_ticket:
            await interaction.response.send_message(f"❌ لديك تذكرة مفتوحة بالفعل: {existing_ticket.mention}", ephemeral=True)
            return
        
        # إنشاء الفئة إذا لم تكن موجودة
        category = None
        if ticket_config.get("category"):
            category = bot.get_channel(ticket_config["category"])
        
        if not category:
            category = await interaction.guild.create_category("🎫 التذاكر")
        
        # إنشاء القناة
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        # إضافة أدوار الموظفين
        staff_roles = ticket_config.get("staff_roles", [])
        for role_id in staff_roles:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        ticket_channel = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.name.lower()}",
            category=category,
            overwrites=overwrites
        )
        
        # إرسال رسالة التذكرة
        embed = discord.Embed(
            title="🎫 تذكرة جديدة",
            description=f"مرحباً {interaction.user.mention}!\n\nتم إنشاء تذكرتك بنجاح. يرجى شرح مشكلتك أو استفسارك وسيتم الرد عليك في أقرب وقت.",
            color=0x3498db
        )
        embed.set_footer(text="للإغلاق، اضغط على الزر أدناه")
        
        close_view = TicketCloseView()
        await ticket_channel.send(embed=embed, view=close_view)
        
        await interaction.response.send_message(f"✅ تم إنشاء تذكرتك: {ticket_channel.mention}", ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="إغلاق التذكرة", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔒 إغلاق التذكرة",
            description="هل أنت متأكد من إغلاق هذه التذكرة؟",
            color=0xe74c3c
        )
        
        confirm_view = TicketConfirmView()
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class TicketConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="نعم، أغلق", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 جاري إغلاق التذكرة...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.followup.send("✅ تم إغلاق التذكرة!")
        await interaction.channel.delete()
    
    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ تم إلغاء إغلاق التذكرة", ephemeral=True)

@bot.tree.command(name="ticket_panel", description="إرسال لوحة التذاكر")
@app_commands.describe(channel="القناة المراد إرسال اللوحة إليها")
async def ticket_panel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ ليس لديك صلاحية لاستخدام هذا الأمر!", ephemeral=True)
        return
    
    target_channel = channel or interaction.channel
    
    embed = discord.Embed(
        title="🎫 نظام التذاكر",
        description="اضغط على الزر أدناه لإنشاء تذكرة جديدة\n\n📋 **ملاحظات:**\n• يمكنك إنشاء تذكرة واحدة فقط\n• سيتم الرد عليك في أقرب وقت\n• لا تقم بإنشاء تذاكر وهمية",
        color=0x3498db
    )
    embed.set_footer(text="نظام التذاكر | البوت الشامل")
    
    view = TicketView()
    await target_channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ تم إرسال لوحة التذاكر إلى {target_channel.mention}", ephemeral=True)

# ================================
# 🚫 فلتر الكلمات (مطور كامل)
# ================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    settings = guild_settings.get(str(message.guild.id), {})
    filter_config = settings.get("word_filter", {})
    
    if filter_config.get("enabled", False):
        banned_words = filter_config.get("words", default_banned_words)
        
        for word in banned_words:
            if word.lower() in message.content.lower():
                await message.delete()
                
                embed = discord.Embed(
                    title="⚠️ كلمة ممنوعة",
                    description=f"{message.author.mention} تم حذف رسالتك لاحتوائها على كلمة ممنوعة!",
                    color=0xe74c3c
                )
                
                warning_msg = await message.channel.send(embed=embed)
                await asyncio.sleep(5)
                await warning_msg.delete()
                
                # إرسال تنبيه للوق
                channel_id = get_log_channel(message.guild.id, "moderation")
                if channel_id:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        log_embed = create_log_embed(
                            "🚫 كلمة ممنوعة",
                            f"**العضو:** {message.author.mention}\n**القناة:** {message.channel.mention}\n**الكلمة:** {word}\n**الرسالة:** {message.content[:500]}",
                            0xe74c3c
                        )
                        await channel.send(embed=log_embed)
                return
    
    await bot.process_commands(message)

# ================================
# 📢 نظام البث Broadcast (مطور كامل)
# ================================

@bot.tree.command(name="broadcast", description="إرسال رسالة لجميع الأعضاء")
@app_commands.describe(message="الرسالة المراد إرسالها")
async def broadcast(interaction: discord.Interaction, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ ليس لديك صلاحية لاستخدام هذا الأمر!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📢 إرسال البث",
        description=f"هل أنت متأكد من إرسال هذه الرسالة لجميع الأعضاء؟\n\n**الرسالة:**\n{message}",
        color=0xf39c12
    )
    
    view = BroadcastView(message)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class BroadcastView(discord.ui.View):
    def __init__(self, message):
        super().__init__(timeout=60)
        self.message = message
    
    @discord.ui.button(label="نعم، أرسل", style=discord.ButtonStyle.primary, emoji="✅")
    async def confirm_broadcast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📤 جاري إرسال الرسالة...", ephemeral=True)
        
        success_count = 0
        failed_count = 0
        
        embed = discord.Embed(
            title="📢 رسالة من إدارة السيرفر",
            description=self.message,
            color=0x3498db
        )
        embed.set_footer(text=f"من سيرفر: {interaction.guild.name}")
        
        for member in interaction.guild.members:
            if not member.bot:
                try:
                    await member.send(embed=embed)
                    success_count += 1
                    await asyncio.sleep(0.5)  # لتجنب الحد الأقصى
                except:
                    failed_count += 1
        
        result_embed = discord.Embed(
            title="📊 نتيجة البث",
            description=f"✅ تم الإرسال بنجاح: {success_count}\n❌ فشل الإرسال: {failed_count}",
            color=0x2ecc71
        )
        await interaction.followup.send(embed=result_embed, ephemeral=True)
    
    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_broadcast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ تم إلغاء البث", ephemeral=True)

# ================================
# 🎮 نظام الألعاب (مطور كامل)
# ================================

@bot.tree.command(name="play", description="لعب الألعاب المختلفة")
@app_commands.describe(game="اختر اللعبة")
@app_commands.choices(game=[
    app_commands.Choice(name="تخمين الرقم", value="guess"),
    app_commands.Choice(name="حجر ورقة مقص", value="rps"),
    app_commands.Choice(name="صح أم خطأ", value="truefalse"),
    app_commands.Choice(name="أسرع كتابة", value="fasttype"),
    app_commands.Choice(name="أسئلة عامة", value="trivia")
])
async def play_game(interaction: discord.Interaction, game: str):
    if game == "guess":
        await start_guess_game(interaction)
    elif game == "rps":
        await start_rps_game(interaction)
    elif game == "truefalse":
        await start_truefalse_game(interaction)
    elif game == "fasttype":
        await start_fasttype_game(interaction)
    elif game == "trivia":
        await start_trivia_game(interaction)

# لعبة تخمين الرقم
async def start_guess_game(interaction):
    number = random.randint(1, 100)
    attempts = 0
    max_attempts = 7
    
    embed = discord.Embed(
        title="🎯 لعبة تخمين الرقم",
        description=f"خمّن الرقم من 1 إلى 100!\nلديك {max_attempts} محاولات",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed)
    
    def check(msg):
        return msg.author == interaction.user and msg.channel == interaction.channel
    
    while attempts < max_attempts:
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            attempts += 1
            
            if not msg.content.isdigit():
                await msg.reply("❌ يرجى إدخال رقم صحيح!")
                continue
            
            guess = int(msg.content)
            
            if guess == number:
                reward = 50 - (attempts * 5)
                add_money(interaction.user.id, reward)
                
                embed = discord.Embed(
                    title="🎉 تهانينا!",
                    description=f"لقد خمّنت الرقم {number} في {attempts} محاولة!\n💰 حصلت على {reward} عملة",
                    color=0x2ecc71
                )
                await msg.reply(embed=embed)
                return
            elif guess < number:
                await msg.reply(f"📈 الرقم أكبر من {guess}! المحاولات المتبقية: {max_attempts - attempts}")
            else:
                await msg.reply(f"📉 الرقم أصغر من {guess}! المحاولات المتبقية: {max_attempts - attempts}")
                
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ انتهت المهلة الزمنية!")
            return
    
    embed = discord.Embed(
        title="😞 انتهت المحاولات",
        description=f"كان الرقم هو {number}",
        color=0xe74c3c
    )
    await interaction.followup.send(embed=embed)

# لعبة حجر ورقة مقص
class RPSView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user
        self.choices = {"🪨": "حجر", "📄": "ورقة", "✂️": "مقص"}
    
    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play_rps(interaction, "🪨")
    
    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play_rps(interaction, "📄")
    
    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play_rps(interaction, "✂️")
    
    async def play_rps(self, interaction, user_choice):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ هذه ليست لعبتك!", ephemeral=True)
            return
        
        bot_choice = random.choice(list(self.choices.keys()))
        
        result = ""
        reward = 0
        
        if user_choice == bot_choice:
            result = "🤝 تعادل!"
            reward = 10
        elif (user_choice == "🪨" and bot_choice == "✂️") or \
             (user_choice == "📄" and bot_choice == "🪨") or \
             (user_choice == "✂️" and bot_choice == "📄"):
            result = "🎉 فزت!"
            reward = 30
        else:
            result = "😞 خسرت!"
            reward = 5
        
        add_money(interaction.user.id, reward)
        
        embed = discord.Embed(
            title="🎮 حجر ورقة مقص",
            description=f"**اختيارك:** {user_choice} {self.choices[user_choice]}\n**اختيار البوت:** {bot_choice} {self.choices[bot_choice]}\n\n{result}\n💰 حصلت على {reward} عملة",
            color=0x3498db
        )
        await interaction.response.edit_message(embed=embed, view=None)

async def start_rps_game(interaction):
    embed = discord.Embed(
        title="🎮 حجر ورقة مقص",
        description="اختر حجر أو ورقة أو مقص!",
        color=0x3498db
    )
    view = RPSView(interaction.user)
    await interaction.response.send_message(embed=embed, view=view)

# لعبة صح أم خطأ
async def start_truefalse_game(interaction):
    questions = [
        {"question": "الشمس تشرق من الشرق", "answer": True},
        {"question": "القطط تحب الماء", "answer": False},
        {"question": "الأرض مسطحة", "answer": False},
        {"question": "الماء يتجمد عند 0 درجة مئوية", "answer": True},
        {"question": "الحوت من الأسماك", "answer": False},
        {"question": "الفيل أكبر الحيوانات البرية", "answer": True},
        {"question": "القمر يضيء بنور ذاتي", "answer": False},
        {"question": "العنكبوت له 8 أرجل", "answer": True}
    ]
    
    question_data = random.choice(questions)
    
    embed = discord.Embed(
        title="❓ صح أم خطأ",
        description=f"**السؤال:** {question_data['question']}\n\nاختر الإجابة الصحيحة!",
        color=0x3498db
    )
    
    view = TrueFalseView(interaction.user, question_data['answer'])
    await interaction.response.send_message(embed=embed, view=view)

class TrueFalseView(discord.ui.View):
    def __init__(self, user, correct_answer):
        super().__init__(timeout=30)
        self.user = user
        self.correct_answer = correct_answer
    
    @discord.ui.button(label="صح", style=discord.ButtonStyle.success, emoji="✅")
    async def true_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question(interaction, True)
    
    @discord.ui.button(label="خطأ", style=discord.ButtonStyle.danger, emoji="❌")
    async def false_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question(interaction, False)
    
    async def answer_question(self, interaction, user_answer):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ هذه ليست لعبتك!", ephemeral=True)
            return
        
        if user_answer == self.correct_answer:
            result = "🎉 إجابة صحيحة!"
            reward = 25
            color = 0x2ecc71
        else:
            result = "😞 إجابة خاطئة!"
            reward = 5
            color = 0xe74c3c
        
        add_money(interaction.user.id, reward)
        
        embed = discord.Embed(
            title="❓ صح أم خطأ",
            description=f"{result}\n**الإجابة الصحيحة:** {'صح' if self.correct_answer else 'خطأ'}\n💰 حصلت على {reward} عملة",
            color=color
        )
        await interaction.response.edit_message(embed=embed, view=None)

# لعبة أسرع كتابة
async def start_fasttype_game(interaction):
    words = ["البرمجة", "الحاسوب", "الإنترنت", "التكنولوجيا", "الذكاء الاصطناعي", "البيانات", "الشبكة", "الخوارزمية"]
    target_word = random.choice(words)
    
    embed = discord.Embed(
        title="⚡ أسرع كتابة",
        description=f"اكتب هذه الكلمة بأسرع ما يمكن:\n\n**{target_word}**",
        color=0xf39c12
    )
    
    await interaction.response.send_message(embed=embed)
    start_time = time.time()
    
    def check(msg):
        return msg.author == interaction.user and msg.channel == interaction.channel
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=15.0)
        end_time = time.time()
        typing_time = round(end_time - start_time, 2)
        
        if msg.content.strip() == target_word:
            if typing_time < 3:
                reward = 50
                grade = "ممتاز"
            elif typing_time < 5:
                reward = 30
                grade = "جيد جداً"
            elif typing_time < 8:
                reward = 20
                grade = "جيد"
            else:
                reward = 10
                grade = "مقبول"
            
            add_money(interaction.user.id, reward)
            
            embed = discord.Embed(
                title="🎉 إجابة صحيحة!",
                description=f"**الوقت:** {typing_time} ثانية\n**التقييم:** {grade}\n💰 حصلت على {reward} عملة",
                color=0x2ecc71
            )
            await msg.reply(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ خطأ في الكتابة",
                description=f"الكلمة الصحيحة: **{target_word}**\nكتبت: **{msg.content}**",
                color=0xe74c3c
            )
            await msg.reply(embed=embed)
            
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ انتهت المهلة الزمنية!")

# لعبة الأسئلة العامة
async def start_trivia_game(interaction):
    questions = [
        {"question": "ما هي عاصمة السعودية؟", "options": ["الرياض", "جدة", "الدمام", "مكة"], "answer": 0},
        {"question": "كم عدد أيام السنة؟", "options": ["364", "365", "366", "367"], "answer": 1},
        {"question": "ما هو أكبر كوكب في المجموعة الشمسية؟", "options": ["الأرض", "المريخ", "المشتري", "زحل"], "answer": 2},
        {"question": "من هو مؤسس شركة مايكروسوفت؟", "options": ["ستيف جوبز", "بيل غيتس", "مارك زوكربيرغ", "إيلون ماسك"], "answer": 1},
        {"question": "كم عدد قارات العالم؟", "options": ["5", "6", "7", "8"], "answer": 2}
    ]
    
    question_data = random.choice(questions)
    
    embed = discord.Embed(
        title="🧠 أسئلة عامة",
        description=f"**السؤال:** {question_data['question']}\n\nاختر الإجابة الصحيحة:",
        color=0x9b59b6
    )
    
    view = TriviaView(interaction.user, question_data)
    await interaction.response.send_message(embed=embed, view=view)

class TriviaView(discord.ui.View):
    def __init__(self, user, question_data):
        super().__init__(timeout=30)
        self.user = user
        self.question_data = question_data
        
        for i, option in enumerate(question_data['options']):
            button = discord.ui.Button(label=f"{i+1}. {option}", style=discord.ButtonStyle.secondary)
            button.callback = self.create_callback(i)
            self.add_item(button)
    
    def create_callback(self, index):
        async def callback(interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("❌ هذه ليست لعبتك!", ephemeral=True)
                return
            
            if index == self.question_data['answer']:
                result = "🎉 إجابة صحيحة!"
                reward = 40
                color = 0x2ecc71
            else:
                result = "😞 إجابة خاطئة!"
                reward = 10
                color = 0xe74c3c
            
            add_money(interaction.user.id, reward)
            
            embed = discord.Embed(
                title="🧠 أسئلة عامة",
                description=f"{result}\n**الإجابة الصحيحة:** {self.question_data['options'][self.question_data['answer']]}\n💰 حصلت على {reward} عملة",
                color=color
            )
            await interaction.response.edit_message(embed=embed, view=None)
        
        return callback

# ================================
# ⚒️ نظام الإدارة (مطور كامل)
# ================================

def add_warning(user_id, guild_id, reason, moderator_id):
    key = f"{guild_id}_{user_id}"
    if key not in warnings_data:
        warnings_data[key] = []
    
    warning = {
        "reason": reason,
        "moderator": moderator_id,
        "timestamp": datetime.now().isoformat()
    }
    warnings_data[key].append(warning)
    save_file(WARNINGS_FILE, warnings_data)

@bot.tree.command(name="mute", description="كتم عضو")
@app_commands.describe(member="العضو المراد كتمه", duration="مدة الكتم بالدقائق", reason="سبب الكتم")
async def mute_member(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "لم يتم تحديد سبب"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ ليس لديك صلاحية لاستخدام هذا الأمر!", ephemeral=True)
        return
    
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ لا يمكنك كتم هذا العضو!", ephemeral=True)
        return
    
    try:
        until = datetime.now() + timedelta(minutes=duration)
        await member.timeout(until, reason=reason)
        
        embed = discord.Embed(
            title="🔇 تم كتم العضو",
            description=f"**العضو:** {member.mention}\n**المدة:** {duration} دقيقة\n**السبب:** {reason}\n**بواسطة:** {interaction.user.mention}",
            color=0xf39c12
        )
        
        await interaction.response.send_message(embed=embed)
        
        # إرسال رسالة للعضو
        try:
            dm_embed = discord.Embed(
                title="🔇 تم كتمك",
                description=f"**السيرفر:** {interaction.guild.name}\n**المدة:** {duration} دقيقة\n**السبب:** {reason}",
                color=0xe74c3c
            )
            await member.send(embed=dm_embed)
        except:
            pass
        
        # لوق الكتم
        channel_id = get_log_channel(interaction.guild.id, "moderation")
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel:
                log_embed = create_log_embed(
                    "🔇 كتم عضو",
                    f"**العضو:** {member.mention}\n**المدة:** {duration} دقيقة\n**السبب:** {reason}\n**بواسطة:** {interaction.user.mention}",
                    0xf39c12
                )
                await channel.send(embed=log_embed)
                
    except Exception as e:
        await interaction.response.send_message(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.tree.command(name="ban", description="حظر عضو")
@app_commands.describe(member="العضو المراد حظره", reason="سبب الحظر")
async def ban_member(interaction: discord.Interaction, member: discord.Member, reason: str = "لم يتم تحديد سبب"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ ليس لديك صلاحية لاستخدام هذا الأمر!", ephemeral=True)
        return
    
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ لا يمكنك حظر هذا العضو!", ephemeral=True)
        return
    
    try:
        # إرسال رسالة للعضو قبل الحظر
        try:
            dm_embed = discord.Embed(
                title="🔨 تم حظرك",
                description=f"**السيرفر:** {interaction.guild.name}\n**السبب:** {reason}",
                color=0xe74c3c
            )
            await member.send(embed=dm_embed)
        except:
            pass
        
        await member.ban(reason=reason)
        
        embed = discord.Embed(
            title="🔨 تم حظر العضو",
            description=f"**العضو:** {member.mention}\n**السبب:** {reason}\n**بواسطة:** {interaction.user.mention}",
            color=0xe74c3c
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.tree.command(name="warn", description="تحذير عضو")
@app_commands.describe(member="العضو المراد تحذيره", reason="سبب التحذير")
async def warn_member(interaction: discord.Interaction, member: discord.Member, reason: str = "لم يتم تحديد سبب"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ ليس لديك صلاحية لاستخدام هذا الأمر!", ephemeral=True)
        return
    
    add_warning(member.id, interaction.guild.id, reason, interaction.user.id)
    
    # حساب عدد التحذيرات
    key = f"{interaction.guild.id}_{member.id}"
    warning_count = len(warnings_data.get(key, []))
    
    embed = discord.Embed(
        title="⚠️ تحذير",
        description=f"**العضو:** {member.mention}\n**السبب:** {reason}\n**بواسطة:** {interaction.user.mention}\n**عدد التحذيرات:** {warning_count}",
        color=0xf39c12
    )
    
    await interaction.response.send_message(embed=embed)
    
    # إرسال رسالة للعضو
    try:
        dm_embed = discord.Embed(
            title="⚠️ تحذير",
            description=f"**السيرفر:** {interaction.guild.name}\n**السبب:** {reason}\n**عدد التحذيرات:** {warning_count}",
            color=0xf39c12
        )
        await member.send(embed=dm_embed)
    except:
        pass

@bot.tree.command(name="warnings", description="عرض تحذيرات العضو")
@app_commands.describe(member="العضو المراد عرض تحذيراته")
async def show_warnings(interaction: discord.Interaction, member: discord.Member):
    key = f"{interaction.guild.id}_{member.id}"
    warnings = warnings_data.get(key, [])
    
    if not warnings:
        embed = discord.Embed(
            title="✅ لا توجد تحذيرات",
            description=f"{member.mention} لم يحصل على أي تحذيرات",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"⚠️ تحذيرات {member.display_name}",
        description=f"**عدد التحذيرات:** {len(warnings)}",
        color=0xf39c12
    )
    
    for i, warning in enumerate(warnings[-5:], 1):  # آخر 5 تحذيرات
        moderator = bot.get_user(warning['moderator'])
        moderator_name = moderator.display_name if moderator else "مجهول"
        
        embed.add_field(
            name=f"تحذير #{i}",
            value=f"**السبب:** {warning['reason']}\n**بواسطة:** {moderator_name}\n**التاريخ:** {warning['timestamp'][:10]}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ================================
# 💰 نظام البنك (مطور كامل)
# ================================

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in bank_data:
        bank_data[user_id] = {
            "balance": 0,
            "bank": 0,
            "last_daily": None,
            "last_work": None,
            "investments": {},
            "items": {}
        }
        save_file(BANK_FILE, bank_data)
    return bank_data[user_id]

def add_money(user_id, amount):
    user_data = get_user_data(user_id)
    user_data["balance"] += amount
    save_file(BANK_FILE, bank_data)

def remove_money(user_id, amount):
    user_data = get_user_data(user_id)
    if user_data["balance"] >= amount:
        user_data["balance"] -= amount
        save_file(BANK_FILE, bank_data)
        return True
    return False

@bot.tree.command(name="daily", description="الحصول على الراتب اليومي")
async def daily_reward(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    
    if user_data["last_daily"]:
        last_daily = datetime.fromisoformat(user_data["last_daily"])
        if datetime.now() - last_daily < timedelta(days=1):
            remaining = timedelta(days=1) - (datetime.now() - last_daily)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            
            embed = discord.Embed(
                title="⏰ راتبك اليومي غير جاهز",
                description=f"يمكنك الحصول على راتبك بعد {hours} ساعة و {minutes} دقيقة",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed)
            return
    
    reward = random.randint(100, 500)
    bonus = random.randint(1, 100)
    
    if bonus <= 10:  # 10% احتمال للحصول على مكافأة إضافية
        reward *= 2
        bonus_text = "\n🎉 مكافأة مضاعفة!"
    else:
        bonus_text = ""
    
    add_money(interaction.user.id, reward)
    user_data["last_daily"] = datetime.now().isoformat()
    save_file(BANK_FILE, bank_data)
    
    embed = discord.Embed(
        title="💰 راتبك اليومي",
        description=f"حصلت على **{reward}** عملة!{bonus_text}\n\n**رصيدك الحالي:** {user_data['balance']} عملة",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="balance", description="عرض الرصيد")
@app_commands.describe(member="العضو المراد عرض رصيده (اختياري)")
async def show_balance(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    user_data = get_user_data(target.id)
    
    total_wealth = user_data["balance"] + user_data["bank"]
    
    embed = discord.Embed(
        title=f"💰 رصيد {target.display_name}",
        color=0x3498db
    )
    embed.add_field(name="💵 النقود", value=f"{user_data['balance']:,} عملة", inline=True)
    embed.add_field(name="🏦 البنك", value=f"{user_data['bank']:,} عملة", inline=True)
    embed.add_field(name="💎 إجمالي الثروة", value=f"{total_wealth:,} عملة", inline=True)
    
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="work", description="العمل للحصول على المال")
async def work_command(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    
    if user_data["last_work"]:
        last_work = datetime.fromisoformat(user_data["last_work"])
        if datetime.now() - last_work < timedelta(hours=1):
            remaining = timedelta(hours=1) - (datetime.now() - last_work)
            minutes = int(remaining.total_seconds() // 60)
            
            embed = discord.Embed(
                title="⏰ أنت متعب",
                description=f"يمكنك العمل مرة أخرى بعد {minutes} دقيقة",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed)
            return
    
    jobs = [
        {"name": "مبرمج", "min": 50, "max": 150},
        {"name": "مصمم", "min": 40, "max": 120},
        {"name": "كاتب", "min": 30, "max": 100},
        {"name": "مترجم", "min": 35, "max": 110},
        {"name": "محاسب", "min": 45, "max": 130}
    ]
    
    job = random.choice(jobs)
    earned = random.randint(job["min"], job["max"])
    
    add_money(interaction.user.id, earned)
    user_data["last_work"] = datetime.now().isoformat()
    save_file(BANK_FILE, bank_data)
    
    embed = discord.Embed(
        title="💼 العمل",
        description=f"عملت كـ **{job['name']}** وحصلت على **{earned}** عملة!\n\n**رصيدك الحالي:** {user_data['balance']} عملة",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deposit", description="إيداع المال في البنك")
@app_commands.describe(amount="المبلغ المراد إيداعه")
async def deposit_money(interaction: discord.Interaction, amount: int):
    user_data = get_user_data(interaction.user.id)
    
    if amount <= 0:
        await interaction.response.send_message("❌ يجب أن يكون المبلغ أكبر من صفر!", ephemeral=True)
        return
    
    if amount > user_data["balance"]:
        await interaction.response.send_message("❌ ليس لديك رصيد كافي!", ephemeral=True)
        return
    
    user_data["balance"] -= amount
    user_data["bank"] += amount
    save_file(BANK_FILE, bank_data)
    
    embed = discord.Embed(
        title="🏦 إيداع ناجح",
        description=f"تم إيداع **{amount:,}** عملة في البنك\n\n**النقود:** {user_data['balance']:,} عملة\n**البنك:** {user_data['bank']:,} عملة",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="withdraw", description="سحب المال من البنك")
@app_commands.describe(amount="المبلغ المراد سحبه")
async def withdraw_money(interaction: discord.Interaction, amount: int):
    user_data = get_user_data(interaction.user.id)
    
    if amount <= 0:
        await interaction.response.send_message("❌ يجب أن يكون المبلغ أكبر من صفر!", ephemeral=True)
        return
    
    if amount > user_data["bank"]:
        await interaction.response.send_message("❌ ليس لديك رصيد كافي في البنك!", ephemeral=True)
        return
    
    user_data["bank"] -= amount
    user_data["balance"] += amount
    save_file(BANK_FILE, bank_data)
    
    embed = discord.Embed(
        title="💳 سحب ناجح",
        description=f"تم سحب **{amount:,}** عملة من البنك\n\n**النقود:** {user_data['balance']:,} عملة\n**البنك:** {user_data['bank']:,} عملة",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="لوحة المتصدرين")
async def leaderboard(interaction: discord.Interaction):
    # ترتيب الأعضاء حسب إجمالي الثروة
    sorted_users = []
    for user_id, data in bank_data.items():
        user = bot.get_user(int(user_id))
        if user and user in interaction.guild.members:
            total_wealth = data["balance"] + data["bank"]
            sorted_users.append((user, total_wealth))
    
    sorted_users.sort(key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(
        title="🏆 لوحة أغنى الأعضاء",
        color=0xf1c40f
    )
    
    for i, (user, wealth) in enumerate(sorted_users[:10], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        embed.add_field(
            name=f"{medal} {user.display_name}",
            value=f"{wealth:,} عملة",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ================================
# 📿 نظام الأذكار (مطور كامل)
# ================================

@tasks.loop(minutes=30)  # تغيير إلى 30 دقيقة لتجنب الإزعاج
async def send_azkar():
    for guild_id, settings in guild_settings.items():
        azkar_config = settings.get("azkar", {})
        
        if azkar_config.get("enabled", False) and azkar_config.get("channel"):
            channel = bot.get_channel(azkar_config["channel"])
            if channel:
                zikr = random.choice(default_azkar)
                
                embed = discord.Embed(
                    title="📿 ذكر",
                    description=zikr,
                    color=0x27ae60
                )
                embed.set_footer(text="اللهم اجعلنا من الذاكرين الله كثيراً")
                
                await channel.send(embed=embed)

# ================================
# 🔊 نظام الغرف الصوتية المؤقتة (مطور كامل)
# ================================

temp_voice_channels = {}

class VoiceControlView(discord.ui.View):
    def __init__(self, owner_id, channel_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.channel_id = channel_id

    @discord.ui.button(label="تغيير الاسم", style=discord.ButtonStyle.primary, emoji="✏️")
    async def change_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ فقط مالك الغرفة يمكنه استخدام هذا!", ephemeral=True)
            return

        modal = ChangeNameModal(self.channel_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="قفل الغرفة", style=discord.ButtonStyle.secondary, emoji="🔒")
    async def lock_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ فقط مالك الغرفة يمكنه استخدام هذا!", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("✅ تم قفل الغرفة!", ephemeral=True)

    @discord.ui.button(label="فتح الغرفة", style=discord.ButtonStyle.success, emoji="🔓")
    async def unlock_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ فقط مالك الغرفة يمكنه استخدام هذا!", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        await channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("✅ تم فتح الغرفة!", ephemeral=True)

    @discord.ui.button(label="طرد عضو", style=discord.ButtonStyle.danger, emoji="🚫")
    async def kick_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ فقط مالك الغرفة يمكنه استخدام هذا!", ephemeral=True)
            return

        await interaction.response.send_message("👤 من تريد منعه من دخول الغرفة؟ اكتب منشن له.", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            member = msg.mentions[0]
            channel = interaction.guild.get_channel(self.channel_id)
            await channel.set_permissions(member, connect=False)
            await interaction.followup.send(f"✅ تم منع {member.mention} من دخول الغرفة!", ephemeral=True)
        except Exception:
            await interaction.followup.send("❌ لم يتم العثور على العضو أو انتهى الوقت.", ephemeral=True)

    @discord.ui.button(label="حذف الغرفة", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ فقط مالك الغرفة يمكنه استخدام هذا!", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        await channel.delete(reason="حذف تلقائي عبر Temp Voice")
        await interaction.response.send_message("🗑️ تم حذف الغرفة!", ephemeral=True)

class ChangeNameModal(discord.ui.Modal, title="تغيير اسم الغرفة"):
    new_name = discord.ui.TextInput(label="اسم الغرفة الجديد", max_length=50)

    def __init__(self, channel_id):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        await channel.edit(name=self.new_name.value)
        await interaction.response.send_message(f"✏️ تم تغيير اسم الغرفة إلى `{self.new_name.value}`.", ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = str(member.guild.id)
    settings = guild_settings.get(guild_id, {})
    temp_channel_id = settings.get("temp_voice_create")

    if after.channel and after.channel.id == temp_channel_id:
        category = after.channel.category
        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(connect=False),
            member: discord.PermissionOverwrite(connect=True, manage_channels=True)
        }
        temp_channel = await member.guild.create_voice_channel(
            name=f"🔊 {member.name}",
            category=category,
            overwrites=overwrites,
            reason="إنشاء قناة مؤقتة"
        )

        await member.move_to(temp_channel)
        temp_voice_channels[member.id] = temp_channel.id

        control_channel_id = settings.get("temp_voice_control")
        control_channel = member.guild.get_channel(control_channel_id)
        if control_channel:
            await control_channel.send(
                content=member.mention,
                embed=discord.Embed(title="لوحة التحكم في غرفتك الصوتية", color=discord.Color.blurple()),
                view=VoiceControlView(member.id, temp_channel.id)
            )
