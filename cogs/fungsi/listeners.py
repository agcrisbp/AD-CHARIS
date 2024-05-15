import discord, asyncio, os, json, time, shutil, subprocess, requests
from discord import Embed
from discord.ext import commands, tasks
from decouple import config
from github import Github
from datetime import datetime, timedelta
from cogs.fungsi.database import DataBase, DATA_OWNER, DATA_SERVER, client
from cogs.fungsi.func import Fungsi, HOLIDAY_API, Embeds, Views, MAX_CHAT_HISTORY_LENGTH, bot_creator_id, owner_ids, recent_channel_id, voice_channel_id, category_id, welcome_settings, leave_settings, nochat_settings

GITHUB_EMAIL = config('GITHUB_EMAIL', default=None)
GITHUB_USERNAME = config('GITHUB_USERNAME', default=None)
GITHUB_TOKEN = config('GITHUB_TOKEN', default=None)
REPO_NAME = config('REPO_NAME', default=None)
BACKUP_FOLDER = '.'

current_presence = "It Never Ends - Aghea, Julian Wilt"
radio_stations = {}
task_managers = {}

# Function to start a task
async def start_task(task_name, task_func, bot):
    print(f"Starting task: {task_name}")
    task = await task_func(bot)
    task_managers[task_name] = task

# Function to check if a task is running
def is_task_running(task_name):
    return task_name in task_managers and not task_managers[task_name].done()

