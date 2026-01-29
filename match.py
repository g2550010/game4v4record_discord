import discord
from discord.ext import commands
from discord.ui import View
from datetime import datetime
import asyncio
from utils import entry_order, match_patterns, get_player, upsert_player, insert_match_history, get_connection
from trueskill import TrueSkill
import traceback

# TrueSkill 初期設定
ts = TrueSkill(mu=1500.0, sigma=50.0, beta=10.0, tau=1.0)

def make_rating(mu, sigma):
    return ts.Rating(mu=mu, sigma=sigma)

def get_next_match_id():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT COALESCE(MAX(match_id), 0) + 1 FROM match_history;')
    next_id = cur.fetchone()[0]
    cur.close()
    conn.close()
    return next_id

class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.aborted = False
        

      

    @commands.hybrid_command(name="order", description="8人のプレイヤー順を指定")
    async def order(self, ctx,
        player1: discord.Member, player2: discord.Member, player3: discord.Member, player4: discord.Member,
        player5: discord.Member, player6: discord.Member, player7: discord.Member, player8: discord.Member):
        try:
            await ctx.defer()
            members = [player1, player2, player3, player4, player5, player6, player7, player8]
            
            missing_players = []
            for member in members:
                if get_player(str(member.id)) is None:
                    missing_players.append(member.display_name)

            if missing_players:
                missing_message = "、".join(missing_players) + "が未登録です。"
                embed = discord.Embed(
                    description=missing_message,
                    color=0x1E90FF
                )
                await ctx.send(embed=embed)
                return
            
            entry_order.clear()
            entry_order.extend(str(m.id) for m in members)

            msg = "**順番を設定しました** 次に `/match` で記録を開始してください。\n"
            for i, m in enumerate(members):
                msg += f"{i}. {m.display_name}\n"
            embed = discord.Embed(
                    description=msg,
                    color=0x1E90FF
                )
            await ctx.send(embed=embed)

        except Exception:
            traceback.print_exc()
            embed = discord.Embed(
                    description="❌ エラーが発生しました",
                    color=0x1E90FF
                )
            await ctx.send(embed=embed)

    

    @commands.hybrid_command(name="match", description="14試合を実行し、勝利数から順位とレートを算出")
    async def match(self, ctx):
        await ctx.defer()
        try:
            if len(entry_order) != 8:
                embed = discord.Embed(
                    description="⚠️ 先に `/order` で8人の順番を設定してください",
                    color=0x1E90FF
                )
                await ctx.send(embed=embed)
                return

            self.aborted = False
            match_id = get_next_match_id()
            win_counts = {uid: 0 for uid in entry_order}
            match_results = []
            last_message = None
            last_winner = None

            class MatchView(View):
                def __init__(self, idx):
                    super().__init__(timeout=900)
                    self.idx = idx
                    self.result = None

                @discord.ui.button(label="Aチーム勝利", style=discord.ButtonStyle.success)
                async def a_win(self, intr, btn):
                    self.result = True
                    self.stop()

                @discord.ui.button(label="Bチーム勝利", style=discord.ButtonStyle.danger)
                async def b_win(self, intr, btn):
                    self.result = False
                    self.stop()

                @discord.ui.button(label="中止", style=discord.ButtonStyle.secondary)
                async def cancel(self, intr, btn):
                    self.result = "abort"
                    self.stop()

            for i, pattern in enumerate(match_patterns):
                if self.aborted:
                    embed = discord.Embed(
                    description="🛑 マッチが中止されました",
                    color=0x1E90FF
                    )
                    await ctx.send(embed=embed)
                    return

                team1 = [entry_order[n] for n in pattern["team1"]]
                team2 = [entry_order[n] for n in pattern["team2"]]

                a_names = [ctx.guild.get_member(int(uid)).display_name if ctx.guild.get_member(int(uid)) else uid for uid in team1]
                b_names = [ctx.guild.get_member(int(uid)).display_name if ctx.guild.get_member(int(uid)) else uid for uid in team2]


                embed = discord.Embed(
                    title=f"第{i+1}試合（Match ID: {match_id}）",
                    color=0x1E90FF
                )
                embed.add_field(name="Aチーム", value=", ".join(a_names), inline=False)
                embed.add_field(name="Bチーム", value=", ".join(b_names), inline=False)

                if last_winner is not None:
                    winner_str = "Aチーム" if last_winner else "Bチーム"
                    embed.add_field(name="前回の勝者", value=winner_str, inline=True)
                
                # 各プレイヤーの勝利数を表示
                wins_text_lines = []
                for uid in entry_order:
                    player_name = ctx.guild.get_member(int(uid)).display_name if ctx.guild.get_member(int(uid)) else uid
                    wins_text_lines.append(f"{player_name}: {win_counts[uid]}勝")
                embed.add_field(name="🏆 勝利数", value="\n".join(wins_text_lines), inline=False)
                    

                view = MatchView(i)
                if i > 0 and last_message:
                    try:
                        await last_message.delete()
                    except Exception:
                        pass
                last_message = await ctx.send(embed=embed, view=view)

                try:
                    await view.wait()
                except asyncio.TimeoutError:
                    embed = discord.Embed(
                    description=f"第{i+1}試合はスキップされました。",
                    color=0x1E90FF
                    )
                    await ctx.send(embed=embed)
                    return

                if view.result == "abort":
                    self.aborted = True
                    if last_message:
                        try:
                            await last_message.delete()
                        except Exception:
                            pass
                    embed = discord.Embed(
                        description="🛑 試合記録が中止されました。",
                        color=0x1E90FF
                    )
                    await ctx.send(embed=embed)
                    return

                last_winner = view.result
                match_results.append(view.result)
                winner = pattern["team1"] if view.result else pattern["team2"]
                for idx in winner:
                    win_counts[entry_order[idx]] += 1

            if last_message:
                try:
                    await last_message.delete()
                except Exception:
                    pass

            ranks = {uid: sum(1 for w in win_counts.values() if w > win_counts[uid]) for uid in entry_order}
            ratings = [make_rating(*(float(get_player(uid)[k]) for k in ('mu', 'sigma'))) for uid in entry_order]
            rated = ts.rate([[r] for r in ratings], ranks=[ranks[uid] for uid in entry_order])

            timestamp = datetime.now()
            results = []

            for idx, uid in enumerate(entry_order):
                player = get_player(uid)
                old_mu, old_sigma = float(player['mu']), float(player['sigma'])
                new_mu, new_sigma = round(float(rated[idx][0].mu), 2), round(float(rated[idx][0].sigma), 2)
                w = win_counts[uid]

                # データベースには通常のμ, σを保存
                player['mu'], player['sigma'], player['games'], player['wins'], player['last_match'] = (
                    new_mu, new_sigma, player['games'] + 1, player['wins'] + w, timestamp
                )
                upsert_player(uid, player['mu'], player['sigma'], player['games'], player['wins'], timestamp.isoformat())
                insert_match_history(uid, match_id, timestamp.isoformat(), ranks[uid], w, old_mu, old_sigma, new_mu, new_sigma)

                # 表示用には保守的レートを計算
                old_conservative = round(old_mu - 3 * old_sigma)
                new_conservative = round(new_mu - 3 * new_sigma)

                name = ctx.guild.get_member(int(uid)).display_name if ctx.guild.get_member(int(uid)) else uid
                results.append({"name": name, "wins": w, "mu_old": old_conservative, "mu_new": new_conservative, "rank": ranks[uid]})


            # （差し替え）表形式の結果表示（Embedでコードブロックをdescriptionに収める）
            results.sort(key=lambda r: r["rank"])

            lines = []
            lines.append("```")
            lines.append(f"{'順位':<3} {'Wins':<4} {'レート':<10} プレイヤー名")
            for r in results:
                delta_mu = round(r['mu_new'] - r['mu_old'])
                mu_str = f"{r['mu_new']}({delta_mu:+})"
                lines.append(f"{r['rank']+1:<3} {r['wins']:<4} {mu_str:<10} {r['name']}")
            lines.append("```")

            result_embed = discord.Embed(
                title="🏁 試合結果",
                description="\n".join(lines),
                color=0x1E90FF
            )
            await ctx.send(embed=result_embed, reference=None)


        except Exception:
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                description="❌ エラーが発生しました。",
                color=0x1E90FF
            )
            await ctx.send(embed=embed)







    @commands.hybrid_command(name='undo', description='最新の試合を取り消します')
    async def undo(self, ctx):
        from utils import get_connection
        try:
            await ctx.defer()
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT MAX(match_id) FROM match_history;")
            latest = cur.fetchone()[0]
            if latest is None:
                await ctx.send("❌ 取り消す試合がありません。")
                cur.close(); conn.close()
                return
            cur.execute("""
                SELECT player_id, mu_before, sigma_before, wins, timestamp
                FROM match_history
                WHERE match_id = %s;
            """, (latest,))
            rows = cur.fetchall()
            undone = []
            for user_id, mu_b, sig_b, w_delta, ts_b in rows:
                cur.execute("SELECT games, wins FROM players WHERE id = %s;", (user_id,))
                games, total_wins = cur.fetchone()
                cur.execute("""
                    UPDATE players SET
                        mu = %s,
                        sigma = %s,
                        games = %s,
                        wins = %s,
                        last_match = (
                            SELECT timestamp
                            FROM match_history
                            WHERE player_id = %s AND match_id < %s
                            ORDER BY match_id DESC
                            LIMIT 1
                        )
                    WHERE id = %s;
                """, (
                    mu_b,
                    sig_b,
                    games - 1,
                    total_wins - w_delta,
                    user_id,
                    latest,
                    user_id
                ))
                undone.append(user_id)
            cur.execute("DELETE FROM match_history WHERE match_id = %s;", (latest,))
            conn.commit()
            cur.close()
            conn.close()
            names = [ctx.guild.get_member(int(uid)).display_name if ctx.guild.get_member(int(uid)) else str(uid) for uid in undone]
            await ctx.send(f"↩️ 試合 (ID: {latest}) を取り消しました\n" + "".join(names))
        
        except Exception:
            traceback.print_exc()
            await ctx.send("❌ エラーが発生しました。")


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
