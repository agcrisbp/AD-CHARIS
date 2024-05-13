import discord, os, pytz, humanize, json, string, asyncio, requests, time, csv
from discord.ext import commands
from openai import OpenAI, OpenAIError
from humanize.i18n import activate
from datetime import datetime
from bs4 import BeautifulSoup
from cogs.fungsi.database import DataBase, DATA_OWNER, DATA_SERVER, client, cuaca_key
from cogs.fungsi.func import Fungsi, Embeds, HOLIDAY_API, bot_creator_id, owner_ids, recent_channel_id, genius, sub_command_cooldown

activate('id_ID')


class Umum(discord.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.bot_start_time = datetime.utcnow()
        self.client = client
        self.channel_data = recent_channel_id
        self.cuaca_key = cuaca_key

    @commands.slash_command(
        name="cuaca",
        description="Menampilkan cuaca berdasarkan kota yang dipilih."
    )
    async def check_weather(self, ctx: discord.ApplicationContext, kota: str):
        await ctx.defer()
    
        api_key = self.cuaca_key
        base_url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={kota}&aqi=no"
    
        response = requests.get(base_url)
    
        if response.status_code == 200:
            weather_data = response.json()
            location = weather_data["location"]["name"]
            country = weather_data["location"]["country"]
            
            # Translate weather condition to Indonesian
            condition = self.translate_condition_to_indonesian(weather_data["current"]["condition"]["text"])
            
            temperature = weather_data["current"]["temp_c"]
            humidity = weather_data["current"]["humidity"]
            wind_speed = weather_data["current"]["wind_kph"]
    
            embed = discord.Embed(title=f"Cuaca di {location}, {country}", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            embed.add_field(name="Kondisi Cuaca", value=condition, inline=False)
            embed.add_field(name="Suhu (°C)", value=temperature, inline=True)
            embed.add_field(name="Kelembapan (%)", value=humidity, inline=True)
            embed.add_field(name="Kecepatan Angin (km/jam)", value=wind_speed, inline=True)
            embed.set_footer(text="Powered by WeatherAPI")
    
            await ctx.respond(content="", embed=embed, delete_after=60)
        else:
            await ctx.respond(content="Maaf, tidak dapat menemukan informasi cuaca untuk kota tersebut.", delete_after=5)
    
    def translate_condition_to_indonesian(self, condition):
        translation_map = {
            "Sunny": "Cerah",
            "Clear": "Cerah",
            "Partly cloudy": "Cerah Berawan",
            "Cloudy": "Berawan",
            "Overcast": "Mendung",
            "Mist": "Kabut",
            "Patchy rain possible": "Hujan Ringan Kemungkinan",
            "Patchy snow possible": "Salju Ringan Kemungkinan",
            "Patchy sleet possible": "Hujan Salju Kemungkinan",
            "Patchy freezing drizzle possible": "Hujan Drizzle Beku Kemungkinan",
            "Thundery outbreaks possible": "Badai Petir Kemungkinan",
            "Blowing snow": "Salju",
            "Blizzard": "Badai Salju",
            "Fog": "Kabut",
            "Freezing fog": "Kabut Beku",
            "Patchy light drizzle": "Gerimis Ringan",
            "Light drizzle": "Gerimis",
            "Freezing drizzle": "Hujan Drizzle Beku",
            "Heavy freezing drizzle": "Hujan Drizzle Beku Berat",
            "Patchy light rain": "Hujan Ringan",
            "Light rain": "Hujan Ringan",
            "Moderate rain at times": "Hujan Sedang Kadang-Kadang",
            "Moderate rain": "Hujan Sedang",
            "Heavy rain at times": "Hujan Berat Kadang-Kadang",
            "Heavy rain": "Hujan Berat",
            "Light freezing rain": "Hujan Beku Ringan",
            "Moderate or heavy freezing rain": "Hujan Beku Sedang atau Berat",
            "Light sleet": "Hujan Salju Ringan",
            "Moderate or heavy sleet": "Hujan Salju Sedang atau Berat",
            "Patchy light snow": "Salju Ringan",
            "Light snow": "Salju Ringan",
            "Patchy moderate snow": "Salju Sedang",
            "Moderate snow": "Salju Sedang",
            "Patchy heavy snow": "Salju Berat",
            "Heavy snow": "Salju Berat",
            "Ice pellets": "Batu Es",
            "Light rain shower": "Hujan Badai Ringan",
            "Moderate or heavy rain shower": "Hujan Badai Sedang atau Berat",
            "Torrential rain shower": "Hujan Badai Deras",
            "Light sleet showers": "Hujan Salju Ringan",
            "Moderate or heavy sleet showers": "Hujan Salju Sedang atau Berat",
            "Light snow showers": "Hujan Salju Ringan",
            "Moderate or heavy snow showers": "Hujan Salju Sedang atau Berat",
            "Light showers of ice pellets": "Badai Es Ringan",
            "Moderate or heavy showers of ice pellets": "Badai Es Sedang atau Berat",
            "Patchy light rain with thunder": "Hujan Ringan dengan Petir",
            "Moderate or heavy rain with thunder": "Hujan Sedang atau Berat dengan Petir",
            "Patchy light snow with thunder": "Salju Ringan dengan Petir",
            "Moderate or heavy snow with thunder": "Salju Sedang atau Berat dengan Petir",
            "Patchy rain nearby": "Hujan Ringan di Sekitar"  # Tambahan terjemahan baru
        }
        return translation_map.get(condition, condition)

    @commands.command(name='url', description='Memperpendek URL menggunakan tinyurl.')
    async def url_general(self, ctx, url: str):
        await self.shorten_url(ctx, url)

    @commands.slash_command(name='url', description='Memperpendek URL menggunakan tinyurl.')
    async def url_slash(self, ctx, url: str):
        await self.shorten_url(ctx, url)

    async def shorten_url(self, ctx, url: str):
        try:
            response = requests.get(f'http://tinyurl.com/api-create.php?url={url}')
            if response.status_code == 200:
                shortened_url = response.text

                # Extract thumbnails if available
                thumbnail_url = self.get_thumbnail_url(url)
                embed = discord.Embed(
                    description=f"URL Diperpendek: {shortened_url}.",
                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                    
                embed.set_footer(text=f"Dibuat oleh {ctx.author.name}!", icon_url=ctx.author.avatar.url)

                if hasattr(ctx, 'respond'):
                    await ctx.respond(embed=embed)
                else:
                    await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    description=f"Error occurred while shortening URL.",
                    color=discord.Color.red())
                
                if hasattr(ctx, 'respond'):
                    await ctx.respond(embed=embed)
                else:
                    await ctx.send(embed=embed)
        except Exception as e:
            if hasattr(ctx, 'respond'):
                await ctx.respond(content=f'Error: {str(e)}')
            else:
                await ctx.send(content=f'Error: {str(e)}')

    def get_thumbnail_url(self, url):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract thumbnail URL from the HTML content
            thumbnail_tag = soup.find('meta', property='og:image')
            if thumbnail_tag:
                return thumbnail_tag['content']
        except Exception as e:
            print(f"Error while fetching thumbnail: {str(e)}")
        return None

    @commands.command(name='jam', description='Menampilkan informasi hari dan waktu saat ini.')
    async def cek_hari(self, ctx):  # Added 'self' parameter
        await self.convert_to_milliseconds(ctx)

    @commands.slash_command(name='jam', description='Menampilkan informasi hari dan waktu saat ini.')
    async def cek_hari_slash(self, ctx):  # Added 'self' parameter
        await self.convert_to_milliseconds(ctx)

    async def convert_to_milliseconds(self, ctx):  # Added 'self' parameter
        # Mengatur zona waktu ke Waktu Indonesia Barat (WIB)
        wib_timezone = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(wib_timezone)
        
        # Menghitung miliseconds
        milliseconds = int(current_time.timestamp() * 1000)
    
        # Format waktu dalam format WIB dengan hari, tanggal, dan jam
        formatted_time = current_time.strftime('%A, %d %B %Y %H:%M:%S')
    
        embed = discord.Embed(
            title='Informasi Hari dan Waktu',
            description=f'Hari/Tanggal: **{formatted_time}** WIB\nMiliseconds: **{milliseconds}**',
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
        )
    
        if hasattr(ctx, 'respond'):
            await ctx.respond(embed=embed, delete_after=15)
        else:
            await ctx.send(embed=embed, delete_after=15)
            await ctx.message.delete()
    

    @commands.command(name='owner')
    async def owner(self, ctx):
        await self.list_owners(ctx)
    @commands.slash_command(name='owner', description='Menampilkan daftar Kreator dan Developer Voicecord.')
    async def owner_slash(self, ctx):
        await self.list_owners(ctx)
    async def list_owners(self, ctx):
        """Daftar kreator bot."""
        global bot_creator_id, owner_ids
    
        owner_data = []
        try:
            with open(DATA_OWNER, 'r') as owner_file:
                reader = csv.reader(owner_file)
                owner_data = list(reader)
        except FileNotFoundError:
            pass
    
        # Find the bot creator in the data
        bot_creator = await self.bot.application_info()
        bot_creator_id = discord.User = bot_creator.owner

        bot_creator_info = f"## Kreator\n666. [{bot_creator_id.name}](https://discord.com/users/{bot_creator_id.id})."
    
        owners_list = []
        for index, owner in enumerate(owner_data):
            if str(owner[1]) != str(bot_creator_id):
                owner_user = await self.bot.fetch_user(owner[1])
                owners_list.append(f"## Developer\n{index + 1}. [{owner_user.name}](https://discord.com/users/{owner[1]}).")
    
        if bot_creator_info:
            owners_message = "\n".join([bot_creator_info] + owners_list) if owners_list else "Tidak ada owner lain ditemukan. Gunakan `!add` untuk menambahkan owner baru."
            embed = discord.Embed(
                description=owners_message,
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
            )
    
            creation_date = self.bot.user.created_at.strftime("%Y")
            
            embed.set_footer(text=f"© {creation_date} Made with ♡ by {bot_creator_id.name}", icon_url=bot_creator_id.avatar.url)
            
            if hasattr(ctx, 'respond'):
                await ctx.respond(embed=embed, delete_after=5)
            else:
                await ctx.send(embed=embed, delete_after=5)
                await ctx.message.delete()
        else:
            if hasattr(ctx, 'respond'):
                await ctx.respond("Kosong.", ephemeral=True)
            else:
                await ctx.send("Kosong.")
                await ctx.message.delete()
    
    # Hari Libur
    @commands.command(name='haribesar')
    async def haribesar(self, ctx):
        await self.cek_hari_besar(ctx)
    @commands.slash_command(name='hari_besar', description='Menampilkan 3 Hari Besar di Indonesia yang akan datang.')
    async def haribesar_slash(self, ctx):
        await self.cek_hari_besar(ctx)
    async def cek_hari_besar(self, ctx):
        response = requests.get(HOLIDAY_API)
        if response.status_code == 200:
            holidays = response.json()
    
            # Check if there are upcoming holidays
            if holidays:
                # Filter out past holidays
                wib_timezone = pytz.timezone('Asia/Jakarta')
                current_date = datetime.now(wib_timezone)
                upcoming_holidays = [holiday for holiday in holidays if datetime.strptime(holiday['date'], '%Y-%m-%d').replace(tzinfo=wib_timezone) >= current_date]
    
                if upcoming_holidays:
                    # Get details of the next three holidays
                    upcoming_holidays = upcoming_holidays[:3]
                    embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                    embed.title = "Hari Besar Mendatang"
    
                    for idx, holiday_info in enumerate(upcoming_holidays, start=1):
                        holiday_name = holiday_info['localName']
                        holiday_date = datetime.strptime(holiday_info['date'], '%Y-%m-%d').replace(tzinfo=wib_timezone)
                        time_until_holiday = holiday_date - current_date
    
                        embed.add_field(
                            name=f"{idx}. {holiday_name}",
                            value=f"Akan diperingati pada **__{holiday_date.strftime('%d %B %Y')}__** ({time_until_holiday.days} hari lagi).",
                            inline=False
                        )
    
                    if hasattr(ctx, 'respond'):
                        await ctx.respond(embed=embed, delete_after=30)
                    else:
                        await ctx.send(embed=embed, delete_after=30)
                else:
                    if hasattr(ctx, 'respond'):
                        await ctx.respond(content="> Tidak ada Hari Besar mendatang.", delete_after=5)
                    else:
                        await ctx.send(content="> Tidak ada Hari Besar mendatang.", delete_after=5)
            else:
                if hasattr(ctx, 'respond'):
                    await ctx.respond(content="> Belum ada data Hari Besar yang diperbarui.", delete_after=5)
                else:
                    await ctx.send(content="> Belum ada data Hari Besar yang diperbarui.", delete_after=5)

    # BUG REPORT
    @commands.slash_command(name='bug', description='Melaporkan bug atau request fitur.')
    async def bug_slash(self, ctx, title: discord.Option(str, description="Masukkan keterangan bug yang akan dilaporkan.", choices=[]), *, message: discord.Option(str, description="Tuliskan detail bug yang dilaporkan.", choices=[]), screenshot: discord.Attachment = None):
        await self.bug(ctx, title, message, screenshot)
    async def bug(self, ctx, title: str, message: str, screenshot: discord.Attachment = None):
        bot_creator = await self.bot.application_info()
        bot_creator_id = discord.User = bot_creator.owner.id
        owner = self.bot.get_user(bot_creator_id)
        if owner:
            bug_report = f""
            embed = discord.Embed(
                title=title,
                description=f"{message}",
                color=discord.Color.red()
            )
            if screenshot:
                # Add the screenshot as an attachment to the embed
                embed.set_image(url=screenshot.url)
                
            embed.set_footer(text=f"Dilaporkan oleh {ctx.author.name} (ID: {ctx.author.id})")
            
            await owner.send(embed=embed)
            embed = discord.Embed(
                description=f'Berhasil melaporkan bug!',
                color=0x7289da
            )
        
            if hasattr(ctx, 'respond'):
                await ctx.respond(embed=embed, delete_after=5)
            else:
                await ctx.send(embed=embed, delete_after=5)
        else:
            embed = discord.Embed(
                description=f'Gagal melaporkan bug! Silahkan DM langsung ke [{bot_creator.name}](https://discord.com/users/{bot_creator_id}).',
                color=discord.Color.red()
            )
        
            if hasattr(ctx, 'respond'):
                await ctx.respond(embed=embed, delete_after=5)
            else:
                await ctx.send(embed=embed, delete_after=5)

    # LIRIK
    @commands.command(name='lyrics')
    async def lyrics_command_general(self, ctx, *args):
        await self.lyrics_command(ctx, ' '.join(args))
    @commands.slash_command(name='lyrics', description="Mencari lirik lagu di Genius.")
    async def lyrics_command_slash(self, ctx, query: discord.Option(str, description="Masukkan nama artis dan judul lagu.", choices=[])):
        await self.lyrics_command(ctx, query)
    async def lyrics_command(self, ctx, query: str):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        
        try:
            # Search for lyrics by the provided query
            song = genius.search_song(query)
    
            # Check if any lyrics are found
            if song:
                # Find the index of the title
                title_index = song.lyrics.find(f"{song.title}")
    
                # List of sections to look for
                sections = ["[Verse", "[Intro", "[Chorus", "[Outro", "[Bridge"]
    
                # Find the index of the next section after the title
                start_index = min(song.lyrics.find(section, title_index) for section in sections if section in song.lyrics)
    
                # Extract lyrics from the first section index till the end
                lyrics = song.lyrics[start_index:]
    
                # Replace "{i}Embed" with an empty string in the lyrics
                for i in range(1, 100000):  # Assuming the maximum number is 100,000
                    lyrics = lyrics.replace(f"{i}Embed", "").replace("Embed", "").replace("You might also like", "")
    
                # Create an embed with the modified lyrics
                embed = discord.Embed(title=f"Lirik {song.artist} - {song.title}", description=lyrics, color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                embed.set_footer(text="Powered by Genius Lyrics API")
    
                # Send the embed message
                await ctx.respond(content="", embed=embed)
            else:
                await ctx.respond(content="Lyrics not found.")
        except Exception as e:
            # Print the exception for debugging
            print(f"An error occurred: {e}")
            await ctx.respond(content="Hari-hari error.")

    # UPTIME
    @commands.slash_command(name='uptime', description="Waktu aktif bot.")
    async def aktif_slash(self, ctx):
        await self.uptime(ctx)
    @commands.command(name='uptime', description="Waktu aktif bot.")
    async def aktif(self, ctx):
        await self.uptime(ctx)
    async def uptime(self, ctx):
        # Convert bot start time to WIB timezone
        wib_timezone = pytz.timezone('Asia/Jakarta')
        bot_start_time_wib = self.bot_start_time.replace(tzinfo=pytz.utc).astimezone(wib_timezone)
        bot_start_time_formatted = bot_start_time_wib.strftime('%d %B %Y %H:%M:%S')
    
        uptime_delta = datetime.utcnow() - self.bot_start_time
    
        if uptime_delta.total_seconds() < 60:
            uptime_str = f"{int(uptime_delta.total_seconds())} detik"
        elif uptime_delta.total_seconds() < 3600:
            minutes, seconds = divmod(int(uptime_delta.total_seconds()), 60)
            uptime_str = f"{minutes} menit {seconds} detik"
        elif uptime_delta.total_seconds() < 86400:  # Add this condition for days
            hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours} jam {minutes} menit {seconds} detik"
        else:
            days, remainder = divmod(int(uptime_delta.total_seconds()), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days} hari {hours} jam {minutes} menit"
    
        embed = discord.Embed(
            description=f"Sudah aktif selama {uptime_str} sejak {bot_start_time_formatted} WIB.",
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            
        if hasattr(ctx, 'respond'):
            await ctx.respond(embed=embed, delete_after=5)
        else:
            await ctx.send(embed=embed, delete_after=5)

    # MENGUBAH NAMA CHANNEL SEMENTARA
    voice = discord.SlashCommandGroup(
        name="voice",
        description="Mengatur channel suara sementara.",
        guild_only=True,
    )
    @voice.command(
      name='settings',
      description="Mengatur channel suara sementara.",
      guild_only=True,
    )
    async def voice_settings(self, ctx, settings: discord.Option(str, description="Pilih pengaturan.", choices=[discord.OptionChoice(name="Ubah Nama", value="name"), discord.OptionChoice(name="Reset Nama", value="resetnama"), discord.OptionChoice(name="Ubah Bitrate", value="bitrate"), discord.OptionChoice(name="Ubah Limit", value="limit"), discord.OptionChoice(name="Slowmode", value="slow_mode"), discord.OptionChoice(name="NSFW", value="nsfw"), discord.OptionChoice(name="Info", value="info"), discord.OptionChoice(name="Hapus Channel", value="delete"), discord.OptionChoice(name="Bersihkan Riwayat Chat", value="clear") ])):
        interaction = ctx
        voice_channel = ctx.author.voice.channel
        channel_data = recent_channel_id["temp"].get(str(voice_channel.id))
        
        if interaction.response.is_done():
            return
        
        if interaction.user.id != channel_data:
            return await interaction.respond(
                "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                ephemeral=True,
                delete_after=5,
            )
        
        if settings == "name":
            if str(voice_channel.id) in recent_channel_id["used"]:
                embed = discord.Embed(
                    description=f"Perintah ini hanya dapat digunakan sekali untuk setiap channel suara sementara.",
                    color=discord.Color.red())
    
                await ctx.respond(embed=embed, delete_after=5)
    
            modal = discord.ui.Modal(title="Nama Channel")
            modal.add_item(
                discord.ui.InputText(
                    label="Nama Baru",
                    placeholder="Masukkan nama baru untuk channel ini",
                    value=voice_channel.name,
                )
            )
    
            async def modal_callback(interaction):
                if interaction.response.is_done():
                    return
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
                    await voice_channel.edit(name=channel_name)
                    recent_entry = recent_channel_id["user"]
                    recent_entry[str(interaction.user.id)] = channel_name
                    recent_channel_id["used"][str(voice_channel.id)] = str(interaction.user.id)
                    DataBase.save_recent_channel_id(recent_channel_id)
                    return await interaction.respond(
                        f"Nama channel diubah menjadi **`{channel_name}`**!",
                        ephemeral=True,
                        delete_after=5,
                    )
    
            modal.callback = modal_callback
            return await interaction.response.send_modal(modal=modal)

        elif settings == "resetnama":
            if interaction.response.is_done():
                return
            await self.clear_channel_name(ctx)
 
        elif settings == "info":
            if interaction.response.is_done():
                return
            channel: discord.VoiceChannel = await interaction.guild.fetch_channel(
                int(voice_channel.id)
            )
            
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

        elif settings == "delete":
            if interaction.response.is_done():
                return
            if not channel_data or interaction.user.id != channel_data:
                return await interaction.respond(
                    "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                    ephemeral=True,
                    delete_after=5,
                )
            else:
                await voice_channel.delete()
                return await interaction.respond(
                    "Done.",
                    ephemeral=True,
                    delete_after=5,
                )

        elif settings == "slow_mode":
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
                if interaction.response.is_done():
                    return
                slowmode_delay = int(dropdown.values[0])
                await voice_channel.edit(slowmode_delay=slowmode_delay)
                return await interaction.response.edit_message(
                    content="Slow Mode berhasil diubah!", view=None, delete_after=5,
                )

            dropdown.callback = slow_mode_select_callback
            return await interaction.respond(
                "Pilih periode di menu di bawah ini",
                view=view,
                ephemeral=True,
                delete_after=300,
            )

        elif settings == "nsfw":
            if interaction.response.is_done():
                return
            if not channel_data or interaction.user.id != channel_data:
                return await interaction.respond(
                    "Hanya pemilik channel yang dapat menggunakan perintah ini.",
                    ephemeral=True,
                    delete_after=5,
                )
                
            if voice_channel.nsfw:
                await voice_channel.edit(nsfw=False)
                return await interaction.respond(
                    f"Channel berhasil ditandai sebagai Non-NSFW!",
                    ephemeral=True,
                    delete_after=5,
                )
            else:
                await voice_channel.edit(nsfw=True)
                return await interaction.respond(
                    f"Channel berhasil ditandai sebagai NSFW!",
                    ephemeral=True,
                    delete_after=5,
                )

        elif settings == "bitrate":
            channel_bits = int(
                str(int(interaction.guild.bitrate_limit))[:-3]
            )  # Bro wtf is this butt-shit?
            placeholder = f"8 Sampai {channel_bits}"
            modal = discord.ui.Modal(title="Channel Bitrate")
            modal.add_item(
                discord.ui.InputText(
                    label="Channel Bitrate Value",
                    placeholder=placeholder,
                    value=voice_channel.user_limit,
                )
            )

            async def modal_callback(interaction: discord.Interaction):
                if interaction.response.is_done():
                    return
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
                await voice_channel.edit(bitrate=(int(modal_value) * 1000))
                return await interaction.respond(
                    f"Channel Bitrate diubah menjadi {modal_value}",
                    ephemeral=True,
                    delete_after=5,
                )

            modal.callback = modal_callback
            return await interaction.response.send_modal(modal=modal)

        elif settings == "limit":
            modal = discord.ui.Modal(title="Channel Limit")
            modal.add_item(
                discord.ui.InputText(
                    label="Channel Limit Baru",
                    placeholder="Masukkan jumlah channel limit (0 untuk unlimited)",
                    value=voice_channel.user_limit,
                )
            )

            async def modal_callback(interaction: discord.Interaction):
                if interaction.response.is_done():
                    return
                channel_limit = modal.children[0].value
                if not channel_limit.isnumeric():
                    return await interaction.respond(
                        f"Masukkan nomor yang benar!",
                        ephemeral=True,
                        delete_after=5,
                    )
                await voice_channel.edit(user_limit=int(channel_limit))
                return await interaction.respond(
                    f"Channel User Limit diubah menjadi {'Unlimited' if int(channel_limit) == 0 else channel_limit}",
                    ephemeral=True,
                    delete_after=5,
                )

            modal.callback = modal_callback
            return await interaction.response.send_modal(modal=modal)

        elif settings == "clear":
            btn_view = discord.ui.View()
            btn = discord.ui.Button(style=discord.ButtonStyle.danger, label="Lanjutkan")
        
            async def btn_view_callback(interaction: discord.Interaction):
                if interaction.response.is_done():
                    return
                check = (
                    lambda m: not m.author.id == interaction.client.user.id
                )  # TODO: smth better
                await voice_channel.purge(limit=500, check=check)
                await interaction.response.edit_message(content="Done!", view=None, delete_after=5)
        
            btn.callback = btn_view_callback
            btn2 = discord.ui.Button(style=discord.ButtonStyle.green, label="Batal")
        
            async def btn2_view_callback(interaction: discord.Interaction):
                try:
                    await ctx.delete()
                except Exception as e:
                    print(f'{e}')
        
            btn2.callback = btn2_view_callback
            
            btn_view.add_item(btn)
            btn_view.add_item(btn2)
            
            await interaction.respond(
                content="Yakin tetap akan menghapusnya?", ephemeral=True, view=btn_view
            )

    async def clear_channel_name(self, ctx):
        try:
            global recent_channel_id
            
            if "reset_used" not in recent_channel_id:
                recent_channel_id["reset_used"] = {}
            
            voice_channel = ctx.author.voice.channel
    
            if str(voice_channel.id) in recent_channel_id["reset_used"]:
                embed = discord.Embed(
                    description=f"Perintah ini hanya dapat digunakan sekali untuk setiap channel suara sementara.",
                    color=discord.Color.red())
                return await ctx.respond(embed=embed, delete_after=5)
    
            # Retrieve owner_id from recent_channel_id["temp"]
            if str(voice_channel.id) in recent_channel_id["temp"]:
                owner_id = recent_channel_id["temp"][str(voice_channel.id)]
    
            # Mark the reset command as used for this channel ID
            recent_channel_id["reset_used"][str(voice_channel.id)] = owner_id
    
            # Reset the channel name to its default
            default_name = f'Channel {ctx.author.display_name}'
            await ctx.author.voice.channel.edit(name=default_name)
    
            # Remove the default channel name from the database
            user_id = str(ctx.author.id)
            if user_id in recent_channel_id["user"]:
                del recent_channel_id["user"][user_id]
                DataBase.save_recent_channel_id(recent_channel_id)
    
            # Send success message
            embed = discord.Embed(
                description=f"Nama channel berhasil direset.",
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            await ctx.respond(embed=embed, delete_after=5)
    
        except Exception as e:
            # Send error message if an exception occurs
            embed = discord.Embed(
                description=f"Terjadi kesalahan: {str(e)}",
                color=discord.Color.red())
            await ctx.respond(embed=embed, delete_after=5)

    # MENGATUR PRIVASI CHANNEL SUARA SEMENTARA
    VALID_PRIVASI_OPTIONS = ['public', 'private', 'add', 'hide', 'unhide']
    
    @commands.command(name='perm', aliases=['permission'])
    async def ganti_izin(self, ctx, privasi: str, member: discord.Member = ''):
        await self.set_channel_permissions(ctx, privasi, member)
    @voice.command(name='permission', description='Mengubah izin channel suara sementara.')
    async def ganti_izin_slash(self, ctx, privasi: discord.Option(str, description="Pilih privasi yang akan diterapkan. Dapat menambah member pada Privat/Sembunyikan.", choices=[discord.OptionChoice(name="Publik", value="public"), discord.OptionChoice(name="Privat", value="private"), discord.OptionChoice(name="Menambah Izin Member", value="add"), discord.OptionChoice(name="Sembunyikan", value="hide") ]), member: discord.Member = ''):
        await self.set_channel_permissions(ctx, privasi, member)
    async def set_channel_permissions(self, ctx, privasi: str, member: discord.Member = ''):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
    
        if privasi is None:
            embed = discord.Embed(
                description=f"Pilihan tidak valid. Opsi yang tersedia adalah:  **`{', '.join(VALID_PRIVASI_OPTIONS)}`**.",
                color=discord.Color.red()
            )
            await ctx.respond(content='', embed=embed, delete_after=5)
            return
    
        # Memeriksa cooldown untuk subcommand
        if privasi.lower() in sub_command_cooldown:
            current_time = time.time()
            last_command_time = sub_command_cooldown[privasi.lower()]
    
            # Memeriksa apakah waktu antar subcommand sudah mencapai 15 detik
            if current_time - last_command_time < 60:
                embed = discord.Embed(
                description=f"Harap tunggu {60 - int(current_time - last_command_time)} detik sebelum menggunakan perintah ini lagi.",
                color=discord.Color.red())
                        
                await ctx.respond(content='', embed=embed, delete_after=5)
                return
              
            sub_command_cooldown[privasi.lower()] = time.time()
        else:
            sub_command_cooldown[privasi.lower()] = time.time()
    
        try:
            if ctx.author.voice and ctx.author.voice.channel:
                voice_channel = ctx.author.voice.channel
    
                # Memvalidasi owner channel
                is_owner = recent_channel_id["temp"].get(str(voice_channel.id)) == ctx.author.id
    
                if is_owner:
                    if privasi.lower() == 'public':
                        # Menyinkronkan permission dengan kategori
                        await voice_channel.edit(sync_permissions=True, reason="Channel diubah ke publik oleh temp owner.")
                        await voice_channel.set_permissions(ctx.author, view_channel=True, read_message_history=True, connect=True, speak=True, send_messages=True, manage_channels=True, set_voice_channel_status=True, reason="User adalah temp owner.")
                        embed = discord.Embed(
                        description=f"Izin channel diubah menjadi publik.",
                        color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                                
                        await ctx.respond(content='', embed=embed, delete_after=5)
    
                    elif privasi.lower() == 'private':
                                                        
                        if member:
                            if isinstance(member, discord.Member):
                                user_id = member.id
                            else:
                                # Check if it's a mention
                                user_id = member.strip('<@!>').replace('>', '') if member.isdigit() else None
                                            
                            if not user_id:
                                embed = discord.Embed(
                                    description=f"Tidak dapat menemukan user dengan ID atau mention {member}.",
                                    color=discord.Color.red()
                                )
                                await ctx.respond(content='', embed=embed, delete_after=5)
                                return
                                            
                            user = ctx.guild.get_member(user_id)
                            if user:
                                await voice_channel.set_permissions(user, connect=False, speak=False, view_channel=True, reason="User dilarang bergabung oleh temp owner.")
                                embed = discord.Embed(
                                    description=f"Berhasil menambahkan {user.mention} ke dalam daftar member yang tidak dapat bergabung.",
                                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                                )
                                await ctx.respond(content='', embed=embed, delete_after=5)
                            else:
                                embed = discord.Embed(
                                    description=f"Tidak dapat menemukan user dengan ID atau mention {member}.",
                                    color=discord.Color.red()
                                )
                                await ctx.respond(content='', embed=embed, delete_after=5)
                        else:
                            # Hide the channel for everyone except the channel owner
                            channel_permissions = voice_channel.overwrites
                                    
                            for role, permission in channel_permissions.items():
                                if isinstance(role, discord.Role):
                                    await voice_channel.set_permissions(role, connect=False, reason="Channel diubah ke privat oleh temp owner.")
                                    await voice_channel.set_permissions(ctx.guild.default_role, connect=False, reason="Channel diubah ke privat oleh temp owner.")
                                elif isinstance(role, discord.Member) and role != ctx.author:
                                    await voice_channel.set_permissions(role, connect=False, reason="Channel diubah ke privat oleh temp owner.")
                                    await voice_channel.set_permissions(ctx.guild.default_role, connect=False, reason="Channel diubah ke privat oleh temp owner.")
                                    
                            await voice_channel.set_permissions(ctx.author, view_channel=True, read_message_history=True, connect=True, speak=True, send_messages=True, manage_channels=True, set_voice_channel_status=True, reason="User adalah temp owner.")
                            embed = discord.Embed(
                                description=f"Izin channel diubah menjadi privat.",
                                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                            )
                            await ctx.respond(content='', embed=embed, delete_after=5)
    
                    if privasi.lower() == 'add':
                        if not member:
                            embed = discord.Embed(
                            description=f"Query tidak boleh kosong. Mention seseorang!",
                            color=discord.Color.red())
                                    
                            await ctx.respond(content='', embed=embed, delete_after=5)
                            return
                    
                        if isinstance(member, discord.Member):
                            user_id = member.id
                        else:
                            # Check if it's a mention
                            user_id = member.strip('<@!>').replace('>', '') if member.isdigit() else None
                    
                        if not user_id:
                            embed = discord.Embed(
                            description=f"Tidak dapat menemukan user dengan ID atau mention {member}.",
                            color=discord.Color.red())
                                    
                            await ctx.respond(content='', embed=embed, delete_after=5)
                            return
                    
                        user = ctx.guild.get_member(user_id)
                        if user:
                            await voice_channel.set_permissions(user, connect=True, speak=True, view_channel=True, send_messages=True, read_message_history=True, reason="User diizinkan bergabung oleh temp owner.")
                            embed = discord.Embed(
                            description=f"Berhasil menambahkan {user.mention} ke daftar yang diizinkan bergabung.",
                            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                                    
                            await ctx.respond(content='', embed=embed, delete_after=5)
                        else:
                            embed = discord.Embed(
                            description=f"Tidak dapat menemukan user dengan ID atau mention {member}.",
                            color=discord.Color.red())
                                    
                            await ctx.respond(content='', embed=embed, delete_after=5)
    
                    elif privasi.lower() == 'hide':
                        await voice_channel.set_permissions(ctx.guild.default_role, view_channel=False, reason="Channel disembunyikan oleh temp owner.")
                                                        
                        if member:
                            if isinstance(member, discord.Member):
                                user_id = member.id
                            else:
                                # Check if it's a mention
                                user_id = member.strip('<@!>').replace('>', '') if member.isdigit() else None
                                            
                            if not user_id:
                                embed = discord.Embed(
                                    description=f"Tidak dapat menemukan user dengan ID atau mention {member}.",
                                    color=discord.Color.red()
                                )
                                await ctx.respond(content='', embed=embed, delete_after=5)
                                return
                                            
                            user = ctx.guild.get_member(user_id)
                            if user:
                                await voice_channel.set_permissions(user, view_channel=False, reason="Channel disembunyikan dari user ini oleh temp owner.")
                                embed = discord.Embed(
                                    description=f"Berhasil menyembunyikan channel dari {user.mention}.",
                                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                                )
                                await ctx.respond(content='', embed=embed, delete_after=5)
                            else:
                                embed = discord.Embed(
                                    description=f"Tidak dapat menemukan user dengan ID atau mention {member}.",
                                    color=discord.Color.red()
                                )
                                await ctx.respond(content='', embed=embed, delete_after=5)
                        else:
                            # Hide the channel for everyone except the channel owner
                            channel_permissions = voice_channel.overwrites
                                    
                            for role, permission in channel_permissions.items():
                                if isinstance(role, discord.Role):
                                    await voice_channel.set_permissions(role, view_channel=False, reason="Channel disembunyikan oleh temp owner.")
                                elif isinstance(role, discord.Member) and role != ctx.author:
                                    await voice_channel.set_permissions(role, view_channel=False, reason="Channel disembunyikan oleh temp owner.")
                                    
                            await voice_channel.set_permissions(ctx.author, view_channel=True, read_message_history=True, connect=True, speak=True, send_messages=True, manage_channels=True, set_voice_channel_status=True, reason="User adalah temp owner.")
                            embed = discord.Embed(
                                description=f"Channel berhasil disembunyikan.",
                                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                            )
                            await ctx.respond(content='', embed=embed, delete_after=5)
    
                else:
                    embed = discord.Embed(
                    description=f"Hanya pemilik channel yang dapat menggunakan perintah ini!",
                    color=discord.Color.red
                        ())
                                    
                    await ctx.respond(content='', embed=embed, delete_after=5)
    
        except commands.CommandOnCooldown as e:
            embed = discord.Embed(
            description=f"Harap tunggu {round(e.retry_after)} detik sebelum menggunakan sub-perintah ini lagi.",
            color=discord.Color.red
                        ())
                                    
            await ctx.respond(content='', embed=embed, delete_after=5)
            
    @voice.command(
      name='kick',
      description="Mengeluarkan pengguna dari channel suara sementara.",
      guild_only=True,
    )
    async def disconnect_member(self, ctx, member: discord.Member):
        """Disconnects a member from the temporary voice channel (temp owner only)."""
        try:
            if ctx.author.voice and ctx.author.voice.channel:
                # Get the voice channel of the author
                voice_channel = ctx.author.voice.channel
        
                # Check if the author is the owner of the voice channel
                if str(voice_channel.id) in recent_channel_id["temp"]:
                    owner_id = recent_channel_id["temp"][str(voice_channel.id)]
                    if str(ctx.author.id) == str(owner_id):
                        if member.voice and member.voice.channel == voice_channel:
                            # Exclude the owner from being disconnected
                            if member != ctx.author:
                                await member.edit(voice_channel=None, reason="User ditendang oleh temp owner.")
                                embed = discord.Embed(
                                    description=f"{member.mention} telah ditendang dari channel suara sementara {voice_channel.mention} oleh {ctx.author.mention}.",
                                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                                await ctx.respond(embed=embed, delete_after=5)
                            else:
                                embed = discord.Embed(
                                    description="Kamu tidak dapat mengeluarkan diri sendiri dari channel suara sementara.",
                                    color=discord.Color.red())
                                await ctx.respond(embed=embed, delete_after=5)
                        else:
                            embed = discord.Embed(
                                description=f"Pengguna tidak berada di dalam channel suara sementara.",
                                color=discord.Color.red())
                            await ctx.respond(embed=embed, delete_after=5)
                    else:
                        embed = discord.Embed(
                            description=f"Hanya pemilik channel yang dapat menggunakan perintah ini.",
                            color=discord.Color.red())
                        await ctx.respond(embed=embed, delete_after=5)
                else:
                    await ctx.respond("Kamu harus berada di channel suara sementaramu untuk menggunakan perintah ini.", delete_after=5)
                    embed = discord.Embed(
                        description=f"Hanya pemilik channel yang dapat menggunakan perintah ini.",
                        color=discord.Color.red())
    
                    await ctx.respond(embed=embed, delete_after=5)
        except Exception as e:
            await ctx.respond(f"Terjadi kesalahan: {str(e)}", delete_after=5)
    
    # CHAT GPT
    gpt = discord.SlashCommandGroup(
        name="gpt",
        description="Setup ChatGPT-3.5.",
        guild_only=True,
    )
    @gpt.command(
      name='chat',
      description="Memulai percakapan dengan GPT-3.5 dalam sebuah thread.",
      guild_only=True,
    )
    async def gpt_command(self, ctx, privasi: discord.Option(str, description="Pilih privasi yang akan diterapkan.", choices=[discord.OptionChoice(name="Publik", value="public"), discord.OptionChoice(name="Privat", value="private")])):
        guild_name = str(ctx.guild.name)
        user_name = str(ctx.author.name)
        
        gpt_channel = None
        for channel_obj in ctx.guild.channels:
            if 'chat-gpt' in channel_obj.name:
                gpt_channel = channel_obj
                break
        if ctx.channel != gpt_channel:
            if hasattr(ctx, 'respond'):
                await ctx.respond(f"> Perintah ini hanya dapat digunakan di channel **{gpt_channel.mention if gpt_channel else 'chat-gpt'}**.", delete_after=5)
            else:
                await ctx.send(f"> Perintah ini hanya dapat digunakan di channel **{gpt_channel.mention if gpt_channel else 'chat-gpt'}**.", delete_after=5)
            return
        
        # Set the thread name
        thread_name = f"{ctx.author.name}'s Chat"
        
        # Check if a thread with the same name already exists
        existing_thread = discord.utils.get(ctx.channel.threads, name=thread_name)
        
        if existing_thread:
            thread = existing_thread
            # Mention the existing thread
            await ctx.respond(f"Thread sudah ada: {thread.mention}", delete_after=15)
        else:
            if privasi == "private":
                # Create a private thread
                thread = await ctx.channel.create_thread(name=thread_name, type=discord.ChannelType.private_thread)
                embed = discord.Embed(
                    description=f"Ini adalah thread privatmu dengan GPT-3.5-turbo. Thread akan dihapus otomatis jika tidak ada aktivitas dalam 1 jam.",
                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                )
                await thread.send(content=f'{ctx.author.mention}', embed=embed)
            else:
                # Create a public thread
                thread = await ctx.channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
                embed = discord.Embed(
                    description=f"Hi {ctx.author.mention}! Ini adalah thread publikmu dengan GPT-3.5-turbo. Thread akan dihapus otomatis jika tidak ada aktivitas dalam 1 jam.",
                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                )
                await thread.send(embed=embed)
            await ctx.respond('> Berhasil', delete_after=5)
        
        # Listen for messages in the thread and respond with GPT-3.5-turbo
        while True:
            try:
                message = await self.bot.wait_for('message', check=lambda m: m.channel == thread and not m.author.bot, timeout=3600)
                await Fungsi.process_message(self, thread, message)
            except asyncio.TimeoutError:
                await thread.send("Menghapus thread dalam 5 detik...")
                await asyncio.sleep(5)
                user_name = str(message.author.name)
                file_path = os.path.join(DATA_SERVER, guild_name, 'chatgpt', f'{user_name}_chat_history.json')
                        
                # Check if the file exists
                if os.path.exists(file_path):
                    # Delete the file
                    os.remove(file_path)
                        
                    # Check if the 'chatgpt' folder is empty
                    chatgpt_folder = os.path.join(DATA_SERVER, guild_name, 'chatgpt')
                    if not os.listdir(chatgpt_folder):
                        # If the folder is empty, delete it
                        os.rmdir(chatgpt_folder)
                        await thread.delete()
                        break
            except Exception as e:
                print(f"Error in thread message processing: {e}")

    @gpt.command(
      name='clear',
      description='Menghapus thread dan riwayat percakapan dengan Chat-GPT.',
      guild_only=True,
    )
    async def clear_conversation(self, ctx):
        guild_name = str(ctx.guild.name)
        user_name = str(ctx.author.name)
        
        gpt_channel = None
        for channel_obj in ctx.guild.channels:
            if 'chat-gpt' in channel_obj.name:
                gpt_channel = channel_obj
                break
        if ctx.channel != gpt_channel:
            if hasattr(ctx, 'respond'):
                await ctx.respond(f"> Perintah ini hanya dapat digunakan di channel **{gpt_channel.mention if gpt_channel else 'chat-gpt'}**.", delete_after=5)
            else:
                await ctx.send(f"> Perintah ini hanya dapat digunakan di channel **{gpt_channel.mention if gpt_channel else 'chat-gpt'}**.", delete_after=5)
            return
    
        # Check if the user already has a chat thread
        existing_threads = [thread for thread in ctx.guild.threads if thread.name == f"{ctx.author.name}'s Chat"]
        if existing_threads:
            # If a thread exists, delete it
            await existing_threads[0].delete()
    
        # Get the file path
        file_path = os.path.join(DATA_SERVER, guild_name, 'chatgpt', f'{user_name}_chat_history.json')
    
        # Check if the file exists
        if os.path.exists(file_path):
            # Delete the file
            os.remove(file_path)
    
            # Check if the 'chatgpt' folder is empty
            chatgpt_folder = os.path.join(DATA_SERVER, guild_name, 'chatgpt')
            if not os.listdir(chatgpt_folder):
                # If the folder is empty, delete it
                os.rmdir(chatgpt_folder)
    
            # Notify the user
            embed = discord.Embed(
                description='Riwayat percakapan berhasil dihapus.',
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
            )
            if hasattr(ctx, 'respond'):
                message = await ctx.respond(embed=embed, delete_after=5)
            else:
                message = await ctx.send(embed=embed, delete_after=5)
        else:
            # Notify the user if the file doesn't exist
            embed = discord.Embed(
                description='Riwayat percakapan tidak ditemukan.',
                color=discord.Color.red()
            )
            if hasattr(ctx, 'respond'):
                message = await ctx.respond(embed=embed, delete_after=5)
            else:
                message = await ctx.send(embed=embed, delete_after=5)

    @gpt.command(
        name='image',
        description='Membuat gambar menggunakan ChatGPT.',
    )
    async def create_image(self, ctx, *, prompt):
        embed = discord.Embed(
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())),
            title="⏳  Membuat gambar...",
            description=f"**Prompt:** \"{prompt}\""
        )

        interaction = await ctx.respond(embed=embed)

        try:
            moderation = self.client.moderations.create(input=prompt)

            if moderation.results[0].flagged:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    title="❌  Error",
                    description="Your prompt is inappropriate."
                ).set_thumbnail(url=ctx.author.display_avatar)
                
                await interaction.edit(embed=embed)
                return

            r = self.client.images.generate(
                prompt=prompt, n=4, size="1024x1024", user=str(ctx.author.id))

            url = r.data[0].url

            embed = discord.Embed(
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())),
                title=f"🖼️  \" {string.capwords(prompt)} \"",
                description=f"oleh <@{ctx.author.id}>"
            ).set_image(url=url)

            await interaction.edit(embed=embed)

        except OpenAIError as e:
            error_message = "Your prompt may contain safety issues. Please try a different prompt."
            if "Safety" in str(e):
                error_message = "Your prompt may contain safety issues. Please try a different prompt."
            elif "Too Many Requests" in str(e):
                error_message = "The server is overloaded. Please try again later."
            elif "Timeout" in str(e):
                error_message = "The request timed out. Please try again later."
            embed = discord.Embed(
                color=discord.Color.red(),
                title="❌  Error",
                description=error_message
            ).set_thumbnail(url=ctx.author.display_avatar)

            await interaction.edit(embed=embed)

    @commands.slash_command(name='info', description="Menampilkan informasi tentang channel suara sementara.")
    async def cari_info_slash(self, ctx, tentang: discord.Option(str, description="Pilih info yang akan dilihat.", choices=[discord.OptionChoice(name="Bot", value="bot"), discord.OptionChoice(name="Channel", value="channel"), discord.OptionChoice(name="Server", value="server")])):
        await self.cari_info(ctx, tentang)
    async def cari_info(self, ctx, tentang: str):
        if tentang == 'server':
            # Retrieve server information
            server_name = ctx.guild.name
            utc_time = ctx.guild.created_at.replace(tzinfo=pytz.UTC)
            wib_timezone = pytz.timezone('Asia/Jakarta')
            wib_time = utc_time.astimezone(wib_timezone)
            server_created_at = wib_time.strftime("%d %B %Y pukul %H:%M:%S WIB")
            server_owner = ctx.guild.owner
                    
            total_members = ctx.guild.member_count
            total_roles = len(ctx.guild.roles)
            total_channels = len(ctx.guild.channels)
            total_voice_channels = len(ctx.guild.voice_channels)
            server_boost_level = ctx.guild.premium_tier
            server_emojis = len(ctx.guild.emojis)
                
            embed = discord.Embed(
                title=f"INFORMASI SERVER",
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                    )
            embed.add_field(name="Nama Server", value=server_name, inline=True)
            embed.add_field(name="Dibuat Pada", value=server_created_at, inline=True)
            embed.add_field(name="Pemilik Server", value=server_owner.mention if server_owner else "Tidak Diketahui", inline=True)
            embed.add_field(name="Jumlah Member", value=total_members, inline=True)
            embed.add_field(name="Jumlah Role", value=total_roles, inline=True)
                    
            embed.add_field(name="Jumlah Channel", value=total_channels, inline=True)
            embed.add_field(name="Jumlah Voice Channel", value=total_voice_channels, inline=True)
            embed.add_field(name="Jumlah Emoji", value=server_emojis, inline=True)
            embed.add_field(name="Level Boost", value=server_boost_level, inline=True)
                    
            await ctx.respond(embed=embed, delete_after=60)
        
        elif tentang == 'channel':
            # Retrieve channel information
            channel_mention = ctx.channel.mention
            utc_time = ctx.channel.created_at.replace(tzinfo=pytz.UTC)
            wib_timezone = pytz.timezone('Asia/Jakarta')
            wib_time = utc_time.astimezone(wib_timezone)
            channel_created_at = wib_time.strftime("%d %B %Y pukul %H:%M:%S WIB")
            channel_type = str(ctx.channel.type).capitalize()
            
            # Get the creator of the channel from the audit log
            channel_creator = None
            async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.channel_create):
                if entry.target.id == ctx.channel.id:
                    channel_creator = entry.user
                    break
            
            # Create embed with channel information
            embed = discord.Embed(
                title=f"Informasi Channel: {channel_mention}",
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
            )
            embed.add_field(name="Dibuat Pada", value=channel_created_at, inline=False)
            embed.add_field(name="Tipe Channel", value=channel_type, inline=False)
            embed.add_field(name="Pembuat Channel", value=channel_creator.mention if channel_creator else "Tidak Diketahui", inline=False)
            
            await ctx.respond(embed=embed, delete_after=15)

        elif tentang == 'bot':
            # Get bot information
            bot_user = ctx.bot.user
        
            # Retrieve bot information
            utc_time = bot_user.created_at.replace(tzinfo=pytz.UTC)
            wib_timezone = pytz.timezone('Asia/Jakarta')
            wib_time = utc_time.astimezone(wib_timezone)
            bot_created_at = wib_time.strftime("%d %B %Y pukul %H:%M:%S WIB")
            bot_app_info = await ctx.bot.application_info()
            bot_owner = bot_app_info.owner
            guild_count = len(ctx.bot.guilds)  # Get the number of servers the bot is in
        
            embed = discord.Embed(
                title=f"Informasi Bot: {bot_user.name}",
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
            )
            embed.add_field(name="Dibuat Pada", value=bot_created_at, inline=False)
            embed.add_field(name="Kreator Bot", value=bot_owner.mention if bot_owner else "Tidak Diketahui", inline=False)
            embed.add_field(name="Jumlah Server", value=guild_count, inline=False)
        
            await ctx.respond(embed=embed, delete_after=15)

    # LIST
    daftar = discord.SlashCommandGroup(
        name="daftar",
        description="Menampilkan daftar channel pilihan.",
    )
    @daftar.command(
      name='voicemaster',
      description='Menampilkan daftar channel VM.',
    )
    async def vm_list(self, ctx):
            await ctx.defer()
            if isinstance(ctx.channel, discord.DMChannel):
                return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
            guild_data_directory = os.path.join(DATA_SERVER, str(ctx.guild.name))
            guild_vm_path = os.path.join(guild_data_directory, 'vm.json')
        
            try:
                with open(guild_vm_path, 'r') as file:
                    guild_data = json.load(file)
            except FileNotFoundError:
                embed = discord.Embed(
                    description=f"Data VM untuk server {ctx.guild.name} tidak ditemukan. Buat VM menggunakan `set vm Nama Channel` atau `ID Channel`.",
                    color=discord.Color.red()
                )
        
                if hasattr(ctx, 'respond'):
                    await ctx.respond(embed=embed, delete_after=5)
                else:
                    await ctx.send(embed=embed, delete_after=5)
                    await ctx.message.delete()
                return
        
            vm_channels = []
            for i, entry in enumerate(guild_data, 1):
                guild_voice_channel_id = entry.get('voice_channel_id')
                if guild_voice_channel_id:
                    vm_channel = discord.utils.get(ctx.guild.voice_channels, id=guild_voice_channel_id)
                    if vm_channel:
                        vm_channels.append(f"{i}. {vm_channel.mention}")
        
            if vm_channels:
                vm_mentions = '\n'.join(vm_channels)
                embed = discord.Embed(
                    title=f"Daftar VM {ctx.guild.name}",
                    description=f"{vm_mentions}",
                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                )
        
                if hasattr(ctx, 'respond'):
                    await ctx.respond(embed=embed, delete_after=15)
                else:
                    await ctx.send(embed=embed, delete_after=15)
                    await ctx.message.delete()
            else:
                embed = discord.Embed(
                    description=f"VM belum diatur. Buat menggunakan `set vm Nama Channel` atau `ID Channel`.",
                    color=discord.Color.red()
                )
        
                if hasattr(ctx, 'respond'):
                    await ctx.respond(embed=embed, delete_after=5)
                else:
                    await ctx.send(embed=embed, delete_after=5)
                    await ctx.message.delete()
                    
    @daftar.command(
      name='nochat',
      description='Menampilkan daftar channel nochat.',
    )
    async def nochat_list(self, ctx):
            await ctx.defer()
            if isinstance(ctx.channel, discord.DMChannel):
                return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
            guild_name = str(ctx.guild.name)
            nochat_settings_path = os.path.join(DATA_SERVER, guild_name, 'nochat.json')
        
            try:
                with open(nochat_settings_path, 'r') as file:
                    nochat_settings = json.load(file)
            except FileNotFoundError:
                if hasattr(ctx, 'respond'):
                    await ctx.respond(f'> Tidak ada channel yang diatur sebagai nochat.', delete_after=5)
                else:
                    await ctx.send('> Tidak ada channel yang diatur sebagai nochat.')
                return
        
            channel_sources = {}
            for setting in nochat_settings:
                channel_id = setting['channel_id']
                source = setting['source']
                if channel_id not in channel_sources:
                    channel_sources[channel_id] = []
                channel_sources[channel_id].append(source)
        
            embed = discord.Embed(title=f'Daftar Channel Nochat di {guild_name}', color=discord.Color.blurple())
        
            for idx, (channel_id, sources) in enumerate(channel_sources.items(), start=1):
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    sources_text = ', '.join(sources)
                    embed.add_field(name=f"{idx}. {channel.mention} = `{sources_text}`.", value=f"", inline=False)
                else:
                    embed.add_field(name=f"Channel Not Found = `{', '.join(sources)}`.", value=f"", inline=False)
        
            if hasattr(ctx, 'respond'):
                await ctx.respond(embed=embed, delete_after=5)
            else:
                await ctx.send(embed=embed, delete_after=5)
