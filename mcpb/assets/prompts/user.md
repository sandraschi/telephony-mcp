# telephony-mcp — User Guide

Server: Telephony Bridge v0.2.0
Description: Outbound phone calls and SMS via Asterisk/ARI + speechops TTS or Twilio.
Transport: stdio (default) or HTTP (set MCP_TRANSPORT=http).

---

## Installation

### Prerequisites

Python 3.11+ with uv. For Asterisk mode: Asterisk server with ARI, speechops-mcp running. For Twilio mode: Twilio account with voice and SMS.

### Setup Steps

git clone https://github.com/sandraschi/telephony-mcp.git
cd telephony-mcp
uv venv
uv sync

Configure: set TELEPHONY_PROVIDER=asterisk
set ASTERISK_ARI_URL=http://localhost:8088/ari
set ASTERISK_ARI_USER=robofang
set ASTERISK_ARI_PASS=your_password

Start: uv run python -m telephony_mcp

### Twilio Configuration

set TELEPHONY_PROVIDER=twilio
set TWILIO_ACCOUNT_SID=your_sid
set TWILIO_AUTH_TOKEN=your_token
set TWILIO_FROM_NUMBER=+436641234567

---

## Step-by-Step Tutorials

### Tutorial 1: Add a Contact

Goal: Add a family member to the phone book.

Tool Call: add_contact(name="Marion", number="+436641234567", notes="Family emergency contact")

Return: {"success": true, "contact": {"name": "Marion", "number": "+436641234567", "notes": "Family emergency contact"}}

What happened: Contact saved to data/contacts.json. Use the name Marion for future calls.

### Tutorial 2: List All Contacts

Tool Call: list_contacts() returns array of contacts with count.

### Tutorial 3: Remove a Contact

Tool Call: remove_contact(name="OldContact") returns success true if found, false if not.

### Tutorial 4: Make an Outbound Call by Name

Goal: Call Steve to tell him dinner is ready.

Tool Call: make_call(contact="Steve", message="Hallo Steve, das Abendessen ist fertig.")

Return: {"success": true, "call_id": "1532467890.42", "audio_played": true, "mode": "asterisk", "contact_name": "Steve", "to_number": "+436649876543"}

What happened: Contact resolved to number, message synthesized via speechops, call originated via ARI, answered, audio played, hung up.

### Tutorial 5: Make a Call by Raw Number

Tool Call: make_call(contact="+4369912345678", message="Automated message.")

Return: Success with contact_name matching the number itself.

### Tutorial 6: Send an SMS via Twilio

Tool Call: send_sms(contact="Marion", text="Vergiss nicht, morgen um 14 Uhr den Termin.")

Return: {"success": true, "sms_id": "SMxxxxxxxxxxxxx", "mode": "twilio"}

Requires TELEPHONY_PROVIDER=twilio.

### Tutorial 7: SMS Fails on Asterisk Provider

Tool Call: send_sms(contact="Steve", text="Test") returns error explaining SMS not supported on Asterisk.

### Tutorial 8: Emergency Call

Tool Call: make_emergency_call(to_number="Marion", message="Achtung, Notruf von RoboFang.")

Return: Same as make_call with script_type emergency.

### Tutorial 9: Dispatch Test

Tool Call: telephony_dispatch_test(sip_uri="sip:linphone@localhost")

Return: Success with call_id and audio_played. Confirms ARI pipeline works end-to-end.

### Tutorial 10: Check Telephony Status

Tool Call: telephony_status() returns provider, ready flag, config (redacted), stats, contact count.

### Tutorial 11: Missing Contact Error

Tool Call: make_call(contact="Nobody") returns error: "Contact not found. Add via add_contact or use E.164."

### Tutorial 12: Invalid Number Format

Tool Call: add_contact(name="Bad", number="0664-1234") returns error: "Number must be E.164 format."

---

## Troubleshooting Guide

