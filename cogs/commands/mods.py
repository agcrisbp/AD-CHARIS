import discord, os, json, re
from discord.ext import commands
from discord.ui import Button, View
from cogs.fungsi.database import DataBase, DATA_SERVER
from cogs.fungsi.func import Fungsi, welcome_settings, leave_settings, bot_creator_id, owner_ids

DEFAULT_PERMISSIONS = discord.Permissions()
DEFAULT_PERMISSIONS.administrator = True

class Mods(discord.Cog, View):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.bot_creator_id = bot_creator_id
        self.owner_ids = owner_ids

    setup_server = discord.SlashCommandGroup(
        name="setup",
        description="Mengatur berbagai macam pengaturan untuk bot di server.",
        guild_only=True,
        default_member_permissions=DEFAULT_PERMISSIONS,
    )
    pesan = setup_server.create_subgroup(name="pesan",
        guild_only=True,
        default_member_permissions=DEFAULT_PERMISSIONS,
    )
    stats = setup_server.create_subgroup(name="stats",
        guild_only=True,
        default_member_permissions=DEFAULT_PERMISSIONS,
    )
    @setup_server.command(
        name="create",
        description="Membuat pengaturan channel untuk server.",
        guild_only=True,
    )
    async def channel(self,ctx: discord.ApplicationContext,
                      setup: discord.Option(str, description="Setting yang ingin diatur.",
                                            choices=[discord.OptionChoice(name="Channel: Verifikasi (Pesan)", value="verifikasi"),
                                                     discord.OptionChoice(name="Channel: Nochat (Tipe)", value="nochat"),
                                                     discord.OptionChoice(name="Channel: Welcome (Pesan)", value="welcome"),
                                                     discord.OptionChoice(name="Channel: Leave", value="leave") ]),
                      channel: discord.TextChannel,
                      pesan: str = '',
                      tipe: discord.Option(str, description="Setting yang ingin diatur.",
                                           choices=[discord.OptionChoice(name="Bot", value="bot"),
                                                    discord.OptionChoice(name="User", value="user") ]) = None):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        
        mod_channel = None
        for channel_obj in ctx.guild.channels:
            if 'bot-command' in channel_obj.name:
                mod_channel = channel_obj
                break
        if ctx.channel != mod_channel:
            return await ctx.respond(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)

        if setup == 'welcome':
            if ctx.guild.name not in welcome_settings:
                welcome_settings[ctx.guild.name] = {}
            
            # Update the welcome channel ID directly
            welcome_settings[ctx.guild.name]['channel_id'] = channel.id
            
            footer = None
            if pesan == '':
                pesan = 'Selamat datang di {server_name}, {mention}!'
                footer = f'Ini adalah pesan bawaan, isi parameter pesan untuk menggunakan pesan kustom.'
            else:
                welcome_settings[ctx.guild.name]['message'] = pesan
            
            pesan = pesan.replace("{mention}", ctx.author.mention).replace("{server_name}", ctx.guild.name).replace("{member_count}", str(len(ctx.guild.members)))
            
            embed_description = f"Berhasil mengatur channel selamat datang ke {channel.mention}.\n\n### __**Pratinjau Pesan**__:\n\n{pesan}\n\n"
            embed = discord.Embed(description=embed_description, color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            
            avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            
            if footer is not None:
                embed.set_footer(text=f"CATATAN: {footer}", icon_url=avatar_url)
            else:
                embed.set_footer(text=f"Dibuat oleh {ctx.author.name}", icon_url=avatar_url)
            
            await ctx.respond(embed=embed, delete_after=30)
            
            save_welcome_settings(ctx.guild.name)
        
        elif setup == 'leave':
            guild_data_directory = os.path.join(DATA_SERVER, ctx.guild.name)
            os.makedirs(guild_data_directory, exist_ok=True)
        
            # Ensure the leave.json file is created
            DataBase.ensure_leave_file(ctx.guild.name)
        
            # Create or load the leave_settings dictionary
            if ctx.guild.name not in leave_settings:
                leave_settings[ctx.guild.name] = {}
        
            # Update the leave channel ID directly
            leave_settings[ctx.guild.name]['channel_id'] = channel.id
        
            # Save the leave_settings to leave.json
            DataBase.save_leave_settings(ctx.guild.name, leave_settings[ctx.guild.name])
        
            embed = discord.Embed(description=f"Channel untuk member yang meninggalkan server diatur ke {channel.mention}.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            await ctx.respond(embed=embed, delete_after=5)
        
        elif setup == 'verifikasi':
            if pesan == '':
                return await ctx.respond("Mohon masukkan **`pesan`**.", delete_after=5)

            await ctx.respond('> Berhasil!', delete_after=5)
          
            if not (ctx.author.guild_permissions.administrator or ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
                embed = discord.Embed(
                description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
                color=discord.Color.red())
                
                return await ctx.respond(embed=embed, delete_after=5)
        
            if not ctx.guild.me.guild_permissions.create_instant_invite:
                return await ctx.respond("Butuh permission gan.", delete_after=5)
        
            try:
                guild_data_directory = os.path.join(DATA_SERVER, str(ctx.guild.name))
                os.makedirs(guild_data_directory, exist_ok=True)
        
                guild_link_path = os.path.join(guild_data_directory, 'link.json')
        
                data = DataBase.load_data(ctx.guild.name)
        
                invite = await channel.create_invite(max_uses=0, max_age=10800, unique=True, reason="Moderator membuat link ini menggunakan /setup create Channel: Verifikasi.")
                embed = discord.Embed(
                    description=f'{pesan}\n\n* Link Server: {invite.url}'
                )
                message = await channel.send(embed=embed)
        
                data['message_id'] = message.id
                data['channel_id'] = channel.id
                data['pesan'] = pesan
                DataBase.save_data(ctx.guild.name, data)
        
            except discord.Forbidden:
                await ctx.respond("Butuh permission gan.", delete_after=5)
            except Exception as e:
                print(f"An error occurred: {e}")
        
        elif setup == 'nochat':
            if tipe is None or tipe.strip() == '':
                return await ctx.respond("Isi parameter `tipe`!", delete_after=10)
            if not (ctx.author.guild_permissions.administrator or ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
                embed = discord.Embed(
                description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
                color=discord.Color.red())
                
                return await ctx.respond(embed=embed, delete_after=5)
        
            # Save the channel ID to the JSON database
            guild_name = str(ctx.guild.name)
            nochat_settings_path = os.path.join(DATA_SERVER, guild_name, 'nochat.json')
        
            # Load existing settings or initialize as an empty list
            try:
                with open(nochat_settings_path, 'r') as file:
                    nochat_settings = json.load(file)
            except FileNotFoundError:
                nochat_settings = []
        
            # Check if the setting already exists
            if any(setting['channel_id'] == channel.id and setting['source'] == tipe for setting in nochat_settings):
                return await ctx.respond(f'Pengaturan **nochat** untuk **`{tipe}`** di {channel.mention} sudah pernah diatur.', delete_after=5)
        
            # Append the setting only if it doesn't exist
            nochat_settings.append({'channel_id': channel.id, 'source': tipe})
        
            # Write the updated settings back to the file
            with open(nochat_settings_path, 'w') as file:
                json.dump(nochat_settings, file, indent=4)
        
            # Provide feedback to the user
            await ctx.respond(f'Pesan **`{tipe}`** di {channel.mention} akan dihapus otomatis.', delete_after=5)

    @setup_server.command(
      name='reset',
      description="Mereset semua pengaturan untuk server.",
      guild_only=True,
    )
    async def unset_setting_slash(self, ctx, setting: discord.Option(str, description="Setting yang ingin dihapus.", choices=[discord.OptionChoice(name="Semua", value="all"), discord.OptionChoice(name="Channel & Pesan: Verifikasi", value="server"), discord.OptionChoice(name="Channel: Nochat", value="nochat"), discord.OptionChoice(name="Channel: Welcome", value="wlc"), discord.OptionChoice(name="Channel: Leave", value="leave"), discord.OptionChoice(name="Pesan: Welcome", value="wlcmsg"), discord.OptionChoice(name="Role Default Bot/User", value="role"), discord.OptionChoice(name="Server Stats", value="stats"), discord.OptionChoice(name="Voice Master", value="vm") ]), tipe: discord.Option(str, description="Role yang ingin dihapus.", choices=[discord.OptionChoice(name="Semua", value="all"), discord.OptionChoice(name="Bot", value="bot"), discord.OptionChoice(name="User", value="user")], required=False), text_channel: discord.TextChannel = None, voice_channel: discord.VoiceChannel = None):
        await self.unset_settings(ctx, setting, tipe, text_channel, voice_channel)
    async def unset_settings(self, ctx, setting: str, tipe: str = '', text_channel: discord.TextChannel = None, voice_channel: discord.VoiceChannel = None):

        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
    
        if not (ctx.author.guild_permissions.administrator or ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
            embed = discord.Embed(description="Kamu tidak memiliki otoritas untuk melakukan perintah ini!", color=discord.Color.red())
            return await ctx.respond(embed=embed, delete_after=5)
    
        # Mencari channel "bot-command"
        mod_channel = None
        for channel in ctx.guild.channels:
            if 'bot-command' in channel.name:
                mod_channel = channel
                break
        if ctx.channel != mod_channel:
            embed = discord.Embed(description=f"Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.", color=discord.Color.red())
            return await ctx.respond(embed=embed, delete_after=5)
    
        guild_data_directory = os.path.join(DATA_SERVER, str(ctx.guild.name))
    
        if setting == 'all':
            await self.unset_welcome_channel(ctx, guild_data_directory)
            await self.unset_custom_welcome_message(ctx, guild_data_directory)
            await self.unset_vm(ctx, guild_data_directory, setting='all')
            await self.unset_leave(ctx, guild_data_directory)
            await self.unset_role(ctx, tipe='all')
            await self.unset_stats(ctx)
            await self.unset_server(ctx)
            await self.unset_nochat(ctx, setting='all', tipe='all')
            return
    
        elif setting == 'wlc':
            await self.unset_welcome_channel(ctx, guild_data_directory)
    
        elif setting == 'wlcmsg':
            await self.unset_custom_welcome_message(ctx, guild_data_directory)
    
        elif setting == 'vm':
            if voice_channel == '':
                await ctx.respond("Mohon isi parameter voice channel dengan nama voice channel atau ID.", delete_after=5)
            else:
                await self.unset_vm(ctx, guild_data_directory, setting, voice_channel)
    
        elif setting == 'leave':
            await self.unset_leave(ctx, guild_data_directory)
    
        elif setting == 'role':
            if tipe == '':
                await ctx.respond("Mohon isi parameter **`tipe`**", delete_after=5)
            else:
                await self.unset_role(ctx, tipe)
            
        elif setting == 'stats':
            await self.unset_stats(ctx)
        
        elif setting == 'server':
            await self.unset_server(ctx)
            
        elif setting == 'nochat':
            if channel is None or (tipe is None or tipe.strip() == ''):
                await ctx.respond("Mohon pilih channel pada parameter **`text_channel`** dan tipe user pada parameter **`tipe`**.", delete_after=10)
                return
            else:
                await self.unset_nochat(ctx, setting, tipe, text_channel)
    
    async def unset_welcome_channel(self, ctx, guild_data_directory):
        if ctx.guild.name in welcome_settings:
            if 'channel_id' in welcome_settings[ctx.guild.name]:
                del welcome_settings[ctx.guild.name]['channel_id']
                embed = discord.Embed(description="Channel selamat datang direset.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                await ctx.respond(embed=embed, delete_after=5)
                DataBase.save_welcome_settings(ctx.guild.name)
    
            if not os.listdir(guild_data_directory):
                os.rmdir(guild_data_directory)
    
    async def unset_custom_welcome_message(self, ctx, guild_data_directory):
        if ctx.guild.name in welcome_settings:
            if 'message' in welcome_settings[ctx.guild.name]:
                del welcome_settings[ctx.guild.name]['message']
                embed = discord.Embed(description="Pesan selamat datang direset.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                await ctx.respond(embed=embed, delete_after=5)
                DataBase.save_welcome_settings(ctx.guild.name)
    
            if os.path.exists(guild_data_directory):
                if not os.listdir(guild_data_directory):
                    os.rmdir(guild_data_directory)
    
    async def unset_vm(self, ctx, guild_data_directory, setting: str, voice_channel: discord.VoiceChannel = None):
        # Reset VM
        vm_data_path = os.path.join(guild_data_directory, 'vm.json')
    
        try:
            with open(vm_data_path, 'r') as file:
                vm_data = json.load(file)
        except FileNotFoundError:
            vm_data = []
    
        if voice_channel is None:
            # If the voice_channel parameter is None and setting is 'all', directly remove vm.json
            if setting == 'all':
                if os.path.exists(vm_data_path):
                    os.remove(vm_data_path)
                    embed = discord.Embed(description="Semua pengaturan Voice Master telah dihapus.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                    await ctx.respond(embed=embed, delete_after=5)
                else:
                    embed = discord.Embed(description="Tidak ada VM untuk server ini.", color=discord.Color.red())
                    await ctx.respond(embed=embed, delete_after=5)
                return
            else:
                await ctx.respond("Mohon pilih sebuah **`voice_channel`**.", delete_after=5)
                return
    
        # Get the voice channel ID directly from the voice_channel parameter
        channel_id = voice_channel.id
    
        if not vm_data:
            embed = discord.Embed(description="Tidak ada VM untuk server ini.", color=discord.Color.red())
            await ctx.respond(embed=embed, delete_after=5)
            return
    
        deleted_channel = ctx.guild.get_channel(channel_id)
    
        # Check if the voice channel ID is in the VM database
        if any(entry.get('voice_channel_id') == channel_id for entry in vm_data):
            # Remove the voice channel entry from VM data
            for entry in vm_data:
                if entry.get('voice_channel_id') == channel_id:
                    vm_data.remove(entry)
                    break
    
            # Update the VM file
            with open(vm_data_path, 'w') as file:
                json.dump(vm_data, file, indent=4)
    
            embed = discord.Embed(description=f"VM {deleted_channel.mention} dihapus.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            await ctx.respond(embed=embed, delete_after=5)
    
            # Check if the guild data directory is empty
            if not vm_data:  # Check if vm_data is empty
                os.remove(vm_data_path)  # Delete the vm.json file
                if not os.listdir(guild_data_directory) and not any(filename.endswith('.json') for filename in os.listdir(guild_data_directory)):
                    os.rmdir(guild_data_directory)
        else:
            embed = discord.Embed(description=f"VM tidak ditemukan untuk channel {deleted_channel.mention}.", color=discord.Color.red())
            await ctx.respond(embed=embed, delete_after=5)
    
    async def unset_leave(self, ctx, guild_data_directory):
        # Reset Leave
        leave_data_path = os.path.join(guild_data_directory, 'leave.json')
    
        try:
            os.remove(leave_data_path)
            embed = discord.Embed(description="Leave channel direset.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            await ctx.respond(embed=embed, delete_after=5)
        except FileNotFoundError:
            embed = discord.Embed(description="Leave channel untuk server ini tidak ditemukan.", color=discord.Color.red())
            await ctx.respond(embed=embed, delete_after=5)
    
        if os.path.exists(guild_data_directory):
            if not os.listdir(guild_data_directory):
                os.rmdir(guild_data_directory)
            
    async def unset_role(self, ctx, tipe: str):
      
        if tipe is None or tipe == '':
            await ctx.respond("Mohon masukkan **`tipe`**.", delete_after=5)
            return
    
        guild_data_directory = os.path.join(DATA_SERVER, ctx.guild.name)
        guild_name = str(ctx.guild.name)
        role_file_path = os.path.join(DATA_SERVER, guild_name, 'role.json')
    
        try:
            if os.path.exists(role_file_path):
                if not os.listdir(guild_data_directory):
                    os.rmdir(guild_data_directory)
                return
              
                tipe_lower = tipe.lower()
                if tipe_lower == 'bot':
                    delete_key = 'default_bot_role_id'
                elif tipe_lower == 'user':
                    delete_key = 'default_human_role_id'
                elif tipe_lower == 'all':
                    # Delete the entire file
                    os.remove(role_file_path)
                    embed = discord.Embed(description="Berhasil menghapus seluruh data role dan file.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                    await ctx.respond(embed=embed, delete_after=5)
                    return
                else:
                    await ctx.respond('Invalid role type. Gunakan "bot", "user", atau "all".', delete_after=5)
                    return
    
                with open(role_file_path, 'r') as file:
                    guild_role_data = json.load(file)
    
                if delete_key in guild_role_data:
                    del guild_role_data[delete_key]
                    with open(role_file_path, 'w') as file:
                        json.dump(guild_role_data, file, indent=4)
                    embed = discord.Embed(description="Berhasil menghapus data role {tipe}.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                    await ctx.respond(embed=embed, delete_after=5)
                else:
                    await ctx.respond(f'Tidak ada data role {tipe}.', delete_after=5)
            else:
                embed = discord.Embed(description="Tidak ada role untuk server ini.", color=discord.Color.red())
                await ctx.respond(embed=embed, delete_after=5)
        except Exception as e:
            print(f'Error deleting role data for guild {guild_name}: {e}')
            await ctx.respond(f'Gagal menghapus data role untuk {guild_name}: {e}', delete_after=5)
    
    async def unset_stats(self, ctx):
        guild = ctx.guild
    
        mod_channel = None
        for channel in ctx.guild.channels:
            if 'bot-command' in channel.name:
                mod_channel = channel
                break
        if ctx.channel != mod_channel:
            await ctx.send(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)
            return
    
        guild_name = str(guild.name)
        stats_file_path = os.path.join(DATA_SERVER, guild_name, 'stats.json')
    
        try:
            with open(stats_file_path, 'r') as file:
                server_stats = json.load(file)
    
            if str(guild.id) in server_stats:
                nama = server_stats[str(guild.id)].get('category_name')
                channel_ids = server_stats[str(guild.id)].get('channel_ids', {})
    
                if nama:
                    category = discord.utils.get(guild.categories, name=nama)
    
                    if category:
                        for channel_id in channel_ids.values():
                            channel = discord.utils.get(guild.channels, id=int(channel_id))
                            if channel:
                                await channel.delete()
    
                        await category.delete()
    
                        del server_stats[str(guild.id)]
                        DataBase.save_stats(guild_name, server_stats)
    
                        os.remove(stats_file_path)
    
                        guild_directory = os.path.join(DATA_SERVER, guild_name)
                        if not os.listdir(guild_directory) and not any(filename.endswith('.json') for filename in os.listdir(guild_directory)):
                            os.rmdir(guild_directory)
    
                        await ctx.respond(content=f'Stats dengan nama **`{nama}`** berhasil dihapus!', delete_after=5)
                    else:
                        await ctx.respond(content=f'Kategori `{nama}` tidak ditemukan.', delete_after=5)
                else:
                    await ctx.respond(content='Kategori tidak ditemukan.', delete_after=5)
    
        except FileNotFoundError:
            embed = discord.Embed(description="Tidak ada data untuk server ini.", color=discord.Color.red())
            await ctx.respond(embed=embed, delete_after=5)

    async def unset_server(self, ctx):
        data = DataBase.load_data(ctx.guild.name)
    
        if 'message_id' in data and 'channel_id' in data:
            message_id = data['message_id']
            channel_id = data['channel_id']
    
            try:
                channel_mention = self.bot.get_channel(channel_id)
                message = await channel_mention.fetch_message(message_id)
    
                # Delete the message
                await message.delete()
    
                # Revoke the invitation link
                invites = await channel_mention.invites()
                for invite in invites:
                    if invite.inviter == self.bot.user:
                        await invite.delete()
    
                # Delete the database file
                DataBase.delete_data(ctx.guild.name)
    
                embed = discord.Embed(description="Pengaturan verifikasi berhasil dihapus!", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                await ctx.respond(embed=embed, delete_after=5)
    
                # Process reactRole removal
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
            except discord.Forbidden:
                await ctx.respond("Butuh permission gan.", delete_after=5)
            except discord.NotFound:
                embed = discord.Embed(description="Pengaturan verifikasi untuk server ini tidak ditemukan.", color=discord.Color.red())
                await ctx.respond(embed=embed, delete_after=5)
        else:
            embed = discord.Embed(
                description=f"Pengaturan verifikasi untuk server ini tidak ditemukan.",
                color=discord.Color.red())
            
            await ctx.respond(embed=embed, delete_after=5)

    async def unset_nochat(self, ctx, setting: str, tipe: str, text_channel: discord.TextChannel = None):
        if not (ctx.author.guild_permissions.administrator or ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
            embed = discord.Embed(
                description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
                color=discord.Color.red())
            if hasattr(ctx, 'respond'):
                await ctx.respond(embed=embed, delete_after=5)
            else:
                await ctx.send(embed=embed, delete_after=5)
            return
    
        # Save the channel ID to the JSON database
        guild_name = str(ctx.guild.name)
        nochat_settings_path = os.path.join(DATA_SERVER, guild_name, 'nochat.json')
    
        # Load existing settings or initialize as an empty list
        try:
            with open(nochat_settings_path, 'r') as file:
                nochat_settings = json.load(file)
        except FileNotFoundError:
            nochat_settings = []
    
        if text_channel is not None:
            channel_mention = text_channel.mention
            # Check if there are settings for the specified channel and type
            filtered_settings = [s for s in nochat_settings if s['channel_id'] == text_channel.id and s['source'] == tipe]
            if filtered_settings:
                # Remove the settings for the specified channel and type
                nochat_settings = [s for s in nochat_settings if not (s['channel_id'] == text_channel.id and s['source'] == tipe)]
                # Write the updated settings back to the file
                with open(nochat_settings_path, 'w') as file:
                    json.dump(nochat_settings, file, indent=4)
                embed = discord.Embed(
                    description=f"Pengaturan **nochat** untuk **`{tipe}`** di {channel_mention} dihapus.",
                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                await ctx.respond(embed=embed, delete_after=5)
            else:
                # No settings found for the specified channel and type
                embed = discord.Embed(
                    description=f"Tidak ditemukan pengaturan nochat untuk **`{tipe}`** di {channel_mention}.",
                    color=discord.Color.red())
                await ctx.respond(embed=embed, delete_after=5)
        else:
            if setting == 'all':
                if os.path.exists(nochat_settings_path):
                    os.remove(nochat_settings_path)
                    embed = discord.Embed(description="Semua pengaturan Nochat telah dihapus.",
                                          color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                    await ctx.respond(embed=embed, delete_after=5)
                    return
            elif tipe == 'all':
                # Handle the case where setting is for all channels
                filtered_settings = [s for s in nochat_settings if s['source'] == 'all']
                if not filtered_settings:
                    embed = discord.Embed(
                        description=f"Tidak ditemukan pengaturan **nochat** untuk semua channel.",
                        color=discord.Color.red())
                    await ctx.respond(embed=embed, delete_after=5)
                    return
                else:
                    # Remove the settings for all channels
                    nochat_settings = [s for s in nochat_settings if s['source'] != 'all']
            # Write the updated settings back to the file
            with open(nochat_settings_path, 'w') as file:
                json.dump(nochat_settings, file, indent=4)
            
            # If no settings remain, delete the file
            if not nochat_settings:
                os.remove(nochat_settings_path)

    @setup_server.command(
        name="voicemaster",
        description="Mengatur voicemaster channel sementara.",
        guild_only=True,
    )
    async def voice(self, ctx: discord.ApplicationContext, voice_channel: discord.VoiceChannel = None, nama_kategori: str = 'ꑭ CHARIS ꑭ', nama_channel: str = '⸸ Voice of Hell ⸸'):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        mod_channel = None
        for channel_obj in ctx.guild.channels:
            if 'bot-command' in channel_obj.name:
                mod_channel = channel_obj
                break
        if ctx.channel != mod_channel:
            return await ctx.respond(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)
    
        guild_data_directory = os.path.join(DATA_SERVER, ctx.guild.name)
        os.makedirs(guild_data_directory, exist_ok=True)
        data_vm_path = os.path.join(guild_data_directory, 'vm.json')
        
        # If voice_channel is provided, use it directly
        if voice_channel is not None:
            category = voice_channel.category
        # If voice_channel is not provided, create a new category and voice channel
        else:
            category = await ctx.guild.create_category(name=nama_kategori)
            voice_channel = await category.create_voice_channel(name=nama_channel)
    
        # Proceed with the rest of the logic to handle setup and saving data
        channel_id = voice_channel.id
        category_id = category.id if category else None
        new_channel_data = {
            "voice_channel_id": channel_id,
            "category_id": category_id
        }
        try:
            with open(data_vm_path, 'r') as file:
                vm_data = json.load(file)
        except FileNotFoundError:
            vm_data = []
    
        # Check if the channel data already exists
        if any(entry.get("voice_channel_id") == channel_id and entry.get("category_id") == category_id for entry in vm_data):
            embed = discord.Embed(
                description=f"Channel {voice_channel.mention} sudah menjadi VM!",
                color=discord.Color.red()
            )
            return await ctx.respond(embed=embed, delete_after=5)
    
        vm_data.append(new_channel_data)
    
        with open(data_vm_path, 'w') as file:
            json.dump(vm_data, file, indent=4)
    
        embed = discord.Embed(description=f"VM diatur ke {voice_channel.mention}.\n\n- Kamu dapat memindahkan Channel VM ke dalam kategori manapun.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
        await ctx.respond(embed=embed, delete_after=15)

    @setup_server.command(
        name="role",
        description="Otomatis menambahkan role tertentu pada member yang bergabung.",
        guild_only=True,
    )
    async def role(self, ctx: discord.ApplicationContext,
                   tipe: discord.Option(str, description="Member yang ingin diatur.",
                                            choices=[discord.OptionChoice(name="Bot", value="bot"),
                                                     discord.OptionChoice(name="User", value="user") ]),
                   role: discord.Role):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        try:
            guild_role_data = await DataBase.get_guild_role_data(ctx.guild)
            if tipe == 'bot':
                guild_role_data['default_bot_role_id'] = role.id
            elif tipe == 'user':
                guild_role_data['default_human_role_id'] = role.id
            else:
                embed = discord.Embed(title="Error", description="Invalid role type. Gunakan `bot` atau `user`.", color=discord.Color.red())
                return await ctx.respond(embed=embed, delete_after=5)
        
            guild_name = str(ctx.guild.name)
            role_file_path = os.path.join(DATA_SERVER, guild_name, 'role.json')
            with open(role_file_path, 'w') as file:
                json.dump(guild_role_data, file)
        
            embed = discord.Embed(description=f"Berhasil mengatur {role.mention} sebagai role {tipe}.", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            await ctx.respond(embed=embed, delete_after=5)
        
        except Exception as e:
            guild_name = str(ctx.guild.name)  # Initialize guild_name here
            print(f'Error saving role data for guild {guild_name}: {e}')


    @pesan.command(
        name="verifikasi",
        description="Mengatur pesan verifikasi sukses untuk server.",
        guild_only=True,
    )
    async def pesan_verifikasi(self, ctx: discord.ApplicationContext, pesan: str):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        mod_channel = None
        for channel_obj in ctx.guild.channels:
            if 'bot-command' in channel_obj.name:
                mod_channel = channel_obj
                break
        if ctx.channel != mod_channel:
            return await ctx.respond(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)

        data = DataBase.load_data(ctx.guild.name)
        
        # Process the input to handle newlines properly
        pesan = pesan.replace("\\n", "\n")
        
        # Set the welcome message directly
        data['verif_message'] = pesan
        
        # Save the data
        DataBase.save_data(ctx.guild.name, data)
        
        response_channel = ctx.respond if hasattr(ctx, 'respond') and callable(ctx.respond) else ctx.send
        await response_channel(f'> Berhasil mengatur pesan verifikasi sukses.', delete_after=5)

    @stats.command(
        name="create",
        description="Membuat server stats.",
        guild_only=True,
    )
    async def stats_create(self, ctx: discord.ApplicationContext, nama_kategori: str = '📊 SERVER STATS 📊'):
            await ctx.defer()
            if isinstance(ctx.channel, discord.DMChannel):
                return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
          
            guild = ctx.guild
        
            mod_channel = None
            for channel in ctx.guild.channels:
                if 'bot-command' in channel.name:
                    mod_channel = channel
                    break
            if ctx.channel != mod_channel:
                await ctx.respond(content=f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)
                return
        
            guild_name = str(guild.name)
            stats_file_path = os.path.join(DATA_SERVER, guild_name, 'stats.json')
        
            try:
                with open(stats_file_path, 'r') as file:
                    server_stats = json.load(file)
            except FileNotFoundError:
                server_stats = {}
        
            if server_stats:
                await ctx.respond(content=f'> Stats sudah pernah diatur. `rstats` untuk menghapus stats.', delete_after=5)
                return
        
            total_members = guild.member_count
            human_members = sum(not member.bot for member in guild.members)
            bot_members = sum(member.bot for member in guild.members)
            created_at = guild.created_at.strftime('%a, %d %b %Y')
        
            category = discord.utils.get(guild.categories, name=nama_kategori)
        
            if not category:
                category = await guild.create_category(nama_kategori)
            else:
                await ctx.respond(content=f"Sudah ada kategori dengan nama {nama_kategori}.", delete_after=5)
                return
        
            server_stats = {
                str(guild.id): {
                    'total_members': total_members,
                    'human_members': human_members,
                    'bot_members': bot_members,
                    'created_at' : created_at,
                    'category_name': nama_kategori,
                    'channel_ids': {}
                }
            }
        
            DataBase.save_stats(guild_name, server_stats)
        
            await Fungsi.create_or_update_voice_channel(guild, category, 'Total', total_members, server_stats)
            await Fungsi.create_or_update_voice_channel(guild, category, 'Members', human_members, server_stats)
            await Fungsi.create_or_update_voice_channel(guild, category, 'Bots', bot_members, server_stats)
            await Fungsi.create_or_update_voice_channel(guild, category, f'{guild.name}', created_at, server_stats)
        
            await ctx.respond(content=f'Stats dibuat dengan nama **{nama_kategori}**!', delete_after=5)
    
    @stats.command(
        name='refresh',
        description="Memuat ulang statistik server.",
        guild_only=True,
    )
    async def update_stats_manually(self, ctx: discord.ApplicationContext):
        guild = ctx.guild
        
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
          
        # Validate channel "bot-command"
        mod_channel = None
        for channel in ctx.guild.channels:
            if 'bot-command' in channel.name:
                mod_channel = channel
                break
        if ctx.channel != mod_channel:
            return await ctx.respond(f'> Perintah ini hanya dapat digunakan di channel {mod_channel.mention}.', delete_after=5)
    
        await Fungsi.update_stats(guild)
        await ctx.respond(f'> Server Stats berhasil dimuat.', delete_after=5)
    
        if not self.bot.is_closed():
            Fungsi.auto_update_stats.start(self)

    # REACTION ROLE
    reaction = discord.SlashCommandGroup(
        name="reaction",
        guild_only=True,
        default_member_permissions=DEFAULT_PERMISSIONS,
    )
    @reaction.command(
      name='create',
      description="Membuat reaction role.",
      guild_only=True,
    )
    async def react(self, ctx, message_id, role: discord.Role, emoji, verifikasi=discord.Option(bool, default=False, description="Otomatis menghapus user reaction.", choices=[discord.OptionChoice(name="Ya", value=True), discord.OptionChoice(name="Bukan", value=False)])):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        message_id = str(message_id)
    
        if isinstance(emoji, discord.Emoji):
            emoji_id = emoji.id
        else:
            try:
                emoji_id = int(emoji)
            except ValueError:
                emoji_id = int(emoji.split(':')[2][:-1])
        
        emoji = self.bot.get_emoji(emoji_id)
    
        if emoji is None:
            embed = discord.Embed(
                description="Invalid emoji ID!",
                color=discord.Color.red()
            )
            return await ctx.respond(embed=embed, delete_after=5)
    
        message = await ctx.fetch_message(message_id)
    
        # Load settings
        settings = DataBase.loadSetting()
    
        # Check if the guild ID exists, if not, create it
        if guild_id not in settings:
            settings[guild_id] = {"reactRole": {}}
    
        # Check if the required keys exist, if not, create them
        if "reactRole" not in settings[guild_id]:
            settings[guild_id]["reactRole"] = {}
        if channel_id not in settings[guild_id]["reactRole"]:
            settings[guild_id]["reactRole"][channel_id] = {}
        if message_id not in settings[guild_id]["reactRole"][channel_id]:
            settings[guild_id]["reactRole"][channel_id][message_id] = {}
    
        role_id = role.id
        await message.add_reaction(emoji)
    
        # Update settings with new role reaction
        settings[guild_id]["reactRole"][channel_id][message_id][str(emoji)] = {
            "role": role_id,
            "clear_reaction": verifikasi
        }
    
        # Save updated settings
        DataBase.saveSetting(settings)
    
        embed = discord.Embed(
            description="Berhasil membuat reaction role!",
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
        )
        await ctx.respond(embed=embed, delete_after=5)

    @reaction.command(
      name='remove',
      description="Menghapus reaction role.",
      guild_only=True,
    )
    async def remove_role_reaction(self, ctx, message_id, emoji):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
    
        settings = DataBase.loadSetting()
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        message_id = str(message_id)
    
        # Check if the guild ID exists in settings
        if guild_id in settings:
            # Check if the channel ID exists in settings for the guild
            if channel_id in settings[guild_id]["reactRole"]:
                # Check if the message ID exists in settings for the channel
                if message_id in settings[guild_id]["reactRole"][channel_id]:
                    # Remove reactions for the message
                    message = await ctx.fetch_message(message_id)
                    message_reactions = settings[guild_id]["reactRole"][channel_id][message_id]
                    for reaction_emoji in message_reactions:
                        await message.remove_reaction(reaction_emoji, self.bot.user)
    
                    # Remove the message ID entry
                    settings[guild_id]["reactRole"][channel_id].pop(message_id)
    
                    # If there are no more entries for the channel, remove the channel ID entry
                    if not settings[guild_id]["reactRole"][channel_id]:
                        settings[guild_id]["reactRole"].pop(channel_id)
    
                    # If there are no more entries for the guild, remove the guild ID entry
                    if not settings[guild_id]["reactRole"]:
                        settings.pop(guild_id)
    
                    # Save the updated settings
                    DataBase.saveSetting(settings)
                    
                    embed = discord.Embed(
                    description=f"Berhasil menghapus reaction role!",
                    color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
                        
                    return await ctx.respond(embed=embed, delete_after=5)
    
        embed = discord.Embed(
        description=f"Tidak ada role reaction yang terkait dengan pesan tersebut.",
        color=discord.Color.red())
            
        await ctx.respond(embed=embed, delete_after=5)

    # MEMBUAT EMBED
    embed = discord.SlashCommandGroup(
        name="embed",
        description="Membuat/Mengedit embed.",
        guild_only=True,
        default_member_permissions=DEFAULT_PERMISSIONS,
    )
    @embed.command(
        name='owner',
        description="Hanya untuk owner bot.",
        guild_only=True,
    )
    async def owner_embed(self, ctx, pesan: str, foto: discord.Attachment = None):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
    
        bot_creator_id = (await self.bot.application_info()).owner.id
    
        if not (ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
            embed = discord.Embed(
                description=f"Hanya pemilik bot yang bisa menggunakan perintah ini!",
                color=discord.Color.red())
            return await ctx.respond(embed=embed, delete_after=10)
        
        await ctx.respond('> Berhasil!', ephemeral=True, delete_after=10)
    
        pesan = pesan.replace("\\n", "\n")  # Replace \n with new line characters
    
        # Regular expression to find emoji IDs in the message
        emoji_ids = re.findall(r'<:\w+:(\d+)>', pesan)
    
        # Retrieve emojis by ID and replace them in the message
        for emoji_id in emoji_ids:
            emoji = self.bot.get_emoji(int(emoji_id))
            if emoji:
                pesan = pesan.replace(f'<:{emoji.name}:{emoji_id}>', str(emoji))

        button1 = Button(
            emoji="<:melody:1237454974183801023>",
            label="Melody",
            url="https://discord.com/oauth2/authorize?client_id=1210056053954318416&permissions=8&scope=bot+applications.commands",
        )
        button2 = Button(
            emoji="<:vulkan:1237454940398419968>",
            label="Vulkan",
            url="https://discord.com/oauth2/authorize?client_id=1221587009433505812&permissions=8&scope=bot+applications.commands",
        )
        button3 = Button(
            emoji="<:charis:1237457208774496266>",
            label="Kreator",
            url="https://discord.com/users/982268021143896064",
        )

        # Adding buttons to the view
        view = View()
        view.add_item(button1)
        view.add_item(button2)
        view.add_item(button3)

        embed = discord.Embed(description=pesan, color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
    
        if foto:
            # Add the screenshot as an attachment to the embed
            embed.set_image(url=foto.url)
    
        for guild in self.bot.guilds:
            for guild_channel in guild.channels:
                if 'bot-command' in guild_channel.name.lower():
                    await guild_channel.send(embed=embed, view=view)

    @embed.command(
      name='create',
      description="Tulis sesuatu.",
      guild_only=True,
    )
    async def create(self, ctx, pesan: str, foto: discord.Attachment = None):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        
        if hasattr(ctx, 'respond'):
            await ctx.respond('> Berhasil!', delete_after=5)
        else:
            await ctx.send('> Berhasil!', delete_after=5)
            await ctx.message.delete()
    
        pesan = pesan.replace("\\n", "\n")  # Replace \n with new line characters
    
        # Regular expression to find emoji IDs in the message
        emoji_ids = re.findall(r'<:\w+:(\d+)>', pesan)
        
        # Retrieve emojis by ID and replace them in the message
        for emoji_id in emoji_ids:
            emoji = self.bot.get_emoji(int(emoji_id))
            if emoji:
                pesan = pesan.replace(f'<:{emoji.name}:{emoji_id}>', str(emoji))
    
        embed = discord.Embed(description=pesan, color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
        
        if foto:
            # Add the screenshot as an attachment to the embed
            embed.set_image(url=foto.url)
    
        await ctx.send(embed=embed)

    @embed.command(
      name='edit',
      description='Mengedit embed yang dikirim oleh bot.',
      guild_only=True,
    )
    async def edit_message_slash(self, ctx: discord.ApplicationContext, message_id: str, pesan: str, foto: discord.Attachment = None):
        await self.edit_message(ctx, int(message_id), pesan, foto)
    async def edit_message(self, ctx: discord.ApplicationContext, message_id: int, pesan: str, foto: discord.Attachment = None):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        
        try:
            message = await ctx.channel.fetch_message(message_id)
            if message.author == ctx.bot.user and message.embeds:
                old_embed = message.embeds[0]
                
                # Process emojis in the message
                emoji_ids = re.findall(r'<:\w+:(\d+)>', pesan)
                for emoji_id in emoji_ids:
                    emoji = self.bot.get_emoji(int(emoji_id))
                    if emoji:
                        pesan = pesan.replace(f'<:{emoji.name}:{emoji_id}>', str(emoji))
                
                new_embed = discord.Embed(description=pesan, color=old_embed.color)
                
                if foto:
                    new_embed.set_image(url=foto.url)
                await message.edit(embed=new_embed)
                
                if hasattr(ctx, 'respond'):
                    await ctx.respond('> Embed berhasil diperbarui!', delete_after=5)
                else:
                    await ctx.send('> Embed berhasil diperbarui!', delete_after=5)
                    await ctx.message.delete()
            else:
                if hasattr(ctx, 'respond'):
                    await ctx.respond('> Masukkan message ID yang valid!', delete_after=5)
                else:
                    await ctx.send('> Masukkan message ID yang valid!', delete_after=5)
                    await ctx.message.delete()
        except discord.NotFound:
            if hasattr(ctx, 'respond'):
                await ctx.respond('> Masukkan message ID yang valid!', delete_after=5)
            else:
                await ctx.send('> Masukkan message ID yang valid!', delete_after=5)
                await ctx.message.delete()
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.slash_command(
      name='purge',
      guild_only=True,
      default_member_permissions=DEFAULT_PERMISSIONS,
    )
    async def purge_messages(self, ctx, jumlah: int):
        """Menghapus semua pesan (maksimal 100)."""
        if not 1 <= jumlah <= 100:
            await ctx.respond("Masukkan angka antara 1 sampai 100.")
            return
        
        if not (ctx.author.guild_permissions.administrator or ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
            embed = discord.Embed(
                description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
                color=discord.Color.red())
            await ctx.respond(embed=embed, delete_after=5)
            return
        
        async def delete_messages():
            deleted = await ctx.channel.purge(limit=jumlah, check=lambda msg: True)
            return deleted
    
        await delete_messages()
        await ctx.respond(content=f"Menghapus {jumlah} pesan.", ephemeral=True, delete_after=10)


####################
def save_welcome_settings(guild_name):
    welcome_settings_path = os.path.join(DATA_SERVER, guild_name, 'wlc.json')

    # Create the folder and file if they don't exist
    os.makedirs(os.path.dirname(welcome_settings_path), exist_ok=True)

    # Check if welcome data is empty
    if welcome_settings.get(guild_name, {}):
        with open(welcome_settings_path, 'w') as file:
            json.dump(welcome_settings[guild_name], file, indent=4)
    else:
        # Delete the welcome data file if it's empty
        try:
            os.remove(welcome_settings_path)
        except FileNotFoundError:
            pass  # Ignore if the file is already deleted
