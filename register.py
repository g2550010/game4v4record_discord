import discord
from discord.ext import commands
from utils import get_player, upsert_player
import traceback

class RegisterCog(commands.Cog):
    """
    プレイヤー登録コマンドを提供するCog
    """
    def __init__(self, bot):
        self.bot = bot


    @commands.hybrid_command(name="register", description="自分のプレイヤー情報を登録します(/registerのみ入力)")
    async def register(self, ctx, member: discord.Member = None):
        try:
            await ctx.defer()

            # 対象ユーザー
            target = member or ctx.author
            target_id = target.id

            # 他者を登録しようとしている → 管理者かチェック
            if member and ctx.author.id != 970133347722485820:  # ← あなたのDiscordユーザーIDに置き換えてください
                embed = discord.Embed(
                        description="他のプレイヤーを登録できるのは管理者のみです",
                        color=0xED4245
                    )
                await ctx.send(embed=embed)
                return

            player = get_player(target_id)
            if player:
                embed = discord.Embed(
                        description=f"{target.display_name} は既に登録済みです。μ={player['mu']:.2f}, σ={player['sigma']:.2f}",
                        color=0xFEE75C
                    )
                await ctx.send(embed=embed)
                return

            upsert_player(
                player_id=target_id,
                mu=1500.0,
                sigma=50.0,
                games=0,
                wins=0,
                last_match=None
            )
            embed = discord.Embed(
                        description=f"{target.display_name} の登録が完了しました！μ=1500.0, σ=50.0",
                        color=0x57F287
                    )
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
    await bot.add_cog(RegisterCog(bot))
