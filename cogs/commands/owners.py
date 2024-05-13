import discord, pytz, os, subprocess, csv, zipfile, random
from discord.ext import commands, tasks
from typing import Union
from decouple import config
from github import Github
from cogs.fungsi.database import DataBase, DATA_OWNER
from cogs.fungsi.func import Fungsi, bot_creator_id, owner_ids

GITHUB_EMAIL = config('GITHUB_EMAIL', default=None)
GITHUB_USERNAME = config('GITHUB_USERNAME', default=None)
GITHUB_TOKEN = config('GITHUB_TOKEN', default=None)
REPO_NAME = config('REPO_NAME', default=None)
BACKUP_FOLDER = '.'


class Owners(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot

    # MENGELUARKAN BOT DARI SERVER
    @commands.command(name='leave', description="Hanya dapat dilakukan oleh Owner Bot.")
    async def leave_server(self, ctx, *, server: str = ''):
        if ctx.author.id != bot_creator_id and ctx.author.id not in owner_ids:
            embed = discord.Embed(
                description=f"Ngapain?",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        # Get the guild associated with the interaction context
        guild = ctx.guild
        
        # Check if the server argument is empty
        if server:
            # Check if the provided server is an ID or name
            if server.isdigit():
                guild_to_leave = discord.utils.get(bot.guilds, id=int(server))
            else:
                # Join all the words in the server name
                server_name = ' '.join(server.split())
                guild_to_leave = discord.utils.get(bot.guilds, name=server_name)
            
            # Check if the guild to leave exists
            if guild_to_leave:
                guild = guild_to_leave
        
        # Load data associated with the guild
        data = DataBase.load_data(guild.name)
        if 'message_id' in data and 'channel_id' in data:
            message_id = data['message_id']
            channel_id = data['channel_id']
            try:
                channel_mention = bot.get_channel(channel_id)
                if channel_mention:
                    try:
                        message = await channel_mention.fetch_message(message_id)
                        await message.delete()
                    except discord.NotFound:
                        pass
                    except discord.Forbidden:
                        pass
                delete_data(guild.name)
            except discord.Forbidden:
                pass
    
        embed = discord.Embed(
            description=f"Keluar dari **{guild.name}**.",
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
        )
        await ctx.send(embed=embed)
        await guild.leave()
    
    # MENAMBAH/MEMGHAPUS OWNER
    @commands.command(name='add')
    async def add_owner(self, ctx, user_identifier: Union[int, discord.Member]):
        """Menambah owner bot."""
        global bot_creator_id, owner_ids
    
        if ctx.author.id != bot_creator_id:
            await ctx.send("Kamu tidak memiliki otoritas untuk melakukan perintah ini!", delete_after=5)
            await ctx.message.delete()
            return
    
        if isinstance(user_identifier, discord.Member):
            user_id = user_identifier.id
            display_name = user_identifier.display_name
        elif isinstance(user_identifier, int):
            try:
                user = await self.bot.fetch_user(user_identifier)
                user_id = user.id
                display_name = user.display_name
            except discord.NotFound:
                await ctx.send("User dengan ID tersebut tidak ditemukan.", delete_after=5)
                await ctx.message.delete()
                return
        else:
            await ctx.send("Parameter tidak valid.", delete_after=5)
            await ctx.message.delete()
            return
    
        if user_id in owner_ids:
            await ctx.send(f"`{display_name}` sudah menjadi owner sebelumnya.", delete_after=5)
        else:
            with open(DATA_OWNER, 'a', newline='') as owner_file:
                writer = csv.writer(owner_file)
                writer.writerow([display_name, user_id])
    
            owner_ids.add(user_id)
            await ctx.send(f"Berhasil menambahkan `{display_name}` menjadi owner.", delete_after=5)
    
        await ctx.message.delete()
    
    @commands.command(name='del')
    async def del_owner(self, ctx, owner_identifier: Union[discord.Member, int]):
        """Menghapus owner bot."""
        global bot_creator_id, owner_ids
    
        if ctx.author.id != bot_creator_id:
            await ctx.send("Kamu tidak memiliki otoritas untuk melakukan perintah ini!", delete_after=5)
            await ctx.message.delete()
            return
    
        owner_data = []
        try:
            with open(DATA_OWNER, 'r') as owner_file:
                reader = csv.reader(owner_file)
                owner_data = list(reader)
        except FileNotFoundError:
            pass
    
        if isinstance(owner_identifier, int):
            owner_id = owner_identifier
        elif isinstance(owner_identifier, discord.Member):
            owner_id = owner_identifier.id
        else:
            await ctx.send("Parameter tidak valid.", delete_after=5)
            await ctx.message.delete()
            return
    
        for owner_entry in owner_data:
            if int(owner_entry[1]) == owner_id:
                deleted_display_name = owner_entry[0]
                owner_data.remove(owner_entry)
                owner_ids.remove(owner_id)
    
                with open(DATA_OWNER, 'w', newline='') as owner_file:
                    writer = csv.writer(owner_file)
                    writer.writerows(owner_data)
    
                await ctx.send(f"{deleted_display_name} berhasil dihapus dari daftar owner.", delete_after=5)
                await ctx.message.delete()
                return
    
        await ctx.send(f"Owner dengan ID {owner_id} tidak ditemukan. Cek `!owner`.", delete_after=5)
        await ctx.message.delete()
    
    # MENGIRIM FILE INI KE DISCORD
    @commands.command(name='sc')
    async def send_source(self, ctx):
        """Mengirim file source bot ini."""
        # Memvalidasi channel "bot-command"
        mod_channel = None
        for channel in ctx.guild.channels:
            if 'bot-command' in channel.name:
                mod_channel = channel
                break
        if ctx.channel != mod_channel:
            await ctx.send(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)
            await ctx.message.delete()
            return
                
        if ctx.author.id == bot_creator_id or ctx.author.id in owner_ids:
            # Menghapus pesan source sebelumnya jika ada
            async for message in ctx.channel.history(limit=50):
                if message.author == self.bot.user and message.content.startswith("**Source Code untuk "):
                    await message.delete()
                    break
        
            # Specify the full path to the file
            file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'main.py'))
            await ctx.send(f"**Source Code untuk {self.bot.user.name}:**", file=discord.File(file_path))
            await ctx.message.delete()
        else:
            embed = discord.Embed(
                description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
                color=discord.Color.red())
            await ctx.send(embed=embed, delete_after=5)
            await ctx.message.delete()
    
    # BACKUP KE GITHUB
    @commands.command(name='backup')
    async def manual_backup(self, ctx, *, commit: str = 'Backup files'):
        """Menyimpan data ke Github."""
        # Memvalidasi channel "bot-command"
        mod_channel = next((channel for channel in ctx.guild.channels if 'bot-command' in channel.name), None)
        if not mod_channel or ctx.channel != mod_channel:
            await ctx.send(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)
            await ctx.message.delete()
            return
        
        if ctx.author.id not in (bot_creator_id, *owner_ids):
            embed = discord.Embed(
                description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
            await ctx.message.delete()
            return
    
        if not all([GITHUB_EMAIL, GITHUB_USERNAME, GITHUB_TOKEN, REPO_NAME]):
            embed = discord.Embed(
                description=f"`.env` Github tidak diatur, tidak dapat mengunggah backup ke Github.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
            await ctx.message.delete()
            return
        
        try:
            g = Github(GITHUB_USERNAME, GITHUB_TOKEN)
            user = g.get_user()
            repo = user.get_repo(REPO_NAME)
            
            repo_thumbnail = user.avatar_url
            
            subprocess.run(['git', 'config', '--global', 'user.email', f'{GITHUB_EMAIL}'])
            subprocess.run(['git', 'config', '--global', 'user.name', f'{GITHUB_USERNAME}'])
            subprocess.run(['git', 'config', '--global', 'init.defaultBranch', 'main'])
            subprocess.run(['git', 'init', '.'])
            subprocess.run(['git', 'branch', '-M', 'main'])
            subprocess.run(['git', 'add', '.'])
            subprocess.run(['git', 'commit', '-m', f'{commit}'])
            subprocess.run(['git', 'remote', 'add', 'origin', 'main', f'https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{REPO_NAME}.git'])
            subprocess.run(['git', 'push', f'https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{REPO_NAME}.git', 'main'])
            
            embed = discord.Embed(
                description=f"Berhasil menyimpan semua data ke [{REPO_NAME}](https://github.com/{GITHUB_USERNAME}/{REPO_NAME}).",
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
            )
            
            embed.set_thumbnail(url=repo_thumbnail)  # Set repository thumbnail
            
            await ctx.send(embed=embed, delete_after=5)
            await ctx.message.delete()
        except Exception as e:
            print(e)
            embed = discord.Embed(
                description=f"Terjadi kesalahan saat melakukan backup ke Github: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=15)
            await ctx.message.delete()
    
    # MENGAMBIL DATABASE
    @commands.command(name='db')
    async def send_database_files(self, ctx):
        """Send all files in the server_data folder."""
        mod_channel = None
        for channel in ctx.guild.channels:
            if 'bot-command' in channel.name:
                mod_channel = channel
                break
        
        if ctx.channel != mod_channel:
            await ctx.send(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)
            return
        
        if ctx.author.id == bot_creator_id or ctx.author.id in owner_ids:
            server_data_folder = 'server_data'
    
            # Send files from user_data folder
            user_data_path = 'user_data'
            user_data_files = [f for f in os.listdir(user_data_path) if os.path.isfile(os.path.join(user_data_path, f))]
    
            if user_data_files:
                for file in user_data_files:
                    file_path = os.path.join(user_data_path, file)
                    with open(file_path, 'rb') as file_content:
                        await ctx.send(file=discord.File(file_content, filename=file))
                
            # Iterate over guild folders
            for guild_folder in os.listdir(server_data_folder):
                guild_data_directory = os.path.join(server_data_folder, guild_folder)
    
                # Check if it's a directory
                if os.path.isdir(guild_data_directory):
                    # Iterate over files in the guild folder
                    for filename in os.listdir(guild_data_directory):
                        file_path = os.path.join(guild_data_directory, filename)
    
                        # Send file to Discord
                        with open(file_path, 'rb') as file_content:
                            # Rename the file to guild name before sending
                            await ctx.send(file=discord.File(file_content, filename=f"{guild_folder} {filename}"))
    
            # Delete the user's command message
            await ctx.message.delete()
        else:
            await ctx.send("> You don't have the authority to use this command!", delete_after=5)
    
    # MEMPERBARUI FILE ROOT & DB
    @commands.command(name='upload', aliases=['up'])
    async def upload_files(self, ctx, sub_command: str = None, guild_identifier: str = None):
        mod_channel = None
        for channel in ctx.guild.channels:
            if 'bot-command' in channel.name:
                mod_channel = channel
                break
        if ctx.channel != mod_channel:
            await ctx.send(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)
            return
        
        if ctx.author.id == bot_creator_id or ctx.author.id in owner_ids:
            if sub_command == 'user':
                await self.upload_folder_files(ctx, 'user_data')
            elif sub_command == 'server':
                await self.upload_to_guild_directory(ctx, guild_identifier)
            elif sub_command == 'radio':
                await self.upload_folder_files(ctx, 'radio')
            elif sub_command == 'cogs':
                await self.upload_folder_files(ctx, 'cogs')
            else:
                # Memvalidasi attachment
                if ctx.message.attachments:
                    for attachment in ctx.message.attachments:
                        if attachment.filename.startswith('.'):
                            # Save the file to a zip archive
                            zip_path = os.path.join(os.getcwd(), 'hidden_file_archive.zip')
                            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                                zip_file.write(os.path.join(os.getcwd(), attachment.filename), attachment.filename)
    
                            # Send the zip archive
                            await ctx.send(file=discord.File(zip_path))
                            await ctx.send(f'> File {attachment.filename} berhasil diunggah sebagai zip archive.', delete_after=5)
    
                            # Remove the zip file
                            os.remove(zip_path)
                        else:
                            file_path = os.path.join(os.getcwd(), attachment.filename)
                            
                            # Remove existing bot.py
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                
                            await ctx.message.delete()
                            await ctx.send(f'> File {attachment.filename} berhasil diunggah dan menggantikan yang lama.', delete_after=5)
                            
                            # Save the new file
                            await attachment.save(file_path)
    
                    # Menghapus pesan !upload
                    await ctx.message.delete()
                else:
                    await ctx.send(f'> Tidak ada file yang diunggah.', delete_after=5)
        else:
            embed = discord.Embed(
            description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
            color=discord.Color.red())
            
            await ctx.send(embed=embed, delete_after=5)
            
    async def upload_folder_files(self, ctx, folder_name):
        """Upload files to the specified folder within the root directory."""
        if ctx.author.id == bot_creator_id or ctx.author.id in owner_ids:
            # Memvalidasi attachment
            if ctx.message.attachments:
                # Get the folder path based on the provided folder_name
                folder_path = os.path.join(os.getcwd(), folder_name)
    
                os.makedirs(folder_path, exist_ok=True)
    
                for attachment in ctx.message.attachments:
                    file_path = os.path.join(folder_path, attachment.filename)
    
                    # Save the attachment to the specified folder
                    await attachment.save(file_path)
                    
                    # Use relative path to display in the message
                    relative_path = os.path.relpath(file_path, start=os.getcwd())
                    await ctx.send(f'> File {attachment.filename} berhasil diunggah ke folder {relative_path}.', delete_after=5)
    
                # Menghapus pesan !upload
                await ctx.message.delete()
            else:
                await ctx.send(f'> Tidak ada file yang diunggah.', delete_after=5)
        else:
            embed = discord.Embed(
            description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
            color=discord.Color.red())
            
            await ctx.send(embed=embed, delete_after=5)
    
    async def upload_to_guild_directory(self, ctx, guild_identifier):
        """Upload files to the guild directory within server_data."""
        if ctx.author.id == bot_creator_id or ctx.author.id in owner_ids:
            # Memvalidasi attachment
            if ctx.message.attachments:
                server_data_folder = 'server_data'
    
                # Gunakan Nama Guild sebagai nama folder
                guild_directory = os.path.join(server_data_folder, str(ctx.guild.name))
    
                os.makedirs(guild_directory, exist_ok=True)
    
                for attachment in ctx.message.attachments:
                    file_path = os.path.join(guild_directory, attachment.filename)
    
                    # Menyimpan attachment ke folder server_data/guild_name
                    await attachment.save(file_path)
                    await ctx.send(f'> File {attachment.filename} berhasil diunggah ke folder {guild_directory}.', delete_after=5)
    
                # Menghapus pesan !upload vm
                await ctx.message.delete()
            else:
                await ctx.send(f'> Tidak ada file yang diunggah.', delete_after=5)
        else:
            embed = discord.Embed(
            description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
            color=discord.Color.red())
            
            await ctx.send(embed=embed, delete_after=5)
            
    @commands.command(name='delfile')
    async def delete_file(self, ctx, directory: str, file_name: str):
        """Delete a file in the specified directory."""
        # Validate the user's permission
        if ctx.author.id == bot_creator_id or ctx.author.id in owner_ids:
            try:
                # Construct the file path
                file_path = os.path.join(os.getcwd(), directory, file_name)
    
                # Check if the file exists
                if os.path.exists(file_path):
                    # Delete the file
                    os.remove(file_path)
                    await ctx.send(f'> File `{file_name}` in directory `{directory}` deleted successfully.', delete_after=5)
                else:
                    await ctx.send(f'> File `{file_name}` in directory `{directory}` not found.', delete_after=5)
            except Exception as e:
                await ctx.send(f'> An error occurred while deleting the file: {str(e)}', delete_after=5)
        else:
            embed = discord.Embed(
            description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
            color=discord.Color.red())
            
            await ctx.send(embed=embed, delete_after=5)
    
    @commands.command(name='rename')
    async def rename_file(self, ctx, old_name: str, new_name: str, directory: str = ''):
        """
        Rename a file in the specified directory (default is the root directory).
        Usage: !rename old_filename new_filename [directory]
        """
        # Validate channel permissions if needed
        # ...
    
        try:
            if directory:
                file_path = os.path.join(os.getcwd(), directory, old_name)
                new_path = os.path.join(os.getcwd(), directory, new_name)
            else:
                file_path = os.path.join(os.getcwd(), old_name)
                new_path = os.path.join(os.getcwd(), nama_baru)
    
            # Rename the file
            os.rename(file_path, new_path)
            await ctx.send(f"> File '{old_name}' has been renamed to '{nama_baru}'.", delete_after=5)
        except FileNotFoundError:
            await ctx.send(f"> Error: File '{old_name}' not found.", delete_after=5)
        except Exception as e:
            await ctx.send(f"> An error occurred: {e}", delete_after=5)

    @discord.Cog.listener()
    async def on_ready(self):
        global bot_creator_id, owner_ids
    
        try:
            bot_creator_id = (await self.bot.application_info()).owner.id
    
            # Memvalidasi data owner
            try:
                with open(DATA_OWNER, 'r') as owner_file:
                    owner_entries = owner_file.readlines()
    
                # Mengupdate data owner dengan nomor jika kosong
                if owner_entries:
                    owner_ids.clear()
                    for index, line in enumerate(owner_entries, start=1):
                        owner_data = line.strip().split(',')
                        owner_id = int(owner_data[-1])
                        owner_ids.add(owner_id)
    
            except FileNotFoundError:
                print("Data owner tidak ditemukan.")
    
        except Exception as e:
            print(f"Error：{e}")

