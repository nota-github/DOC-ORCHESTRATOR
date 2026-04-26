# Document Orchestrator

AI agent that automatically updates Confluence documents based on meeting notes.
Built as a Claude Code skill — run it with `/doc-orchestrator` inside Claude Code.

## What It Does

1. Takes meeting notes (audio file or text)
2. Searches Confluence for related documents
3. Analyzes what needs to change based on meeting decisions
4. Proposes changes with classification (Required / Recommended)
5. Applies approved changes to Confluence with change log comments

## Prerequisites

- [Claude Code](https://claude.com/claude-code) installed
- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Atlassian account with API token
- OpenAI API key (for audio transcription)

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd doc-orchestrator
```

### 2. Create `.env` file

Copy the template below and fill in your credentials:

```bash
# .env
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your-email@company.com
CONFLUENCE_TOKEN=your-atlassian-api-token
OPENAI_API_KEY=your-openai-api-key
```

To get an Atlassian API token:
- Go to https://id.atlassian.com/manage-profile/security/api-tokens
- Click "Create API token"
- Copy the token

### 3. Open Claude Code

```bash
cd doc-orchestrator
claude
```

The MCP server (Confluence connection) will be configured automatically via `.mcp.json`.

### 4. Run the skill

```
/doc-orchestrator
```

## Usage Flow

### Input Options

| Input Type | How |
|-----------|-----|
| Audio file | Provide path to `.mp3`, `.m4a`, `.wav`, etc. — transcribed via OpenAI GPT-4o Transcribe |
| Text file | Provide path to `.md` or `.txt` meeting notes |
| Paste text | Paste meeting notes directly into the chat |

### Step-by-Step

1. **(Optional)** Provide Confluence page URLs you know are related
2. Provide meeting notes (audio / text file / paste)
3. Review the list of related Confluence documents found
4. Select which documents to analyze
5. Review proposed changes (Required / Recommended)
6. Select which changes to apply
7. Confirm target pages before update
8. Changes are applied to Confluence with comments

### Confluence URL Formats

Both formats are supported:
- Full URL: `https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Title`
- Short URL: `https://your-domain.atlassian.net/wiki/x/AbCdEf`

## Project Structure

```
doc-orchestrator/
├── .mcp.json                          # Confluence MCP server config
├── .env                               # Your credentials (not in git)
├── .gitignore
├── requirements.txt                   # Python dependencies (openai)
├── README.md
├── DESIGN.md                          # Agent & Classifier architecture
├── scripts/
│   ├── transcribe.py                  # Audio → text transcription
│   └── helper_mcp.py                  # Confluence helper MCP server
├── logs/                              # Auto-generated logs (not in git)
│   ├── YYYY-MM-DD_HH-MM_transcript.json
│   ├── YYYY-MM-DD_HH-MM_meeting_analysis.json
│   └── YYYY-MM-DD_HH-MM_update.json
└── .claude/
    └── skills/
        └── doc-orchestrator/
            ├── SKILL.md               # Main skill prompt
            └── domains/
                ├── classifiers/
                │   ├── topic.md       # Topic classifier (5 meeting types)
                │   └── part.md        # Part classifier (5 domains)
                ├── agents/
                │   ├── q.md           # Quantization agent
                │   ├── go.md          # Graph Optimization agent
                │   ├── mr.md          # Model Representation agent
                │   ├── me.md          # Model Engineering agent
                │   └── swe.md         # Software Engineering agent
                └── cross-cut/
                    └── scenarios.md   # Shared S0-S3 context
```

## Logs

Every run generates log files in `logs/`:

- `*_transcript.json` — Raw transcription from audio input
- `*_update.json` — Full record of what was analyzed, proposed, applied, and skipped

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `/mcp` shows no servers | Make sure `uv` is installed and restart Claude Code |
| `OPENAI_API_KEY not set` | Check that `.env` file exists and contains the key |
| Confluence auth fails | Verify your email and API token in `.env` |
