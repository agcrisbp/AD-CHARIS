import json, os
from decouple import config
from openai import OpenAI

welcome_settings = {}
leave_settings = {}
nochat_settings = {}

DATA_OWNER = 'user_data/owner.csv'
DATA_SERVER = 'server_data'

api_key = config("OPENAI_API_KEY")
if api_key is None:
    print("API key not found in environment variables.")
client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")


cuaca_key = config("WeatherAPI_KEY")

class DataBase:

    def __init__(self):
        self.welcome_settings = welcome_settings
        self.leave_settings = leave_settings
        self.nochat_settings = nochat_settings
      
    # MENGATUR STATS
    @classmethod
    def save_stats(cls, guild_name, server_stats):
        os.makedirs(os.path.join(DATA_SERVER, guild_name), exist_ok=True)
    
        stats_file_path = os.path.join(DATA_SERVER, guild_name, 'stats.json')
        with open(stats_file_path, 'w') as file:
            json.dump(server_stats, file)
    
    @classmethod
    def load_data(cls, guild_name):
        file_path = os.path.join(DATA_SERVER, guild_name, 'link.json')
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        return {}
    
    @classmethod
    def save_data(cls, guild_name, data):
        file_path = os.path.join(DATA_SERVER, guild_name, 'link.json')
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
    
    @classmethod
    def delete_data(cls, guild_name):
        file_path = os.path.join(DATA_SERVER, guild_name, 'link.json')
        if os.path.exists(file_path):
            os.remove(file_path)
    
    @classmethod
    async def get_verif_message(cls, guild):
        data = DataBase.load_data(guild.name)
        return data.get('verif_message') or DEFAULT_WELCOME_MESSAGE
    
    @classmethod
    async def get_channel_id(cls, guild):
        # Fetch the saved channel ID from data
        data = DataBase.load_data(guild.name)
    
        try:
            return data.get('channel_id')
        except discord.NotFound:
            pass
    
    @classmethod
    def save_welcome_settings(cls, guild_name):
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
    
    # New function to load leave settings
    @classmethod
    def load_leave_settings(cls, guild_name):
        leave_settings_path = os.path.join(DATA_SERVER, guild_name, 'leave.json')
        if os.path.exists(leave_settings_path):
            with open(leave_settings_path, 'r') as file:
                return json.load(file)
        return {}
    
    # New function to save leave settings
    @classmethod
    def save_leave_settings(cls, guild_name, settings):
        guild_data_directory = os.path.join(DATA_SERVER, guild_name)
        os.makedirs(guild_data_directory, exist_ok=True)
    
        leave_settings_path = os.path.join(guild_data_directory, 'leave.json')
        with open(leave_settings_path, 'w') as file:
            json.dump(settings, file, indent=4)
    
    @classmethod
    def ensure_leave_file(cls, guild_name):
        leave_settings_path = os.path.join(DATA_SERVER, guild_name, 'leave.json')
        if not os.path.exists(leave_settings_path):
            with open(leave_settings_path, 'w') as file:
                json.dump({}, file)
    
    @classmethod
    def loadSetting(cls):
        if os.path.exists('server_data/react.json'):
            with open('server_data/react.json', 'r', encoding='utf-8') as f:
                setting = json.load(f)
        else:
            # If settings file doesn't exist, create an empty dictionary
            setting = {}
        return setting
    
    @classmethod
    def saveSetting(cls, data):
        with open('server_data/react.json', 'w') as f:
            json.dump(data, f, indent=4)
    
    # SET ROL UNTUK SEMUA BOT YANG BARU MASUK
    @classmethod
    async def get_guild_role_data(cls, guild):
        guild_name = str(guild.name)
        role_file_path = os.path.join(DATA_SERVER, guild_name, 'role.json')
    
        try:
            os.makedirs(os.path.join(DATA_SERVER, guild_name), exist_ok=True)
    
            if os.path.exists(role_file_path):
                with open(role_file_path, 'r') as file:
                    guild_role_data = json.load(file)
            else:
                with open(role_file_path, 'w') as file:
                    guild_role_data = {}
                    json.dump(guild_role_data, file)
    
            return guild_role_data
        except Exception as e:
            print(f'Error creating or loading role data for guild {guild_name}: {e}')
            return {}
    
    @classmethod
    async def load_role_data(cls, guild):
        guild_name = str(guild.name)
        role_file_path = os.path.join(DATA_SERVER, guild_name, 'role.json')
    
        try:
            with open(role_file_path, 'r') as file:
                guild_role_data = json.load(file)
            return guild_role_data or {}  # Return an empty dictionary if guild_role_data is None
        except FileNotFoundError:
            print(f'No role data found for guild {guild.name}.')
            return {}
        except Exception as e:
            print(f'Error loading role data for guild {guild.name}: {e}')
            return {}

    @classmethod
    def load_chat_history(cls, guild_name, user_name):
        # Create directory if it doesn't exist
        chat_directory = os.path.join(DATA_SERVER, guild_name, 'chatgpt')
        if not os.path.exists(chat_directory):
            os.makedirs(chat_directory)
    
        # Load chat history from storage
        file_path = os.path.join(chat_directory, f'{user_name}_chat_history.json')
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        else:
            return []

    @classmethod
    def save_chat_history(cls, guild_name, user_name, chat_history):
        # Create directory if it doesn't exist
        chat_directory = os.path.join(DATA_SERVER, guild_name, 'chatgpt')
        if not os.path.exists(chat_directory):
            os.makedirs(chat_directory)
    
        # Save chat history to storage
        file_path = os.path.join(chat_directory, f'{user_name}_chat_history.json')
        with open(file_path, 'w') as file:
            json.dump(chat_history, file)

    @classmethod
    def load_user_channel_names(cls):
        try:
            with open('user_data/user.json', 'r') as file:
                return json.load(file).get("user", {})
        except FileNotFoundError:
            return {}
    
    @classmethod
    def load_recent_channel_id(cls):
        try:
            with open('user_data/user.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {"temp": {}, "user": {}}
    
    @classmethod
    def save_user_channel_name(cls, user_id, display_name, default_name):
        try:
            with open('user_data/user.json', 'r') as file:
                recent_channel_id = json.load(file)
    
            if user_id not in recent_channel_id["user"]:
                recent_channel_id["user"][user_id] = default_name
    
            with open('user_data/user.json', 'w') as file:
                json.dump(recent_channel_id, file, indent=4)
    
        except FileNotFoundError:
            print("File tidak ditemukan. Pastikan file 'user.json' di folder database ada.")
    
    @classmethod
    def save_recent_channel_id(cls, recent_channel_id):
        with open('user_data/user.json', 'w') as file:
            json.dump(recent_channel_id, file, indent=4)