1. Contact not found: Run list_contacts() to verify names. Use raw E.164 as fallback.
2. ARI fails: Verify Asterisk running. Test with telephony_dispatch_test().
3. No audio: Check speechops at SPEECHOPS_BASE_URL. Verify fallback WAVs exist.
4. Twilio auth error: Verify TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER. Check telephony_status().
5. SMS fails on Asterisk: Switch to TELEPHONY_PROVIDER=twilio.
6. Call not answered: Increase ARI_ANSWER_TIMEOUT_S (default 30s).
7. Audio cuts off: Increase ARI_PLAYBACK_TIMEOUT_S (default 60s).
8. Bad number format: E.164 format is + followed by country code and up to 15 digits.
9. ARI connection refused: Check Asterisk running and ari.conf enabled. Check firewall on port 8088.
10. SIP endpoint not registered: Verify ASTERISK_OUTBOUND_ENDPOINT in pjsip.conf.
11. Twilio 21211 error: The to_number is invalid. Verify E.164 format.
12. Call connects silently: speechops unreachable and no fallback WAV. Check speechops-mcp service.

---

## Complete Contact Management Workflow

Step 1: add_contact(name="Steve", number="+436649876543", notes="Primary emergency contact")
Step 2: add_contact(name="Marion", number="+436641234567", notes="Backup contact")
Step 3: list_contacts() to verify both contacts exist
Step 4: make_emergency_call(to_number="Steve", message="Notfall. Bitte reagieren.")
Step 5: make_call(contact="Marion", message="Zweite Benachrichtigung.", script_type="emergency")
Step 6: telephony_status() to verify all calls logged
Step 7: remove_contact(name="Marion") to clean up

---

## Security Best Practices

Credential Protection: Store in environment variables. Never commit to version control. Rotate ARI passwords and Twilio tokens regularly.

Network Security: Run ARI over HTTPS in production. Bind ARI to localhost only. Restrict Twilio API access to known IPs.

Audit Log Security: SQLite database contains phone numbers and message content. Implement retention policies. Consider encrypting at rest.

---

## Performance Characteristics

add_contact: under 50ms. list_contacts: under 20ms. remove_contact: under 50ms.
telephony_status: under 50ms. make_call Asterisk: 10-45s. make_call Twilio: 5-30s.
send_sms Twilio: 1-5s. telephony_dispatch_test: 10-30s.

---

## Asterisk ARI Setup

In ari.conf: [general] enabled=yes. [robofang] type=user, read_only=no, password=your_password.
Configure PJSIP outbound endpoint in pjsip.conf.
Mount audio share directory into Asterisk container.
Restart Asterisk and verify ARI accessible.

## Twilio Setup

Create Twilio account. Purchase phone number with voice and SMS. Get Account SID and Auth Token. Set environment variables. Set TELEPHONY_PROVIDER=twilio. Start server.

---

## Provider Comparison

Asterisk: Voice via ARI, no SMS, TTS via speechops Gemini, 10-45s latency, high setup complexity, local testing with Linphone.

Twilio: Voice via REST API, SMS support, TTS via Polly Marlene-Neural, 5-30s latency, medium setup complexity, no local testing.

---

## Message Content Guidelines

German messages: Use formal Sie. Speak numbers individually. Use Bitte for polite requests. Avoid regional dialects. Keep emergency messages under 150 characters.

English messages: Standard pronunciation. Avoid homophones. Spell out acronyms. Keep concise for clear TTS delivery.

---

## FAQ

1. Asterisk vs Twilio? Asterisk = your PBX for voice only. Twilio = cloud API for voice + SMS.
2. Switch providers? Set TELEPHONY_PROVIDER to asterisk or twilio before starting.
3. TTS voice? Gemini Kore via speechops, or Twilio Polly Marlene-Neural.
4. Contact storage? data/contacts.json, created automatically on first add.
5. Audit logs? data/calls.db SQLite with full call and SMS history.
6. No provider? One of Asterisk or Twilio is required.
7. Inbound calls? Not supported, outbound only.
8. MCP Bridge? MCP_BRIDGE_URLS for cross-server tool federation.
9. Trial mode? Twilio trial restricts to verified numbers only.
10. Concurrent access? Contact file uses last-write-wins. Single contact manager recommended.

---

## Complete Scenario: Multi-Person Emergency Notification

