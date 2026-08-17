# Roblox group bot for me
# Author: Cadem

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
def get_csrf():
    r = requests.post("https://auth.roblox.com/v2/logout", headers=BASE)
    return r.headers.get("x-csrf-token")
def auth_headers():
    return {**BASE, "x-csrf-token": get_csrf()}
class RobloxGroup:
    def __init__(self, group_id):
        self.group_id = group_id
    def get_user_id(self, username):
        r = requests.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username], "excludeBannedUsers": False},
            headers=BASE)
        data = r.json()
        if not data["data"]:
            return None
        return data["data"][0]["id"]
    def get_roles(self):
        r = requests.get(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/roles",
            headers=BASE)
        return r.json().get("roles", [])
    def get_user_rank(self, user_id):
        r = requests.get(
            f"https://groups.roblox.com/v1/users/{user_id}/groups/roles",
            headers=BASE)
        for g in r.json().get("data", []):
            if g["group"]["id"] == self.group_id:
                return g["role"]["name"], g["role"]["rank"], g["role"]["id"]
        return None, None, None
    def set_rank(self, user_id, role_name):
        roles = self.get_roles()
        role = next((r for r in roles if r["name"].lower() == role_name.lower()), None)
        if not role:
            return False, "Role not found"
        r = requests.patch(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/users/{user_id}",
            headers=auth_headers(),
            json={"roleId": role["id"]})
        return r.status_code == 200, r.text
    def kick(self, user_id):
        r = requests.delete(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/users/{user_id}",
            headers=auth_headers())
        return r.status_code == 200, r.text
    def get_requests(self, cursor=None):
        r = requests.get(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/join-requests",
            headers=BASE,
            params={"cursor": cursor} if cursor else None)
        return r.json()
    def accept(self, user_id):
        r = requests.post(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/join-requests/users/{user_id}",
            headers=auth_headers())
        return r.status_code == 200, r.text
    def deny(self, user_id):
        r = requests.delete(
            f"https://groups.roblox.com/v1/groups/{self.group_id}/join-requests/users/{user_id}",
            headers=auth_headers())
        return r.status_code == 200, r.text
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
group = RobloxGroup(GROUP_ID)
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")
@bot.tree.command(name="kick", description="Kick a user from the Roblox group")
async def kick(interaction: discord.Interaction, username: str):
    user_id = group.get_user_id(username)
    if not user_id:
        return await interaction.response.send_message(
            "User not found.",
            ephemeral=True)
    ok, res = group.kick(user_id)
    if ok:
        await interaction.response.send_message(
            f"{username} has been kicked.",
            ephemeral=True)
    else:
        await interaction.response.send_message(
            f"Failed to kick {username}.\nRoblox says: {res}",
            ephemeral=True)
@bot.tree.command(name="view", description="View a user's rank in the Roblox group")
async def view(interaction: discord.Interaction, username: str):
    user_id = group.get_user_id(username)
    if not user_id:
        return await interaction.response.send_message(
            "User not found.",
            ephemeral=True)
    role_name, rank_num, role_id = group.get_user_rank(user_id)
    if role_name is None:
        return await interaction.response.send_message(
            f"{username} is not in the group.",
            ephemeral=True)
    await interaction.response.send_message(
        f"User: {username}\nRank: {role_name}\nRankNum: {rank_num}\nRoleID: {role_id}",
        ephemeral=True)
@bot.tree.command(name="accept", description="Accept a user's join request")
async def accept(interaction: discord.Interaction, username: str):
    user_id = group.get_user_id(username)
    if not user_id:
        return await interaction.response.send_message(
            "User not found.",
            ephemeral=True)
    ok, res = group.accept(user_id)
    if ok:
        await interaction.response.send_message(
            f"Accepted {username}.",
            ephemeral=True)
    else:
        await interaction.response.send_message(
            f"Failed to accept {username}.\nRoblox says: {res}",
            ephemeral=True)
@bot.tree.command(name="deny", description="Deny a user's join request")
async def deny(interaction: discord.Interaction, username: str):
    user_id = group.get_user_id(username)
    if not user_id:
        return await interaction.response.send_message(
            "User not found.",
            ephemeral=True)
    ok, res = group.deny(user_id)
    if ok:
        await interaction.response.send_message(
            f"Denied {username}.",
            ephemeral=True)
    else:
        await interaction.response.send_message(
            f"Failed to deny {username}.\nRoblox says: {res}",
            ephemeral=True)
@bot.tree.command(name="setrank", description="Set a user's rank in the Roblox group")
async def setrank(interaction: discord.Interaction, username: str, role: str):
    user_id = group.get_user_id(username)
    if not user_id:
        return await interaction.response.send_message(
            "User not found.",
            ephemeral=True)
    ok, res = group.set_rank(user_id, role)
    if ok:
        await interaction.response.send_message(
            f"Set {username} to {role}.",
            ephemeral=True)
    else:
        await interaction.response.send_message(
            f"Failed to set rank.\nRoblox says: {res}",
            ephemeral=True)
@bot.tree.command(name="requests", description="View Roblox join requests")
async def requests_cmd(interaction: discord.Interaction):
    data = group.get_requests()
    page = data.get("data", [])
    cursor = data.get("nextPageCursor")
    if not page:
        return await interaction.response.send_message(
            "No pending join requests.",
            ephemeral=True)
    text = "\n".join([f"{r['requester']['name']} ({r['requester']['userId']})" for r in page])
    await interaction.response.send_message(
        f"Join Requests:\n{text}\nCursor: {cursor}",
        ephemeral=True)
async def accept_and_rank(interaction, username, role_name):
    user_id = group.get_user_id(username)
    if not user_id:
        return await interaction.response.send_message(
            "User not found.",
            ephemeral=True)
    ok, res = group.accept(user_id)
    if not ok:
        return await interaction.response.send_message(
            f"Failed to accept {username}.\nRoblox says: {res}",
            ephemeral=True)
    ok2, res2 = group.set_rank(user_id, role_name)
    if not ok2:
        return await interaction.response.send_message(
            f"Accepted {username}, but failed to rank.\nRoblox says: {res2}",
            ephemeral=True)
    await interaction.response.send_message(
        f"{username} accepted + ranked {role_name}",
        ephemeral=True)
@bot.tree.command(name="accepthelper", description="Accept + rank Helper")
async def accepthelper(interaction: discord.Interaction, username: str):
    await accept_and_rank(interaction, username, "Helper")
@bot.tree.command(name="acceptmod", description="Accept + rank Moderator")
async def acceptmod(interaction: discord.Interaction, username: str):
    await accept_and_rank(interaction, username, "Moderator")
@bot.tree.command(name="acceptlbstaff", description="Accept + rank Leaderboard Staff")
async def acceptlbstaff(interaction: discord.Interaction, username: str):
    await accept_and_rank(interaction, username, "Leaderboard Staff")
bot.run(os.getenv("DISCORD_TOKEN"))