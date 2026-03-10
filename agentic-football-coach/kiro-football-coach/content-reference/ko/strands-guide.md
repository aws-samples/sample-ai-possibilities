# Strands Agents SDK 가이드

Strands Agents SDK로 풋볼 에이전트를 구축하기 위한 종합 참조 자료. 23가지 핵심 개념, 샘플 에이전트 구조, 강화 패턴, 배포를 다룹니다.

## 에이전트 아키텍처 개요

각 팀은 5명의 선수를 보유하며, 각 선수가 에이전트입니다. 에이전트는 매 틱(초당 60회)마다 게임 상태를 수신하고 500ms 이내에 액션을 반환해야 합니다.

```
게임 상태 (JSON) → 에이전트 → 선수 액션 (JSON)
```

---

## 23가지 핵심 개념

### 1. 구조화된 출력 (Structured Output)

Pydantic 모델을 사용하여 에이전트가 원시 텍스트 대신 검증된 타입 안전 게임 명령을 반환하도록 합니다.

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

### 2. 커스텀 도구 (Custom Tools)

에이전트가 호출할 수 있는 전술 분석 함수를 제공합니다:

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

### 3. 모델 프로바이더 (Model Providers)

모델 간 쉽게 전환:

```python
from strands.models import BedrockModel

model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")  # 빠르고 비용 효율적
# model = BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0")  # 더 높은 성능
agent = Agent(model=model, tools=[calculate_distance, should_shoot])
```

### 4. 관측성 (Observability)

메트릭, 토큰, 레이턴시, 도구 사용량 추적:

```python
result = agent("What should I do?")
summary = result.metrics.get_summary()
# summary['accumulated_usage']['totalTokens']
# summary['accumulated_metrics']['latencyMs']
# summary['tool_usage']
```

`result.traces`를 통해 추론 사이클별 상세 트레이스 확인 가능.

### 5. 훅 (Hooks)

라이프사이클 포인트에서 에이전트 동작을 모니터링하고 수정:

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

고급: `LimitToolCalls` 훅을 사용하여 호출당 도구 호출 횟수를 제한할 수 있습니다.

### 6. 가드레일 (Guardrails)

Bedrock Guardrails를 통한 콘텐츠 필터링 및 안전:

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

### 7. 직접 도구 호출 (Direct Tool Invocation)

LLM 추론 없이 프로그래밍 방식으로 도구 호출:

```python
distance = agent.tool.calculate_distance(pos1={"x": 0, "y": 0}, pos2={"x": 10, "y": 5})
```

### 8. 커뮤니티 도구 (Community Tools)

`strands-agents-tools`의 사전 구축 도구:

```python
from strands_tools import calculator, python_repl
agent = Agent(tools=[calculator, python_repl], system_prompt="You are a football analyst.")
```

유용한 커뮤니티 도구: `calculator`, `python_repl`, `current_time`.

### 9. 대화 관리 (Conversation Management)

메시지 기록 제어를 위한 세 가지 내장 관리자:

```python
from strands.agent.conversation_manager import (
    NullConversationManager,           # 트리밍 없음
    SlidingWindowConversationManager,   # 최근 N개 메시지 유지
    SummarizingConversationManager,     # 이전 메시지 요약
)

# 기본값: 슬라이딩 윈도우
agent = Agent(conversation_manager=SlidingWindowConversationManager(window_size=10))

# 풋볼용: 일반적으로 틱당 상태 비저장 (매번 새 에이전트)
agent = Agent()  # 새 에이전트 = 새로운 시작
```

### 10. 에이전트 상태 관리 (Agent State Management)

호출 간 키-값 저장소 (모델에 전송되지 않음):

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

### 11. 세션 관리 (Session Management)

에이전트 재시작 간 상태와 대화 기록 유지:

```python
from strands.session.file_session_manager import FileSessionManager

session_manager = FileSessionManager(session_id="team-alpha-session", storage_dir="./sessions")
agent = Agent(session_manager=session_manager, state={"opponent_patterns": {}})
```

클라우드 배포의 경우 `S3SessionManager`를 사용합니다.

### 12. 재시도 전략 (Retry Strategies)

고빈도 게임 틱 중 모델 스로틀링 처리:

```python
from strands import ModelRetryStrategy
agent = Agent(retry_strategy=ModelRetryStrategy(max_attempts=3, initial_delay=2, max_delay=60))
# 또는 최저 레이턴시를 위해 재시도 비활성화:
agent = Agent(retry_strategy=None)
```

### 13. 스트리밍 (Streaming)

에이전트 결정을 실시간으로 모니터링:

```python
async for event in agent.stream_async("Ball at (30,10), should I shoot?"):
    if "data" in event: print(event["data"], end="")
    elif "current_tool_use" in event and event["current_tool_use"].get("name"):
        print(f"Using tool: {event['current_tool_use']['name']}")
```

### 14. 클래스 기반 도구 (Class-Based Tools)

클래스를 사용하여 관련 도구 간 상태 공유:

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

### 15. MCP 도구 (MCP Tools)

Model Context Protocol을 통해 외부 도구 서버에 연결:

```python
from strands.tools.mcp import MCPClient
mcp_client = MCPClient(lambda: sse_client("http://localhost:8000/sse"))
with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
```

### 16. 멀티 에이전트 — 도구로서의 에이전트 (Agents as Tools)

전문 에이전트를 오케스트레이터의 도구로 래핑:

```python
@tool
def defensive_analyst(game_state: str) -> str:
    """Analyze defensive positioning."""
    analyst = Agent(system_prompt="You are a defensive football analyst.")
    return str(analyst(game_state))

coach = Agent(tools=[defensive_analyst, offensive_strategist],
    system_prompt="You are the head coach. Route to the right specialist.")
```