Step 1: Primary call to Steve with standard emergency message.
Step 2: If unanswered after 30s, call backup contact Marion.
Step 3: If both fail, send SMS to both as fallback.
Step 4: Check telephony_status to verify all operations logged.
Step 5: Review audit database for compliance records.

## Complete Scenario: Automated Daily Status Call

Step 1: telephony_status to gather system stats.
Step 2: Compose message with key metrics.
Step 3: make_call with composed message.
Step 4: Retry after 5 minutes if first attempt fails.
Step 5: Log outcome in external monitoring system.

## Complete Scenario: Two-Factor Voice Authentication

Step 1: Generate 6-digit verification code.
Step 2: Call make_call with message containing each digit spoken individually.
Step 3: User enters code into application for verification.
Step 4: Audit log provides timestamp and phone number records.

## Audio Pipeline Troubleshooting

If calls connect with silence: Verify WAV file exists in TELEPHONY_AUDIO_SHARE. Verify mount in Asterisk container at /var/lib/asterisk/sounds/telephony_tts. Check ARI logs for playback errors. Verify WAV format is 8kHz mono for Asterisk. Test with manually placed WAV file.

## Complete Security Reference

Credential Management: All telephony credentials should be stored in environment variables only. Never hardcode passwords in source code or configuration files. Use a secrets manager like HashiCorp Vault or Windows Credential Manager for production deployments. Rotate passwords and tokens on a regular schedule. Use different credentials for development and production environments.

Network Security: The Asterisk ARI port (8088) should be bound to localhost only in production. Use HTTPS for ARI connections when possible. Restrict Twilio API access to known IP addresses in the Twilio console. The audio share directory should have restricted filesystem permissions so only the telephony-mcp server can write to it. The Asterisk container should have read-only access to the mounted audio share.

Audit Log Management: The SQLite audit database contains sensitive information including phone numbers and message content. Implement data retention policies that match your compliance requirements. Consider encrypting the database file using SQLite encryption extensions. The database is append-only by design to preserve audit trail integrity. Regular backups are recommended for compliance purposes.

## Multi-Call Orchestration Patterns

Pattern 1 - Cascading Emergency Alert: Call make_emergency_call to primary contact. If the call fails or is not answered, immediately call the backup contact. If both fail, send SMS to both contacts. Log all attempts via telephony_status. This pattern ensures no single point of failure in alert delivery.

Pattern 2 - Scheduled Status Reports: Schedule a recurring task that calls telephony_status to gather system statistics, composes a message with current metrics, and places a call to the on-call contact. If the call fails, retry after 5 minutes with an escalating message. Log all outcomes for compliance reporting.

Pattern 3 - Multi-Language Notification: Call a contact with an English message, then immediately call the same contact with a German translation of the same message. This ensures understanding regardless of the recipient's primary language. Use script_type parameter to differentiate the calls in the audit log.

## Asterisk ARI Configuration Details

The ari.conf file must have the general section enabling ARI and a user section for robofang with type user, read_only no, and password set. The pjsip.conf file must have a provider-endpoint section with the outbound trunk configuration including auth credentials and AOR settings. The audio share directory must be mounted at /var/lib/asterisk/sounds/telephony_tts inside the Asterisk container. The ARI application name must be set to "robofang" in the Asterisk dialplan.

## Twilio Configuration Details

The Twilio account must have an active phone number with voice and SMS capabilities enabled. The number must be in E.164 format. The Account SID and Auth Token are obtained from the Twilio Console dashboard. For production, use Twilio API keys instead of Auth Tokens for better security and granular permissions. The Twilio SDK handles authentication automatically when environment variables are set.

## E.164 Number Validation Reference

The E.164 standard defines the international public telecommunication numbering plan. Phone numbers in E.164 format start with a + followed by the country code and national significant number. For Austria the country code is 43, for Germany 49, for the UK 44, for the US 1. Mobile numbers in Austria start with 436 followed by the operator prefix. Landline numbers start with 431 for Vienna. The total length must be between 8 and 15 digits. Spaces, dashes, parentheses, and leading zeros are not allowed.

## Contact Store Maintenance

