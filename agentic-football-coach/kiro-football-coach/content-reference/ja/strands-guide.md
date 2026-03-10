# Strands Agents SDKガイド

Strands Agents SDKを使用したフットボールエージェント構築の包括的リファレンス。23のコアコンセプト、サンプルエージェント構造、強化パターン、デプロイメントをカバーします。

## エージェントアーキテクチャ概要

各チームは5人のプレイヤーを持ち、各プレイヤーがエージェントです。エージェントは毎ティック（60回/秒）ゲーム状態を受信し、500ms以内にアクションを返す必要があります。

```
ゲーム状態 (JSON) → エージェント → プレイヤーアクション (JSON)
```

---

## 23のコアコンセプト

### 1. 構造化出力（Structured Output）

Pydanticモデルを使用して、生テキストの代わりにバリデーション済みの型安全なゲームコマンドを返します。

```python
from pydantic import BaseModel, Field
from strands import Agent

class FootballAction(BaseModel):
    commandType: str = Field(description="Action type: MOVE_TO, SHOOT, PASS, etc.")
    playerId: int = Field(description="Player ID performing the action")
    parameters: dict = Field(description="Action parameters")
    duration: int = Field(default=0, description="How long action persists")

agent = Agent(system_prompt="You are a football player. Analyze game state and return ONE action.")
result = agent("Ball at (10,5), I'm at (0,0). What should I do?", structured_output_model=FootballAction)
action: FootballAction = result.structured_output
```

### 2. カスタムツール（Custom Tools）

エージェントが呼び出せる戦術分析関数を提供するツール：

```python
from strands import Agent, tool
import math

@tool
def calculate_distance(pos1: dict, pos2: dict) -> float:
    """Calculate distance between two positions."""
    return math.sqrt((pos1['x'] - pos2['x'])**2 + (pos1['y'] - pos2['y'])**2)

@tool
def should_shoot(player_x: float, goal_x: float) -> dict:
    """Determine if player should shoot based on distance to goal."""
    distance = abs(player_x - goal_x)
    return {'should_shoot': distance < 30, 'recommended_power': max(0.5, min(1.0, 1.0 - distance/100))}

agent = Agent(tools=[calculate_distance, should_shoot], system_prompt="You are a football player agent.")
```

### 3. モデルプロバイダー（Model Providers）

モデルを簡単に切り替え：

```python
from strands.models import BedrockModel

model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")  # 高速、コスト効率的
# model = BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0")  # より高性能
agent = Agent(model=model, tools=[calculate_distance, should_shoot])
```

### 4. オブザーバビリティ（Observability）

メトリクス、トークン、レイテンシ、ツール使用状況を追跡：

```python
result = agent("What should I do?")
summary = result.metrics.get_summary()
# summary['accumulated_usage']['totalTokens']
# summary['accumulated_metrics']['latencyMs']
# summary['tool_usage']
```

`result.traces`で推論サイクルごとの詳細トレースが利用可能。

### 5. フック（Hooks）

ライフサイクルポイントでエージェントの動作を監視・変更：

```python
from strands.hooks import HookProvider, HookRegistry, BeforeToolCallEvent, AfterToolCallEvent

class FootballMonitoringHook(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.log_tool_start)
        registry.add_callback(AfterToolCallEvent, self.log_tool_end)
    def log_tool_start(self, event): print(f"Calling: {event.tool_use['name']}")
    def log_tool_end(self, event): print(f"Result: {event.result}")

agent = Agent(tools=[...], hooks=[FootballMonitoringHook()])
```

上級：`LimitToolCalls`フックで1回の呼び出しあたりのツール呼び出し回数を制限。

### 6. ガードレール（Guardrails）

Bedrock Guardrailsによるコンテンツフィルタリングと安全性：

```python
model = BedrockModel(
    model_id="us.amazon.nova-micro-v1:0",
    guardrail_id="your-guardrail-id", guardrail_version="1", guardrail_trace="enabled"
)
agent = Agent(model=model)
result = agent("Some prompt")
if result.stop_reason == "guardrail_intervened":
    print("Content blocked by guardrails")
```

### 7. ダイレクトツール呼び出し（Direct Tool Invocation）

LLM推論なしでプログラム的にツールを呼び出し：

```python
distance = agent.tool.calculate_distance(pos1={"x": 0, "y": 0}, pos2={"x": 10, "y": 5})
```

### 8. コミュニティツール（Community Tools）

`strands-agents-tools`からの構築済みツール：

```python
from strands_tools import calculator, python_repl
agent = Agent(tools=[calculator, python_repl], system_prompt="You are a football analyst.")
```

便利なコミュニティツール：`calculator`、`python_repl`、`current_time`。

### 9. 会話管理（Conversation Management）

メッセージ履歴を制御する3つの組み込みマネージャー：

