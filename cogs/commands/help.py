import discord, os, json, random
from discord.ext import commands
from discord.ui import Button, View
from cogs.fungsi.func import Fungsi, bot_creator_id, owner_ids

class Help(commands.Cog, View):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.bot_creator_id = bot_creator_id
        self.owner_ids = owner_ids

    @commands.slash_command(name='help', aliases=['cmd'], description='Menampilkan daftar perintah.')
    async def help_command(self, ctx):
        await self.send_help_message(ctx, ctx.bot)
    
    @commands.command(name='help', aliases=['cmd'])
    async def help_command_prefix(self, ctx):
        await self.send_help_message(ctx, ctx.bot)
    
    async def send_help_message(self, ctx, bot):
        global bot_creator_id, owner_ids
        self.bot = ctx.bot

        # Memvalidasi kreator
        is_creator = ctx.author.id == bot_creator_id
        # Memvalidasi owner
        is_owner = ctx.author.id in owner_ids
        # Memvalidasi administrator role
        is_administrator = ctx.author.guild_permissions.administrator
        # Mengambil semua role dengan permission Administrator
        admin_roles = [role for role in ctx.guild.roles if role.permissions.administrator]
        # Mengambil mention untuk setiap role Administrator
        mention_admin_roles = [role.mention for role in admin_roles]
        # Mencari channel bot-command di server
        mod_channel = None
        for channel in ctx.guild.channels:
            if 'bot-command' in channel.name:
                mod_channel = channel
                break
        gpt_channel = None
        for channel in ctx.guild.channels:
            if 'chat-gpt' in channel.name:
                gpt_channel = channel
                break
    
        # Membuat embed
        embed = discord.Embed(
            title="DAFTAR PERINTAH",
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())),
            description=f"__Semua perintah dapat digunakan menggunakan mention atau tag {ctx.bot.user.mention}. Bug? Laporkan menggunakan **`/bug`**.__\n"
        )
    
        if is_creator or is_owner:
            embed.description += "\n"
            embed.description += f"### KREATOR & DEVELOPER\n"
            if mod_channel:
                if is_creator or is_owner:
                    embed.description += f"- **`sc`** - Mengambil sc bot.\n"
                    embed.description += f"- **`backup`** - Mengupdate data ke Github.\n"
                else:
                    embed.description += "\n"
                    embed.description += f"- **`sc`** - Mengambil sc bot.\n"
                    embed.description += f"- **`backup`** - Mengupdate data ke Github.\n"
            else:
                embed.description += "\n"
                embed.description += f"> Buat channel dengan nama `bot-command`, dan ulangi perintah `/help`.\n"
        if is_administrator:
            embed.description += "\n"
            embed.description += f"### SERVER MODERATOR\n"
            if mod_channel:
                if is_administrator:
                    embed.description += f"> Semua perintah hanya dapat dilakukan di teks channel {mod_channel.mention}, dan hanya dapat dilakukan oleh member dengan role {', '.join(mention_admin_roles)}.\n"
                    embed.description += f"\n"
                    embed.description += f"- **`/setup create`** - Untuk mengatur berbagai macam pengaturan pada bot.\n"
                else:
                    embed.description += f"\n"
                    embed.description += f"- **`/setup create`** - Untuk mengatur berbagai macam pengaturan pada bot.\n"
            else:
                embed.description += "\n"
                embed.description += f"> Buat channel dengan nama `bot-command`, dan ulangi perintah `/help`.\n"
        embed.description += f"\n"
        embed.description += f"\n"
        embed.description += f"> Request fitur? Hubungi **`/owner`**. Bayar!\n"
        embed.description += f"\n"
        embed.description += f"### UMUM\n"
        embed.description += f"- **`/prayer check`** - Untuk menampilkan jadwal shalat. Gunakan **`/prayer add`** untuk mendapatkan notifikasi otomatis.\n"
        embed.description += f"- **`/hari_besar`** - Untuk melihat 3 peringatan hari besar/hari libur yang akan datang.\n"
        embed.description += f"- **`/daftar`** - Untuk menampilkan daftar pengaturan dan stasiun radio.\n"
        embed.description += f"- **`/voice settings`** - Untuk mengatur channel sementaramu.\n"
        embed.description += f"- **`/radio`** - Untuk mengatur radio.\n"
        
        embed.set_footer(text=f"Enjoy aman {ctx.author.name}!", icon_url=ctx.author.avatar.url)
    
        # Membuat embed tambahan untuk penjelasan
        explanation_embed = discord.Embed(
            title="PENJELASAN SINGKAT",
            color=discord.Color.from_rgb(*Fungsi.hex_to_rgb(Fungsi.generate_random_color())),
            description="Berikut adalah penjelasan singkat untuk beberapa perintah:"
        )
    
        explanation_embed.description += f"\n"
        explanation_embed.description += f"- **`/voice permission private/add/hide`** - Tambahkan user, **`private`** dan **`hide`** (OPSIONAL).\n"
        explanation_embed.description += f"- AD-GPT3 hanya dapat digunakan di **{gpt_channel.mention if gpt_channel else 'chat-gpt'}**.\n"
        
        if is_administrator:
            explanation_embed.description += f"### __SERVER MODERATOR__\n"
            explanation_embed.description += f"- **`/setup create Channel: Verifikasi`** - Isi parameter **`channel`** dan **`pesan`** untuk membuat invitation link yang diperbarui setiap 3 jam. Gunakan **`/reaction create`** untuk menambahkan reaction role.\n"
            explanation_embed.description += f"-  **`/setup create Channel: Welcome`** - Isi parameter **`channel`** dan  **`pesan`** untuk mengatur channel dan pesan selamat datang ketika ada member baru. **__Format__**:\n   - `{{mention}}` untuk menyebut member yang baru bergabung.\n    - `{{server_name}}` untuk menampilkan nama server.\n    - `{{member_count}}` untuk menampilkan jumlah member.\n   - **Pesan Bawaan** : “Selamat datang di {{server_name}}, {{mention}}!\n"
            explanation_embed.description += f"-  **`/setup create Channel: Leave`** - Isi parameter **`channel`** untuk mengatur channel pesan member yang keluar.\n"
            explanation_embed.description += f"- **`/setup pesan verifikasi`** - Untuk mengatur pesan jika seseorang berhasil melakukan verifikasi role user dengan mengisi parameter **`pesan`**.\n  - Untuk membuat new line atau enter gunakan **`\\n`**. Baca: [Discord Markdown Support](https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline).\n"
            explanation_embed.description += f"- **`/setup stats create`** - Isi parameter **`nama_kategori`**, kosongi jika ingin menggunakan nama default **`📊 SERVER STATS 📊`**.\n"
            explanation_embed.description += f"- **`/setup voicemaster`**:\n - Isi parameter **`voice_channel`** menggunakan ID (Kosongi parameter lainnya).\n - Kosongi parameter **`voice_channel`** jika ingin membuat kategori sendiri.\n - Kosongi semua parameter jika ingin menggunakan nama default.\n"
            explanation_embed.description += f"### __TAMBAHAN__\n"
            explanation_embed.description += f"- Hapus semua pengaturan menggunakan **`/setup reset`**.\n"
            explanation_embed.description += f"- Buat teks channel dengan nama **{gpt_channel.mention if gpt_channel else 'chat-gpt'}** untuk menggunakan AD-GPT3.\n"
            explanation_embed.description += f"- Untuk menerima notifikasi jadwal shalat, buat kategori dengan nama yang mengandung kata **shalat** (Contoh: `NOTIFIKASI SHALAT`), atau gunakan **`/prayer category create`**, kosongi parameter **`nama_kategori`** untuk menggunakan nama default '🕌 NOTIFIKASI SHALAT 🕌'. Gunakan **`/prayer category remove`** untuk menghapusnya.\n"
    
        bot_creator = await self.bot.application_info()
        bot_creator_id = discord.User = bot_creator.owner

        avatar_url = bot_creator_id.avatar.url if bot_creator_id.avatar else bot_creator_id.default_avatar.url
        
        explanation_embed.set_footer(text=f"Regards, {bot_creator_id.name}!", icon_url=avatar_url)
        
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

        if hasattr(ctx, 'respond'):
            message = await ctx.respond(embed=embed, ephemeral=True)
        else:
            message = await ctx.send(embed=embed)
    
        # Mengirim embed kedua
        if hasattr(ctx, 'respond'):
            message = await ctx.respond(embed=explanation_embed, view=view, ephemeral=True)
        else:
            message = await ctx.send(embed=explanation_embed, view=view)
