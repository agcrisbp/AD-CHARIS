import discord, random, os, requests, asyncio, pytz, json, lyricsgenius, aiohttp, re, httpx
from discord.ext import tasks, commands
from discord.ui import Button, View
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from discord.utils import get
from decouple import config

from cogs.fungsi.database import DataBase, DATA_SERVER, client

recent_channel_id = {"temp": {}, "user": {}, "used": {}, "reset_used": {}, "temp_cooldown": {}}
voice_channel_id = None
category_id = None
welcome_settings = {}
leave_settings = {}
nochat_settings = {}
bot_creator_id = None
owner_ids = set()
sub_command_cooldown = {}
default_volume = 30

DEFAULT_WELCOME_MESSAGE = "Verifiksi berhasil!"
MAX_CHAT_HISTORY_LENGTH = 100
HOLIDAY_API = 'https://date.nager.at/Api/v2/NextPublicHolidays/ID'
genius = lyricsgenius.Genius(config("GENIUS_API_KEY"))

class Fungsi(discord.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.recent_channel_id = recent_channel_id
        self.client = client
        
    async def has_voted(self, user_id: int) -> bool:
        topgg_token = config("TOPGG_TOKEN")
        
        url = f"https://top.gg/api/bots/{self.bot.user.id}/check?userId={user_id}"
        headers = {"Authorization": topgg_token}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            return False

        data = response.json()
        return data.get("voted", False)

    # KOTA
    kota_mapping = {
        'Aceh': 'Banda Aceh',
        'Bali': 'Bali',
        'Balikpapan': 'Balikpapan',
        'Belitung': 'Belitung',
        'Enrekang': 'Enrekang',
        'Jakarta': 'DKI Jakarta',
        'Jayapura': 'Jayapura',
        'Parepare': 'Kota Parepare',
        'Makassar': 'Makassar',
        'Pontianak': 'Pontianak',
        'Sidoarjo': 'Sidoarjo',
        'Surabaya': 'Surabaya',
        'Yogyakarta': 'D.I. Yogyakarta'
    }
    
    @staticmethod
    async def clear_empty_channel(bot):
        while True:
            for guild in bot.guilds:
                guild_data_directory = os.path.join(DATA_SERVER, str(guild.name))
                os.makedirs(guild_data_directory, exist_ok=True)
    
                guild_vm_path = os.path.join(guild_data_directory, 'vm.json')
    
                try:
                    with open(guild_vm_path, 'r') as file:
                        guild_data = json.load(file)
                except FileNotFoundError:
                    guild_data = []  # Initialize as an empty list if file not found
    
                for guild_entry in guild_data:  # Iterate over the list
                    guild_voice_channel_id = guild_entry.get('voice_channel_id')
                    guild_category_id = guild_entry.get('category_id')
    
                    for channel in guild.voice_channels:
                        if str(channel.id) in recent_channel_id["temp"] and len(channel.members) == 0:
                            owner_id = recent_channel_id["temp"].get(str(channel.id))
                            recent_channel_id["temp"].pop(str(channel.id))
                            await channel.delete()
    
            await asyncio.sleep(1)
            if "used" in recent_channel_id and any(channel_id in recent_channel_id["used"] for channel_id in recent_channel_id["used"]):
                for channel_id in list(recent_channel_id["used"]):
                    if channel_id not in recent_channel_id["temp"]:
                        owner_id = recent_channel_id["used"].pop(channel_id)
                        print(f"Channel ID {channel_id} and Owner ID {owner_id} removed from used.")
            
            await asyncio.sleep(1)
            if "reset_used" in recent_channel_id and any(channel_id in recent_channel_id["reset_used"] for channel_id in recent_channel_id["reset_used"]):
                for channel_id in list(recent_channel_id["reset_used"]):
                    if channel_id not in recent_channel_id["temp"]:
                        owner_id = recent_channel_id["reset_used"].pop(channel_id)
                        print(f"Channel ID {channel_id} and Owner ID {owner_id} removed from reset_used.")
    
    @staticmethod
    async def sort_channels(guild):
        shalat_categories = [category for category in guild.categories if 'shalat' in category.name.lower()]
        for category in shalat_categories:
            channels = sorted(category.text_channels, key=lambda x: x.name.lower())
            pilih_kota_channel = discord.utils.get(category.text_channels, name='pilih-kota')
            if pilih_kota_channel:
                channels.remove(pilih_kota_channel)
                channels.insert(0, pilih_kota_channel)
            for index, channel in enumerate(channels):
                await channel.edit(position=index)

    @staticmethod
    async def create_pilih_kota_channel(guild):
        while True:
            guild_data_directory = os.path.join(DATA_SERVER, str(guild.name))
            os.makedirs(guild_data_directory, exist_ok=True)
    
            guild_pilih_kota_path = os.path.join(guild_data_directory, 'pilih_kota.txt')
    
            channel_name = 'pilih-kota'
            
            embed_title = "CARA PILIH KOTA"
            embed_description = ("- Ketik **`/prayer add`** lalu pilih kota daerahmu, channel kota yang kamu pilih akan muncul dalam beberapa saat. "
                                "Gunakan **`/prayer delete`** untuk menghentikan notifikasi.")
    
            embed_note = ("- Jika kotamu tidak tersedia, lapor menggunakan **`/bug`**.")
    
            embed = discord.Embed(title=embed_title, description=embed_description, color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            embed.add_field(name="CATATAN", value=embed_note, inline=False)
            
            image_url = "https://i.ibb.co.com/55rJCPQ/Cuplikan-Layar-2024-05-20-06-11-44.png"
            try:
                embed.set_image(url=image_url)
            except discord.errors.HTTPException:
                print("Invalid image URL:", image_url)
    
            if os.path.exists(guild_pilih_kota_path):
                await Fungsi.sort_channels(guild)
            else:
                for category in guild.categories:
                    if 'shalat' in category.name.lower():
                        existing_channel = discord.utils.get(category.text_channels, name=channel_name)
                        if existing_channel:
                            await existing_channel.send(embed=embed)
                        else:
                            overwrites = {}
                            for role, perm in category.overwrites.items():
                                overwrites[role] = perm
                            new_channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
                            await Fungsi.sort_channels(guild)  # Sort channels alphabetically after creating new channel
                            await new_channel.send(embed=embed)
                    
                        with open(guild_pilih_kota_path, 'w') as f:
                            f.write('Udah')
            await asyncio.sleep(60)
        
    @tasks.loop(hours=3)
    async def auto_update_link(self):
        for guild in self.bot.guilds:
            data = DataBase.load_data(guild.name)
    
            if 'message_id' in data and 'channel_id' in data and 'pesan' in data:
                message_id = data['message_id']
                channel_id = data['channel_id']
                pesan = data['pesan']
    
                try:
                    channel = self.bot.get_channel(channel_id)
                    message = await channel.fetch_message(message_id)
    
                    # Revoke previous invite created by the bot
                    invites = await guild.invites()
                    for before_invite in invites:
                        if before_invite.inviter == self.bot.user:
                            try:
                                await before_invite.delete()
                            except discord.NotFound:
                                pass
                    
                    # Create a new invite
                    new_invite = await channel.create_invite(max_uses=0, max_age=10800, unique=True, reason="Moderator membuat link ini menggunakan /setup create Channel: Verifikasi.")
                    updated_embed = discord.Embed(
                        description=f'{pesan}\n\n* Link Server: {new_invite.url}'
                    )
    
                    await message.edit(embed=updated_embed)
    
                except discord.Forbidden:
                    print(f"Butuh permission di guild {guild.name}")
                except discord.NotFound:
                    print(f"Pesan tidak ditemukan di guild {guild.name}. Mungkin sudah dihapus.")
        
    @tasks.loop(seconds=60)
    async def auto_update_stats(self):
        for guild in self.bot.guilds:
            await Fungsi.update_stats(guild)
    
    @staticmethod
    async def update_stats(guild):
        guild_name = str(guild.name)
        stats_file_path = os.path.join(DATA_SERVER, guild_name, 'stats.json')
    
        try:
            with open(stats_file_path, 'r') as file:
                server_stats = json.load(file)
        except FileNotFoundError:
            server_stats = {}
    
        await Fungsi.create_or_update_voice_channel(guild, None, 'Total', guild.member_count, server_stats)
        await Fungsi.create_or_update_voice_channel(guild, None, 'Members', sum(not member.bot for member in guild.members), server_stats)
        await Fungsi.create_or_update_voice_channel(guild, None, 'Bots', sum(member.bot for member in guild.members), server_stats)
    
    @staticmethod
    async def create_or_update_voice_channel(guild, category, name, value, server_stats):
        channel_name = name.lower()
    
        if str(guild.id) not in server_stats or 'channel_ids' not in server_stats[str(guild.id)]:
            return
        
        voice_channel_id = server_stats[str(guild.id)]['channel_ids'].get(channel_name)
    
        if not voice_channel_id:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(connect=False, speak=False, view_channel=True),
                    guild.me: discord.PermissionOverwrite(connect=True, speak=True, view_channel=True)
                }
    
                if category is None:
                    # If category is not provided, create the voice channel directly under the guild
                    voice_channel = await guild.create_voice_channel(name=f'{name}: {value}', overwrites=overwrites)
                else:
                    # Create the voice channel under the specified category
                    voice_channel = await category.create_voice_channel(name=f'{name}: {value}', overwrites=overwrites)
    
                server_stats[str(guild.id)]['channel_ids'][channel_name] = str(voice_channel.id)
                guild_name = str(guild.name)
                DataBase.save_stats(guild_name, server_stats)
            except Exception as e:
                print(f"Error creating voice channel: {e}")
        else:
            voice_channel = discord.utils.get(guild.channels, id=int(voice_channel_id))
            if voice_channel:
                try:
                    await voice_channel.edit(name=f'{name.capitalize()}: {value}')
                except Exception as e:
                    print(f"Error updating voice channel: {e}")
                    
    @staticmethod
    async def process_message(self, thread, message):
        try:
            # Process each message as needed
            guild_name = str(thread.guild.name)
            user_name = str(message.author.name)
            chat_history = DataBase.load_chat_history(guild_name, user_name)
            
            # Load chat history for this user in this guild
            chat_history = DataBase.load_chat_history(guild_name, user_name)

            # If chat history is already at maximum length, replace the oldest message
            if len(chat_history) >= MAX_CHAT_HISTORY_LENGTH:
                chat_history.pop(0)  # Remove the oldest message

            # Add current message to chat history
            chat_history.append(message.clean_content)

            # Save updated chat history
            DataBase.save_chat_history(guild_name, user_name, chat_history)

            # Concatenate chat history with the current message
            input_messages = [{"role": "user", "content": msg} for msg in chat_history]
            input_messages.append({"role": "user", "content": message.clean_content})

            # Integrasi GPT-3.5-turbo with chat history
            async with message.channel.typing():
                await asyncio.sleep(2)
                response = None
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=input_messages,
                        temperature=0.9,
                        max_tokens=1500,
                        top_p=1,
                        frequency_penalty=0,
                        presence_penalty=0.6
                    )
                except Exception as e:
                    print(f"[AI-Chat] {e}")

                reply = response.choices[0].message.content if response and response.choices else "[Mencapai Limit Bulanan] Bantu admin agar bot ini tetap berjalan dengan berdonasi ke [Saweria](https://saweria.co/agcrisbp)."
                chunks = [reply[i:i + 2000] for i in range(0, len(reply), 2000)]

                for chunk in chunks:
                    await thread.send(chunk)
                
        except Exception as e:
            print(f"Error processing message in thread: {e}")

    async def holiday_event_messages(bot):
        while True:
            try:
                response = requests.get(HOLIDAY_API)
                if response.status_code == 200:
                    holidays = response.json()
    
                    for holiday in holidays:
                        holiday_name = holiday['localName']
                        holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d')
    
                        wib_timezone = pytz.timezone('Asia/Jakarta')
                        holiday_date = wib_timezone.localize(holiday_date)
    
                        current_date = datetime.now(wib_timezone)
    
                        # Check if the holiday date is in the future
                        if holiday_date > current_date:
                            time_until_holiday = holiday_date - current_date
                            await Fungsi.holiday_message(bot, holiday_name, time_until_holiday.total_seconds())
            except Exception as e:
                print(f"An error occurred: {e}")
    
            await asyncio.sleep(60)
    
    async def holiday_message(bot, holiday_name, delay_seconds):
        await asyncio.sleep(delay_seconds)
        sent_message = False  # Flag to track if the message has been sent
    
        for guild in bot.guilds:
            guild_data_directory = os.path.join(DATA_SERVER, str(guild.name))
            os.makedirs(guild_data_directory, exist_ok=True)
            holiday_file_path = os.path.join(guild_data_directory, f'{holiday_name}.txt')
    
            # Check if the message has already been sent
            if not os.path.exists(holiday_file_path):
                for channel in guild.channels:
                    if 'information' in channel.name and isinstance(channel, discord.TextChannel):
                        embed = discord.Embed(color=discord.Color.random())
                        embed.description = f"Selamat Memperingati **__{holiday_name}__**!"
                        await channel.send(embed=embed)
                        with open(holiday_file_path, 'w') as file:
                            file.write(f'Udah dikirim ke {", ".join(str(channel.id) for channel in guild.channels if "information" in channel.name)}.')
                        sent_message = True
            else:
                with open(holiday_file_path, 'w') as file:
                    file.write(f'Udah dikirim ke {", ".join(str(channel.id) for channel in guild.channels if "information" in channel.name)}.')
    