```python
from strands.agent.conversation_manager import (
    NullConversationManager,           # トリミングなし
    SlidingWindowConversationManager,   # 直近N件のメッセージを保持
    SummarizingConversationManager,     # 古いメッセージを要約
)

# デフォルト：スライディングウィンドウ
agent = Agent(conversation_manager=SlidingWindowConversationManager(window_size=10))

# フットボール用：通常はティックごとにステートレス（毎回新しいエージェント）
agent = Agent()  # 新しいエージェント = フレッシュスタート
```

### 10. エージェント状態管理（Agent State Management）

呼び出し間のキーバリューストレージ（モデルには送信されない）：

```python
from strands import tool, ToolContext

@tool(context=True)
def track_opponent(opponent_id: int, tendency: str, tool_context: ToolContext) -> str:
    """Record an opponent's tendency."""
    tendencies = tool_context.agent.state.get("opponent_tendencies") or {}
    tendencies[str(opponent_id)] = tendency
    tool_context.agent.state.set("opponent_tendencies", tendencies)
    return f"Recorded: player {opponent_id} → {tendency}"

agent = Agent(tools=[track_opponent], state={"opponent_tendencies": {}, "match_minute": 0})
```

### 11. セッション管理（Session Management）

エージェント再起動間で状態と会話履歴を永続化：

```python
from strands.session.file_session_manager import FileSessionManager

session_manager = FileSessionManager(session_id="team-alpha-session", storage_dir="./sessions")
agent = Agent(session_manager=session_manager, state={"opponent_patterns": {}})
```

クラウドデプロイメントには`S3SessionManager`を使用。

### 12. リトライ戦略（Retry Strategies）

高頻度ゲームティック中のモデルスロットリング処理：

```python
from strands import ModelRetryStrategy
agent = Agent(retry_strategy=ModelRetryStrategy(max_attempts=3, initial_delay=2, max_delay=60))
# または最低レイテンシのためにリトライを無効化：
agent = Agent(retry_strategy=None)
```

### 13. ストリーミング（Streaming）

エージェントの判断をリアルタイムで監視：

```python
async for event in agent.stream_async("Ball at (30,10), should I shoot?"):
    if "data" in event: print(event["data"], end="")
    elif "current_tool_use" in event and event["current_tool_use"].get("name"):
        print(f"Using tool: {event['current_tool_use']['name']}")
```

### 14. クラスベースツール（Class-Based Tools）

クラスを使用して関連ツール間で状態を共有：

```python
class MatchAnalytics:
    def __init__(self):
        self.shots_taken = 0
    @tool
    def record_shot(self, result: str) -> str:
        """Record a shot attempt."""
        self.shots_taken += 1
        return f"Shot #{self.shots_taken}: {result}"

analytics = MatchAnalytics()
agent = Agent(tools=[analytics.record_shot])
```

### 15. MCPツール（MCP Tools）

Model Context Protocolを介して外部ツールサーバーに接続：

```python
from strands.tools.mcp import MCPClient
mcp_client = MCPClient(lambda: sse_client("http://localhost:8000/sse"))
with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
```

### 16. マルチエージェント — ツールとしてのエージェント（Agents as Tools）

スペシャリストエージェントをオーケストレーター用のツールとしてラップ：

```python
@tool
def defensive_analyst(game_state: str) -> str:
    """Analyze defensive positioning."""
    analyst = Agent(system_prompt="You are a defensive football analyst.")
    return str(analyst(game_state))

coach = Agent(tools=[defensive_analyst, offensive_strategist],
    system_prompt="You are the head coach. Route to the right specialist.")
```

### 17. マルチエージェント — スウォーム（Swarm）

タスクを自律的に引き継ぐ協調エージェント：

```python
from strands.multiagent import Swarm
scout = Agent(name="scout", system_prompt="Analyze opponent weaknesses.")
tactician = Agent(name="tactician", system_prompt="Design game plans.")
coach = Agent(name="coach", system_prompt="Finalize tactics.")
swarm = Swarm([scout, tactician, coach], entry_point=scout, max_handoffs=10)
result = swarm("Prepare a game plan against a 4-4-2 high-pressing team")
```

### 18. マルチエージェント — グラフ（Graph）

定義された実行順序を持つ構造化パイプライン：

```python
from strands.multiagent import GraphBuilder
builder = GraphBuilder()
builder.add_node(analyzer, "analyze")
builder.add_node(planner, "plan")
builder.add_node(executor, "execute")
builder.add_edge("analyze", "plan")
builder.add_edge("plan", "execute")
builder.set_entry_point("analyze")
graph = builder.build()
result = graph("Possession in midfield, 1-1, 80th minute")
```

### 19. インタラプト（Interrupts） — ヒューマンインザループ

人間の入力のために実行を一時停止（例：コーチング判断）：

