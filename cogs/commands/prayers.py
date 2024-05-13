import discord, pytz, requests, time, aiohttp, asyncio, os, random
from discord.ext import commands
from datetime import datetime
from cogs.fungsi.database import DataBase, DATA_SERVER
from cogs.fungsi.func import Fungsi, bot_creator_id, owner_ids

DEFAULT_PERMISSIONS = discord.Permissions()
DEFAULT_PERMISSIONS.administrator = True

class Prayers(discord.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.bot_creator_id = bot_creator_id
        self.owner_ids = owner_ids
    
    prayer = discord.SlashCommandGroup(
        name="prayer",
        description="Menampilkan/mengatur jadwal shalat.",
    )
    category = prayer.create_subgroup(
        name="category",
        guild_only=True,
        default_member_permissions=DEFAULT_PERMISSIONS,
    )
    @prayer.command(
        name="check",
        description="Menampilkan jadwal shalat berdasarkan kota yang dipilih.",
    )
    async def cek_shalat(self, ctx: discord.ApplicationContext, kota: str):
        await ctx.defer()

        current_date = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y")
        timings = await Fungsi.get_prayer_times_by_city(kota, current_date)
        if timings:
            timezone = timings.get('timezone', 'Unknown')
            
            # Map English prayer names to Indonesian counterparts
            prayer_names = {
                "Imsak": "Imsak",
                "Fajr": "Subuh",
                "Dhuhr": "Dzuhur",
                "Asr": "Ashar",
                "Maghrib": "Maghrib",
                "Isha": "Isya"
            }
    
            embed = discord.Embed(title=f"Jadwal Shalat Daerah {kota.title()} dan Sekitarnya!", description=f"{current_date}", color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())))
            for prayer, time in timings.items():
                if prayer in prayer_names:
                    prayer_name = prayer_names[prayer]
                    embed.add_field(name=f"{prayer_name}", value=f"Pukul {time} {timezone}", inline=False)
            embed.set_footer(text="Powered by Aladhan API")
    
            await ctx.respond(content="", embed=embed, delete_after=60)
        else:
            await ctx.respond(content="Maaf, kota yang Anda masukkan bukan di Indonesia atau tidak tersedia.", delete_after=5)
    
    @category.command(
        name="create",
        description="Membuat kategori untuk notifikasi shalat.",
        guild_only=True,
    )
    async def buat_kategori(self, ctx, *, nama_kategori: str = '🕌 NOTIFIKASI SHALAT 🕌'):
        await ctx.defer()
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
        
        if not (ctx.author.guild_permissions.administrator or ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
            embed = discord.Embed(
            description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
            color=discord.Color.red())
                
            return await ctx.respond(embed=embed, delete_after=5)
        
        existing_categories = [category for category in ctx.guild.categories if 'shalat' in category.name.lower()]
        
        if existing_categories:
            existing_category_names = ", ".join(category.name for category in existing_categories)
            embed = discord.Embed(
                title="Gagal!",
                description=f"Sudah ada kategori notifikasi shalat dengan nama {existing_category_names}.",
                color=discord.Color.red()
            )
            
            await ctx.respond(content="", embed=embed, delete_after=15)
            return
    
        category = await ctx.guild.create_category(nama_kategori)
    
        embed = discord.Embed(
            title="Berhasil!",
            description=f"Kategori notifikasi shalat dibuat dengan nama {nama_kategori}.",
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
        )
        embed.set_footer(text="Jika kotamu tidak tersedia, laporkan menggunakan /bug agar owner membuatnya.")
    
        await ctx.respond(content="", embed=embed, delete_after=10)

    @category.command(
        name='remove',
        description='Menghapus kategori notifikasi shalat dan semua channel di dalamnya.',
        guild_only=True,
    )
    async def delkategori(self, ctx):
        await ctx.defer()
    
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa menggunakan perintah ini di DM!", delete_after=10)
            
        if not (ctx.author.guild_permissions.administrator or ctx.author.id == bot_creator_id or ctx.author.id in owner_ids):
            embed = discord.Embed(
            description=f"Kamu tidak memiliki otoritas untuk melakukan perintah ini!",
            color=discord.Color.red())
                
            return await ctx.respond(embed=embed, delete_after=5)
    
        for category in ctx.guild.categories:
            if 'shalat' in category.name.lower():
                while category.channels:
                    for channel in category.channels:
                        await channel.delete()
                    if not category.channels:
                        await category.delete()
    
                guild_data_directory = os.path.join(DATA_SERVER, str(ctx.guild.name))
                guild_pilih_kota_path = os.path.join(guild_data_directory, 'pilih_kota.txt')
                if os.path.exists(guild_pilih_kota_path):
                    os.remove(guild_pilih_kota_path)
    
                embed_description = f'Kategori {category.name} berhasil dihapus.'
                embed_color = discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
                break
        else:
            embed_description = 'Kategori notifikasi shalat tidak ditemukan.'
            embed_color = discord.Color.red()
    
        embed = discord.Embed(
            title='Berhasil!' if 'shalat' in category.name.lower() else 'Gagal!',
            description=embed_description,
            color=embed_color
        )
        await ctx.respond(content='', embed=embed, delete_after=5)

    @prayer.command(
      name='add',
      description='Mengatur role kota untuk mendapatkan notifikasi jadwal shalat.',
    )
    async def set_kota_slash(self, ctx: discord.ApplicationContext, kota: discord.Option(str, description="Pilih kota kamu.", choices=[discord.OptionChoice(name="Banda Aceh", value="Aceh"), discord.OptionChoice(name="Bali", value="Bali"), discord.OptionChoice(name="Balikpapan", value="Balikpapan"), discord.OptionChoice(name="Belitung", value="Belitung"), discord.OptionChoice(name="Enrekang", value="Enrekang"), discord.OptionChoice(name="DKI Jakarta", value="Jakarta"), discord.OptionChoice(name="Jayapura", value="Jayapura"),discord.OptionChoice(name="Kota Parepare", value="Parepare"), discord.OptionChoice(name="Makassar", value="Makassar"), discord.OptionChoice(name="Pontianak", value="Pontianak"), discord.OptionChoice(name="Sidoarjo", value="Sidoarjo"), discord.OptionChoice(name="Surabaya", value="Surabaya"), discord.OptionChoice(name="D.I. Yogyakarta", value="Yogyakarta")])):
        await self.set_kota(ctx, kota)
    async def set_kota(self, ctx, kota: str):
        await ctx.defer()
    
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa mengatur pengaturan ini di DM!", delete_after=10)
        
        shalat_category = None
        for category in ctx.guild.categories:
            if 'shalat' in category.name.lower():
                shalat_category = category
                break
    
        if not shalat_category:
            embed = discord.Embed(
                title='Gagal!',
                description=f'Hubungi moderator server ini untuk membuat kategori notifikasi shalat.',
                color=discord.Color.red()
            )
            message = await ctx.respond(embed=embed, delete_after=5) if hasattr(ctx, 'respond') else await ctx.send(embed=embed, delete_after=5)
            return
        
        kota = kota.title()  # Convert input to title case
        
        nama_kota = Fungsi.kota_mapping[kota]
        
        # Check if the user already has a city role
        for role in ctx.author.roles:
            if role.name in Fungsi.kota_mapping.values():
                embed = discord.Embed(
                    description=f'Kamu sudah memilih kota **{role.name}**.',
                    color=discord.Color.red()
                )
                message = await ctx.respond(embed=embed, delete_after=5) if hasattr(ctx, 'respond') else await ctx.send(embed=embed, delete_after=5)
                return
    
        # Check if the role already exists
        role_kota = discord.utils.get(ctx.guild.roles, name=nama_kota)
    
        # If the role doesn't exist, create it
        if not role_kota:
            role_kota = await ctx.guild.create_role(name=nama_kota)
    
        # Add the role to the member
        await ctx.author.add_roles(role_kota)
        embed = discord.Embed(
            title='Berhasil!',
            description=f'Kota kamu diatur menjadi **{nama_kota}**.',
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
        )
        message = await ctx.respond(embed=embed, delete_after=5) if hasattr(ctx, 'respond') else await ctx.send(embed=embed, delete_after=5)
    
    @prayer.command(
        name='delete',
        description='Menghapus role kota.',
    )
    async def del_kota(self, ctx: discord.ApplicationContext):
        await ctx.defer()
    
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.respond("Kamu tidak bisa mengatur pengaturan ini di DM!", delete_after=10)
        
        role_to_delete = None
        for role in ctx.author.roles:
            if role.name in Fungsi.kota_mapping.values():
                # Remove the role from the user
                await ctx.author.remove_roles(role)
                
                # Check if any member still has this role
                members_with_role = sum(1 for member in ctx.guild.members if role in member.roles)
                if members_with_role == 0:
                    # If no member has this role, mark it for deletion
                    role_to_delete = role
                break
        
        if role_to_delete:
            # Delete the role
            await role_to_delete.delete()
            embed = discord.Embed(
                title='Berhasil!',
                description=f'Role kota berhasil dihapus.',
                color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color()))
            )
        else:
            embed = discord.Embed(
                description=f'Kamu belum memilih kota.',
                color=discord.Color.red()
            )
    
        if hasattr(ctx, 'respond'):
            message = await ctx.respond(embed=embed, delete_after=5)
        else:
            message = await ctx.send(embed=embed, delete_after=5)
