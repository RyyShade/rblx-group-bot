import os
import requests
import discord
from discord import app_commands
from discord.ext import commands

ROBLOSECURITY = os.getenv("ROBLOSECURITY")
GROUP_ID = 333735931
BASE = {
    "Cookie": f".ROBLOSECURITY={ROBLOSECURITY}",
    "Content-Type": "application/json"}
def csrf():
    r = requests.post("https://auth.roblox.com/v2/logout", headers=BASE)
    return r.headers.get("x-csrf-token")
def auth():
    return {**BASE, "x-csrf-token": csrf()}
class RobloxGroup:
    def __init__(self, gid):
        self.group_id = gid
    def get_user_id(self, username):
        r = requests.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username], "excludeBannedUsers": False},
            headers=BASE)
        d = r.json().get("data")
        return d[0]["id"] if d else None
    def get_user_rank(self, user_id):
        r = requests.get(
            f"https://groups.roblox.com/v1/users/{user_id}/groups/roles",
            headers=BASE)
        for g in r.json().get("data", []):
            if g["group"]["id"] == self.group_id:
                r = g["role"]
                return r["name"], r["rank"], r["id"]
        return None, None, None
    def set_rank(self, user_id, role_name):
        rls = requests.get(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/roles",
            headers=BASE
        ).json().get("roles", [])
        role = next((x for x in rls if x["name"].lower() == role_name.lower()), None)
        if not role:
            return False, "Role not found"
        r = requests.patch(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/users/{user_id}",
            headers=auth(),
            json={"roleId": role["id"]})
        return r.ok, r.text
    def kick(self, user_id):
        r = requests.delete(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/users/{user_id}",
            headers=auth())
        return r.ok, r.text
    def get_requests(self):
        r = requests.get(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/join-requests",
            headers=BASE)
        return r.json()
    def accept(self, user_id):
        r = requests.post(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/join-requests/users/{user_id}",
            headers=auth())
        return r.ok, r.text
    def deny(self, user_id):
        r = requests.delete(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/join-requests/users/{user_id}",
            headers=auth())
        return r.ok, r.text
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
group = RobloxGroup(GROUP_ID)
@bot.event
async def on_ready():
    await bot.tree.sync()
@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, username: str):
        uid = group.get_user_id(username)
        if not uid:
            return await interaction.response.send_message("User not found.", ephemeral=True)
        ok, res = group.kick(uid)
        if ok:
            await interaction.response.send_message(f"{username} kicked.", ephemeral=True)
        else:
            await interaction.response.send_message(res, ephemeral=True)
@bot.tree.command(name="view")
async def view(interaction: discord.Interaction, username: str):
        uid = group.get_user_id(username)
        if not uid:
            return await interaction.response.send_message("User not found.", ephemeral=True)
        n, r, i = group.get_user_rank(uid)
        if not n:
            return await interaction.response.send_message(f"{username} not in group.", ephemeral=True)
        await interaction.response.send_message(f"{username}\nRank: {n}\nRankNum: {r}\nRoleID: {i}", ephemeral=True)
@bot.tree.command(name="accept")
async def accept(interaction: discord.Interaction, username: str):
        uid = group.get_user_id(username)
        if not uid:
            return await interaction.response.send_message("User not found.", ephemeral=True)
        ok, res = group.accept(uid)
        if ok:
            await interaction.response.send_message(f"Accepted {username}.", ephemeral=True)
        else:
            await interaction.response.send_message(res, ephemeral=True)
@bot.tree.command(name="deny")
async def deny(interaction: discord.Interaction, username: str):
        uid = group.get_user_id(username)
        if not uid:
            return await interaction.response.send_message("User not found.", ephemeral=True)
        ok, res = group.deny(uid)
        if ok:
            await interaction.response.send_message(f"Denied {username}.", ephemeral=True)
        else:
            await interaction.response.send_message(res, ephemeral=True)
@bot.tree.command(name="setrank")
async def setrank(interaction: discord.Interaction, username: str, role: str):
        uid = group.get_user_id(username)
        if not uid:
            return await interaction.response.send_message("User not found.", ephemeral=True)
        ok, res = group.set_rank(uid, role)
        if ok:
            await interaction.response.send_message(f"{username} ranked {role}.", ephemeral=True)
        else:
            await interaction.response.send_message(res, ephemeral=True)
@bot.tree.command(name="requests")
async def requests_cmd(interaction: discord.Interaction):
        d = group.get_requests()
        p = d.get("data", [])
        if not p:
            return await interaction.response.send_message("No requests.", ephemeral=True)
        t = "\n".join([f"{x['requester']['name']} ({x['requester']['userId']})" for x in p])
        await interaction.response.send_message(t, ephemeral=True)
async def accept_and_rank(interaction, username, role):
        uid = group.get_user_id(username)
        if not uid:
            return await interaction.response.send_message("User not found.", ephemeral=True)
        ok, res = group.accept(uid)
        if not ok:
            return await interaction.response.send_message(res, ephemeral=True)
        ok2, res2 = group.set_rank(uid, role)
        if not ok2:
            return await interaction.response.send_message(res2, ephemeral=True)
        await interaction.response.send_message(f"{username} accepted + ranked {role}", ephemeral=True)
@bot.tree.command(name="accepthelper")
async def accepthelper(interaction: discord.Interaction, username: str):
        await accept_and_rank(interaction, username, "Helper")
@bot.tree.command(name="acceptmod")
async def acceptmod(interaction: discord.Interaction, username: str):
        await accept_and_rank(interaction, username, "Moderator")
@bot.tree.command(name="acceptlbstaff")
async def acceptlbstaff(interaction: discord.Interaction, username: str):
        await accept_and_rank(interaction, username, "Leaderboard Staff")
bot.run(os.getenv("DISCORD_TOKEN"))