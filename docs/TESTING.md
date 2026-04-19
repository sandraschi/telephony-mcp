# Testing the RoboFang "Help!" Chain (Linphone Walkthrough)

To verify that your fleet can successfully place rescue calls without triggering a real-world emergency alert, follow these steps to set up a local **Softphone** test harness.

## 1. Install Linphone
Download and install the **Linphone** desktop client on your PC. It is free and open-source.
- [Linphone Downloads](https://www.linphone.org/downloads-platforms)

## 2. Configure the Test Account
In Linphone, add a new account using the "Mock Responder" credentials we've pre-configured in `asterisk/pjsip.conf`.

- **SIP Address**: `sip:linphone@localhost` (or the IP of your Docker host)
- **Username**: `linphone`
- **Password**: `testpass`
- **Domain**: `localhost` (or Docker host IP)

## 3. Start the Telephony Gateway
Run the docker-compose stack to bring the Asterisk engine online:
```powershell
docker-compose up -d
```

## 4. Trigger the "Dry Run" Discovery
Use the `telephony_dispatch_test` tool to place a call to your Linphone instance.

### Example Tool Call:
```json
{
  "sip_uri": "sip:linphone@localhost"
}
```

## 5. Expected Results
1. Your **Linphone** app should begin ringing.
2. Accept the call.
3. You should hear the AI's digital voice distinctly stating: 
   *"Achtung. Dies ist ein Test der RoboFang Rettungskette..."*

> [!TIP]
> **No Airgap**: Notice that you are hearing the AI perfectly even if your PC microphone is muted. This proves the **Clean Bridge** is working correctly and the fleet is ready for dispatch.

---
**Next Step**: Once you've confirmed the Linphone test, you can add your real **Austrian SIP Credentials** to the `asterisk/pjsip.conf` to enable calls to your relatives' mobile phones.