The contact store in data/contacts.json is a simple JSON file that grows as contacts are added. Regular maintenance involves: removing outdated contacts with remove_contact, updating changed numbers with add_contact using the same name, and periodically reviewing the contact list with list_contacts. For large contact lists, consider externalizing to a database. The JSON file is written atomically but is not suitable for concurrent write access from multiple processes.

## Deployment Architecture Options

Option 1 Monolithic: Asterisk, speechops, and telephony-mcp on the same machine. Simple setup, low latency, no network dependencies. Best for development, testing, and home use.

Option 2 Docker Compose Stack: All components in Docker containers. Orchestrated with docker-compose. Includes the Asterisk container, telephony-mcp container, and speechops container. The audio share is managed as a Docker volume.

Option 3 Cloud Hybrid: Twilio API plus local telephony-mcp. No Asterisk needed. Simple setup with per-call costs. Best for small deployments and rapid prototyping. No PBX management required.

## Log File Analysis Reference

The telephony-mcp server logs key events at INFO level: "Calling {name} ({number})" before originating, "Contact saved: {name}" after contact updates, "Sending SMS to {name}" before SMS, and "Dispatch test -> {sip_uri}" before test calls. Audio synthesis results are logged as "TTS WAV written" on success or "speechops unreachable" on failure. ARI events are logged at DEBUG level for detailed troubleshooting. The SQLite audit database provides persistent storage for compliance and analysis.

## Provider Configuration Walkthrough

For Asterisk configuration, edit the ari.conf file to enable ARI, create the robofang user with a strong password, and bind to localhost for security. Then configure the PJSIP endpoint in pjsip.conf with the provider authentication details. Start or restart Asterisk to apply changes. Verify the ARI is accessible by checking that a GET to the ARI URL returns a valid response. The AsteriskProvider class connects to ARI using the configured URL, user, password, and application name.

For Twilio configuration, purchase a phone number with voice and SMS capabilities from the Twilio console. Configure the voice URL to use TwiML or leave it empty if using the REST API. Get the Account SID and Auth Token from the console dashboard. Set the environment variables and start the server. The TwilioProvider class creates a Twilio client using the credentials. The provider falls back to mock mode if credentials are missing, returning synthetic IDs for testing without making actual API calls.

## Audio Pipeline Configuration Walkthrough

The audio synthesis pipeline has three tiers. The primary tier uses the speechops REST API at the configured SPEECHOPS_BASE_URL with the configured TTS provider and voice. The fallback tier uses pre-recorded WAV files stored in audio/fallback/ named by script type. The silent tier produces no audio when both tiers are unavailable. Configure the speechops URL to point to a running speechops-mcp server. Deploy fallback WAV files to the audio/fallback/ directory for each used script type. Verify the pipeline by calling telephony_dispatch_test and checking the audio_played field.

## Dialplan Configuration For Asterisk

The Asterisk dialplan must include a context that handles calls from the robofang ARI application. When ARI originates a call, the channel enters the Stasis application specified in the originate request. The Stasis application must be defined in extensions.conf or the ARI application configuration. The robofang application name must match between the ari.conf configuration and the ASTERISK_ARI_APP environment variable. Without proper dialplan configuration, calls will fail at the origination stage.

## Audit Database Query Reference

The SQLite audit database at data/calls.db supports standard SQL queries. Query total calls by operation: SELECT op, COUNT(*) FROM calls GROUP BY op. Query recent failures: SELECT ts, to_number, error FROM calls WHERE success=0 ORDER BY ts DESC LIMIT 10. Query average duration: SELECT op, AVG(duration_ms) FROM calls GROUP BY op. Query provider breakdown: SELECT provider, COUNT(*) FROM calls GROUP BY provider. These queries enable compliance analysis, performance monitoring, and troubleshooting without separate logging infrastructure.

## SIP Trunk Configuration Reference

For Asterisk outbound calls, the SIP trunk must be configured as a PJSIP endpoint in pjsip.conf. The endpoint must have outbound_auth configured with the provider credentials. The AOR must contain the provider's SIP server address. The transport must be configured for UDP or TCP as required by the provider. The codec settings must allow at least ulaw or alaw for voice compatibility. The outbound endpoint name in the AsteriskProvider configuration must match the endpoint name in pjsip.conf exactly.

