# Web Tempo Sync Explainer

## Introduction

Music creation tools on the web include web-based digital audio workstations (DAWs), synthesizers, drum machines, live coding environments, and interactive music education sites. Today, these applications run in isolation. A musician playing a synth in a browser cannot easily play in tempo with a friend using Ableton Live, an iOS groovebox, or a hardware instrument on the same Wi-Fi network.

Outside the browser, musicians solve this problem using Ableton Link. Ableton Link is a peer-to-peer network protocol over UDP multicast. It synchronizes musical tempo, beat grid, phase, and start/stop state across independent devices without a central clock master.

Web Tempo Sync brings native tempo synchronization to the web platform. The browser manages network discovery, UDP sockets, and distributed clock consensus in native code. Web applications interact with a high-level API to capture synchronized timeline snapshots and coordinate audio playback.

## Goals

* Enable web audio applications to synchronize tempo, beat position, and musical phase with local-network musical software and hardware.
* Support optional shared start/stop transport state across peers.
* Align seamlessly with the Web Audio API (`AudioContext.currentTime`) and high-resolution timing (`performance.now()`).
* Support robust scheduling patterns, including lookahead audio scheduling and visual playhead rendering.
* Protect user privacy and local network security by avoiding raw socket exposure, IP address leakage, and fingerprinting vectors.

## Non-goals

* Exposing raw UDP or multicast sockets to web pages.
* Exposing remote peer IP addresses, network interfaces, or device identifiers.
* Transporting audio streams or MIDI events between devices. The API synchronizes timing and transport only.
* Internet-wide tempo synchronization over wide-area networks (WAN). Link is engineered for local area networks with low packet jitter.
* Replacing existing Web MIDI 1.0 clock messages where hardware DIN/USB MIDI cabling is already in use.

## User Research and Motivating Use Cases

Musicians and developers encounter several common scenarios where browser-based tempo synchronization is missing:

1. **Music education platforms**:
   Interactive tutorial platforms, such as Ableton's "Learning Synths" and "Learning Music" (learn.ableton.com), teach rhythmic concepts directly in the browser. Students cannot sync browser exercises with an external DAW or groovebox without exporting audio files. With Web Tempo Sync, a student can jam in the browser alongside an external drum machine.

2. **Browser-based DAWs and sequencers**:
   Web DAWs (such as Soundtrap, BandLab, and Amped Studio) and in-browser modular synths allow users to compose and produce music. In collaborative live performance settings, multiple musicians often play together on a local network. Web DAWs currently have no native way to lock tempo with other musicians on stage.

3. **Multi-device web ensembles**:
   Musicians using phones, tablets, and laptops can open a web synthesizer URL and immediately form a synchronized ensemble over local Wi-Fi.

4. **Hybrid software and hardware setups**:
   Standalone hardware devices (such as Akai MPCs, Ableton Push 3, and Teenage Engineering devices) speak Ableton Link over Wi-Fi. A web-based synthesizer running on a laptop can lock to hardware grooves with zero configuration.

