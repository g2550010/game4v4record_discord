import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# .env から環境変数を読み込む
load_dotenv()

# DB接続設定
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER', 'postgres'),
}

def get_connection():
    """
    新しいデータベース接続を返す
    """
    return psycopg2.connect(**DB_CONFIG)


def get_player(player_id: int) -> dict:
    """
    指定した player_id の情報を players テーブルから取得して辞書で返す。
    レコードがなければ None。
    """
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, mu, sigma, games, wins, last_match
            FROM players
            WHERE id = %s
            """,
            (player_id,)
        )
        player = cur.fetchone()
    conn.close()
    return player


def upsert_player(player_id: int, mu: float, sigma: float, games: int, wins: int, last_match: str):
    """
    players テーブルにレコードを挿入、
    既存なら mu, sigma, games, wins, last_match を更新する
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO players (id, mu, sigma, games, wins, last_match)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                mu = EXCLUDED.mu,
                sigma = EXCLUDED.sigma,
                games = EXCLUDED.games,
                wins = EXCLUDED.wins,
                last_match = EXCLUDED.last_match
            """,
            (player_id, mu, sigma, games, wins, last_match)
        )
    conn.commit()
    conn.close()


def insert_match_history(
    player_id: int,
    match_id: int,
    timestamp: str,
    rank: int,
    wins: int,
    mu_before: float,
    sigma_before: float,
    mu_after: float,
    sigma_after: float
):
    """
    match_history テーブルに履歴レコードを追加する
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO match_history (
                player_id, match_id, timestamp, rank, wins,
                mu_before, sigma_before, mu_after, sigma_after
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (player_id, match_id, timestamp, rank, wins, mu_before, sigma_before, mu_after, sigma_after)
        )
    conn.commit()
    conn.close()


def get_all_players() -> list:
    """
    players テーブルの全プレイヤー情報を辞書リストで返す
    """
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, mu, sigma, games, wins, last_match FROM players")
        players = cur.fetchall()
    conn.close()
    return players


def get_player_history(player_id: int) -> list:
    """
    指定した player_id の試合履歴を timestamp 降順で返す
    """
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, player_id, match_id, timestamp, rank, wins,
                   mu_before, sigma_before, mu_after, sigma_after
            FROM match_history
            WHERE player_id = %s
            ORDER BY timestamp DESC
            """,
            (player_id,)
        )
        history = cur.fetchall()
    conn.close()
    return history


# ロビー用グローバル変数
entry_list = []  # 現在のエントリー順（Discord IDのリスト）
host_id = None   # 現在のホストのDiscord ID

# 試合エントリー順（ホスト＋参加者の順）
entry_order = []  # 試合実行時にセットされる（例: [host_id, ...]）

# 手動定義の試合パターン（インデックスベース）
match_patterns = [
    {"team1": [0, 1, 2, 3], "team2": [4, 5, 6, 7]},
    {"team1": [0, 2, 4, 6], "team2": [1, 3, 5, 7]},
    {"team1": [0, 3, 4, 7], "team2": [1, 2, 5, 6]},
    {"team1": [0, 1, 6, 7], "team2": [2, 3, 4, 5]},
    {"team1": [0, 2, 5, 7], "team2": [1, 3, 4, 6]},
    {"team1": [0, 1, 4, 5], "team2": [2, 3, 6, 7]},
    {"team1": [0, 3, 5, 6], "team2": [1, 2, 4, 7]},
    {"team1": [0, 1, 2, 4], "team2": [3, 5, 6, 7]},
    {"team1": [0, 3, 4, 6], "team2": [1, 2, 5, 7]},
    {"team1": [0, 1, 3, 7], "team2": [2, 4, 5, 6]},
    {"team1": [0, 2, 3, 5], "team2": [1, 4, 6, 7]},
    {"team1": [0, 2, 6, 7], "team2": [1, 3, 4, 5]},
    {"team1": [0, 1, 5, 6], "team2": [2, 3, 4, 7]},
    {"team1": [0, 4, 5, 7], "team2": [1, 2, 3, 6]},
]
