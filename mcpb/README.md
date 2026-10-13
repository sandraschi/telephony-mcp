# telephony-mcp (MCPB Bundle)

FastMCP 3.2 Telephony Bridge — emergency calls via Asterisk/ARI+speechops TTS or Twilio

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "telephony-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "telephony_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **make_call**: make_call
- **make_emergency_call**: make_emergency_call
- **send_sms**: send_sms
- **telephony_dispatch_test**: telephony_dispatch_test
- **add_contact**: add_contact
- **list_contacts**: list_contacts
- **remove_contact**: remove_contact
- **telephony_status**: telephony_status

## Requirements

- Python 3.12+
- uv