## Contact Store Format Reference

The data/contacts.json file uses a simple dictionary format keyed by lowercased contact name. Each entry contains name, number, and notes fields. The number must be in E.164 format. The notes field is optional and defaults to an empty string. The file is created automatically on the first add_contact call. The file is written atomically using a write-then-rename pattern to prevent corruption. Concurrent writes are not protected and the last write wins in case of race conditions.

## Complete Tools Quick Reference

make_call parameters: contact (string, required), message (string, required), script_type (string, optional, default general), ctx (Context, auto-injected). Returns success boolean, call_id string, audio_played boolean, mode string, contact_name string, to_number string. Errors: contact not found, ARI origination failure, no answer, audio synthesis failure, Twilio API error.

make_emergency_call parameters: to_number (string, required), message (string, required), ctx (Context, auto-injected). Returns same as make_call. This is a wrapper that sets script_type to emergency automatically.

send_sms parameters: contact (string, required), text (string, required), ctx (Context, auto-injected). Returns success boolean, sms_id string, mode string. Errors: contact not found, Asterisk provider not supported, Twilio API error.

telephony_dispatch_test parameters: sip_uri (string, required), ctx (Context, auto-injected). Returns success boolean, call_id string, audio_played boolean, mode string. Uses hardcoded German test message.

add_contact parameters: name (string, required), number (string, required, E.164 format), notes (string, optional), ctx (Context, auto-injected). Returns success boolean, contact object. Errors: invalid number format.

list_contacts parameters: ctx (Context, auto-injected). Returns contacts array and count integer.

remove_contact parameters: name (string, required), ctx (Context, auto-injected). Returns success boolean and removed name string. Errors: contact not found.

telephony_status parameters: ctx (Context, auto-injected). Returns provider string, ready boolean, config object, stats object with total_calls, successful, failed, last_call fields, and contact_count integer.

## Provider Configuration Reference

For Asterisk mode, configure these environment variables. ASTERISK_ARI_URL defaults to http://localhost:8088/ari. ASTERISK_ARI_USER defaults to robofang. ASTERISK_ARI_PASS defaults to robofang_pass. ASTERISK_OUTBOUND_ENDPOINT defaults to provider-endpoint. ARI_ANSWER_TIMEOUT_S defaults to 30 seconds. ARI_PLAYBACK_TIMEOUT_S defaults to 60 seconds. SPEECHOPS_BASE_URL defaults to http://localhost:10918. SPEECHOPS_TTS_PROVIDER defaults to gemini. SPEECHOPS_TTS_VOICE defaults to Kore. SPEECHOPS_TIMEOUT_S defaults to 10 seconds. For Twilio mode, configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER.

## Data Storage Reference

The telephony-mcp server stores data in two files. data/contacts.json stores the phone book as a JSON dictionary keyed by lowercased contact name. Each value contains name, number, and notes fields. The file is created on first write and persists across restarts. data/calls.db stores the SQLite audit database with the calls table containing all call and SMS records. The database is created on first write and persists across restarts. Both files are configurable via TELEPHONY_CONTACTS_PATH and TELEPHONY_DB_PATH respectively.

## Error Response Reference

All telephony-mcp tools return a structured error response on failure. The response includes success false and a descriptive error string explaining the failure. For make_call and send_sms, contact resolution errors include the specific input that failed and guidance on how to fix it. Provider errors include provider-specific error messages from the underlying ARI or Twilio API. Validation errors for E.164 numbers include the invalid input shown in the error message. Audit database errors are caught and logged but should not occur in normal operation.

## Integration With Other Fleet MCP Servers

telephony-mcp exposes an MCP Bridge via MCP_BRIDGE_URLS. This comma-separated list of remote MCP server URLs registers each as a ProxyProvider. Cross-server tool calls are routed through the bridge. The speechops-mcp server provides the TTS audio synthesis that telephony-mcp consumes for Asterisk mode calls. The fleet-agent-mcp server can orchestrate telephony-mcp operations as part of automated alert workflows. The aiwatcher-mcp server can trigger emergency calls based on alert conditions detected in monitored feeds.

