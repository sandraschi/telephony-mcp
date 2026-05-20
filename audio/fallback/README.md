# Fallback audio files for telephony-mcp
#
# These WAV files are played when speechops is unreachable.
# Format: 8kHz, 16-bit, mono, PCM (Asterisk native slin format).
#
# Required files:
#   emergency.wav  — "Achtung. Dies ist ein automatischer Notfall-Anruf der RoboFang Rettungskette. Bitte rufen Sie sofort zurueck."
#   test.wav       — "Achtung. Dies ist ein Test der RoboFang Rettungskette. Bitte bestaetigen Sie den Empfang."
#
# Generate with e.g. espeak-ng or any TTS, then convert:
#   ffmpeg -i input.mp3 -ar 8000 -ac 1 -acodec pcm_s16le emergency.wav
#
# Without these files present, telephony-mcp will log a warning and
# the call will connect but play silence before hanging up.
