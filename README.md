# 📞 Telephony-MCP (SIP Gateway)

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://biomejs.dev"><img src="https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white" alt="Biome"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

**Autonomous Emergency Communication & Digital Telephony Bridge.**

---

Telephony-MCP is a modular FastMCP server designed for high-fidelity, sovereign telephony. It serves as the primary "Clean Bridge" for the RoboFang fleet, enabling AI agents to interact with the global telephony network (PSTN) via Asterisk and SIP without air-gapped hardware loops.

## Quick Start

```powershell
git clone https://github.com/sandraschi/telephony-mcp
cd telephony-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:

## 🚀 Key Features

- **Clean Bridge Architecture**: Direct digital audio injection via **Asterisk ARI** and **AudioSocket**.
- **Provider Agnostic**: Factory pattern support for both **Asterisk/SIP** (Sovereign) and **Twilio** (Legacy/Cloud).
- **Rescue (AED)**: Purpose-built for Level 4 Autonomous Emergency Dispatch.
- **Sovereign Security Trinity**: Integrated **Ruff**, **Biome**, and **Semgrep** for production-grade code quality.

## 🏗️ Architecture

Telephony-MCP manages a containerized **Asterisk 20+** stack. Signaling is handled via PJSIP, and media is orchestrated through the Asterisk REST Interface (ARI).

### Digital Signaling Workflow
1. **Initiation**: Supervisor triggers an AED alert.
2. **Provider Selection**: Gateway selects the `AsteriskProvider` (local SIP trunk).
3. **ARI Bridge**: The system creates a bridge and injects high-quality digital speech (AI-generated).
4. **Human Interaction**: The AI identifies itself as an "Emergency Dispatch Assistant" to human responders.

## 📦 Getting Started

### 1. Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [UV Package Manager](https://github.com/astral-sh/uv)

### 2. Infrastructure Launch
```bash
docker-compose up -d
```

### 3. Server Startup
```bash
uv sync
py -m telephony_mcp.server
```

## 🛡️ Security Trinity
This project enforces the **Trinity Protocol**:
- **Lint**: `py -m ruff check .`
- **Format**: `npx @biomejs/biome check --write .`
- **SAST**: `semgrep scan --config .semgrep.yml .`

## 🤝 RoboFang Integration
The gateway is designed to be called by the **RoboFang Council** (Orchestrator) during verified life-safety events.

---
*Engineering the digital bridge for autonomous agency.*