#        bot.loop.create_task(Fungsi.remove_holiday_file(bot, holiday_name))
#        print("Memulai loop penghapusan")
    
    @staticmethod
    async def remove_holiday_file(bot, holiday_name):
        try:
            wib_timezone = pytz.timezone('Asia/Jakarta')
            now = datetime.now(wib_timezone)
            if now.hour == 0 and now.minute == 0:  # Check if it's 12 AM WIB
                for guild in bot.guilds:
                    guild_data_directory = os.path.join(DATA_SERVER, str(guild.name))
                    holiday_file_path = os.path.join(guild_data_directory, f'{holiday_name}.txt')
                    if os.path.exists(holiday_file_path):
                        os.remove(holiday_file_path)
                        print(f"Removed {holiday_file_path}")
            print(f"Memulai loop penghapusan.")
        except Exception as e:
            print(f"An error occurred while removing file: {e}")
    
#    async def remove_holiday_file(bot, holiday_name):
#        while True:
#            try:
#                wib_timezone = pytz.timezone('Asia/Jakarta')
#                now = datetime.now(wib_timezone)
#                if now.hour == 0 and now.minute == 0:
#                    for guild in bot.guilds:
#                        guild_data_directory = os.path.join(DATA_SERVER, str(guild.name))
#                        holiday_file_path = os.path.join(guild_data_directory, f'{holiday_name}.txt')
#                        if os.path.exists(holiday_file_path):
#                            os.remove(holiday_file_path)
#            except Exception as e:
#                print(f"An error occurred: {e}")
            
