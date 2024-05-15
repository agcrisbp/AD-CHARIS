import discord, json, random, asyncio, requests
from discord.ext import commands
from decouple import config
from cogs.fungsi.func import Fungsi, owner_ids

radio_stations = {}
default_volume = 50
guild_volumes = {}

class Radio(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.invoke_messages = {}
        self.invoke_message_ids = {}
        self.default_volume = default_volume
        self.owner_ids = owner_ids
        self.leave_on_empty = False
        self.radio_stations = radio_stations
    
    radio = discord.SlashCommandGroup(
        name="radio",
        description="Menampilkan daftar channel pilihan.",
    )
    
    async def send_radio_info(self, ctx, station_name, station_logo_url):
        
        guild_id = ctx.guild.id
        volume = guild_volumes.get(guild_id, default_volume) / 100
        
        embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
        embed.title = f"Radio Diputar: {station_name}"
    
        if station_logo_url:
            embed.set_image(url=station_logo_url)
            
        embed.set_footer(text=f"🔊 {volume * 100} | Gunakan /radio refresh jika buffering.")
    
        message = await ctx.respond(embed=embed)
        
        # Store the message content as an indicator of being an invoke message
        self.invoke_messages[ctx.guild.id] = message
    
        # Store the message ID for later reference
        self.invoke_message_ids[ctx.guild.id] = message.id
    
    @radio.command(name='volume', description='Mengatur volume radio.')
    async def adjust_volume(self, ctx, volume: int):
        """Adjust the volume of the radio."""
        if volume < 0 or volume > 100:
            return await ctx.respond("> Volume harus dalam rentang 0 hingga 100.", delete_after=5)
    
        guild_id = ctx.guild.id
        guild_volumes[guild_id] = volume
    
        if ctx.guild.id in radio_stations:
            voice_channel = ctx.guild.voice_client
            if voice_channel and voice_channel.is_playing():
                if volume == int(voice_channel.source.volume * 100):
                    await ctx.respond(f"> Volume saat ini adalah {volume}.", delete_after=5)
                else:    
                    voice_channel.source.volume = volume / 100
                    await ctx.respond(f"> Volume radio telah diatur menjadi {volume}.", delete_after=5)
            else:
                await ctx.respond("> Tidak ada radio yang sedang diputar.", delete_after=5)
        else:
            await ctx.respond("> Tidak ada radio yang sedang diputar.", delete_after=5)

    @radio.command(name='play', description='Memutar radio.')
    async def play_radio(self, ctx, nama_radio: str, keluar_otomatis: discord.Option(bool, default=False, description="Bot meninggalkan channel suara jika channel suara kosong.", choices=[discord.OptionChoice(name="Ya", value=True), discord.OptionChoice(name="Tidak", value=False)])):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            return await ctx.respond("> Kamu harus berada di dalam voice channel!", delete_after=5)
    
        self.invoke_channel = ctx.channel
        guild_id = ctx.guild.id
    
        try:
            radio_data_file = 'radio/radio_data.json'
    
            with open(radio_data_file, 'r') as file:
                radio_data = json.load(file)
    
            matching_stations = {}
    
            for station_id, station_info in radio_data.items():
                station_name = station_info['name'].lower()
                if nama_radio in station_name:
                    matching_stations[station_id] = station_info
    
            if not matching_stations:
                return await ctx.respond("> Nama radio tidak ditemukan.", delete_after=5)
    
            radio_id, station_info = matching_stations.popitem()
            station_name = station_info['name']
            station_url = station_info['url']
            station_logo_url = station_info.get('logo')
    
            if guild_id in self.radio_stations:
                current_station = self.radio_stations[guild_id]
    
                if (current_station != radio_id) or (hasattr(self, 'leave_on_empty') and self.leave_on_empty != keluar_otomatis):
                    # Change radio station
                    channel = ctx.author.voice.channel
                    voice_channel = ctx.guild.voice_client
    
                    # Stop playback if the bot is playing
                    if voice_channel and voice_channel.is_playing():
                        voice_channel.stop()
    
                    self.radio_stations[guild_id] = radio_id
    
                    volume = guild_volumes.get(guild_id, default_volume) / 100  # Get volume from guild_volumes dictionary
                    voice_channel.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(station_url), volume=volume),
                                       after=lambda e: print('Sudah.'))
    
                    # Update leaveOnEmpty configuration
                    self.leave_on_empty = keluar_otomatis
    
                    await channel.set_status(f"<:radio:1230396943377629216> **{station_name}**")
    
                    # Delete previous radio info message if exists
                    if self.invoke_message_ids:
                        try:
                            await self.invoke_messages[ctx.guild.id].delete()
                        except discord.HTTPException as e:
                            pass
                        except discord.NotFound:
                            pass
    
                    # Send new radio info message
                    await self.send_radio_info(ctx, station_name, station_logo_url)
                else:
                    await ctx.respond(
                        f"> Radio {station_name} sedang diputar dengan pengaturan `keluar otomatis` yang sama. Coba gunakan pengaturan `keluar otomatis` atau gunakan `/radio refresh` jika terjadi error.",
                        delete_after=15)
            else:
                # Connect to voice channel and play the radio
                channel = ctx.author.voice.channel
                voice_channel = await channel.connect()
                volume = guild_volumes.get(guild_id, default_volume) / 100  # Get volume from guild_volumes dictionary
                voice_channel.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(station_url), volume=volume),
                                   after=lambda e: print('Sudah.'))
                
                if self.invoke_message_ids:
                    try:
                        await self.invoke_messages[ctx.guild.id].delete()
                    except discord.HTTPException as e:
                        pass
                    except discord.NotFound:
                        pass
    
                # Update leaveOnEmpty configuration
                self.leave_on_empty = keluar_otomatis
    
                await channel.set_status(f"<:radio:1230396943377629216> **{station_name}**")
    
                # Store the station being played in the server
                self.radio_stations[guild_id] = radio_id
    
                # Send radio info
                await self.send_radio_info(ctx, station_name, station_logo_url)
    
        except FileNotFoundError:
            await ctx.respond("> Data radio tidak ditemukan. ", delete_after=5)
    
    @radio.command(name='refresh', description='Refresh radio error.')
    async def refresh_command(self, ctx):
        guild_id = ctx.guild.id
        
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
    
        voice_channel = ctx.guild.voice_client
    
        if voice_channel is None:  # Check if bot is not connected to any voice channel
            # Get the member's voice channel
            member_voice_channel = ctx.author.voice.channel
            if member_voice_channel:
                # Connect to the member's voice channel
                voice_channel = await member_voice_channel.connect()
            else:
                # If member is not in a voice channel, return error message
                embed = discord.Embed(color=discord.Color.red())
                embed.description = "Kamu harus berada di voice channel untuk menggunakan perintah ini."
                return await ctx.respond(embed=embed, delete_after=5)
    
        if guild_id in radio_stations:
            current_radio_id = radio_stations[guild_id]
            radio_data_file = 'radio/radio_data.json'
    
            try:
                with open(radio_data_file, 'r') as file:
                    radio_data = json.load(file)
    
                if current_radio_id in radio_data:
                    station_info = radio_data[current_radio_id]
                    station_name = station_info['name']
                    station_url = station_info['url']
                    station_logo_url = station_info.get('logo')
                    
                    await voice_channel.channel.set_status(None)
    
                    # Stop any currently playing audio
                    if voice_channel.is_playing():
                        voice_channel.stop()
    
                    # Play the audio stream
                    voice_channel.play(discord.FFmpegPCMAudio(station_url), after=lambda e: print('Sudah.', e))
                    
                    await voice_channel.channel.set_status(f"<:radio:1230396943377629216> **{station_name}**")
    
                    embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                    embed.title = f"Memutar Ulang: {station_name}"
    
                    if station_logo_url:
                        embed.set_image(url=station_logo_url)
    
                    await ctx.respond(embed=embed, delete_after=5)
                else:
                    embed = discord.Embed(color=discord.Color.red())
                    embed.description = "Tidak ada radio yang sedang diputar."
    
                    await ctx.respond(embed=embed, delete_after=5)
            except FileNotFoundError:
                embed = discord.Embed(color=discord.Color.red())
                embed.description = "Data radio tidak ditemukan."
    
                await ctx.respond(embed=embed, delete_after=5)
        else:
            embed = discord.Embed(color=discord.Color.red())
            embed.description = "Bot sedang tidak memainkan radio apapun. Gunakan **`/radio play`** untuk memutar radio setelah bot terputus dari voice channel."
    
            await ctx.respond(embed=embed, delete_after=15)
            await asyncio.sleep(3)
            await voice_channel.disconnect()
    
    @radio.command(name='stop', description='Menghentikan pemutaran radio.')
    async def disconnect_command(self, ctx):
        guild_id = ctx.guild.id
        
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
    
        # Check if the bot is connected to a voice channel
        voice_channel = ctx.guild.voice_client
    
        if voice_channel is None:
            embed = discord.Embed(color=discord.Color.red())
            embed.description = "Bot tidak sedang terhubung ke channel suara."
    
            if hasattr(ctx, 'respond') and callable(ctx.respond):
                await ctx.respond(embed=embed, delete_after=5)
            else:
                await ctx.send(embed=embed, delete_after=5)
        else:
            channel = ctx.author.voice.channel
            voice_channel.stop()
            await channel.set_status(None)
            await voice_channel.disconnect()
            if guild_id in radio_stations:
                del radio_stations[guild_id]
    
            if self.invoke_message_ids:
                try:
                    await self.invoke_messages[ctx.guild.id].delete()
                except discord.HTTPException as e:
                    pass
                except discord.NotFound:
                    pass
    
            embed = discord.Embed(color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            embed.description = f"Radio dihentikan oleh {ctx.author.display_name}."
    
            await ctx.respond(embed=embed)

    @radio.command(name='upload', description='Menambah daftar radio baru.')
    async def update_radio(self, ctx, name: str, url: str, logo: discord.Attachment = None):
        await ctx.defer()
        try:
            radio_data_file = 'radio/radio_data.json'
        
            with open(radio_data_file, 'r') as file:
                radio_data = json.load(file)
        
            # Find the next available ID
            next_id = str(len(radio_data) + 1)
        
            # Get logo URL if attachment is provided
            logo_url = None
            if logo:
                # Upload the logo to imgbb album
                upload_url = "https://api.imgbb.com/1/upload"
                imgbb_key = config("IMGBB_KEY")  # Replace "your_imgbb_key" with your actual imgbb API key
                album_url = "https://ibb.co/album/0mBm9v"   # Replace "your_album_url" with the URL of your imgbb album
                
                # Read the attachment data
                logo_data = await logo.read()
                
                # Make the POST request with the attachment data
                logo_response = requests.post(upload_url, params={"key": imgbb_key, "album": album_url, "expiration": 0}, files={'image': logo_data})
                if logo_response.status_code == 200:
                    logo_url = logo_response.json()['data']['url']
                else:
                    raise Exception("Failed to upload logo to imgbb")
        
            # Create a new entry
            radio_data[next_id] = {
                'name': name,
                'url': url,
                'logo': logo_url
            }
        
            # Write the updated data back to the file
            with open(radio_data_file, 'w') as file:
                json.dump(radio_data, file, indent=2)
        
            await ctx.respond("> Berhasil menambahkan radio baru!", delete_after=5)
        
        except Exception as e:
            await ctx.respond(f'An error occurred: {e}')
    
    @radio.command(name='delete', description='Menghapus entri data radio berdasarkan nama.')
    async def delete_radio(self, ctx, nama_radio: str):
        await ctx.defer()
        
        bot_creator_id = (await self.bot.application_info()).owner.id
    
        if not (ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
            embed = discord.Embed(
                description=f"Hanya pemilik bot yang bisa menggunakan perintah ini!",
                color=discord.Color.red())
            return await ctx.respond(embed=embed, delete_after=10)
        
        try:
            radio_data_file = 'radio/radio_data.json'
    
            with open(radio_data_file, 'r') as file:
                radio_data = json.load(file)
    
            matching_stations = {}
            for station_id, station_info in radio_data.items():
                station_name = station_info['name'].lower()
                if nama_radio.lower() in station_name:
                    matching_stations[station_id] = station_info
    
            if not matching_stations:
                return await ctx.respond(f"Tidak ada radio dengan nama **`{nama_radio}`**.", delete_after=5)
    
            # Deleting matching stations
            for station_id in matching_stations:
                del radio_data[station_id]
    
            with open(radio_data_file, 'w') as file:
                json.dump(radio_data, file, indent=2)
    
            await ctx.respond(f"Berhasil menghapus radio **`{station_info['name']}`**.", delete_after=5)
    
        except FileNotFoundError:
            await ctx.respond("> Data radio tidak ditemukan.", delete_after=5)
        except Exception as e:
            await ctx.respond(f'An error occurred: {e}', delete_after=5)
    
    @radio.command(
      name='list',
      description='Menampilkan daftar stasiun radio.',
    )
    async def radio_list(self, ctx):
            radio_data_file = 'radio/radio_data.json'
            try:
                with open(radio_data_file, 'r') as file:
                    radio_data = json.load(file)
            except FileNotFoundError:
                radio_data = {}
        
            if radio_data:
                radio_list = [f"{index + 1}. {station_info['name']}" for index, station_info in enumerate(radio_data.values())]
        
                midpoint = len(radio_list) // 2
                
                column1 = radio_list[:midpoint]
                column2 = radio_list[midpoint:]
                
                embed = discord.Embed(title="Daftar Stasiun Radio", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                
                embed.add_field(name="Radio 1", value="\n".join(column1), inline=True)
                embed.add_field(name="Radio 2", value="\n".join(column2), inline=True)
            else:
                embed = discord.Embed(description="Tidak ada stasiun radio yang tersedia.", color=discord.Color.red())
        
            if hasattr(ctx, 'respond') and callable(ctx.respond):
                await ctx.respond(embed=embed, delete_after=60)
            else:
                await ctx.send(embed=embed, delete_after=60)