## Sending And Receiving Flows

The make_call tool follows this flow. The contact string is resolved through the contact store to an E.164 number. The message text is sent to the audio synthesis pipeline. The synthesized audio is written to the shared directory. The ARI client originates the call through the configured PJSIP endpoint. The call rings the recipient's phone. When answered, the audio message is played. After playback completes, the call is hung up. The entire operation is logged to the audit database with timing information. Failure at any step is caught and returned as a structured error response.

The send_sms tool follows this simpler flow. The contact is resolved to an E.164 number. The Twilio client creates an SMS message with the body text and from number. The Twilio API sends the message and returns a message SID. The operation is logged to the audit database. In Asterisk mode, SMS is not supported and a clear error is returned guiding the user to switch to Twilio.

## Operational Notes

Call duration varies significantly by provider and network conditions. Asterisk calls typically take 10-45 seconds including ringing and audio playback. Twilio calls typically take 5-30 seconds. SMS delivery via Twilio is typically under 5 seconds but may be delayed by carrier networks. The dispatch test is the fastest way to verify the pipeline, completing in 10-30 seconds with a local SIP client. The telephony_status tool provides real-time visibility into provider readiness and call statistics. Regular status checks are recommended for production monitoring.

## Emergency Alert Patterns

Pattern 1: Single Contact Alert. Call make_emergency_call to a single contact with the emergency message. Verify success with telephony_status. This is the simplest pattern suitable for non-critical alerts where confirmation is not required.

Pattern 2: Escalating Contact Chain. Call the primary contact first. If the call is unsuccessful or not answered, immediately call the secondary contact. If both fail, send SMS to both contacts. This pattern provides redundancy for critical alerts where at least one person must be reached.

Pattern 3: Broadcast Alert. Call all contacts simultaneously or in rapid succession. Each contact receives the same emergency message. This pattern is suitable for widespread alerts where multiple people need to be informed quickly.

Pattern 4: Confirmation Loop. Call the contact and after the message is played, the system waits for the contact to press a key to confirm receipt. This pattern requires additional IVR logic not currently implemented in telephony-mcp but can be added through Asterisk dialplan configuration.

## Asterisk Log Analysis

Asterisk logs are essential for diagnosing call failures. The main Asterisk log file is typically at /var/log/asterisk/full or /var/log/asterisk/messages. Look for lines containing the channel ID returned by telephony-mcp to trace the call lifecycle. The ARI log shows REST API requests and responses. The PJSIP log shows SIP signaling messages. Common error patterns include registration failures, authentication errors, and codec negotiation failures. The Asterisk CLI command "asterisk -r" provides real-time access to logs and debugging commands.

## Twilio Error Code Reference

Error 21211: Invalid To phone number. The number format is wrong or the number does not exist. Verify E.164 format and check that the number is active.

Error 21408: SMS not enabled for this region. The destination country is not in your Twilio account's SMS-enabled regions. Enable the region in the Twilio console or use a different provider.

Error 21608: From number not owned by account. The TWILIO_FROM_NUMBER is not a number you own. Verify the number in the Twilio console.

Error 30001: Queue overflow. Twilio is experiencing high volume. Retry the request after a short delay.

Error 30002: Account suspended. Your Twilio account has been suspended due to billing or compliance issues. Check the Twilio console for details.

## Compliance And Legal Considerations

When using telephony-mcp for automated calls and SMS, ensure compliance with relevant regulations. In the European Union, the GDPR applies to processing of personal data including phone numbers. The contact store and audit database contain personal data and must be handled accordingly. In Austria, the Telekommunikationsgesetz regulates automated calls. In the United States, the TCPA (Telephone Consumer Protection Act) restricts automated calls and SMS. Always obtain consent before sending automated communications. Include opt-out instructions in SMS messages. Identify the caller at the beginning of automated voice calls. Maintain audit logs for compliance verification. Consult legal counsel for specific regulatory requirements in your jurisdiction.

## Asterisk Quick Start Checklist