### 17. 멀티 에이전트 — 스웜 (Swarm)

자율적으로 작업을 인계하는 협업 에이전트:

```python
from strands.multiagent import Swarm
scout = Agent(name="scout", system_prompt="Analyze opponent weaknesses.")
tactician = Agent(name="tactician", system_prompt="Design game plans.")
coach = Agent(name="coach", system_prompt="Finalize tactics.")
swarm = Swarm([scout, tactician, coach], entry_point=scout, max_handoffs=10)
result = swarm("Prepare a game plan against a 4-4-2 high-pressing team")
```

### 18. 멀티 에이전트 — 그래프 (Graph)

정의된 실행 순서를 가진 구조화된 파이프라인:

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

### 19. 인터럽트 (Human-in-the-Loop)

사람의 입력을 위해 실행 일시 중지 (예: 코칭 결정):

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
        # 사용자 입력으로 인터럽트 처리
        pass
```

### 20. 에이전트 루프 (The Agent Loop)

핵심 추론 사이클: 모델 호출 → 도구 사용 확인 → 도구 실행 → 모델 재호출 → 최종 응답까지 반복.

**중지 이유:**
- `end_turn` — 모델 완료 (정상 종료)
- `tool_use` — 모델이 도구 호출 원함 (루프 계속)
- `max_tokens` — 응답 잘림 (오류)
- `guardrail_intervened` — 안전 차단
- `interrupt` — 사람 개입 일시 중지

### 21. 도구 실행기 (Tool Executors)

동시 vs 순차 도구 실행 제어:

```python
from strands.tools.executors import SequentialToolExecutor
# 기본값: 동시 (여러 옵션을 한 번에 평가)
agent = Agent(tools=[calculate_distance, should_shoot])
# 순차 (도구 간 의존성이 있을 때):
agent = Agent(tool_executor=SequentialToolExecutor(), tools=[...])
```

### 22. 멀티모달 프롬프팅 (Multi-Modal Prompting)

텍스트와 함께 이미지/문서 전송 (경기 전후 분석에 유용):

```python
with open("opponent_heatmap.png", "rb") as f:
    image_bytes = f.read()
result = agent([
    {"text": "Analyze this opponent heatmap. Where are the gaps?"},
    {"image": {"format": "png", "source": {"bytes": image_bytes}}},
])
```

참고: 라이브 게임플레이 중 에이전트는 이미지가 아닌 JSON 게임 상태를 수신합니다.

### 23. 디버그 로깅 (Debug Logging)

에이전트 동작 진단을 위한 상세 로그 활성화:

```python
import logging
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s", handlers=[logging.StreamHandler()])
```

---

## 샘플 에이전트 구조

```
fifa-agentic-football-strands/
├── src/
│   └── main.py                          # 에이전트 구현
├── .bedrock_agentcore.yaml.template     # AgentCore 설정 템플릿
├── deploy-local.sh                      # 배포 스크립트
├── test_local.py                        # 로컬 테스트 스위트
└── requirements.txt                     # Python 의존성 (strands-agents>=1.13.0, bedrock-agentcore>=1.0.3)
```

**코드 가져오기:**
```bash
git clone https://github.com/aws-samples/fifa-agentic-football-strands.git
```

**샘플 에이전트 동작:**
1. BedrockAgentCoreApp을 런타임 프레임워크로 사용
2. `Agent(model=BedrockModel(...), system_prompt=...)`로 Strands Agent 생성
3. 게임 상태 JSON을 읽기 쉬운 텍스트로 요약
4. 에이전트 호출: `response = agent(state_summary)`
5. 응답을 게임 명령(JSON 배열)으로 파싱
6. LLM 실패 시 규칙 기반 로직으로 폴백

---

## 강화 패턴

1. **구조화된 출력** — 수동 파싱을 Pydantic 모델로 대체
2. **커스텀 도구** — 전술 분석 추가 (슈팅 각도, 거리)
3. **관측성** — 틱당 토큰, 레이턴시, 도구 사용량 추적
4. **훅** — 결정 모니터링, 도구 호출 제한
5. **모델 전환** — Nova Micro (빠름) vs Claude (고성능) 시도
6. **가드레일** — 잘못된 명령 필터링
7. **상태 추적** — 틱 간 상대 패턴 기억
8. **재시도 전략** — Bedrock 스로틀링 우아하게 처리
9. **멀티 에이전트 파이프라인** — 분석 → 계획 → 실행 그래프

---

## AgentCore에 배포

배포 스크립트 실행:
```bash
./deploy-local.sh
```

스크립트가 처리하는 내용: IAM 역할 생성, ARM64용 의존성 패키징, S3 업로드, 에이전트 배포.

**중요한 출력:** Agent ARN 형식 `arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<agent-id>` — 포털 등록용으로 저장.

배포 후 확인:
```bash
agentcore status
```

로그 확인:
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/<id>-DEFAULT --follow
```

코드 변경 후 재배포:
```bash
./deploy-local.sh    # ARN은 동일하게 유지
```

### 로컬 테스트

로컬 개발 서버 시작:
```bash
agentcore dev
```

별도 터미널에서 테스트 호출 전송:
```bash
agentcore invoke --dev '{"prompt": "{\"gameState\": {\"ball\": {\"position\": {\"x\": 30, \"y\": 10}}, \"players\": [], \"score\": {\"home\": 0, \"away\": 0}, \"gameTime\": 60}, \"teamId\": 0}"}'
```