#            await asyncio.sleep(60)

    @staticmethod
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def generate_random_color():
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))
    
    @staticmethod
    async def get_timezone(kota):
        geolocator = Nominatim(user_agent="get_timezone")
        location = geolocator.geocode(kota)
        if location:
            tf = TimezoneFinder()
            timezone_name = tf.timezone_at(lat=location.latitude, lng=location.longitude)
            return pytz.timezone(timezone_name)
        else:
            return None
    
    @staticmethod
    async def get_prayer_times_by_city(kota=None, date=None):
        if kota is None:
            kota = "Jakarta"
        timezone = await Fungsi.get_timezone(kota)
        
        if timezone:
            if date:
                url = f"http://api.aladhan.com/v1/timingsByCity?city={kota}&country=Indonesia&method=5&date={date}"
            else:
                url = f"http://api.aladhan.com/v1/timingsByCity?city={city}&country=Indonesia&method=5"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
            timings = data['data']['timings']
            # Extract timezone abbreviation
            timezone_abbr = Fungsi.get_timezone_abbreviation(timezone)
            timings['timezone'] = timezone_abbr
            return timings
        else:
            return None
    
    @staticmethod
    def get_timezone_abbreviation(timezone):
        tz_offset = timezone.utcoffset(datetime.now())
        if tz_offset == timedelta(hours=7):  # UTC+7
            return 'WIB'
        elif tz_offset == timedelta(hours=8):  # UTC+8
            return 'WITA'
        elif tz_offset == timedelta(hours=9):  # UTC+9
            return 'WIT'
        else:
            return None

    ####### WAKTU INDONESIA BARAT #######
    # Banda Aceh
    async def start_aceh_times(bot):
        await Fungsi.check_aceh_times(bot)
    
    async def check_aceh_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y")
                aceh_timings = await Fungsi.get_aceh_times(current_date)
                wib_timezone = pytz.timezone('Asia/Jakarta')
                current_time = datetime.now(wib_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = aceh_timings.get('Maghrib', None)
                imsyak_time = aceh_timings.get('Imsak', None)
                fajr_time = aceh_timings.get('Fajr', None)
                dhuhr_time = aceh_timings.get('Dhuhr', None)
                asr_time = aceh_timings.get('Asr', None)
                isha_time = aceh_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Banda Aceh')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'banda-aceh' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='banda-aceh', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
    
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WIB | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Banda Aceh & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Banda Aceh, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Banda Aceh & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Banda Aceh, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Banda Aceh & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Banda Aceh, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Banda Aceh & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Banda Aceh, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Banda Aceh & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Banda Aceh, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Banda Aceh & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Banda Aceh, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            
            await asyncio.sleep(60)
    
    async def get_aceh_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=BandaAceh&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        aceh_timings = data['data']['timings']
        return aceh_timings
    
    # Belitung
    async def start_belitung_times(bot):
        await Fungsi.check_belitung_times(bot)
    
    async def check_belitung_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y")
                belitung_timings = await Fungsi.get_belitung_times(current_date)
                wib_timezone = pytz.timezone('Asia/Jakarta')
                current_time = datetime.now(wib_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = belitung_timings.get('Maghrib', None)
                imsyak_time = belitung_timings.get('Imsak', None)
                fajr_time = belitung_timings.get('Fajr', None)
                dhuhr_time = belitung_timings.get('Dhuhr', None)
                asr_time = belitung_timings.get('Asr', None)
                isha_time = belitung_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Belitung')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'belitung' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='belitung', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
    
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WIB | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Belitung & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Belitung, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Belitung & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Belitung, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Belitung & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Belitung, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Belitung & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Belitung, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Belitung & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Belitung, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Belitung & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Belitung, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            
            await asyncio.sleep(60)
    
    async def get_belitung_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Belitung&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        belitung_timings = data['data']['timings']
        return belitung_timings
    
    # Jakarta
    async def start_jakarta_times(bot):
        await Fungsi.check_jakarta_times(bot)
    
    async def check_jakarta_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y")
                jakarta_timings = await Fungsi.get_jakarta_times(current_date)
                wib_timezone = pytz.timezone('Asia/Jakarta')
                current_time = datetime.now(wib_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = jakarta_timings.get('Maghrib', None)
                imsyak_time = jakarta_timings.get('Imsak', None)
                fajr_time = jakarta_timings.get('Fajr', None)
                dhuhr_time = jakarta_timings.get('Dhuhr', None)
                asr_time = jakarta_timings.get('Asr', None)
                isha_time = jakarta_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='DKI Jakarta')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'dki-jakarta' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='dki-jakarta', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
    
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
    
                            embed.set_footer(text=f"{current_time_str} WIB | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "DKI Jakarta & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Khusus Ibukota Jakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "DKI Jakarta & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Khusus Ibukota Jakarta, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "DKI Jakarta & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Khusus Ibukota Jakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "DKI Jakarta & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Khusus Ibukota Jakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "DKI Jakarta & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Khusus Ibukota Jakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "DKI Jakarta & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Khusus Ibukota Jakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_jakarta_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Jakarta&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        jakarta_timings = data['data']['timings']
        return jakarta_timings
    
    # Pontianak
    async def start_pontianak_times(bot):
        await Fungsi.check_pontianak_times(bot)
    
    async def check_pontianak_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Pontianak')).strftime("%d-%m-%Y")
                pontianak_timings = await Fungsi.get_pontianak_times(current_date)
                wib_timezone = pytz.timezone('Asia/Pontianak')
                current_time = datetime.now(wib_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = pontianak_timings.get('Maghrib', None)
                imsyak_time = pontianak_timings.get('Imsak', None)
                fajr_time = pontianak_timings.get('Fajr', None)
                dhuhr_time = pontianak_timings.get('Dhuhr', None)
                asr_time = pontianak_timings.get('Asr', None)
                isha_time = pontianak_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Pontianak')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'pontianak' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='pontianak', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WIB | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Pontianak & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Pontianak, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Pontianak & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Pontianak, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Pontianak & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Pontianak, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Pontianak & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Pontianak, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Pontianak & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Pontianak, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Pontianak & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Pontianak, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_pontianak_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Pontianak&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        pontianak_timings = data['data']['timings']
        return pontianak_timings
    
    # Sidoarjo
    async def start_sidoarjo_times(bot):
        await Fungsi.check_sidoarjo_times(bot)
    
    async def check_sidoarjo_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y")
                sidoarjo_timings = await Fungsi.get_sidoarjo_times(current_date)
                wib_timezone = pytz.timezone('Asia/Jakarta')
                current_time = datetime.now(wib_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = sidoarjo_timings.get('Maghrib', None)
                imsyak_time = sidoarjo_timings.get('Imsak', None)
                fajr_time = sidoarjo_timings.get('Fajr', None)
                dhuhr_time = sidoarjo_timings.get('Dhuhr', None)
                asr_time = sidoarjo_timings.get('Asr', None)
                isha_time = sidoarjo_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Sidoarjo')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'sidoarjo' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='sidoarjo', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WIB | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Sidoarjo & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Sidoarjo, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Sidoarjo & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Sidoarjo, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Sidoarjo & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Sidoarjo, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Sidoarjo & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Sidoarjo, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Sidoarjo & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Sidoarjo, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Sidoarjo & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Sidoarjo, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_sidoarjo_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Sidoarjo&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        sidoarjo_timings = data['data']['timings']
        return sidoarjo_timings
    
    # Surabaya
    async def start_surabaya_times(bot):
        await Fungsi.check_surabaya_times(bot)
    
    async def check_surabaya_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y")
                surabaya_timings = await Fungsi.get_surabaya_times(current_date)
                wib_timezone = pytz.timezone('Asia/Jakarta')
                current_time = datetime.now(wib_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = surabaya_timings.get('Maghrib', None)
                imsyak_time = surabaya_timings.get('Imsak', None)
                fajr_time = surabaya_timings.get('Fajr', None)
                dhuhr_time = surabaya_timings.get('Dhuhr', None)
                asr_time = surabaya_timings.get('Asr', None)
                isha_time = surabaya_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Surabaya')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'surabaya' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='surabaya', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WIB | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Surabaya & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Surabaya, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Surabaya & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Surabaya, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Surabaya & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Surabaya, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Surabaya & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Surabaya, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Surabaya & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Surabaya, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Surabaya & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Surabaya, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_surabaya_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Surabaya&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        surabaya_timings = data['data']['timings']
        return surabaya_timings
    
    # Yogyakarta
    async def start_jogja_times(bot):
        await Fungsi.check_jogja_times(bot)
    
    async def check_jogja_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y")
                jogja_timings = await Fungsi.get_jogja_times(current_date)
                wib_timezone = pytz.timezone('Asia/Jakarta')
                current_time = datetime.now(wib_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = jogja_timings.get('Maghrib', None)
                imsyak_time = jogja_timings.get('Imsak', None)
                fajr_time = jogja_timings.get('Fajr', None)
                dhuhr_time = jogja_timings.get('Dhuhr', None)
                asr_time = jogja_timings.get('Asr', None)
                isha_time = jogja_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='D.I. Yogyakarta')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'yogyakarta' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='yogyakarta', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            embed.set_footer(text=f"{current_time_str} WIB | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "D.I. Yogyakarta & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk D.I. Yogyakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "D.I. Yogyakarta & Sekitarnya"
                                embed.description = "Sudah Imsak untuk D.I. Yogyakarta, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "D.I. Yogyakarta & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk D.I. Yogyakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "D.I. Yogyakarta & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk D.I. Yogyakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "D.I. Yogyakarta & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk D.I. Yogyakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "D.I. Yogyakarta & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk D.I. Yogyakarta, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_jogja_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Yogyakarta&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        jogja_timings = data['data']['timings']
        return jogja_timings
    
    ####### WAKTU INDONESIA TENGAH #######
    # Balikpapan
    async def start_balikpapan_times(bot):
        await Fungsi.check_balikpapan_times(bot)
    
    async def check_balikpapan_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Makassar')).strftime("%d-%m-%Y")
                balikpapan_timings = await Fungsi.get_balikpapan_times(current_date)
                wita_timezone = pytz.timezone('Asia/Makassar')
                current_time = datetime.now(wita_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = balikpapan_timings.get('Maghrib', None)
                imsyak_time = balikpapan_timings.get('Imsak', None)
                fajr_time = balikpapan_timings.get('Fajr', None)
                dhuhr_time = balikpapan_timings.get('Dhuhr', None)
                asr_time = balikpapan_timings.get('Asr', None)
                isha_time = balikpapan_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Balikpapan')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'balikpapan' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='balikpapan', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
    
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WIB | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Balikpapan & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Balikpapan, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Balikpapan & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Balikpapan, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Balikpapan & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Balikpapan, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Balikpapan & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Balikpapan, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Balikpapan & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Balikpapan, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Balikpapan & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Balikpapan, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            
            await asyncio.sleep(60)
    
    async def get_balikpapan_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Balikpapan&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        balikpapan_timings = data['data']['timings']
        return balikpapan_timings
    
    # Bali
    async def start_bali_times(bot):
        await Fungsi.check_bali_times(bot)
    
    async def check_bali_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Makassar')).strftime("%d-%m-%Y")
                bali_timings = await Fungsi.get_bali_times(current_date)
                wita_timezone = pytz.timezone('Asia/Makassar')
                current_time = datetime.now(wita_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = bali_timings.get('Maghrib', None)
                imsyak_time = bali_timings.get('Imsak', None)
                fajr_time = bali_timings.get('Fajr', None)
                dhuhr_time = bali_timings.get('Dhuhr', None)
                asr_time = bali_timings.get('Asr', None)
                isha_time = bali_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Bali')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'bali' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='bali', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WITA | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Bali & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Bali, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Bali & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Bali, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Bali & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Bali, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Bali & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Bali, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Bali & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Bali, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Bali & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Bali, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_bali_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Bali&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        bali_timings = data['data']['timings']
        return bali_timings
    
    # Enrekang
    async def start_enrekang_times(bot):
        await Fungsi.check_enrekang_times(bot)
    
    async def check_enrekang_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Makassar')).strftime("%d-%m-%Y")
                enrekang_timings = await Fungsi.get_enrekang_times(current_date)
                wita_timezone = pytz.timezone('Asia/Makassar')
                current_time = datetime.now(wita_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = enrekang_timings.get('Maghrib', None)
                imsyak_time = enrekang_timings.get('Imsak', None)
                fajr_time = enrekang_timings.get('Fajr', None)
                dhuhr_time = enrekang_timings.get('Dhuhr', None)
                asr_time = enrekang_timings.get('Asr', None)
                isha_time = enrekang_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Enrekang')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'enrekang' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='enrekang', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WITA | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Enrekang & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Enrekang, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Enrekang & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Enrekang, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Enrekang & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Enrekang, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Enrekang & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Enrekang, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Enrekang & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Enrekang, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Enrekang & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Enrekang, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_enrekang_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Enrekang&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        enrekang_timings = data['data']['timings']
        return enrekang_timings
    
    # Makassar
    async def start_makassar_times(bot):
        await Fungsi.check_makassar_times(bot)
    
    async def check_makassar_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Makassar')).strftime("%d-%m-%Y")
                makassar_timings = await Fungsi.get_makassar_times(current_date)
                wita_timezone = pytz.timezone('Asia/Makassar')
                current_time = datetime.now(wita_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = makassar_timings.get('Maghrib', None)
                imsyak_time = makassar_timings.get('Imsak', None)
                fajr_time = makassar_timings.get('Fajr', None)
                dhuhr_time = makassar_timings.get('Dhuhr', None)
                asr_time = makassar_timings.get('Asr', None)
                isha_time = makassar_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Makassar')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'makassar' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='makassar', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WITA | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Makassar & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Makassar, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Makassar & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Makassar, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Makassar & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Makassar, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Makassar & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Makassar, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Makassar & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Makassar, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Makassar & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Makassar, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_makassar_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Makassar&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        makassar_timings = data['data']['timings']
        return makassar_timings
    
    # Kota Parepare
    async def start_parepare_times(bot):
        await Fungsi.check_parepare_times(bot)
    
    async def check_parepare_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Makassar')).strftime("%d-%m-%Y")
                parepare_timings = await Fungsi.get_parepare_times(current_date)
                wita_timezone = pytz.timezone('Asia/Makassar')
                current_time = datetime.now(wita_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = parepare_timings.get('Maghrib', None)
                imsyak_time = parepare_timings.get('Imsak', None)
                fajr_time = parepare_timings.get('Fajr', None)
                dhuhr_time = parepare_timings.get('Dhuhr', None)
                asr_time = parepare_timings.get('Asr', None)
                isha_time = parepare_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Kota Parepare')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'kota-parepare' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='kota-parepare', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WITA | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Kota Parepare & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Kota Parepare, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Kota Parepare & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Kota Parepare, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Kota Parepare & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Kota Parepare, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Kota Parepare & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Kota Parepare, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Kota Parepare & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Kota Parepare, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Kota Parepare & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Kota Parepare, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_parepare_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=KotaParepare&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        parepare_timings = data['data']['timings']
        return parepare_timings
    
    # Samarinda
    async def start_samarinda_times(bot):
        await Fungsi.check_samarinda_times(bot)
    
    async def check_samarinda_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Makassar')).strftime("%d-%m-%Y")
                samarinda_timings = await Fungsi.get_samarinda_times(current_date)
                wita_timezone = pytz.timezone('Asia/Makassar')
                current_time = datetime.now(wita_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = samarinda_timings.get('Maghrib', None)
                imsyak_time = samarinda_timings.get('Imsak', None)
                fajr_time = samarinda_timings.get('Fajr', None)
                dhuhr_time = samarinda_timings.get('Dhuhr', None)
                asr_time = samarinda_timings.get('Asr', None)
                isha_time = samarinda_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Samarinda')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'samarinda' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='samarinda', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                            
                            embed.set_footer(text=f"{current_time_str} WITA | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Samarinda & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Samarinda, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Samarinda & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Samarinda, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Samarinda & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Samarinda, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Samarinda & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Samarinda, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Samarinda & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Samarinda, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Makassar & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Samarinda, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_samarinda_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Samarinda&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        samarinda_timings = data['data']['timings']
        return samarinda_timings
    
    ####### WAKTU INDONESIA TIMUR #######
    # Jayapura
    async def start_jayapura_times(bot):
        await Fungsi.check_jayapura_times(bot)
    
    async def check_jayapura_times(bot):
        while True:
            try:
                current_date = datetime.now(pytz.timezone('Asia/Jayapura')).strftime("%d-%m-%Y")
                jayapura_timings = await Fungsi.get_jayapura_times(current_date)
                wit_timezone = pytz.timezone('Asia/Jayapura')
                current_time = datetime.now(wit_timezone)
    
                # Format current_time as string without seconds
                current_time_str = current_time.strftime("%H:%M")
    
                maghrib_time = jayapura_timings.get('Maghrib', None)
                imsyak_time = jayapura_timings.get('Imsak', None)
                fajr_time = jayapura_timings.get('Fajr', None)
                dhuhr_time = jayapura_timings.get('Dhuhr', None)
                asr_time = jayapura_timings.get('Asr', None)
                isha_time = jayapura_timings.get('Isha', None)
    
                for guild in bot.guilds:
                    for category in guild.categories:
                        if 'shalat' in category.name.lower():
                            channel_found = False
                            role = discord.utils.get(guild.roles, name='Jayapura')
                            role_mention = role.mention if role else ''
                            
                            for channel in category.channels:
                                if 'jayapura' in channel.name:
                                    channel_found = True
    
                                    if role:
                                        overwrites = channel.overwrites
                                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                        await channel.edit(overwrites=overwrites)
                                    break
                            
                            if not channel_found:
                                overwrites = {
                                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                }
                                new_channel = await category.create_text_channel(name='jayapura', overwrites=overwrites)
                                channel = new_channel
    
                                if role:
                                    overwrites = channel.overwrites
                                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True)
                                    await channel.edit(overwrites=overwrites)
                                
                            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
    
                            embed.set_footer(text=f"{current_time_str} WIT | Powered by Aladhan API")
    
                            if current_time_str == maghrib_time:
                                embed.title = "Jayapura & Sekitarnya"
                                embed.description = "Selamat Menunaikan Ibadah Shalat Maghrib & Selamat Berbuka Puasa untuk Daerah Jayapura, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == imsyak_time:
                                embed.title = "Jayapura & Sekitarnya"
                                embed.description = "Sudah Imsak untuk Daerah Jayapura, dan sekitarnya! Selamat menunaikan ibadah puasa bagi yang menjalankan."
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == fajr_time:
                                embed.title = "Jayapura & Sekitarnya"
                                embed.description = "Waktu Shalat Subuh untuk Daerah Jayapura, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == dhuhr_time:
                                embed.title = "Jayapura & Sekitarnya"
                                embed.description = "Waktu Shalat Dzuhur untuk Daerah Jayapura, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == asr_time:
                                embed.title = "Jayapura & Sekitarnya"
                                embed.description = "Waktu Shalat Ashar untuk Daerah Jayapura, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
                            if current_time_str == isha_time:
                                embed.title = "Jayapura & Sekitarnya"
                                embed.description = "Waktu Shalat Isya untuk Daerah Jayapura, dan sekitarnya!"
                                await channel.send(content=f'{role_mention}', embed=embed)
    
            except aiohttp.ClientConnectorError:
                print("Failed to connect to the API server. Retrying in 1 minute...")
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
    
            # Check every minute
            await asyncio.sleep(60)
    
    async def get_jayapura_times(date):
        url = f"http://api.aladhan.com/v1/timingsByCity?city=Jayapura&country=Indonesia&method=5&date={date}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        jayapura_timings = data['data']['timings']
        return jayapura_timings

class Views:
    def __init__(self):
        pass

    class UserSelector(discord.ui.View):

        def __init__(self, user: discord.Member, edit_user: discord.Member):
            self.channel_data = recent_channel_id
            self.user = user
            self.edit_user: discord.Member = edit_user
            super().__init__()

        @discord.ui.select(
            placeholder="Pilih opsi untuk member yang dipilih",
            options=[
                discord.SelectOption(
                    label="Disconnct",
                    description="Disconnect user dari channel ini",
                    value="disconnect",
                ),
                discord.SelectOption(
                    label="Mute",
                    description="Mute user",
                    value="mute",
                ),
                discord.SelectOption(
                    label="Reject",
                    description="Melarang user untuk bergabung ke channel ini",
                    value="reject",
                ),
                discord.SelectOption(
                    label="Hide",
                    description="Menyembunyikan channel ini dari user dipilih",
                    value="hide",
                ),
            ],
        )
        async def edit_member_callback(
            self, select: discord.ui.Select, interaction: discord.Interaction
        ):
            await interaction.response.defer()
            selected = select.values[0]
            # placeholder
            if selected == "reject":
                params: discord.PermissionOverwrite = (
                    interaction.channel.overwrites_for(self.edit_user)
                )
                params.connect = False
                await interaction.channel.set_permissions(
                    target=self.edit_user,
                    overwrite=params,
                    reason="User ini dilarang bergabung oleh temp owner channel.",
                )
                msg = await interaction.original_response()
                await interaction.respond(
                    content=f"{self.edit_user.mention} ditolak.",
                    view=None,
                    delete_after=5,
                )
                if (
                    self.edit_user.voice
                    and self.edit_user.voice.channel.id == interaction.channel_id
                ):  # (Fixed) Possible Error "NoneType Has No attr"
                    # If the user alr on the channel, kick it out
                    return await self.edit_user.move_to(None)
                else:
                    # otherwise continue
                    return

            if selected == "hide":
                if (
                    self.edit_user.voice
                    and self.edit_user.voice.channel.id == interaction.channel_id
                ):  # (fixed) ERROR: NoneType has no attr ...
                    await self.edit_user.move_to(None)
                params: discord.PermissionOverwrite = (
                    interaction.channel.overwrites_for(self.edit_user)
                )
                params.view_channel = False
                await interaction.channel.set_permissions(
                    target=self.edit_user,
                    overwrite=params,
                    reason="Channel ini disembunyikan dari user ini oleh temp owner.",
                )
                msg = await interaction.original_response()
                return await msg.edit(
                    content=f"Channel ini disembunyikan dari {self.edit_user.mention}.",
                    view=None,
                    delete_after=5,
                )

            if not self.edit_user.voice:
                return await interaction.respond(
                    "This user is not connected to this voice channel.", ephemeral=True
                )
            elif not self.edit_user.voice.channel.id == interaction.channel_id:
                return await interaction.respond(
                    "This user is not connected to this voice channel.", ephemeral=True
                )

            if selected == "disconnect":
                await self.edit_user.move_to(None)
                return await interaction.respond(
                    content=f"{self.edit_user.mention} has been disconnected.",
                    view=None,
                    delete_after=5,
                )

            if selected == "mute":
                # this one actully broke my mind for how it works
                # since when you edit a user permissions (mute it)
                # the user should get reconnected so he get muted ;-;
                # moving the user will also work
                # here the user get's moved to the SAME channel
                # and the perms gets applied, nice
                this_channel = await interaction.guild.fetch_channel(
                    int(interaction.channel.id)
                )
                params: discord.PermissionOverwrite = this_channel.overwrites_for(
                    self.edit_user
                )
                if params.speak or params.speak is None:
                    params.speak = False
                    await interaction.channel.set_permissions(
                        target=self.edit_user,
                        overwrite=params,
                        reason="User ini dibisukan oleh temp owner.",
                    )
                    msg = await interaction.original_response()
                    await self.edit_user.move_to(
                        interaction.channel
                    )  # it works but i dont know why
                    return await msg.edit(
                        content=f"{self.edit_user.mention} dibisukan.",
                        view=None,
                        delete_after=5,
                    )
                else:
                    params.speak = None
                    await interaction.channel.set_permissions(
                        target=self.edit_user,
                        overwrite=params,
                        reason="This user has been unmuted by the temp owner.",
                    )
                    msg = await interaction.original_response()
                    await self.edit_user.move_to(interaction.channel)
                    return await msg.edit(
                        content=f"{self.edit_user.mention} sudah tidak dibisukan.",
                        view=None,
                        delete_after=5,
                    )

    class Dropdown(discord.ui.View):
        def __init__(self, bot):
            super().__init__(timeout=None)
            self.bot: discord.Bot = bot
            self.channel_data = recent_channel_id
            self.cooldown = commands.CooldownMapping.from_cooldown(
                1, 600, commands.BucketType.member
            )

        @discord.ui.select(
            custom_id="channel_settings",
            placeholder="Pilih opsi channel",
            options=[
                discord.SelectOption(
                    label="Info",
                    description="Menampilkan informasi temp voice channel ini",
                    value="info",
                ),
                discord.SelectOption(
                    label="Hapus",
                    description="Menghapus temp voice",
                    value="delete",
                ),
                discord.SelectOption(
                    label="Ubah Nama",
                    description="Mengubah nama channel ini",
                    value="name",
                ),
                discord.SelectOption(
                    label="Limit",
                    description="Mengubah limit user channel ini",
                    value="limit",
                ),
                discord.SelectOption(
                    label="Slow Mode",
                    description="Untuk mengatur/mengedit slow-mode/cooldown channel ini",
                    value="slow_mode",
                ),
                discord.SelectOption(
                    label="NSFW",
                    description="Menandai channel ini sebagai not safe for work (+18)",
                    value="nsfw",
                ),
                discord.SelectOption(
                    label="Kunci",
                    description="Mengunci channel ini bersama dengan user di dalamnya",
                    value="lock",
                ),
                discord.SelectOption(
                    label="Sembunyikan",
                    description="Menyembunyikan channel ini dan hanya dapat dilihat oleh user yang sudah bergabung",
                    value="hide",
                ),
                discord.SelectOption(
                    label="Bitrate",
                    description="Mengubah bitrate channel ini",
                    value="bitrate",
                ),
                discord.SelectOption(
                    label="Bersihkan",
                    description="Menghapus semua pesan di channel ini",
                    value="clear",
                ),
            ],
        )
        async def settings_callback(
            self, select: discord.ui.Select, interaction: discord.Interaction
        ):
            await interaction.message.edit(
                content=interaction.message.content, view=self
            )
        
            selected = select.values[0]
        
            voice_channel = interaction.channel
            channel_data = recent_channel_id["temp"].get(str(voice_channel.id))
            
            if not await Fungsi.has_voted(self, interaction.user.id):
                button1 = Button(
                    emoji="<:charis:1237457208774496266>",
                    label="VOTE",
                    url=f"https://top.gg/bot/{self.bot.user.id}/vote"
                )
                
                view = View()
                view.add_item(button1)
                embed = discord.Embed(
                    description=f"Silahkan [vote](https://top.gg/bot/{self.bot.user.id}/vote) bot terlebih dahulu untuk menggunakan perintah ini!",
                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                )
                
                return await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
            if channel_data is None:
                return await interaction.response.send_message(
                    "Channel data not found.", ephemeral=True
                )
        
            if selected == "name":
                bucket = self.cooldown.get_bucket(interaction.message)
                retry = bucket.update_rate_limit()
                if retry:
                    return await interaction.response.send_message(
                        f"Coba lagi dalam `{round(retry, 1)}` detik.",
                        ephemeral=True,
                    )
        
                modal = discord.ui.Modal(title="Nama Channel")
                modal.add_item(
                    discord.ui.InputText(
                        label="Nama Baru",
                        placeholder="Masukkan nama baru untuk channel ini",
                        value=interaction.channel.name,
                    )
                )
        
                async def modal_callback(interaction: discord.Interaction):
                    await interaction.response.defer()
                    channel_name = modal.children[0].value
                    if channel_name.isspace():
                        channel_name = f"{interaction.channel.user_limit}"
                    if interaction.user.id != channel_data:
                        return await interaction.respond(
                            "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                            ephemeral=True,
                            delete_after=5,
                        )
                    else:
                        await interaction.channel.edit(name=channel_name)
                        recent_entry = recent_channel_id["user"]
                        recent_entry[str(interaction.user.id)] = channel_name
                        DataBase.save_recent_channel_id(recent_channel_id)
                        return await interaction.respond(
                            f"Nama channel diubah menjadi **`{channel_name}`**!",
                            ephemeral=True,
                            delete_after=5,
                        )
        
                modal.callback = modal_callback
                return await interaction.response.send_modal(modal=modal)

            elif selected == "limit":
                modal = discord.ui.Modal(title="Channel Limit")
                modal.add_item(
                    discord.ui.InputText(
                        label="Channel Limit Baru",
                        placeholder="Masukkan jumlah channel limit (0 untuk unlimited)",
                        value=interaction.channel.user_limit,
                    )
                )

                async def modal_callback(interaction: discord.Interaction):
                    await interaction.response.defer()
                    channel_limit = modal.children[0].value
                    if not channel_limit.isnumeric():
                        return await interaction.respond(
                            f"Masukkan nomor yang benar!",
                            ephemeral=True,
                            delete_after=5,
                        )
                    await interaction.channel.edit(user_limit=int(channel_limit))
                    return await interaction.respond(
                        f"Channel User Limit diubah menjadi {'Unlimited' if int(channel_limit) == 0 else channel_limit}",
                        ephemeral=True,
                        delete_after=5,
                    )

                modal.callback = modal_callback
                return await interaction.response.send_modal(modal=modal)

            elif selected == "bitrate":
                channel_bits = int(
                    str(int(interaction.guild.bitrate_limit))[:-3]
                )  # Bro wtf is this butt-shit?
                placeholder = f"8 Sampai {channel_bits}"
                modal = discord.ui.Modal(title="Channel Bitrate")
                modal.add_item(
                    discord.ui.InputText(
                        label="Channel Bitrate Value",
                        placeholder=placeholder,
                        value=interaction.channel.user_limit,
                    )
                )

                async def modal_callback(interaction: discord.Interaction):
                    await interaction.response.defer()
                    modal_value = modal.children[0].value
                    if not modal_value.isnumeric():
                        return await interaction.respond(
                            f"Masukkan nomor yang benar!",
                            ephemeral=True,
                            delete_after=5,
                        )
                    elif int(modal_value) > channel_bits or int(modal_value) < 8:
                        return await interaction.respond(
                            f"Masukkan nomor antara 8 dan {str(channel_bits)}",
                            ephemeral=True,
                            delete_after=5,
                        )
                    await interaction.channel.edit(bitrate=(int(modal_value) * 1000))
                    return await interaction.respond(
                        f"Channel Bitrate diubah menjadi {modal_value}",
                        ephemeral=True,
                        delete_after=5,
                    )

                modal.callback = modal_callback
                return await interaction.response.send_modal(modal=modal)

            await interaction.response.defer()

            if (
                selected == "info"
            ):
                channel: discord.VoiceChannel = await interaction.guild.fetch_channel(
                    int(interaction.channel_id)
                )
                voice_channel = interaction.channel
                channel_data = recent_channel_id["temp"].get(str(voice_channel.id))
                
                utc_time = channel.created_at.replace(tzinfo=pytz.UTC)
                wib_timezone = pytz.timezone('Asia/Jakarta')
                wib_time = utc_time.astimezone(wib_timezone)
                creation_date = wib_time.strftime("%d %B %Y pukul %H:%M:%S WIB")

                embed = Embeds.Info(
                    interaction=interaction, channel=channel, channel_data=channel_data
                )
                message = await interaction.respond(embed=embed, delete_after=60)
                
                if interaction.user.id != channel_data:
                    return await interaction.respond(
                        "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                        ephemeral=True,
                        delete_after=5,
                    )

            if selected == "delete":
                voice_channel = interaction.channel
                channel_data = recent_channel_id["temp"].get(str(voice_channel.id))
                if not channel_data or interaction.user.id != channel_data:
                    return await interaction.respond(
                        "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                        ephemeral=True,
                        delete_after=5,
                    )
                else:
                    return await voice_channel.delete()

            elif selected == "slow_mode":
                voice_channel = interaction.channel
                channel_data = recent_channel_id["temp"].get(str(voice_channel.id))
                if not channel_data or interaction.user.id != channel_data:
                    return await interaction.respond(
                        "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                        ephemeral=True,
                        delete_after=5,
                    )
                else:
                    view = discord.ui.View(timeout=300)
                    dropdown = discord.ui.Select(
                        placeholder="Masukkan periode cooldown",
                        options=[
                            discord.SelectOption(label="off", value="0"),
                            discord.SelectOption(label="5s", value="5"),
                            discord.SelectOption(label="10s", value="10"),
                            discord.SelectOption(label="15s", value="15"),
                            discord.SelectOption(label="30s", value="30"),
                            discord.SelectOption(label="1m", value="60"),
                            discord.SelectOption(label="2m", value="120"),
                            discord.SelectOption(label="5m", value="300"),
                            discord.SelectOption(label="10m", value="600"),
                            discord.SelectOption(label="15m", value="900"),
                            discord.SelectOption(label="30m", value="1800"),
                            discord.SelectOption(label="1h", value="3600"),
                            discord.SelectOption(label="2h", value="7200"),
                            discord.SelectOption(label="6h", value="21600"),
                        ],
                    )
                    view.add_item(dropdown)

                async def slow_mode_select_callback(interaction: discord.Interaction):
                    slowmode_delay = int(dropdown.values[0])
                    await interaction.response.defer()
                    await interaction.channel.edit(slowmode_delay=slowmode_delay)
                    msg = await interaction.original_response()
                    return await msg.edit(
                        f"Slow Mode berhasil diubah!", view=None, delete_after=5
                    )

                dropdown.callback = slow_mode_select_callback
                return await interaction.respond(
                    "Pilih periode di menu di bawah ini",
                    view=view,
                    ephemeral=True,
                    delete_after=300,
                )

            elif selected == "nsfw":
                voice_channel = interaction.channel
                channel_data = recent_channel_id["temp"].get(str(voice_channel.id))
                if not channel_data or interaction.user.id != channel_data:
                    return await interaction.respond(
                        "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                        ephemeral=True,
                        delete_after=5,
                    )
                    
                if interaction.channel.nsfw:
                    await interaction.channel.edit(nsfw=False)
                    return await interaction.respond(
                        f"Channel berhasil ditandai sebagai Non-NSFW!",
                        ephemeral=True,
                        delete_after=5,
                    )
                else:
                    await interaction.channel.edit(nsfw=True)
                    return await interaction.respond(
                        f"Channel berhasil ditandai sebagai NSFW!",
                        ephemeral=True,
                        delete_after=5,
                    )

            elif selected == "lock":
                voice_channel = interaction.channel
                channel_data = recent_channel_id["temp"].get(str(voice_channel.id))
                if not channel_data or interaction.user.id != channel_data:
                    return await interaction.respond(
                        "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                        ephemeral=True,
                        delete_after=5,
                    )
                
                this_channel = await interaction.guild.fetch_channel(
                    int(interaction.channel.id)
                )
                everyone_perms = this_channel.permissions_for(
                    interaction.guild.default_role
                )
                overwrite_perms = this_channel.overwrites

                if everyone_perms.connect:
                    for member in interaction.channel.members:
                        perms: discord.Permissions = interaction.channel.overwrites_for(
                            member
                        )
                        perms.connect = True
                        await interaction.channel.set_permissions(
                            target=member,
                            overwrite=perms,
                            reason="This user has acsess to this channel by the temp owner.",
                        )
                    role = interaction.guild.default_role
                    perms = interaction.channel.overwrites_for(role)
                    perms.connect = False
                    await interaction.channel.set_permissions(
                        target=role,
                        overwrite=perms,
                        reason="This user has no acsess to this channel by the temp owner.",
                    )
                    return await interaction.respond(
                        f"Channel berhasil dikunci!",
                        ephemeral=True,
                        delete_after=5,
                    )
                else:
                    for perm in overwrite_perms:
                        overwrite = interaction.channel.overwrites_for(perm)
                        overwrite.connect = None
                        await interaction.channel.set_permissions(
                            target=perm, overwrite=overwrite
                        )
                    return await interaction.respond(
                        f"Channel sudah tidak dikunci!", ephemeral=True, delete_after=5
                    )

            elif selected == "hide":
                this_channel = await interaction.guild.fetch_channel(
                    int(interaction.channel.id)
                )
                everyone_perms = this_channel.permissions_for(
                    interaction.guild.default_role
                )
                overwrite_perms = this_channel.overwrites
                # ^^ you got the point above
                if everyone_perms.view_channel:
                    for member in interaction.channel.members:
                        perms: discord.Permissions = interaction.channel.overwrites_for(
                            member
                        )
                        perms.view_channel = True
                        await interaction.channel.set_permissions(
                            target=member,
                            overwrite=perms,
                            reason="This channel has been hidden by the temp owner.",
                        )
                    role = interaction.guild.default_role
                    perms = interaction.channel.overwrites_for(role)
                    perms.view_channel = False
                    await interaction.channel.set_permissions(
                        target=role,
                        overwrite=perms,
                        reason="This user has no acsess to this channel by the temp owner.",
                    )
                    return await interaction.respond(
                        f"Channel berhasil disembunyikan!",
                        ephemeral=True,
                        delete_after=5,
                    )
                else:
                    for perm in overwrite_perms:
                        overwrite = interaction.channel.overwrites_for(perm)
                        overwrite.view_channel = None
                        await interaction.channel.set_permissions(
                            target=perm, overwrite=overwrite, reason=""
                        )
                    return await interaction.respond(
                        f"Channel sudah tidak disembunyikan!", ephemeral=True, delete_after=5
                    )

            elif selected == "clear":
                btn_view = discord.ui.View()
                btn = discord.ui.Button(style=discord.ButtonStyle.danger, label="Lanjutkan")

                async def btn_view_callback(interaction: discord.Interaction):
                    await interaction.response.defer()
                    check = (
                        lambda m: not m.author.id == interaction.client.user.id
                    )  # TODO: smth better
                    await interaction.channel.purge(limit=500, check=check)
                    return await interaction.edit_original_response(
                        content="Done!", view=None, delete_after=5
                    )

                btn.callback = btn_view_callback
                btn2 = discord.ui.Button(style=discord.ButtonStyle.green, label="Batal")

                async def btn2_view_callback(interaction: discord.Interaction):
                    await interaction.response.defer()
                    return await interaction.delete_original_response()

                btn2.callback = btn2_view_callback
                btn_view.add_item(btn)
                btn_view.add_item(btn2)
                return await interaction.respond(
                    f"Yakin tetap akan menghapusnya?", ephemeral=True, view=btn_view
                )

        @discord.ui.select(
            custom_id="activity",
            placeholder="Pilih aktivitas",
            options=[
                discord.SelectOption(label="Watch Together", value="watch_together"),
                discord.SelectOption(label="Poker Night", value="poker_night"),
                discord.SelectOption(label="Jamspace", value="jamspace"),
                discord.SelectOption(label="Putt Party", value="putt_party"),
                discord.SelectOption(label="Gartic Phone", value="gartic_phone"),
                discord.SelectOption(
                    label="Know What I Meme", value="know_what_i_meme"
                ),
                discord.SelectOption(
                    label="Chess In The Park", value="chess_in_the_park"
                ),
                discord.SelectOption(label="Bobble League", value="bobble_league"),
                discord.SelectOption(label="Land", value="land"),
                discord.SelectOption(label="Sketch Heads", value="sketch_heads"),
                discord.SelectOption(label="Blazing 8s", value="blazing_8s"),
                discord.SelectOption(label="SpellCast", value="spell_cast"),
                discord.SelectOption(
                    label="Checkers In The Park", value="checkers_in_the_park"
                ),
                discord.SelectOption(label="Letter League", value="letter_league"),
            ],
        )
        async def activites_callback(
            self, select: discord.ui.Select, interaction: discord.Interaction
        ):
            await interaction.response.defer()
            await interaction.message.edit(
                content=interaction.message.content, view=self
            )
            voice_channel = interaction.channel
            channel_data = recent_channel_id["temp"][str(voice_channel.id)]
            
            if not await Fungsi.has_voted(self, interaction.user.id):
                button1 = Button(
                    emoji="<:charis:1237457208774496266>",
                    label="VOTE",
                    url=f"https://top.gg/bot/{self.bot.user.id}/vote"
                )
                
                view = View()
                view.add_item(button1)
                embed = discord.Embed(
                    description=f"Silahkan [vote](https://top.gg/bot/{self.bot.user.id}/vote) bot terlebih dahulu untuk menggunakan perintah ini!",
                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                )
                
                return await interaction.respond(embed=embed, view=view, ephemeral=True)
            
            if interaction.user.id != channel_data:
                return await interaction.respond(
                    "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                    ephemeral=True,
                    delete_after=5,
                )
            invite = await interaction.channel.create_activity_invite(
                discord.EmbeddedActivity[select.values[0]]
            )
            return await interaction.respond(
                f"{interaction.user.mention} membuat link invitation activity_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍_‍{invite}"
            )

        @discord.ui.select(
            select_type=discord.ComponentType.user_select,
            placeholder="Pilih user untuk menggunakan menu ini",
            custom_id="member_settings",
        )
        async def view_callback(
            self, select: discord.ui.Select, interaction: discord.Interaction
        ):
            await interaction.response.defer()
            await interaction.message.edit(
                content=interaction.message.content, view=self
            )
        
            voice_channel = interaction.channel
            channel_data = recent_channel_id["temp"].get(str(voice_channel.id))
            if not channel_data or interaction.user.id != channel_data:
                return await interaction.respond(
                    "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                    ephemeral=True,
                    delete_after=5,
                )
        
            # "cool placeholder"
            if self.bot.get_user(interaction.user.id):
                selected_user = await self.bot.fetch_user(select.values[0])
                if selected_user.id == interaction.user.id:
                    return await interaction.respond(
                        "You can't edit yourself 🗿", ephemeral=True, delete_after=5
                    )
                elif selected_user.id == self.bot.user.id:
                    return await interaction.respond(
                        "You can't edit me bro 💀", ephemeral=True, delete_after=5
                    )
                elif selected_user.id == interaction.guild.owner_id:
                    return await interaction.respond(
                        "So, actually you want to get banned 🗿, you're trying to edit the owner? Lol",
                        ephemeral=True,
                        delete_after=5,
                    )
                # goofy ahh return messages 💀
                if not selected_user.guild:
                    return await interaction.respond(
                        "This user is not a member of this guild.",
                        ephemeral=True,
                        delete_after=5,
                    )
                elif selected_user.bot:
                    return await interaction.respond(
                        f'Dear {interaction.user.mention}, jika kamu mempunyai "Mata ✨", kamu akan melihat bahwa user yang kamu pilih adalah sebuah bot!',  # better way?
                        ephemeral=True,
                        delete_after=15,
                    )
                await interaction.respond(
                    "Pilih opsi untuk mengedit user ini.",
                    view=Views.UserSelector(
                        user=interaction.user, edit_user=selected_user
                    ),
                    ephemeral=True,
                )
            else:
                return await interaction.respond(
                    "Ngapain? Kamu bukan owner channel ini.", ephemeral=True, delete_after=5
                )

class Embeds:

    class Panel(discord.Embed):

        def __init__(self, member: discord.Member):
            super().__init__(color=discord.Color.blurple())
            self.add_field(
                name="CHANNEL SEMENTARA BERHASIL DIBUAT",
                value=f"""
Ini adalah channel sementaramu, {member.mention}!

- Kamu dapat mengontrol channel ini dengan memilih opsi yang ada di menu dropdown di bawah atau gunakan **`/voice settings`**.
                """,
            )
            
            self.set_image(
                url="https://i.ibb.co.com/Y7cmfgN/Cuplikan-Layar-2024-05-20-06-14-05.png",
            )

    class Info(discord.Embed):
        def __init__(
            self,
            interaction: discord.Interaction,
            channel: discord.VoiceChannel,
            channel_data,
        ):
            super().__init__(title="Informasi Channel", color=discord.Color.blurple())
    
            utc_time = channel.created_at.replace(tzinfo=pytz.UTC)
            wib_timezone = pytz.timezone('Asia/Jakarta')
            wib_time = utc_time.astimezone(wib_timezone)
            creation_date = wib_time.strftime("%d %B %Y pukul %H:%M:%S WIB")
    
            self.add_field(name="Nama Channel", value=f"{channel.name}")
            self.add_field(
                name="Kreator",
                value=f"<@{channel_data}>",
            )
            self.add_field(name="", value="", inline=False) 
            self.add_field(
                name="Dibuat Pada", value=f"{creation_date} (<t:{int(channel.created_at.timestamp())}:R>)"
            )
            self.add_field(
                name="NSFW", value=f"{'Tidak' if not channel.is_nsfw() else 'Yup'}"
            )
            self.add_field(name="", value="", inline=False)
            self.add_field(
                name="Channel bitrate",
                value=f"{int(channel.bitrate / 1000)}Kbps ({'Kualitas Rendah' if channel.bitrate < 60000 else 'Kualitas Sedang' if channel.bitrate < 90000 else 'Kualitas Tinggi'})",
            )
            self.add_field(
                name="Kualitas Video",
                value=f"{'Tinggi' if channel.video_quality_mode == discord.VideoQualityMode.full else 'Normal'}",
            )
            self.add_field(name="", value="", inline=False)
            self.add_field(
                name="User Limit",
                value=f"{'Unlimited' if channel.user_limit == 0 else channel.user_limit}",
            )
            try:
                slowmode_delay = channel.slowmode_delay
            except:
                slowmode_delay = False
            self.add_field(
                name="Slowmode Delay",
                value=f"{'```-```' if not slowmode_delay else 'No Slowmode' if slowmode_delay == 0 else slowmode_delay}",
            )
            self.add_field(name="", value="", inline=False)
            self.add_field(
                name="User Bergabung",
                value=f"{list(map((lambda x: x.mention), channel.members))}",
            )
    
            self.set_footer(
                text=f"Dibuat oleh {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

    class ClearWarning(discord.Embed):
        """Discord Embed that will be used to warn the temp channel owner about clearing the channel content"""

        def __init__(self):
            super().__init__(title="Warning :warning:", color=discord.Color.red())
            self.add_field(
                name="Message",
                value=f"""
> Kamu akan menghapus semua pesan yang ada di channel ini.
                """,
            )

def setup(bot: discord.Bot):
    bot.add_cog(Fungsi(bot))
