<center><img src="/public/sign.png" /></center>

<p align="center">
    <img alt='GitHub Clones' src='https://img.shields.io/badge/dynamic/json?color=success&label=Clone&query=count&url=https://gist.github.com/agcrisbp/1fbd1d6a861373cb5a15f392018ee24f/raw/clone.json&logo=github'>
    <img alt='GitHub Clones' src='https://img.shields.io/badge/dynamic/json?color=success&label=Unique&query=uniques&url=https://gist.github.com/agcrisbp/1fbd1d6a861373cb5a15f392018ee24f/raw/clone.json&logo=githubactions&logoColor=white'>
</p>

---

# About

- A messy code for an Indonesian multipurpose Discord bot, the goddess of charm, beauty, nature, human creativity, and fertility. Meet [CHARIS](https://discord.com/users/1200362228440895528) the bot.

---

# Support

<a href="https://www.buymeacoffee.com/agcrisbp" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 32px !important;width: 114px !important;" ></a>
<a href="https://saweria.co/agcrisbp" target="_blank"><img src="https://bio.aghea.biz.id/saweria-button.png" alt="Saweria" style="height: 30px !important;width: 114px !important;" ></a>
<a href="https://github.com/sponsors/agcrisbp" target="_blank"><img src="/public/sponsor-badge.svg" alt="Github Sponsor" style="height: 30px !important;width: 114px !important;" ></a>

---

# Get Started

- Clone this repo:
```
gh repo clone https://github.com/agcrisbp/AD-CHARIS
# or
git clone https://github.com/agcrisbp/AD-CHARIS
```

- Rename `.env.dev` to `.env` and fill it with yours.

- Install requirements and run the bot:
```
python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install -r requirements.txt && python3 bot.py
```

> Edit & deploy to VPS.

---

<details>
   <summary>
   
   ### Create OpenAIKey

   </summary>

- Read: [Quickstart Tutorial](https://platform.openai.com/docs/quickstart), and create the OpenAIKey in [OpenAI Platform](https://platform.openai.com/api-keys).

</details>

<details>
   <summary>
   
   ### Features

   </summary>

- Create OpenAI GPT-3 Chat/Image, Temporary Voice Channel, Server Invitation Link, Welcome & Leave Message, Reaction Role, etc. See: [mods.py](/cogs/commands/mods.py) and [umum.py](/cogs/commands/umum.py).

- Create Prayers Time Notification and its categories. See: [prayers.py](/cogs/commands/prayers.py).

- Playing radio, upload new radio, delete radio data (Bot Creator & Owner only). See: [radio.py](/cogs/commands/radio.py).

- Bot Creator & Owner only commands. See: [owners.py](/cogs/commands/owners.py).

</details>

---

# BUG?
- Sometimes, when you restart the bot, it will make the [user.json](/user_data/user.json) data get deleted (as you see right now) due to some loops.

- Found another? Please create Pull-Requests to this repo and/or report it via Issues and/or contact me through [SimpleX](https://aghea.biz.id/contact), [Email](https://aghea.biz.id/email), or [Discord](https://aghea.biz.id/discord).

---

# CREDITS?
- Radio Logo: [plus62radio-v2](https://github.com/radio-indonesia/plus62radio-v2).
- Contributor: [MbingSDK](https://github.com/MbingSDK).