Verify Asterisk is installed and running. Check that the ARI module is enabled in ari.conf with the correct user credentials. Configure the PJSIP outbound endpoint in pjsip.conf with your SIP trunk provider details. Create the audio share directory and set appropriate permissions. Restart Asterisk to apply configuration changes. Test ARI connectivity by calling telephony_status which should show provider asterisk and ready true. Run telephony_dispatch_test to verify the full pipeline including ARI origination, audio playback, and hangup. If the test succeeds, add your first contact and make a real outbound call.

## Twilio Quick Start Checklist

Create a Twilio account and purchase a phone number with voice and SMS capabilities. Obtain the Account SID and Auth Token from the Twilio console. Set the environment variables for Twilio configuration. Start the server and check telephony_status for provider twilio and ready true. Add a test contact with a verified phone number. Send a test SMS with send_sms. Make a test call with make_call. Monitor the audit database for the test records. If all steps succeed, the Twilio integration is working correctly.

## Data Retention Policy Recommendations

The audit database and contact store can contain personally identifiable information. Implement a data retention policy that complies with applicable regulations. The audit database logs every call and SMS with phone numbers and message content. Retain this data for the minimum period required by law, typically 6 to 24 months depending on jurisdiction. Archive old records to encrypted storage before deletion. The contact store contains phone numbers and names. Remove outdated or unused contacts regularly. Implement a process for handling data deletion requests from contacts.

## Monitoring And Alerting Recommendations

Set up monitoring for the telephony-mcp server to ensure reliability. Monitor the server process health with a process supervisor or container orchestration. Check telephony_status periodically to verify provider readiness. Alert on rapid increases in call failure rates which may indicate a provider issue. Monitor the audit database size for growth trends. Set up alerts for Twilio account balance thresholds to prevent service interruption. Log all telephony-mcp server logs to a centralized logging system for analysis. Track call duration trends to identify performance degradation over time. Monitor contact store changes for unexpected modifications.

## Appendix: Data File Reference

The telephony-mcp server uses two persistent data files. The contact store at data/contacts.json is a JSON dictionary file. The audit database at data/calls.db is a SQLite database file. Both files are configurable through environment variables. The contact store is human-readable and editable with any text editor for bulk import or correction. The audit database requires SQLite tools for direct inspection. Both files persist across server restarts and are created automatically on first use. Both files should be included in regular system backups. For production deployments, configure backup automation and retention policies for both the contact store and the audit database.

## Appendix: Port And Network Reference

The telephony-mcp server communicates over these ports and protocols. ASTERISK_ARI_URL defaults to port 8088 with HTTP protocol for REST API calls. The ARI WebSocket connection uses the same port with WS protocol. SPEECHOPS_BASE_URL defaults to port 10918 with HTTP protocol for TTS synthesis requests. In HTTP transport mode, the MCP server listens on port 8000 by default. When using MCP Bridge federation, outbound connections are made to the configured remote server URLs. Twilio API calls go to api.twilio.com over HTTPS on port 443. No inbound ports are required for Twilio mode as the server only makes outbound REST API calls. The complete telephony stack integrates Asterisk ARI, speechops TTS, and the contact management system into a unified MCP tool surface for automated communications. The telephony-mcp server provides a comprehensive solution for automated outbound voice and SMS communications within the MCP ecosystem. With support for both Asterisk and Twilio providers, the server adapts to different deployment scenarios from local PBX to cloud-based telephony. The contact management and audit logging systems ensure operational visibility and compliance. All calls and SMS messages are recorded in the SQLite audit database with timestamps, success status, and provider information. The contact store provides a simple name-based resolution system that simplifies daily operations. The combined tools give LLM agents full control over telephony operations from contact management through call origination and status monitoring. Whether sending emergency notifications, verifying system status with daily calls, or sending automated SMS alerts, telephony-mcp provides the complete tool surface for voice and SMS communications within the MCP ecosystem. The server handles provider abstraction, contact resolution, audio synthesis, audit logging, and error recovery automatically. telephony-mcp is a fleet-standard MCP server for automated outbound voice and SMS communications. The server integrates with Asterisk ARI and Twilio APIs for robust telephony operations across different deployment scenarios and provider backends. Its contact management and audit logging provide operational visibility and compliance support.
