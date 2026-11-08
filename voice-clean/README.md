# Voice Clean (Android)

Removes background noise from a video and keeps the voice of the person talking. The picture is copied
untouched (no re-encoding, no quality loss); only the sound is cleaned and saved again as AAC in an MP4.

**Install:** download [`VoiceClean.apk`](VoiceClean.apk) on the phone, open it, and allow "install unknown apps"
for your browser or file manager when Android asks. Android 7.0 or newer.

**Use:** Choose video (or *Share* a video from the gallery to Voice Clean) → set *Noise removal* → *Remove
background noise* → compare **Cleaned** and **Original** → *Save to phone* or *Share*. Everything runs on the
phone; nothing is uploaded.

## How the cleaning works (1.1)

1. The sound track is decoded to mono and converted to 48 kHz (`Resampler.java`).
2. **Neural voice filter** (`NeuralCleaner.java`, native code in `libs/`): RNNoise 0.2, a recurrent neural
   network trained on thousands of hours of speech and noise, keeps what sounds like a human voice and
   removes the rest, 10 ms at a time. Its speech detector also turns down whatever is left between words.
3. **Noise-profile cleaner** (`Denoiser.java`, the 1.0 engine): learns the background that is still left
   from the pauses and removes it (log-spectral-amplitude gain, rumble and hiss cut).
4. **Level:** a quiet voice is raised to a normal level, with a soft limiter so it never clips.

If the native library cannot load (for example on an x86 emulator) the app says so on its first screen and
uses step 3 alone.

Measured on a desktop with the same code (`tools/NeuralCli.java` then `tools/DenoiseCli.java`), speech mixed
with noise as loud as the voice; "pauses" is the background left between words (lower is better):

| noise | original | 1.0 | 1.1 |
|---|---|---|---|
| fan + hum | −24 dB | −53 dB | **−70 dB** |
| wind | −25 dB | −44 dB | **−79 dB** |
| hiss | −24 dB | −52 dB | **−76 dB** |
| traffic | −24 dB | −40 dB | **−48 dB** |
| music | −24 dB | −41 dB | −41 dB |
| other people talking | −24 dB | −31 dB | −31 dB |

The voice itself also comes out 1–6 dB cleaner than in 1.0. Music and other voices *at the same moment*
as the speaker remain hard: the filter cannot tell which voice is "the" speaker. `demo-before-after.m4a`
plays each test before (beep) and after.

The native ARM code was checked under QEMU against the desktop build (same output within −47 dB).

## Build

`libs/<abi>/libvoiceclean.so` (arm64-v8a, armeabi-v7a) is prebuilt. To rebuild it, get RNNoise 0.2 with its
model from Ubuntu (`https://archive.ubuntu.com/ubuntu/pool/universe/r/rnnoise/rnnoise_0.2+ds.orig.tar.xz`,
sha256 `db2718ee4a0b294bfbbe198fe94aabfdc8cd0d77cb9cd95d76c7a818ad805f0b`) and run
`RNNOISE=<unpacked dir> JDK_INCLUDE=<jdk>/include ./jni/build-native.sh $PWD/libs` (plain clang + lld,
no NDK). RNNoise is BSD licensed, see `jni/RNNOISE-COPYING`.

The APK: no Android SDK needed (same approach as `../launchpad-android`), see the header of `build.sh` for the tools:

    TOOLS=<tools dir> KEYSTORE=voiceclean.p12 KEYPASS=<password> ./build.sh

Updates must be signed with the same keystore, or Android refuses to install them over the old app.
Bump `VERSION_CODE` for each update.