def backup_to_github():
    if all([GITHUB_EMAIL, GITHUB_USERNAME, GITHUB_TOKEN, REPO_NAME]):
        g = Github(GITHUB_USERNAME, GITHUB_TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        
        subprocess.run(['git', 'config', '--global', 'user.email', f'{GITHUB_EMAIL}'])
        subprocess.run(['git', 'config', '--global', 'user.name', f'{GITHUB_USERNAME}'])
        subprocess.run(['git', 'config', '--global', 'init.defaultBranch', 'main'])
        subprocess.run(['git', 'init', '.'])
        subprocess.run(['git', 'branch', '-M', 'main'])
        subprocess.run(['git', 'add', '.'])
        subprocess.run(['git', 'commit', '-m', 'Backup files'])
        subprocess.run(['git', 'remote', 'add', 'origin', 'main', f'https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{REPO_NAME}.git'])
        subprocess.run(['git', 'push', f'https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{REPO_NAME}.git', 'main'])
    else:
        print("One or more required environment variables are missing or empty. Skipping backup process.")

class Control(discord.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.bot_start_time = datetime.utcnow()
        self.update_presence.start()
        self.client = client
        self.bot_creator_id = bot_creator_id
        self.owner_ids = owner_ids
        self.recent_channel_id = recent_channel_id
        self.voice_channel_id = voice_channel_id
        self.category_id = category_id
        self.welcome_settings = welcome_settings
        self.leave_settings = leave_settings
        self.nochat_settings = nochat_settings
        self.invoke_messages = {}
        self.invoke_message_ids = {}
        
    @tasks.loop(seconds=10)
    async def update_presence(self):
        await self.update_bot_presence()

    @update_presence.before_loop
    async def before_update_presence(self):
        await self.bot.wait_until_ready()

    async def update_bot_presence(self):
        global current_presence
        
        uptime_delta = datetime.utcnow() - self.bot_start_time

        if uptime_delta.total_seconds() < 60:
            uptime_str = f"{int(uptime_delta.total_seconds())}s."
        elif uptime_delta.total_seconds() < 3600:
            minutes, seconds = divmod(int(uptime_delta.total_seconds()), 60)
            uptime_str = f"{minutes}m {seconds}s."
        elif uptime_delta.total_seconds() < 86400:
            hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s."
        else:
            days, remainder = divmod(int(uptime_delta.total_seconds()), 86400)
            hours, remainder = divmod(remainder, 3600)
            uptime_str = f"{days}d {hours}h."

        url = None
        
        if current_presence == "It Never Ends - Aghea, Julian Wilt":
            bot_status = discord.Status.online
            current_presence = "suggestions!"
            activity_type = discord.ActivityType.listening
        elif current_presence == "suggestions!":
            total_servers = len(self.bot.guilds)
            bot_status = discord.Status.idle
            current_presence = f"{total_servers} servers for {uptime_str}"
            activity_type = discord.ActivityType.watching
        else:
            bot_status = discord.Status.dnd
            current_presence = "It Never Ends - Aghea, Julian Wilt"
            activity_type = discord.ActivityType.streaming
            url = "https://www.youtube.com/watch?v=6t_TZ4hbAMo"
        
        bot_activity = discord.Activity(type=activity_type, name=current_presence, url=url)
        await self.bot.change_presence(status=bot_status, activity=bot_activity)
        
    async def on_ready_backup(self):
        while True:
            backup_to_github()
            await asyncio.sleep(3 * 3600)

    @discord.Cog.listener()
    async def on_ready(self):
        welcome_settings = {}
        leave_settings = {}
        nochat_settings = {}
        
        if all([GITHUB_EMAIL, GITHUB_USERNAME, GITHUB_TOKEN, REPO_NAME]):
            self.bot.loop.create_task(self.on_ready_backup())
    
        # Load welcome_settings and leave_settings for each guild
        for guild in self.bot.guilds:
            guild_name = str(guild.name)
    
            # Load nochat_settings
            nochat_settings_path = os.path.join(DATA_SERVER, guild_name, 'nochat.json')
            try:
                with open(nochat_settings_path, 'r') as file:
                    nochat_settings[guild.id] = json.load(file)
            except FileNotFoundError:
                nochat_settings[guild.id] = []
    
        Fungsi.auto_update_stats.start(self)
        Fungsi.auto_update_link.start(self)
        DataBase.loadSetting()
    
        # Load role data for each guild
        for guild in self.bot.guilds:
            await DataBase.load_role_data(guild)
    
        # Set bot_creator_id
        try:
            bot_creator_id = (await self.bot.application_info()).owner.id
    
            # Validate owner data
            try:
                with open(DATA_OWNER, 'r') as owner_file:
                    owner_entries = owner_file.readlines()
    
                # Update owner data with numbers if empty
                if owner_entries:
                    owner_ids.clear()
                    for index, line in enumerate(owner_entries, start=1):
                        owner_data = line.strip().split(',')
                        owner_id = int(owner_data[-1])
                        owner_ids.add(owner_id)
                        
                        print(f"Owner #{index}: {owner_data[0]} ({owner_id})")
    
            except FileNotFoundError:
                print("Owner data not found.")
                
            response = requests.get(HOLIDAY_API)
            if response.status_code == 200:
                holidays = response.json()

                for holiday in holidays:
                    holiday_name = holiday['localName']
            
            self.bot.loop.create_task(Fungsi.remove_holiday_file(self.bot, holiday_name))
    
        except Exception as e:
            print(f"Error in on_ready: {e}")
        
        for guild in self.bot.guilds:
            guild_data_directory = os.path.join(DATA_SERVER, guild.name)
            
            # Update category ID for voice channels in the database
            for channel in guild.channels:
                if isinstance(channel, discord.VoiceChannel):
                    data_vm_path = os.path.join(DATA_SERVER, guild.name, 'vm.json')
                    try:
                        with open(data_vm_path, 'r') as file:
                            vm_data = json.load(file)
                    except FileNotFoundError:
                        vm_data = []
                    
                    for entry in vm_data:
                        if entry["voice_channel_id"] == channel.id:
                            entry["category_id"] = channel.category_id
                            break
                    
                    if os.path.exists(data_vm_path):
                        with open(data_vm_path, 'w') as file:
                            json.dump(vm_data, file, indent=4)
                    if not vm_data:
                        if os.path.exists(data_vm_path):
                            os.remove(data_vm_path)
                            if os.path.exists(guild_data_directory) and not os.listdir(guild_data_directory):
                                os.rmdir(guild_data_directory)

        for guild in self.bot.guilds:
            guild_name = str(guild.name)
            for thread in guild.threads:
                # Check if the thread name matches the desired pattern
                if thread.name.endswith("'s Chat"):
                    # Fetch the message history of the existing thread
                    messages = await thread.history(limit=None).flatten()
                    for message in messages:
                        # Skip processing messages during initial loading
                        pass
    
                    # Listen for new messages in the thread
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

            # Filter out deleted voice channels from the database
            for guild in self.bot.guilds:
                data_vm_path = os.path.join(DATA_SERVER, guild.name, 'vm.json')
                try:
                    with open(data_vm_path, 'r') as file:
                        vm_data = json.load(file)
                except FileNotFoundError:
                    vm_data = []
            
                filtered_vm_data = []
                for entry in vm_data:
                    voice_channel_id = entry.get("voice_channel_id")
                    if guild.get_channel(voice_channel_id) is not None:
                        filtered_vm_data.append(entry)
            
                if os.path.exists(data_vm_path):
                    with open(data_vm_path, 'w') as file:
                        json.dump(filtered_vm_data, file, indent=4)
                    if not vm_data:
                        if os.path.exists(data_vm_path):
                            os.remove(data_vm_path)
                            if os.path.exists(guild_data_directory) and not os.listdir(guild_data_directory):
                                os.rmdir(guild_data_directory)
        
        for guild in self.bot.guilds:
            guild_data_directory = os.path.join(DATA_SERVER, guild.name)
            data_vm_path = os.path.join(guild_data_directory, 'vm.json')
            try:
                with open(data_vm_path, 'r') as file:
                    vm_data = json.load(file)
            except FileNotFoundError:
                vm_data = []
    
            for vm_entry in vm_data:
                voice_channel_id = vm_entry.get('voice_channel_id')
                category_id = vm_entry.get('category_id')
    
                # Perform actions with each VM entry
    
            recent_channel_id.update(DataBase.load_recent_channel_id())
            user_channel_names = DataBase.load_user_channel_names()
        
        tasks_to_start = {
            "aceh_times": Fungsi.start_aceh_times,
            "balikpapan_times": Fungsi.start_balikpapan_times,
            "belitung_times": Fungsi.start_belitung_times,
            "enrekang_times": Fungsi.start_enrekang_times,
            "jakarta_times": Fungsi.start_jakarta_times,
            "bali_times": Fungsi.start_bali_times,
            "jayapura_times": Fungsi.start_jayapura_times,
            "jogja_times": Fungsi.start_jogja_times,
            "parepare_times": Fungsi.start_parepare_times,
            "makassar_times": Fungsi.start_makassar_times,
            "samarinda_times": Fungsi.start_samarinda_times,
            "pontianak_times": Fungsi.start_pontianak_times,
            "sidoarjo_times": Fungsi.start_sidoarjo_times,
            "surabaya_times": Fungsi.start_surabaya_times,
            "holidays": Fungsi.holiday_event_messages
        }
    
        tasks = []
        for task_name, task_func in tasks_to_start.items():
            if not is_task_running(task_name):
                tasks.append(start_task(task_name, task_func, self.bot))
            else:
                print(f"Task {task_name} is already running.")
    
        for task in tasks:
            asyncio.create_task(task)
    
        for guild in self.bot.guilds:
                self.bot.loop.create_task(Fungsi.create_pilih_kota_channel(guild))
                self.bot.loop.create_task(Fungsi.clear_empty_channel(self.bot))
        
        for guild in self.bot.guilds:
            setting_channel = discord.utils.get(guild.channels, name="charis-notif")
            if setting_channel:
                await setting_channel.send(f'> **Bot sudah aktif!**')
                break


    @discord.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        global recent_channel_id, cooldown_duration
        keluar_otomatis = self.bot.get_cog("Radio").leave_on_empty
        
        guild_id = member.guild.id
        voice_channel = member.guild.voice_client
    
        if member == member.guild.me and before.channel and not after.channel:
            await before.channel.set_status(None)
            if voice_channel and voice_channel.channel == before.channel:
                if voice_channel.is_playing():
                    voice_channel.stop()
                if self.bot.get_cog("Radio").invoke_channel:
                    try:
                        embed = discord.Embed(color=discord.Color.red())
                        embed.title = f"Pemutaran radio dihentikan karena bot ditendang atau terputus dari channel suara."
                        await self.bot.get_cog("Radio").invoke_channel.send(embed=embed)
                    except discord.NotFound:
                        pass
                try:
                    await voice_channel.connect(reconnect=False, timeout=2)
                    await voice_channel.disconnect()
                except discord.ClientException:
                    pass
                except asyncio.TimeoutError:
                    pass
                finally:
                    if voice_channel and not voice_channel.is_connected():
                        voice_channel.cleanup()

            if guild_id in radio_stations:
                del radio_stations[guild_id]
    
            if member.guild.id in self.bot.get_cog("Radio").invoke_messages:
                try:
                    await self.bot.get_cog("Radio").invoke_messages[guild_id].delete()
                except discord.NotFound:
                    pass
        
        if member == member.guild.me and before.channel and after.channel:
            try:
                radio_data_file = 'radio/radio_data.json'
    
                # Load radio data
                with open(radio_data_file, 'r') as file:
                    radio_data = json.load(file)
    
                if guild_id in radio_stations:
                    current_radio_id = radio_stations[guild_id]
                    
                    if current_radio_id in radio_data:
                        # Get station information
                        station_info = radio_data[current_radio_id]
                        station_name = station_info['name']
                        station_url = station_info['url']
                        station_logo_url = station_info.get('logo')
    
                        if before.channel and before.channel.guild == member.guild:
                            await before.channel.set_status(None)
    
                        # Update the status in the new channel
                        if after.channel and after.channel.guild == member.guild:
                            await after.channel.set_status(f"<:radio:1230396943377629216> **{station_name}**")
            except Exception as e:
                print(e)
        
        if voice_channel and voice_channel.channel:
            members_ids = [member.id for member in voice_channel.channel.members]

            self.leave_on_empty = keluar_otomatis
            
            if len(members_ids) == 1 and member.guild.me.id in members_ids and self.leave_on_empty:
                await asyncio.sleep(300)
                members_ids_after_sleep = [member.id for member in voice_channel.channel.members]
                if len(members_ids_after_sleep) == 1 and member.guild.me.id in members_ids_after_sleep:
                    try:
                        if voice_channel.is_playing():
                            voice_channel.stop()
                        await voice_channel.channel.set_status(None)
                        await asyncio.sleep(1)
                        await voice_channel.disconnect()
                        
                        if self.bot.get_cog("Radio").invoke_channel:
                            try:
                                embed = discord.Embed(color=discord.Color.red())
                                embed.title = f"Pemutaran radio dihentikan karena tidak ada aktivitas apapun selama 5 menit."
                                await self.bot.get_cog("Radio").invoke_channel.send(embed=embed)
                            except discord.NotFound:
                                pass
                        
                        if member.guild.id in self.bot.get_cog("Radio").invoke_messages:
                            try:
                                await self.bot.get_cog("Radio").invoke_messages[guild_id].delete()
                            except discord.NotFound:
                                pass
                    except:
                        pass
        
        # Cooldown duration in seconds
        cooldown_duration = 15
        
        # Initialize temp_cooldown if it doesn't exist
        if "temp_cooldown" not in recent_channel_id:
            recent_channel_id["temp_cooldown"] = {}
        
        # Load VM data for the guild
        guild_data_directory = os.path.join(DATA_SERVER, str(member.guild.name))
        guild_vm_path = os.path.join(guild_data_directory, 'vm.json')
    
        try:
            with open(guild_vm_path, 'r') as file:
                guild_data = json.load(file)
        except FileNotFoundError:
            guild_data = []
    
        for vm_entry in guild_data:
            guild_voice_channel_id = vm_entry.get('voice_channel_id')
            guild_category_id = vm_entry.get('category_id')
    
            # Perform actions with each VM entry
    
        if after.channel and (not before.channel or before.channel != after.channel or str(after.channel.id) not in recent_channel_id["temp"]):
            for vm_entry in guild_data:
                guild_voice_channel_id = vm_entry.get('voice_channel_id')
                guild_category_id = vm_entry.get('category_id')
        
                if after.channel and after.channel.id == guild_voice_channel_id:
                    if str(member.id) in recent_channel_id["temp_cooldown"]:
                        remaining_cooldown = recent_channel_id["temp_cooldown"][str(member.id)] - time.time()
                        if remaining_cooldown > 0:
                            user = str(member.id)
                            guild = member.guild
                            voice_state = member.voice
                            if voice_state and voice_state.channel:
                                channel = guild.get_channel(voice_state.channel.id)
                                timestamp = int((time.time() + remaining_cooldown))
                                countdown_message = await channel.send(f"<a:loading:1234363290134515762> {member.mention}, membuat temporary voice channel lagi <t:{timestamp}:R>.", delete_after=30)
                            await asyncio.sleep(remaining_cooldown)
                            await countdown_message.edit(content=f"{member.mention}, sekarang kamu dapat membuat temporary voice channel lagi.")
                    else:  # Only create the temporary voice channel if the cooldown is not active
                        recent_entry = recent_channel_id["user"]
                        user_default_name = recent_entry.get(str(member.id), f'Channel {member.display_name}')
                        
                        try:
                            channel = await after.channel.clone(name=user_default_name)
                
                            # Set permissions
                            await channel.edit(sync_permissions=True, reason="Pembuatan temp voice.")
                            await channel.set_permissions(member, view_channel=True, read_message_history=True, connect=True, speak=True, send_messages=True, manage_channels=True, set_voice_channel_status=True, reason="User ini adalah pemilik channel temp voice.")
                
                            if guild_category_id:
                                await channel.edit(category=self.bot.get_channel(guild_category_id))
                
                            await member.move_to(channel)
                
                            recent_channel_id["temp"][str(channel.id)] = member.id
                            DataBase.save_recent_channel_id(recent_channel_id)
                
                            embed = discord.Embed(
                                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                            )
                
                            embed = Embeds.Panel(member=member)
                            await channel.send(embed=embed, view=Views.Dropdown(self.bot))
                        except discord.errors.NotFound:
                            pass
    
        if before.channel and (not after.channel or before.channel != after.channel):
            channel = before.channel
            if str(channel.id) in recent_channel_id["temp"]:
                if len(channel.members) == 0:
                    # Sync channel if owner channel goes down
                    recent_channel_id["temp_cooldown"][str(member.id)] = time.time() + cooldown_duration
                    owner_id = recent_channel_id["temp"].pop(str(channel.id))
                    DataBase.save_recent_channel_id(recent_channel_id)
                    try:
                        await channel.delete()
                    except discord.NotFound:
                        pass

        await self.resume_playback_after_move(member.guild)
    
        async def check_and_clear_cooldown():
            while True:
                for member_id, cooldown_time in list(recent_channel_id["temp_cooldown"].items()):
                    if time.time() > cooldown_time:
                        del recent_channel_id["temp_cooldown"][member_id]
                    else:
                        remaining_time = int(cooldown_time - time.time())
    
                DataBase.save_recent_channel_id(recent_channel_id)
    
                # Sleep for a short duration before running the loop again
                await asyncio.sleep(1)  # Adjust the sleep duration as needed
    
        # Run the asyncio task
        asyncio.create_task(check_and_clear_cooldown())

    async def resume_playback_after_move(self, guild):
        voice_channel = discord.utils.get(self.bot.voice_clients, guild=guild)
    
        if voice_channel and (voice_channel.is_paused() or voice_channel.is_playing()):
            voice_channel.resume()
        else:
            pass

    @discord.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        # Check if the channel type is voice channel
        if isinstance(after, discord.VoiceChannel):
            # Check if the channel was moved to another category
            if before.category != after.category:
                # Load VM data
                data_vm_path = os.path.join(DATA_SERVER, after.guild.name, 'vm.json')
                try:
                    with open(data_vm_path, 'r') as file:
                        vm_data = json.load(file)
                except FileNotFoundError:
                    vm_data = []

                # Update category ID for the voice channel in the database
                for entry in vm_data:
                    if entry["voice_channel_id"] == after.id:
                        entry["category_id"] = after.category_id
                        break

                # Write updated data back to the file
                with open(data_vm_path, 'w') as file:
                    json.dump(vm_data, file, indent=4)

    @discord.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild_name = str(channel.guild.name)
        nochat_settings_path = os.path.join(DATA_SERVER, guild_name, 'nochat.json')
    
        try:
            with open(nochat_settings_path, 'r') as file:
                nochat_settings = json.load(file)
        except FileNotFoundError:
            # No nochat settings file, nothing to do
            return
    
        # Remove the channel ID from nochat settings if it exists
        nochat_settings = [setting for setting in nochat_settings if setting['channel_id'] != channel.id]
    
        # Write the updated settings back to the file
        with open(nochat_settings_path, 'w') as file:
            json.dump(nochat_settings, file, indent=4)
        
        if not nochat_settings:
            os.remove(nochat_settings_path)
        
        if isinstance(channel, discord.VoiceChannel):
            for guild in self.bot.guilds:
                # Define the path to the guild's data directory
                guild_data_directory = os.path.join(DATA_SERVER, guild.name)
                
                data_vm_path = os.path.join(guild_data_directory, 'vm.json')
                
                # Load existing VM data
                try:
                    with open(data_vm_path, 'r') as file:
                        vm_data = json.load(file)
                except FileNotFoundError:
                    vm_data = []
            
                filtered_vm_data = []
                for entry in vm_data:
                    voice_channel_id = entry.get("voice_channel_id")
                    if guild.get_channel(voice_channel_id) is not None:
                        filtered_vm_data.append(entry)
            
                if os.path.exists(data_vm_path):
                    with open(data_vm_path, 'w') as file:
                        json.dump(filtered_vm_data, file, indent=4)
                    if not vm_data:
                        if os.path.exists(data_vm_path):
                            os.remove(data_vm_path)
                            if os.path.exists(guild_data_directory) and not os.listdir(guild_data_directory):
                                os.rmdir(guild_data_directory)
            
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild:
            settings = DataBase.loadSetting()
            guild_id = str(message.guild.id)
            channel_id = str(message.channel.id)
            message_id = str(message.id)
        
            # Check if the guild ID and channel ID exist in settings
            if guild_id in settings and channel_id in settings[guild_id]["reactRole"]:
                # Check if the message ID exists in settings for the channel
                if message_id in settings[guild_id]["reactRole"][channel_id]:
                    # Remove the reaction role data associated with the deleted message
                    settings[guild_id]["reactRole"][channel_id].pop(message_id)
                    
                    # If there are no more entries for the channel, remove the channel ID entry
                    if not settings[guild_id]["reactRole"][channel_id]:
                        settings[guild_id]["reactRole"].pop(channel_id)
                    
                    # If there are no more entries for the guild, remove the guild ID entry
                    if not settings[guild_id]["reactRole"]:
                        settings.pop(guild_id)
                    
                    # Save the updated settings
                    DataBase.saveSetting(settings)
    
    @discord.Cog.listener()
    async def on_guild_join(self, guild):
        while True:
            guild_data_directory = os.path.join(DATA_SERVER, str(guild.name))
            os.makedirs(guild_data_directory, exist_ok=True)
    
            guild_pilih_kota_path = os.path.join(guild_data_directory, 'pilih_kota.txt')
    
            channel_name = 'pilih-kota'
            
            embed_title = "CARA PILIH KOTA"
            embed_description = ("- Ketik **`/kota`** lalu pilih kota daerahmu, channel kota yang kamu pilih akan muncul dalam beberapa saat. "
                                "Gunakan **`/delkota`** untuk menghapus kota daerahmu.")
    
            embed_note = ("- Jika kotamu tidak tersedia, lapor menggunakan **`/bug`** agar owner membuatnya.")
    
            embed = discord.Embed(title=embed_title, description=embed_description, color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            embed.add_field(name="CATATAN", value=embed_note, inline=False)
            
            image_url = "https://i.ibb.co/sywMp5S/Cuplikan-Layar-2024-04-20-16-02-59.png"
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
        
    @discord.Cog.listener()
    async def on_guild_remove(self, guild):
        # Load settings
        settings = DataBase.loadSetting()
    
        # Convert guild ID to string
        guild_id = str(guild.id)
    
        # Check if the guild ID exists in settings
        if guild_id in settings:
            # Remove the guild ID entry
            settings.pop(guild_id)
    
            # Save updated settings
            DataBase.saveSetting(settings)
    
        guild_directory = os.path.join(DATA_SERVER, str(guild))
        if os.path.exists(guild_directory):
            shutil.rmtree(guild_directory)
    
    @discord.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.name != after.name:
            old_guild_directory = os.path.join(DATA_SERVER, before.name)
            new_guild_directory = os.path.join(DATA_SERVER, after.name)
            if os.path.exists(old_guild_directory):
                os.rename(old_guild_directory, new_guild_directory)
    
    @discord.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild_name = str(channel.guild.name)
        nochat_settings_path = os.path.join(DATA_SERVER, guild_name, 'nochat.json')
    
        try:
            with open(nochat_settings_path, 'r') as file:
                nochat_settings = json.load(file)
        except FileNotFoundError:
            # No nochat settings file, nothing to do
            return
    
        # Remove the channel ID from nochat settings if it exists
        nochat_settings = [setting for setting in nochat_settings if setting['channel_id'] != channel.id]
    
        # Write the updated settings back to the file
        with open(nochat_settings_path, 'w') as file:
            json.dump(nochat_settings, file, indent=4)
        
        if not nochat_settings:
            os.remove(nochat_settings_path)
    
    @discord.Cog.listener()
    async def on_member_join(self, member):
        # Load welcome settings for the guild
        welcome_settings_path = os.path.join(DATA_SERVER, member.guild.name, 'wlc.json')
        try:
            with open(welcome_settings_path, 'r') as file:
                welcome_settings = json.load(file)
        except FileNotFoundError:
            welcome_settings = {}
        
        welcome_channel_id = welcome_settings.get('channel_id')
        welcome_channel = self.bot.get_channel(welcome_channel_id)
    
        if welcome_channel:
            member_count = sum(1 for member in member.guild.members)
            welcome_message = welcome_settings.get('message', f"Selamat datang di {member.guild.name}, {member.mention}!")
            final_welcome_message = welcome_message.replace("{server_name}", member.guild.name)
            final_welcome_message = final_welcome_message.replace("{mention}", member.mention)
            final_welcome_message = final_welcome_message.replace("{member_count}", str(member_count))
    
            embed = discord.Embed(
                title=f"SELAMAT DATANG, {member.name}!",
                description=final_welcome_message,
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_footer(text=f"Jumlah member saat ini: {member.guild.member_count}")
    
            await welcome_channel.send(embed=embed)
    
        # Check if the joined member is a bot
        if member.bot:
            guild_role_data = await DataBase.get_guild_role_data(member.guild)
            role_id = guild_role_data.get('default_bot_role_id')
    
            if role_id:
                role = member.guild.get_role(int(role_id))
                if role:
                    # Retry mechanism with a delay
                    for attempt in range(3):
                        try:
                            await member.add_roles(role)
                        except discord.HTTPException as e:
                            print(f"Failed to add role to bot: {e}")
                            await asyncio.sleep(5)  # Wait for 2 seconds before retrying
                        else:
                            break  # If role added successfully, exit the loop
                    else:
                        print("Failed to add role after multiple attempts.")
                else:
                    print(f'Bot role with ID {role_id} not found.')
            else:
                print('No default bot role ID specified in guild role data.')
        
        await Fungsi.update_stats(member.guild)
    
    @discord.Cog.listener()
    async def on_member_remove(self, member):
        leave_settings_path = os.path.join(DATA_SERVER, member.guild.name, 'leave.json')
        try:
            with open(leave_settings_path, 'r') as file:
                leave_settings = json.load(file)
        except FileNotFoundError:
            leave_settings = {}
    
        leave_channel_id = leave_settings.get('channel_id')
        
        if leave_channel_id:
            leave_channel = self.bot.get_channel(leave_channel_id)
            if leave_channel and isinstance(leave_channel, discord.TextChannel):
                embed = discord.Embed(
                    title=f"SELAMAT JALAN, {member.name}!",
                    description=f"[{member.name}](https://discord.com/users/{member.id}) keluar dari server.",
                    color=discord.Color.red()
                )
    
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                embed.set_footer(text=f"Jumlah member saat ini: {member.guild.member_count}.")
    
                await leave_channel.send(embed=embed)
        
        await Fungsi.update_stats(member.guild)
    
    @discord.Cog.listener()
    async def on_member_update(self, before, after):
        role_data = await DataBase.load_role_data(after.guild)
        default_human_role_id = role_data.get('default_human_role_id')
    
        if default_human_role_id:
            human_role = discord.utils.get(after.guild.roles, id=default_human_role_id)
    
            if human_role:
                if human_role not in before.roles and human_role in after.roles:
                    guild_id = after.guild.id
    
                    # Fetch the channel ID and welcome message from the saved data
                    channel_id = await DataBase.get_channel_id(after.guild)
                    verif_message = await DataBase.get_verif_message(after.guild)
                    pesan = verif_message.replace("{mention}", after.mention)
                    
                    channel = after.guild.get_channel(channel_id)
                    if channel:
                        embed = Embed(
                            description=f"{pesan}",
                            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                        )
    
                        delete_time = datetime.utcnow() + timedelta(seconds=30)
    
                        while datetime.utcnow() < delete_time:
                            remaining_seconds = (delete_time - datetime.utcnow()).seconds
                            embed.set_footer(text=f"\nPesan akan otomatis hilang dalam {remaining_seconds} detik.")
                            if 'message' in locals():
                                await message.edit(embed=embed)
                            else:
                                message = await channel.send(embed=embed)
                            await asyncio.sleep(1)
                        await message.delete()

    @discord.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        settings = DataBase.loadSetting()
        if str(payload.guild_id) not in settings:
            return
        if str(payload.channel_id) not in settings[str(payload.guild_id)]["reactRole"]:
            return
    
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)
        channel = guild.get_channel(payload.channel_id)
    
        if str(payload.channel_id) in settings[str(payload.guild_id)]["reactRole"] and user != self.bot.user:
            emoji = str(payload.emoji)
            emojiSet = settings[str(payload.guild_id)]["reactRole"][str(payload.channel_id)][str(payload.message_id)]
            if emoji in settings[str(payload.guild_id)]["reactRole"][str(payload.channel_id)][str(payload.message_id)]:
                role = discord.utils.get(guild.roles, id=settings[str(payload.guild_id)]["reactRole"][str(payload.channel_id)][str(payload.message_id)][emoji]["role"])
                if settings[str(payload.guild_id)]["reactRole"][str(payload.channel_id)][str(payload.message_id)][emoji]["clear_reaction"]:
                    message = await channel.fetch_message(payload.message_id)
                    await message.remove_reaction(emoji, user)
                await user.add_roles(role)
    
    @discord.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        settings = DataBase.loadSetting()
        if str(payload.guild_id) not in settings:
            return
        if str(payload.channel_id) not in settings[str(payload.guild_id)]["reactRole"]:
            return
    
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)
        channel = guild.get_channel(payload.channel_id)
    
        if str(payload.channel_id) in settings[str(payload.guild_id)]["reactRole"] and user != self.bot.user:
            emoji = str(payload.emoji)
            if emoji in settings[str(payload.guild_id)]["reactRole"][str(payload.channel_id)][str(payload.message_id)]:
                role = discord.utils.get(guild.roles, id=settings[str(payload.guild_id)]["reactRole"][str(payload.channel_id)][str(payload.message_id)][emoji]["role"])
                clear_reaction = settings[str(payload.guild_id)]["reactRole"][str(payload.channel_id)][str(payload.message_id)][emoji]["clear_reaction"]
                if clear_reaction == False:
                    await user.remove_roles(role)

    @discord.Cog.listener()
    async def on_message(self, message):
        # Menangani prefix kustom
        default_prefix = ('!', '.')
        
        if message.guild:
            guild_name = str(message.guild.name)
            nochat_settings_path = os.path.join(DATA_SERVER, guild_name, 'nochat.json')
    
            try:
                with open(nochat_settings_path, 'r') as file:
                    nochat_settings = json.load(file)
            except FileNotFoundError:
                nochat_settings = []
    
            for setting in nochat_settings:
                if message.channel.id == setting['channel_id']:
                    if (setting['source'] == 'bot' and message.author.bot) or (setting['source'] == 'user' and not message.author.bot):
                        await message.delete()
                        break
    
        # Menghapus prefix dan memproses perintah jika ada
        for prefix in default_prefix:
            if message.content.lower().startswith(prefix.lower()):
                message.content = message.content[len(prefix):].lstrip()
                await self.bot.process_commands(message)
                break
        else:
            if message.author == self.bot.user or message.author.bot:
                return  # Skip messages from the bot
            
            # Handle command invocation by mention
            if self.bot.user in message.mentions:
                # Remove the mention from the message content
                message.content = message.content.replace(self.bot.user.mention, '').strip()
                await self.bot.process_commands(message)
            
                # Check if the message content is empty or specifically requesting help
                if not message.content:
                    help_command = self.bot.get_command('cmd')
                    if help_command:
                        ctx = await self.bot.get_context(message)
                        await ctx.invoke(help_command)
                return
            elif 'chat-gpt' in message.channel.name and not message.reference:
                guild_name = str(message.guild.name)
                user_name = str(message.author.name)  # Use user's username instead of ID
                
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
                    e = None
                    try:
                        response = client.chat.completions.create(
                            model="llama-3-sonar-large-32k-online",
                            messages=input_messages,
                        )
                    except Exception as error:
                        e = error
                        print(f"[AI-Chat] {e}")
                        
                    reply = response.choices[0].message.content if response and response.choices else f"### [Kuota Mencapai Limit]\n{e}"
                    chunks = [reply[i:i + 2000] for i in range(0, len(reply), 2000)]
    
                    for chunk in chunks:
                        await message.channel.send(chunk)

def setup(bot: discord.Bot):
    bot.add_cog(Control(bot))
