import discord
from discord.ext import commands
from utils import entry_list, host_id, get_player
import traceback

class LobbyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="host", description="ホストを設定してエントリーをリセット")
    async def host(self, ctx):
        try:
            await ctx.defer()
            user_id = str(ctx.author.id)
            player = get_player(user_id)
            if not player:
                await ctx.send("❌ 未登録です。先に `/register` を実行してください。")
                return

            global host_id
            global entry_list
            host_id = user_id
            entry_list.clear()
            await ctx.send(f"✅ <@{user_id}> をホストに設定しました。エントリーをリセットしました。")
        except Exception:
            traceback.print_exc()
            await ctx.send("❌ エラーが発生しました。")

    @commands.hybrid_command(name="join", description="試合のエントリーに参加")
    async def join(self, ctx):
        try:
            await ctx.defer()
            user_id = str(ctx.author.id)
            if user_id in entry_list:
                await ctx.send("⚠️ 既にエントリー済みです。")
                return
            if len(entry_list) >= 8:
                await ctx.send("⚠️ エントリーが満員です。")
                return

            entry_list.append(user_id)
            await ctx.send(f"✅ {ctx.author.display_name} をエントリーに追加しました。現在: {len(entry_list)}/8")
        except Exception:
            traceback.print_exc()
            await ctx.send("❌ エラーが発生しました。")

    @commands.hybrid_command(name="leave", description="エントリーから離脱")
    async def leave(self, ctx):
        try:
            await ctx.defer()
            user_id = str(ctx.author.id)
            if user_id not in entry_list:
                await ctx.send("⚠️ エントリーに含まれていません。")
                return

            entry_list.remove(user_id)
            await ctx.send(f"✅ {ctx.author.display_name} をエントリーから削除しました。現在: {len(entry_list)}/8")
        except Exception:
            traceback.print_exc()
            await ctx.send("❌ エラーが発生しました。")

    @commands.hybrid_command(name="entry", description="現在のエントリーリストを表示")
    async def entry(self, ctx):
        try:
            await ctx.defer()
            if not entry_list:
                await ctx.send("🔔 現在エントリーしているプレイヤーはいません。")
                return

            lines = ["📋 現在のエントリーリスト:"]
            for i, uid in enumerate(entry_list):
                member = ctx.guild.get_member(int(uid))
                name = member.display_name if member else uid
                lines.append(f"{i+1}. {name}")
            await ctx.send("\n".join(lines))
        except Exception:
            traceback.print_exc()
            await ctx.send("❌ エラーが発生しました。")

async def setup(bot):
    await bot.add_cog(LobbyCog(bot))
