<h2>4対4のチーム戦を想定したレート対戦管理Discord bot</h2>

<h3>使用技術</h3>
<li>Python</li>
<li>PostgreSQL</li>
<li>レーティングシステム：TrueSkill</li>

<h3>機能</h3>
<li>Discrod idの取得からデータベースにユーザー登録(register.py)</li>
<li>参加者募集(lobby.py)</li>
<li>試合記録(match.py)</li>
<li>試合情報管理(PostgreSQL match.py)</li>
<li>試合履歴閲覧：試合数や勝率、レート変動のグラフを表示(stats.py)</li>
<li>ランキング表示(stats.py)</li>

<h3>制作背景</h3>
<li>従来サービスは、海外発の全般的に使える汎用botで、利用するには設定が必要だった</li>
<li>説明が全て英語で、日本人にとって使いづらいサービスだった</li>
<h3>制作目的</h3>
<li>対象ゲームに特化したbotにして、利便性を向上（ユーザーの操作の手間を削減）したい</li>
<li>日本語対応して、botなどの利用知識がないユーザーでも利用できるようなUI/UXを設計</li>