5. **A phone in the room**:
   A musician with an Ableton Move or a laptop running Live opens a web instrument or a practice tool on their Android phone, on the same Wi-Fi, and it plays in time with no app to install. This is the most direct mobile case, and the one that depends most on how Android handles local networking (see [Android](#android)).

## Proposed API

The API exposes a `TempoSync` entry point on `navigator` in secure contexts. Calling `navigator.tempoSync.requestSession()` prompts the user for permission (if not already granted) and returns a `TempoSession`.

```webidl
[SecureContext]
partial interface Navigator {
  readonly attribute TempoSync tempoSync;
};

interface TempoSync {
  Promise<TempoSession> requestSession(optional TempoSessionOptions options = {});
};

dictionary TempoSessionOptions {
  double quantum = 4;
  boolean startStopSync = false;
};

interface TempoSession : EventTarget {
  readonly attribute unsigned long numPeers;
  readonly attribute double quantum;
  TempoSessionState captureState(optional BaseAudioContext context);
  undefined commitState(TempoSessionState state);
  undefined close();
  attribute EventHandler onnumpeerschange;
  attribute EventHandler ontempochange;
  attribute EventHandler onplayingchange;
};

interface TempoSessionState {
  readonly attribute double tempo;
  undefined setTempo(double bpm, double atTime);
  double beatAtTime(double time, optional double quantum);
  double phaseAtTime(double time, optional double quantum);
  double timeAtBeat(double beat, optional double quantum);
  undefined requestBeatAtTime(double beat, double time, optional double quantum);
  undefined forceBeatAtTime(double beat, double time, optional double quantum);
  readonly attribute boolean isPlaying;
  readonly attribute double timeForIsPlaying;
  undefined setIsPlaying(boolean playing, double atTime);
};
```

### Code Examples

#### Example 1: Lookahead Audio Scheduling in a Step Sequencer

Web Audio applications typically schedule audio events slightly ahead in time using `AudioContext.currentTime` to avoid glitches. Passing the `AudioContext` to `captureState()` aligns the tempo session timeline with `context.currentTime`.

```javascript
const audioCtx = new AudioContext();
const session = await navigator.tempoSync.requestSession({ quantum: 4 });

let nextBeatToSchedule = 0;
const scheduleAheadTime = 0.1; // 100 ms lookahead window

function scheduler() {
  // Capture an immutable snapshot mapped to audioCtx.currentTime.
  const state = session.captureState(audioCtx);

  if (state.isPlaying) {
    const currentAudioTime = audioCtx.currentTime;
    const windowEndTime = currentAudioTime + scheduleAheadTime;

    // Find the beat number corresponding to the lookahead boundary.
    const maxBeatInWindow = state.beatAtTime(windowEndTime);

    while (nextBeatToSchedule < maxBeatInWindow) {
      const beatTime = state.timeAtBeat(nextBeatToSchedule);
      if (beatTime >= currentAudioTime) {
        scheduleNoteOn(nextBeatToSchedule, beatTime);
      }
      nextBeatToSchedule += 1.0; // Advance by quarter note (1 beat)
    }
  }

  setTimeout(scheduler, 25);
}

function scheduleNoteOn(beat, time) {
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.frequency.value = (beat % 4 === 0) ? 880 : 440;
  gain.gain.setValueAtTime(0.2, time);
  gain.gain.exponentialRampToValueAtTime(0.001, time + 0.05);
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.start(time);
  osc.stop(time + 0.05);
}

scheduler();
```

#### Example 2: Visual Beat Indicator Using `performance.now()`

When no `AudioContext` is passed to `captureState()`, the time base defaults to `performance.now()` expressed in seconds. This fits UI rendering loops driven by `requestAnimationFrame`.

```javascript
const session = await navigator.tempoSync.requestSession({ quantum: 4 });
const indicator = document.querySelector("#beat-indicator");

function draw() {
  // Time base is performance.now() in seconds.
  const state = session.captureState();
  const nowInSeconds = performance.now() / 1000.0;

  // phaseAtTime returns a value in [0, quantum), representing position in the bar.
  const phase = state.phaseAtTime(nowInSeconds, 4.0);
  const beatIndex = Math.floor(phase);

  indicator.textContent = `Beat: ${beatIndex + 1} (${phase.toFixed(2)})`;
  indicator.style.opacity = (phase - beatIndex < 0.2) ? "1.0" : "0.4";

  requestAnimationFrame(draw);
}

requestAnimationFrame(draw);
```

#### Example 3: Changing Tempo and Transport State

Applications modify session state by modifying a captured snapshot and committing it back to the session.

```javascript
const session = await navigator.tempoSync.requestSession({
  quantum: 4,
  startStopSync: true
});

const tempoInput = document.querySelector("#bpm");
const playBtn = document.querySelector("#play-toggle");

tempoInput.addEventListener("change", () => {
  const state = session.captureState();
  const now = performance.now() / 1000.0;
  state.setTempo(parseFloat(tempoInput.value), now);
  session.commitState(state);
});

playBtn.addEventListener("click", () => {
  const state = session.captureState();
  const now = performance.now() / 1000.0;
  state.setIsPlaying(!state.isPlaying, now);
  session.commitState(state);
});
```

#### Example 4: Reacting to Network Peer Changes

A session notifies the page when peers join or leave the local network session.

```javascript
const session = await navigator.tempoSync.requestSession();
const peerCountDisplay = document.querySelector("#peer-count");

function updatePeerCount() {
  peerCountDisplay.textContent = `Connected Link Peers: ${session.numPeers}`;
}

session.addEventListener("numpeerschange", updatePeerCount);
session.addEventListener("tempochange", () => {
  const state = session.captureState();
  console.log(`New session tempo: ${state.tempo} BPM`);
});

updatePeerCount();
```

## Detailed Design Discussion

### Capture and Commit Snapshots

A common API design question is why `TempoSession` uses `captureState()` and `commitState()` snapshots rather than live getters like `session.tempo` or `session.currentBeat`.

There are two primary reasons:
1. **Avoiding torn reads**:
   In audio programming, musical timing calculations require consistent evaluations of tempo, beat origin, and time origin. If properties updated dynamically between separate property accesses, an application could read tempo from one beat grid and beat position from a subsequent grid update. This causes jitter and audible glitches. A snapshot provides an immutable view of the timeline for a given calculation pass.
2. **Atomic audio callback integration**:
   Audio engines process blocks of audio on a real-time thread or in an `AudioWorklet`. The host application captures the session state at the beginning of an audio render pass, processes all buffer frames against that static snapshot, and commits any user edits atomically at the end.

### Single Session Per Browser Profile

The underlying Ableton Link protocol assumes one logical endpoint per host process or network participant. If every open browser tab created an independent Link peer, a user opening three musical tabs on the same computer would see three peers competing and flooding local network multicast.

Under this specification, the browser runs a single Link endpoint per user profile. All tabs requesting a session share this underlying endpoint. When multiple tabs connect, the browser acts as a single peer on the network. Tab-to-tab synchronization happens within the browser process without network overhead.

### Browser Ownership of Sockets

Exposing raw UDP sockets to web pages presents severe security risks. Multicast UDP sockets allow local network discovery, device fingerprinting, and potential amplification attacks.

By having the browser own the UDP socket and protocol implementation:
* The page cannot craft arbitrary network packets.
* The page cannot discover IP addresses, MAC addresses, or hardware details of other devices on the network.
* The browser can enforce permissions, pause network activity when tabs are backgrounded, and rate-limit state modifications.

### Time Base Mapping and Error Sources

`captureState()` accepts an optional `BaseAudioContext`. When supplied, time arguments and return values use `context.currentTime`. When omitted, the time base is `performance.now()` in seconds.

The browser maps between these clocks and the underlying system host clock:
* `performance.now()` measures monotonic time since document navigation start.
* `AudioContext.currentTime` measures time elapsed in the audio hardware buffer pipeline.

Mapping between the audio hardware clock and system host time is subject to two sources of error:
1. **Clock drift**: The audio output DAC crystal oscillator runs at a slightly different rate than the CPU host clock.
2. **Buffer latency**: Audio output buffers introduce a fixed or dynamic delay between when a buffer is scheduled and when sound leaves the speakers.

The browser implementation runs continuous clock drift estimation to align `AudioContext.currentTime` with the network timeline. The spec defines the mapping points at the boundary of each captured snapshot.

### Quantum and Phase

Musical sync requires more than identical tempo. It requires alignment on bar boundaries (phase).

* **Quantum**: The number of beats in a musical cycle or bar. Standard 4/4 time has a quantum of 4. A 3/4 waltz has a quantum of 3.
* **Phase**: The instantaneous position within the bar, defined as `phase = beat mod quantum`.
* **Beat realignment**: When a user jumps to a new beat position, `requestBeatAtTime()` shifts the beat grid while maintaining continuous phase alignment with the rest of the network. In contrast, `forceBeatAtTime()` sets an absolute beat position immediately.

### Android

The design is expected to carry over to Chrome on Android. Ableton Link already runs in Android apps (through the NDK), and the browser process, not the page, owns the protocol, as on desktop. The differences are in the platform around it:

* **Receiving multicast.** Android filters incoming multicast unless the app holds a `WifiManager.MulticastLock`, which needs the `CHANGE_WIFI_MULTICAST_STATE` permission. The browser would take the lock only while at least one tab has an open session, and release it when the last one closes, since holding it costs battery.
* **Local network permission.** Android is adding a runtime permission for local network access, previewed in Android 16. The browser would need it in addition to the per-origin `"tempo-sync"` prompt this proposal defines, and the two prompts should read as one decision to the user where possible. Chrome's Local Network Access permission for web pages is a related precedent worth aligning with.
* **Background tabs.** Chrome on Android throttles, freezes and may discard background tabs, and the OS can stop the browser process. A frozen page cannot schedule audio, so a session is only useful while its tab is visible or playing audio. A reasonable rule: the browser stays joined to the Link session while any tab with a session is in the foreground or audible, and leaves it (so `numPeers` elsewhere drops) when none is.
* **Audio latency.** Output latency is higher on Android and varies more between devices. That makes the `AudioContext` time mapping in `captureState()` (see [Time Base Mapping and Error Sources](#time-base-mapping-and-error-sources)), including the reported output latency, more important on Android than on desktop.
* **Networks.** Phones are often on networks where Link cannot work: guest Wi-Fi and hotspots with client isolation, or mobile data. Pages should treat `numPeers` of 0 as a normal state and say so, not as an error.

Open question: should the browser keep the session alive briefly after the last tab is backgrounded, so that switching apps mid-performance doesn't drop the device out of the session?

## Considered Alternatives

### 1. Local Helper Application over WebSocket

Many web audio developers currently instruct users to run a native helper application (such as a local Node.js or C++ daemon) that connects to Ableton Link and relays messages over a local WebSocket.

* **Trade-off**: Requires the user to download, install, and execute unverified native software outside the browser sandbox. This introduces security friction and is impossible on mobile operating systems like iOS or ChromeOS.

### 2. Direct Sockets Multicast

The Direct Sockets API provides UDP socket access, but is restricted to Isolated Web Apps (IWAs).

* **Trade-off**: Standard websites cannot use Direct Sockets. Furthermore, requiring every web page to implement the complex Link protocol in JavaScript would result in incompatible implementations and high battery drain.

### 3. Exposing MIDI Clock over Web MIDI

The Web MIDI API can receive and send MIDI 2.0 or MIDI 1.0 clock bytes.

* **Trade-off**: MIDI clock is a pulse-based protocol (24 pulses per quarter note) designed for point-to-point cables. It does not provide distributed consensus, does not handle packet loss on wireless networks, and requires external MIDI routing configuration.

### 4. Page-to-Page WebRTC Sync Protocol

A web-only synchronization protocol could be designed using WebRTC Data Channels and a public signaling server.

* **Trade-off**: This approach would only sync web browsers with other web browsers. It would fail to interoperate with existing hardware (Ableton Push, MPCs, synthesizers) and DAWs (Ableton Live, Bitwig, Logic Pro) that already speak Ableton Link.

## Privacy and Security Considerations

### Local Network Presence and Peer Count Leakage

Ableton Link broadcasts UDP discovery packets on the local subnet. If a web page could freely join a Link session, it could detect whether other Link-enabled devices are active on the local network. The `numPeers` attribute could reveal the presence of studio hardware or specific workstations.

Mitigations:
* **Explicit permission prompt**: Joining a session requires user consent via a permission prompt modeled on Local Network Access and Web MIDI.
* **No network identifiers**: The API does not expose peer IP addresses, port numbers, hostnames, or hardware UUIDs. Only the aggregate count of active peers is visible.
* **Secure Context required**: The API is restricted to HTTPS (`[SecureContext]`) and top-level browsing contexts.
* **Permissions Policy**: Embedded iframes cannot access the API unless granted by the `tempo-sync` feature policy.
* **Single endpoint per profile**: The browser acts as a single participant, preventing fingerprinting of internal tab structures.
* **Rate limits**: The browser throttles `commitState()` calls to prevent a rogue page from spamming multicast packets or disturbing other musicians on the network.

## Stakeholder Feedback

* **Ableton**: Favorable to browser integration of Link. Prototyping explores compatibility with the Link protocol specification.
* **Mozilla**: Pending review in standards venues.
* **Chromium**: Active prototype in development behind `--enable-blink-features=TempoSync`.

## References

* [Ableton Link Protocol and Source Code](https://github.com/Ableton/link)
* [W3C Web Audio API Specification](https://www.w3.org/TR/webaudio/)
* [W3C High Resolution Time](https://www.w3.org/TR/hr-time/)
* [W3C Permissions Policy](https://w3c.github.io/webappsec-permissions-policy/)
* [Local Network Access Specification](https://wicg.github.io/local-network-access/)
* [A Tale of Two Clocks: Lookahead Scheduling in Web Audio](https://web.dev/audio-scheduling/)

