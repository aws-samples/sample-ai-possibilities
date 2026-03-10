# ⚽ Kiro Football Coach — Agentic Football World Cup Workshop

A guided workshop coach that transforms [Kiro](https://kiro.dev) into your personal coach for the **Agentic Football World Cup** workshop. Build AI-powered football agents using Strands Agents SDK or LangChain, and deploy them to Amazon Bedrock AgentCore.

## Prerequisites

- **Kiro IDE** or **Kiro CLI**
- **Python 3.x**
- **AWS CLI** (v2 recommended)
- **AWS Workshop Studio** access (12-digit event access code provided by your workshop host)

---

## Setup — Option A: Prompt-Based (Recommended)

The fastest way to get started. Open Kiro and ask:

> Clone the kiro-football-coach repo and set up my workspace.

Kiro will:
1. Clone this repository into your workspace
2. Copy the `.kiro/` configuration files
3. Create a Python virtual environment and install dependencies
4. Verify your AWS credentials

The built-in coach will greet you and guide you through the rest.

## Setup — Option B: Manual (Fallback)

If you prefer to set up manually, or if the prompt-based flow doesn't work:

```bash
# 1. Clone the repository
git clone <repo-url> kiro-football-coach
cd kiro-football-coach

# 2. Run the bootstrap script
chmod +x setup.sh
./setup.sh
```

The script will:
- Copy `.kiro/` and `content-reference/` to your working directory
- Create a Python virtual environment (`.venv/`)
- Install dependencies from `requirements.txt`
- Verify your AWS credentials (and show instructions if they're missing)

You can also pass a target directory: `./setup.sh /path/to/workspace`

---

## Workshop Progression

| Phase | Topic |
|-------|-------|
| 1 | Welcome & Setup |
| 2 | AI Agent Fundamentals |
| 3 | Football Basics |
| 4 | Framework Choice (Strands or LangChain) |
| 5 | Build & Deploy Agent |
| 6 | Register & Play |
| 7 | Enhance Agent |
| 8 | Match Day |
| 9 | Compete |

---

## Project Structure

```
kiro-football-coach/
├── README.md
├── setup.sh
├── .kiro/
│   ├── steering/        # Always-on coach context
│   ├── skills/          # On-demand knowledge modules
│   ├── hooks/           # Event-driven automations
│   └── agents/          # Custom coach subagent
└── content-reference/
    ├── en/              # English content
    ├── ja/              # Japanese content
    └── ko/              # Korean content
```

---

# ⚽ Kiro Football Coach — エージェント型フットボールワールドカップ ワークショップ（日本語）

[Kiro](https://kiro.dev) をワークショップ専用コーチに変える、**エージェント型フットボールワールドカップ**のガイド付きチュートリアルです。Strands Agents SDK または LangChain を使って AI フットボールエージェントを構築し、Amazon Bedrock AgentCore にデプロイします。

## 前提条件

- **Kiro IDE** または **Kiro CLI**
- **Python 3.x**
- **AWS CLI**（v2 推奨）
- **AWS Workshop Studio** アクセス（ワークショップホストから提供される12桁のイベントアクセスコード）

## セットアップ — オプション A: プロンプトベース（推奨）

Kiro を開いて、以下のように入力してください：

> kiro-football-coach リポジトリをクローンして、ワークスペースをセットアップしてください。

Kiro が以下を自動で行います：
1. リポジトリをワークスペースにクローン
2. `.kiro/` 設定ファイルをコピー
3. Python 仮想環境を作成し、依存関係をインストール
4. AWS 認証情報を確認

コーチが挨拶し、ワークショップを案内します。

## セットアップ — オプション B: 手動（フォールバック）

```bash
# 1. リポジトリをクローン
git clone <repo-url> kiro-football-coach
cd kiro-football-coach

# 2. セットアップスクリプトを実行
chmod +x setup.sh
./setup.sh
```

スクリプトは以下を行います：
- `.kiro/` と `content-reference/` を作業ディレクトリにコピー
- Python 仮想環境（`.venv/`）を作成
- `requirements.txt` から依存関係をインストール
- AWS 認証情報を確認（未設定の場合は手順を表示）

---

# ⚽ Kiro Football Coach — 에이전틱 풋볼 월드컵 워크숍 (한국어)

[Kiro](https://kiro.dev)를 워크숍 전용 코치로 변환하는 **에이전틱 풋볼 월드컵** 가이드 튜토리얼입니다. Strands Agents SDK 또는 LangChain를 사용하여 AI 풋볼 에이전트를 구축하고 Amazon Bedrock AgentCore에 배포합니다.

## 사전 요구 사항

- **Kiro IDE** 또는 **Kiro CLI**
- **Python 3.x**
- **AWS CLI** (v2 권장)
- **AWS Workshop Studio** 접근 (워크숍 호스트가 제공하는 12자리 이벤트 접근 코드)

## 설정 — 옵션 A: 프롬프트 기반 (권장)

Kiro를 열고 다음과 같이 입력하세요:

> kiro-football-coach 리포지토리를 클론하고 워크스페이스를 설정해 주세요.

Kiro가 자동으로 다음을 수행합니다:
1. 리포지토리를 워크스페이스에 클론
2. `.kiro/` 설정 파일 복사
3. Python 가상 환경 생성 및 의존성 설치
4. AWS 자격 증명 확인

코치가 인사하고 워크숍을 안내합니다.

## 설정 — 옵션 B: 수동 (대체 방법)

```bash
# 1. 리포지토리 클론
git clone <repo-url> kiro-football-coach
cd kiro-football-coach

# 2. 설정 스크립트 실행
chmod +x setup.sh
./setup.sh
```

스크립트가 수행하는 작업:
- `.kiro/` 및 `content-reference/`를 작업 디렉토리에 복사
- Python 가상 환경(`.venv/`) 생성
- `requirements.txt`에서 의존성 설치
- AWS 자격 증명 확인 (미설정 시 안내 표시)
