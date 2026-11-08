# Voice Clean (Android)

Removes background noise from a video and keeps the voice of the person talking. The picture is copied
untouched (no re-encoding, no quality loss); only the sound is cleaned and saved again as AAC in an MP4.

**Install:** download [`VoiceClean.apk`](VoiceClean.apk) on the phone, open it, and allow "install unknown apps"
for your browser or file manager when Android asks. Android 7.0 or newer.

**Use:** Choose video (or *Share* a video from the gallery to Voice Clean) → set *Noise removal* → *Remove
background noise* → compare **Cleaned** and **Original** → *Save to phone* or *Share*. Everything runs on the
phone; nothing is uploaded.

## How the cleaning works (`src/com/valdek/voiceclean/Denoiser.java`)

1. The sound track is decoded to mono PCM.
2. **Listen pass:** for every frequency band the app learns the steady background — what is left in the
   pauses between words (hum, fan, air-con, engine, traffic, hiss, wind rumble).
3. **Clean pass:** each ~21 ms slice of sound is split into frequencies; bands that are only background are
   turned down (Ephraim–Malah log-spectral gain, which avoids the "watery" artefacts of simple noise gates).
   A noise tracker follows background that changes during the video, and a voice detector lowers everything
   further while nobody is speaking. Optional voice-band filter cuts rumble below ~80 Hz and hiss above 10 kHz.
4. **Level:** a quiet voice is raised to a normal level, with a soft limiter so it never clips.

Settings: *Noise removal* 0–100 % (default 60). Higher removes more but can make the voice thinner.

Works best on steady noise. Other people talking or music behind the speaker are much harder: they are
reduced in the pauses, but anything that sounds like a voice at the same moment as the speaker stays.

Tested on a desktop with the same engine (`tools/DenoiseCli.java`) on speech mixed with fan/hum, hiss and
traffic noise: about 30 dB less background in the pauses, and 2–13 dB better voice-to-noise during speech.

## Build

No Android SDK needed (same approach as `../launchpad-android`), see the header of `build.sh` for the tools:

    TOOLS=<tools dir> KEYSTORE=voiceclean.p12 KEYPASS=<password> ./build.sh

Updates must be signed with the same keystore, or Android refuses to install them over the old app.
Bump `VERSION_CODE` for each update.
