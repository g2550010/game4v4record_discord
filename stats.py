import discord
from discord.ext import commands
from discord import app_commands
from utils import get_all_players, get_player, get_player_history
import traceback
import matplotlib.pyplot as plt
from io import BytesIO
import asyncio

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="history",
        description="（メンション対応）戦績とレート変動を表示します"
    )
    @app_commands.describe(user="戦績を見たい相手をメンション（未指定なら自分）")
    async def history(self, ctx: commands.Context, user: discord.User | None = None):
        """メンションで任意ユーザーの戦績を表示（管理者制限なし）"""
        target_user: discord.User = user or ctx.author

        # --- DBから履歴を取得 ---
        player_id = str(target_user.id)
        history = get_player_history(player_id)  # List[dict] を想定（mu_after, sigma_after, rank を含む）

        if not history:
            await ctx.send(f"{target_user.display_name} さんの履歴が見つかりません。")
            return

        # ---- 時系列を古い→新しいに整形 ----
        chronological = list(reversed(history))

        # ---- メトリクス計算 ----
        ratings = [(row["mu_after"] - 3 * row["sigma_after"]) for row in chronological]
        ranks = [row["rank"] for row in chronological]  # 0位が勝利という仕様
        match_count = len(ranks)
        wins = sum(1 for r in ranks if r == 0)
        avg_rank = sum((r + 1) for r in ranks) / match_count  # 表示は1始まり
        latest_rating = ratings[-1]

        # ---- グラフ生成 ----
        try:
            plt.figure()
            plt.plot(range(1, match_count + 1), ratings, marker="o", label="Rate")
            plt.xlabel("Match")
            plt.ylabel("Rate")
            plt.grid(True)
            plt.tight_layout()
            plt.savefig("rating.png")  # ファイル名は固定
        finally:
            plt.close()

        # ---- Embed作成 ----
        embed = discord.Embed(
            title=f"{target_user.display_name} の戦績",
            color=0x1E90FF
        )
        embed.add_field(name="試合数", value=f"{match_count} 試合", inline=True)
        embed.add_field(name="勝利数", value=f"{wins} 回", inline=True)
        embed.add_field(name="平均順位", value=f"{avg_rank:.2f} 位", inline=True)
        embed.add_field(name="最新レート", value=f"{latest_rating:.2f}", inline=True)
        embed.set_footer(text="SwitchSports Arena")

        # 画像を添付し、Embedに表示
        file = discord.File("rating.png", filename="rating.png")
        embed.set_image(url="attachment://rating.png")

        await ctx.send(embed=embed, file=file)


    @commands.hybrid_command(name="player_list", description="登録プレイヤーの一覧を表示")
    async def player_list(self, ctx):
        try:
            await ctx.defer()
            players = get_all_players()
            if not players:
                embed = discord.Embed(
                    description="エラーが発生しました",
                    color=0xFEE75C
                )
                await ctx.send("🔔 登録プレイヤーがいません。")
                return

            # 表形式のメッセージ整形
            lines = ["👥 **プレイヤー一覧** 👥"]
            lines.append("```")
            lines.append(f"{'番号':<4} | {'プレイヤー名':<20}")
            lines.append("-" * 30)

            for i, p in enumerate(players, start=1):
                member = ctx.guild.get_member(p['id'])
                name = member.display_name if member else str(p['id'])
                lines.append(f"{i:<4} | {name:<20}")

            lines.append("```")
            await ctx.send("\n".join(lines))
        except Exception:
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                    description="エラーが発生しました",
                    color=0xED4245
                )
            await ctx.send(embed=embed)




    @commands.hybrid_command(name="ranking", description="全プレイヤーのレート順位を表示")
    async def ranking(self, ctx):
        try:
            await ctx.defer()
            players = get_all_players()
            if not players:
                embed = discord.Embed(
                    description="登録プレイヤーがいません",
                    color=0xFEE75C
                )
                await ctx.send(embed=embed)
                return

            # 保守的レートでソート
            sorted_players = sorted(players, key=lambda p: p['mu'] - 3 * p['sigma'], reverse=True)

            # 表形式のメッセージ整形

            lines = []

            for i, p in enumerate(sorted_players, start=1):
                member = ctx.guild.get_member(p['id'])
                name = member.display_name if member else str(p['id'])
                conservative = round(p['mu'] - 3 * p['sigma'])

                # レートを右揃えでフォーマット
                lines.append(f"{i}.  {conservative:<6} `{name}`")


            embed = discord.Embed(
                title="ランキング",
                description="\n".join(lines),
                color=0x800080
            )
            embed.set_footer(text="SwitchSports Arena")
            await ctx.send(embed=embed)

        except Exception:
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                    description="エラーが発生しました",
                    color=0xED4245
                )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StatsCog(bot))
