# 📞 Telephony-MCP (Industrial SIP Gateway)

**Autonomous Emergency Communication & Digital Telephony Bridge.**

---

Telephony-MCP is a modular FastMCP server designed for high-fidelity, sovereign telephony. It serves as the primary "Clean Bridge" for the RoboFang fleet, enabling AI agents to interact with the global telephony network (PSTN) via Asterisk and SIP without air-gapped hardware loops.

## 🚀 Key Features

- **Clean Bridge Architecture**: Direct digital audio injection via **Asterisk ARI** and **AudioSocket**.
- **Provider Agnostic**: Factory pattern support for both **Asterisk/SIP** (Sovereign) and **Twilio** (Legacy/Cloud).
- **Industrial Rescue (AED)**: Purpose-built for Level 4 Autonomous Emergency Dispatch.
- **Sovereign Security Trinity**: Integrated **Ruff**, **Biome**, and **Semgrep** for industrial-grade code quality.

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