```python
class SubstitutionApproval(HookProvider):
    def approve(self, event: BeforeToolCallEvent) -> None:
        if event.tool_use["name"] != "substitute_player": return
        approval = event.interrupt("coach-approval", reason={...})
        if approval.lower() != "y":
            event.cancel_tool = "Coach rejected the substitution"

result = agent("Player 7 is tired, sub in player 12")
if result.stop_reason == "interrupt":
    for interrupt in result.interrupts:
        # インタラプトをユーザー入力で処理
        pass
```

### 20. エージェントループ（The Agent Loop）

コア推論サイクル：モデル呼び出し→ツール使用チェック→ツール実行→モデル再呼び出し→最終レスポンスまで繰り返し。

**停止理由：**
- `end_turn` — モデル完了（通常終了）
- `tool_use` — モデルがツールを呼び出したい（ループ継続）
- `max_tokens` — レスポンス切り捨て（エラー）
- `guardrail_intervened` — 安全ブロック
- `interrupt` — ヒューマンインザループ一時停止

### 21. ツールエグゼキューター（Tool Executors）

並行 vs 逐次ツール実行の制御：

```python
from strands.tools.executors import SequentialToolExecutor
# デフォルト：並行（複数のオプションを同時に評価）
agent = Agent(tools=[calculate_distance, should_shoot])
# 逐次（ツールが互いに依存する場合）：
agent = Agent(tool_executor=SequentialToolExecutor(), tools=[...])
```

### 22. マルチモーダルプロンプティング（Multi-Modal Prompting）

テキストと一緒に画像/ドキュメントを送信（試合前後の分析に有用）：

```python
with open("opponent_heatmap.png", "rb") as f:
    image_bytes = f.read()
result = agent([
    {"text": "Analyze this opponent heatmap. Where are the gaps?"},
    {"image": {"format": "png", "source": {"bytes": image_bytes}}},
])
```

注意：ライブゲームプレイ中、エージェントはJSONゲーム状態を受信し、画像ではありません。

### 23. デバッグログ（Debug Logging）

エージェントの動作を診断するための詳細ログを有効化：

```python
import logging
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s", handlers=[logging.StreamHandler()])
```

---

## サンプルエージェント構造

```
fifa-agentic-football-strands/
├── src/
│   └── main.py                          # エージェント実装
├── .bedrock_agentcore.yaml.template     # AgentCore設定テンプレート
├── deploy-local.sh                      # デプロイスクリプト
├── test_local.py                        # ローカルテストスイート
└── requirements.txt                     # Python依存関係 (strands-agents>=1.13.0, bedrock-agentcore>=1.0.3)
```

**コードの取得：**
```bash
git clone https://github.com/aws-samples/fifa-agentic-football-strands.git
```

**サンプルの動作：**
1. BedrockAgentCoreAppをランタイムフレームワークとして使用
2. `Agent(model=BedrockModel(...), system_prompt=...)`でStrands Agentを作成
3. ゲーム状態JSONを読みやすいテキストに要約
4. エージェントを呼び出し：`response = agent(state_summary)`
5. レスポンスをゲームコマンド（JSON配列）にパース
6. LLMが失敗した場合はルールベースロジックにフォールバック

---

## 強化パターン

1. **構造化出力** — 手動パースをPydanticモデルに置き換え
2. **カスタムツール** — 戦術分析を追加（シュート角度、距離）
3. **オブザーバビリティ** — ティックごとのトークン、レイテンシ、ツール使用状況を追跡
4. **フック** — 判断を監視、ツール呼び出しを制限
5. **モデル切り替え** — Nova Micro（高速）vs Claude（高性能）を試す
6. **ガードレール** — 無効なコマンドをフィルタリング
7. **状態追跡** — ティック間で相手パターンを記憶
8. **リトライ戦略** — Bedrockスロットリングを適切に処理
9. **マルチエージェントパイプライン** — 分析→計画→実行グラフ

---

## AgentCoreへのデプロイ

デプロイスクリプトを実行：
```bash
./deploy-local.sh
```

スクリプトが処理する内容：IAMロール作成、ARM64用依存関係パッケージング、S3アップロード、エージェントデプロイ。

**重要な出力：** Agent ARN形式 `arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<agent-id>` — ポータル登録用に保存。

デプロイ後の確認：
```bash
agentcore status
```

ログの確認：
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/<id>-DEFAULT --follow
```

コード変更後の再デプロイ：
```bash
./deploy-local.sh    # ARNは同じまま
```

### ローカルテスト

ローカル開発サーバーを起動：
```bash
agentcore dev
```

別のターミナルでテスト呼び出しを送信：
```bash
agentcore invoke --dev '{"prompt": "{\"gameState\": {\"ball\": {\"position\": {\"x\": 30, \"y\": 10}}, \"players\": [], \"score\": {\"home\": 0, \"away\": 0}, \"gameTime\": 60}, \"teamId\": 0}"}'
```
