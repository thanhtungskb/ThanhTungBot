import discord
import sqlite3, uuid, os, asyncio
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

TOKEN = os.getenv("DISCORD_TOKEN")
conn = sqlite3.connect("launcher.db")
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL
)""")
c.execute("""CREATE TABLE IF NOT EXISTS tokens (
  user_id TEXT NOT NULL,
  token TEXT UNIQUE NOT NULL,
  issued_at TEXT NOT NULL
)""")
conn.commit()

ADMIN_ROLE_ID = 1392079783030165596  # thay bằng ID role admin thật

@client.event
async def on_ready():
    await tree.sync()
    print(f"bot đã online: {client.user}")

async def has_admin_role(interaction):
    if not interaction.guild:
        return False
    member = await interaction.guild.fetch_member(interaction.user.id)
    return ADMIN_ROLE_ID in [r.id for r in member.roles]

@tree.command(name="checkpoint1", description="bắt đầu quy trình lấy token")
async def checkpoint1(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    now = datetime.utcnow().isoformat()
    token = str(uuid.uuid4())
    c.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
    c.execute("INSERT INTO tokens (user_id, token, issued_at) VALUES (?, ?, ?)", (user_id, token, now))
    conn.commit()
    await interaction.response.send_message("đã ghi nhận checkpoint 1. đợi 10 giây rồi gõ /checkpoint2", ephemeral=True)
    await asyncio.sleep(10)
    await interaction.followup.send("đủ thời gian rồi, gõ /checkpoint2 đi", ephemeral=True)

@tree.command(name="checkpoint2", description="tiếp tục bước tiếp theo")
async def checkpoint2(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    c.execute("SELECT issued_at FROM tokens WHERE user_id = ?", (user_id,))
    data = c.fetchone()

    if not data:
        return await interaction.response.send_message("chưa dùng /checkpoint1", ephemeral=True)

    if not await has_admin_role(interaction):
        issued = datetime.fromisoformat(data[0])
        if datetime.utcnow() - issued < timedelta(seconds=10):
            c.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
            conn.commit()
            return await interaction.response.send_message("chưa đủ thời gian chờ. gõ lại từ đầu", ephemeral=True)

    now = datetime.utcnow().isoformat()
    c.execute("UPDATE tokens SET issued_at = ? WHERE user_id = ?", (now, user_id))
    conn.commit()
    await interaction.response.send_message("đã xong checkpoint 2. đợi 10 giây nữa rồi gõ /checkpoint3", ephemeral=True)
    await asyncio.sleep(10)
    await interaction.followup.send("đủ thời gian rồi, gõ /checkpoint3 đi", ephemeral=True)

@tree.command(name="checkpoint3", description="hoàn tất và nhận token")
async def checkpoint3(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    c.execute("SELECT token, issued_at FROM tokens WHERE user_id = ?", (user_id,))
    data = c.fetchone()

    if not data:
        return await interaction.response.send_message("chưa hoàn thành checkpoint2", ephemeral=True)

    if not await has_admin_role(interaction):
        issued = datetime.fromisoformat(data[1])
        if datetime.utcnow() - issued < timedelta(seconds=10):
            c.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
            conn.commit()
            return await interaction.response.send_message("chưa đủ thời gian. bắt đầu lại bằng /checkpoint1", ephemeral=True)

    await interaction.response.send_message("token của bạn:", ephemeral=True)
    await interaction.followup.send(f"```\n{data[0]}\n```", ephemeral=True)

@tree.command(name="quydoi", description="nhập token để lấy key")
async def quydoi(interaction: discord.Interaction, token: str):
    user_id = str(interaction.user.id)
    c.execute("SELECT user_id FROM tokens WHERE token = ?", (token,))
    match = c.fetchone()

    if not match or match[0] != user_id:
        return await interaction.response.send_message("token không hợp lệ hoặc không phải của bạn", ephemeral=True)

    c.execute("SELECT key FROM keys ORDER BY RANDOM() LIMIT 1")
    key_row = c.fetchone()
    if not key_row:
        return await interaction.response.send_message("hết key rồi", ephemeral=True)

    key = key_row[0]
    c.execute("DELETE FROM tokens WHERE token = ?", (token,))
    conn.commit()

    await interaction.response.send_message("key của bạn:", ephemeral=True)
    await interaction.followup.send(f"```\n{key}\n```", ephemeral=True)

@tree.command(name="getkey", description="admin nhận key trực tiếp")
async def getkey(interaction: discord.Interaction):
    if not await has_admin_role(interaction):
        return await interaction.response.send_message("chỉ admin mới dùng được lệnh này", ephemeral=True)

    c.execute("SELECT key FROM keys ORDER BY RANDOM() LIMIT 1")
    row = c.fetchone()
    if not row:
        return await interaction.response.send_message("hết key rồi", ephemeral=True)

    key = row[0]
    await interaction.response.send_message("key admin của bạn:", ephemeral=True)
    await interaction.followup.send(f"```\n{key}\n```", ephemeral=True)

@tree.command(name="addkey", description="thêm một key mới vào database")
async def addkey(interaction: discord.Interaction, key: str):
    if not await has_admin_role(interaction):
        return await interaction.response.send_message("chỉ admin mới dùng được lệnh này", ephemeral=True)

    try:
        c.execute("INSERT INTO keys (key) VALUES (?)", (key,))
        conn.commit()
        await interaction.response.send_message("đã thêm key mới thành công", ephemeral=True)
    except sqlite3.IntegrityError:
        await interaction.response.send_message("key đã tồn tại hoặc bị lỗi", ephemeral=True)

@tree.command(name="checkkey", description="kiểm tra số lượng key còn lại")
async def checkkey(interaction: discord.Interaction):
    if not await has_admin_role(interaction):
        return await interaction.response.send_message("chỉ admin mới dùng được lệnh này", ephemeral=True)

    c.execute("SELECT COUNT(*) FROM keys")
    count = c.fetchone()[0]
    await interaction.response.send_message(f"còn lại `{count}` key trong database", ephemeral=True)
    
@tree.command(name="getugphone", description="nhận localStorage máy trial server Hong Kong")
async def getugphone(interaction: discord.Interaction):
    import requests, json, uuid, time, random

    login_url = "https://www.ugphone.com/api/apiv1/visitor/login"
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.ugphone.com",
        "referer": "https://www.ugphone.com/toc-portal/",
        "terminal": "web",
        "lang": "en",
        "user-agent": "Mozilla/5.0"
    }

    def try_login_visitor():
        for attempt in range(3):
            try:
                res = requests.post(login_url, headers=headers, json={}, timeout=5)
                if res.status_code == 200:
                    login_json = res.json()
                    if login_json.get("code") == 200:
                        return login_json
                    elif login_json.get("code") == 500503:
                        time.sleep(2)
            except:
                time.sleep(1)
        return None

    login_json = try_login_visitor()
    if not login_json:
        return await interaction.response.send_message("❌ Hệ thống UgPhone đang bận hoặc chặn request.", ephemeral=True)

    data = login_json.get("data", {})
    if not data or "id" not in data or "token" not in data or "mqtt_info" not in data:
        return await interaction.response.send_message("❌ Không thể lấy thông tin login từ API.", ephemeral=True)

    ugid = data["id"]
    token = data["token"]
    client_id = data.get("mqtt_client_id", f"mqtt_client_{random.randint(10000000,99999999)}")

    local_data = {
        "ugPhoneLang": "en",
        "ugBrowserId": uuid.uuid4().hex,
        "UGPHONE-ID": ugid,
        "hadAgreePolicy": "true",
        "UGPHONE-Token": token,
        "UGPHONE-MQTT": json.dumps(data["mqtt_info"])
    }

    await interaction.response.send_message("✅ Đây là localStorage của bạn:", ephemeral=True)
    await interaction.followup.send(f"```json\n{json.dumps(local_data, indent=2)}\n```", ephemeral=True)

client.run(TOKEN)
