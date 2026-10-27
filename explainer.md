# Web Tempo Sync Explainer

## Introduction

Making music on the web is the lowest barrier to entry there is: open a link and play. But a web instrument plays alone. A student working through a lesson on [learn.ableton.com](https://learn.ableton.com), a live coder in [Strudel](https://strudel.cc), or someone trying a synth on their phone can't play in time with the DAW on their laptop, the groovebox on the desk, or the friend across the room.

Outside the browser, musicians solve this with [Ableton Link](https://www.ableton.com/link/), a local-network protocol that keeps tempo, beat phase and start/stop in step across apps and devices, with no master clock and no setup. Live, Bitwig, Traktor, Rekordbox, Serato, Push, Move, MPCs and hundreds of mobile apps speak it. Web pages can't: joining takes UDP multicast, which no web page can do, and no browser offers anything like it.

Web Tempo Sync lets a web page join that shared timeline. The browser does the networking and clock synchronization; the page captures snapshots of the timeline to schedule audio and visuals, and commits changes to it. The specification is independent of any protocol. Link is how browsers would implement it today, and the reason it's worth doing.

**This is about reach, not timing.** Every alternative available today needs a native install: a helper app, a browser extension with a helper, a desktop wrapper. That rules out the cases that matter most for lowering the barrier: a lesson that just works, a phone, a school Chromebook. We built one of those alternatives ([an extension and helper](https://baylesj.github.io/web-tempo-sync-demo/#setup)) and its timing is fine. What it can't do is reach people.

## Goals

* Let web pages play in time (shared tempo, bar phase and start/stop) with music software and hardware on the local network, and with each other.
* Work with no installation, on desktop and mobile.
* Fit Web Audio scheduling: times in `AudioContext.currentTime` or `performance.now()`, usable from the main thread, Workers and AudioWorklets.
* Never let one page disrupt everyone else's playing by accident.
* Reveal as little as possible about the local network: one permission, one bit of presence, no addresses or device details.

## Non-goals

* Exposing raw UDP or multicast sockets to web pages.
* Defining a network protocol. The specification defines the timeline model; browsers implement it with existing protocols.
* Carrying audio or MIDI between devices. Only timing and transport are shared.
* Playing together over the internet. Link and similar protocols are designed for local networks with low jitter.
* Replacing MIDI clock over cables, which Web MIDI already handles.

## Motivating use cases

1. **Music education (the motivating case).**
   Ableton's [Learning Music and Learning Synths](https://learn.ableton.com) teach rhythm, harmony and synthesis interactively in the browser. A lesson that plays in time with the student's Live set, Push or Move, with nothing to install, turns an exercise into playing along. This is the case that needs the lowest barrier: a learner shouldn't have to install a helper to follow a lesson.

2. **Live coding and visuals.**
   [Strudel](https://strudel.cc) (TidalCycles in the browser) and [Hydra](https://hydra.ojack.xyz) (live-coded visuals) are mainstays of algorave performance, often run side by side, and often next to a DAW or drum machine. Strudel's maintainers have wanted Link since 2023 ([issue #611](https://github.com/tidalcycles/strudel/issues/611)); two attempts ([#394](https://github.com/tidalcycles/strudel/pull/394), [#719](https://github.com/tidalcycles/strudel/pull/719)) were closed unfinished, and the issue concludes it would need a node server or a desktop app. An open pull request on Strudel's current home ([uzu/strudel#2135](https://codeberg.org/uzu/strudel/pulls/2135)) adds a pluggable external clock to follow MIDI clock, citing the same request. With this API, a Strudel tab, a Hydra tab and Live stay in time with no install.

3. **Visuals for DJs and performers.**
   DJ software (Rekordbox, Serato, Traktor) speaks Link. Browser-based visuals can follow the set's tempo and bar phase.

4. **Web DAWs, sequencers and instruments.**
   Web DAWs (Soundtrap, BandLab, Amped Studio) and web instruments can lock to the other gear on stage or in the studio.

5. **A phone in the room.**
   Someone with Live or a Move opens a web instrument or practice tool on their phone, on the same Wi-Fi, and it plays in time. This depends most on how Android handles local networking (see [Android](#android)).

6. **Many devices, one URL.**
   A class or ensemble opens the same page on phones, tablets and Chromebooks and plays together.

## Proposed API

A page calls `navigator.tempoSync.requestSession()`, which asks the user for permission the first time and returns a `TempoSession`. The page captures snapshots of the shared timeline with `captureState()`, schedules from them, and commits changes with `commitState()`.

```webidl
[SecureContext]
partial interface Navigator {
  readonly attribute TempoSync tempoSync;
};

[SecureContext, Exposed=Window]
interface TempoSync {
  Promise<TempoSession> requestSession(optional TempoSessionOptions options = {});
};

dictionary TempoSessionOptions {
  double quantum = 4;
};

[SecureContext, Exposed=Window]
interface TempoSession : EventTarget {
  readonly attribute boolean hasPeers;
  readonly attribute double quantum;
  TempoSessionState captureState(optional BaseAudioContext context);
  undefined commitState(TempoSessionState state);
  undefined close();
  attribute EventHandler onpeerschange;
  attribute EventHandler ontimelinechange;
  attribute EventHandler onplayingchange;
};

[SecureContext, Exposed=(Window,Worker,AudioWorklet), Serializable]
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

### Code examples

#### Example 1: Lookahead scheduling in a step sequencer

Web Audio apps schedule a little ahead of `AudioContext.currentTime`. Passing the context to `captureState()` puts the snapshot's times in that clock.

```javascript
const audioCtx = new AudioContext();
const session = await navigator.tempoSync.requestSession({ quantum: 4 });

let nextBeat = null;
const lookahead = 0.1; // seconds

function scheduler() {
  const state = session.captureState(audioCtx);
  const now = audioCtx.currentTime;

  if (state.isPlaying) {
    nextBeat ??= Math.ceil(state.beatAtTime(now));
    while (state.timeAtBeat(nextBeat) < now + lookahead) {
      scheduleClick(nextBeat, state.timeAtBeat(nextBeat), state.phaseAtTime(state.timeAtBeat(nextBeat)));
      nextBeat += 1;
    }
  } else {
    nextBeat = null;
  }
  setTimeout(scheduler, 25);
}

function scheduleClick(beat, time, phase) {
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.frequency.value = phase < 0.01 ? 880 : 440; // accent the downbeat
  gain.gain.setValueAtTime(0.2, time);
  gain.gain.exponentialRampToValueAtTime(0.001, time + 0.05);
  osc.connect(gain).connect(audioCtx.destination);
  osc.start(time);
  osc.stop(time + 0.05);
}

scheduler();
```

#### Example 2: Starting a loop on the next bar

A lesson wants its four-bar exercise to start at beat 0, on a bar line, without moving anyone else's bars. `requestBeatAtTime()` waits for the next point where the session's phase matches and numbers it beat 0 for this page only. If the page is alone in the session, it starts right away.

```javascript
startButton.addEventListener("click", () => {
  const state = session.captureState(audioCtx);
  state.requestBeatAtTime(0, audioCtx.currentTime, 4);
  if (!state.isPlaying) {
    state.setIsPlaying(true, state.timeAtBeat(0, 4));
  }
  session.commitState(state);
  exercise.startAt(state.timeAtBeat(0, 4)); // the next bar line, or now if alone
});
```

#### Example 3: A visual beat indicator

Without an `AudioContext`, times are `performance.now()` in seconds, which suits `requestAnimationFrame`.

```javascript
function draw() {
  const state = session.captureState();
  const phase = state.phaseAtTime(performance.now() / 1000, 4);
  indicator.textContent = `Beat ${Math.floor(phase) + 1}`;
  indicator.style.opacity = phase % 1 < 0.2 ? "1" : "0.4";
  requestAnimationFrame(draw);
}
requestAnimationFrame(draw);
```

#### Example 4: Changing tempo and transport

```javascript
tempoInput.addEventListener("change", () => {
  const state = session.captureState();
  state.setTempo(Number(tempoInput.value), performance.now() / 1000);
  session.commitState(state);
});

playButton.addEventListener("click", () => {
  const state = session.captureState(audioCtx);
  const now = audioCtx.currentTime;
  // Start or stop on the next bar line.
  const nextBar = Math.ceil(state.beatAtTime(now, 4) / 4) * 4;
  state.setIsPlaying(!state.isPlaying, state.timeAtBeat(nextBar, 4));
  session.commitState(state);
});
```

#### Example 5: Scheduling in an AudioWorklet

Snapshots are serializable. The main thread posts one to its processor whenever the timeline changes, and the processor reads it in its own `currentTime`, with no message per block.

```javascript
// Main thread
const node = new AudioWorkletNode(audioCtx, "clicker");
const send = () => node.port.postMessage(session.captureState(audioCtx));
send();
session.addEventListener("timelinechange", send);
session.addEventListener("playingchange", send);
```

```javascript
// clicker-processor.js
class Clicker extends AudioWorkletProcessor {
  constructor() {
    super();
    this.port.onmessage = (e) => (this.state = e.data); // a TempoSessionState
  }
  process(inputs, [output]) {
    const s = this.state;
    if (!s?.isPlaying) return true;
    const end = currentTime + 128 / sampleRate;
    const beat = Math.ceil(s.beatAtTime(currentTime));
    if (s.timeAtBeat(beat) < end) {
      const frame = Math.round((s.timeAtBeat(beat) - currentTime) * sampleRate);
      output[0][frame] = 1; // a one-sample click on the beat
    }
    return true;
  }
}
registerProcessor("clicker", Clicker);
```

#### Example 6: Showing whether anyone is playing along

```javascript
const status = () => (badge.textContent = session.hasPeers ? "Playing in time with your setup" : "Turn on Link in Live to play along");
session.addEventListener("peerschange", status);
status();
```

## Detailed design discussion

### Snapshots: capture and commit

Why snapshots instead of live properties like `session.tempo`? Timing maths needs tempo, beat origin and time origin from the same moment. If they could change between reads, a page could combine the tempo from one grid with the position from another and glitch. A snapshot is consistent, and because a timeline is linear, it stays correct until the timeline changes, which the `timelinechange` and `playingchange` events announce.

Committing writes back only what the page changed. If another participant changes the tempo between a page's capture and commit, the commit doesn't undo it, unless the page also set a tempo.

### Shared phase, local beat numbers

Participants share tempo and **phase** (where the bar lines fall for a given quantum), not beat numbers. Each session numbers beats its own way. That's what makes `requestBeatAtTime()` safe: a page that wants its pattern to start at beat 0 waits for the next bar line and calls it beat 0, and nobody else's music moves. `forceBeatAtTime()` is the deliberate exception. It moves the bar lines for everyone, by up to half a quantum, and is meant for apps that must put a beat at an exact time.

The `quantum` arguments give beat numbers meaning across quanta: a page's beats keep the shared phase for whichever quantum it asks about.

An earlier draft shared one beat grid and had `requestBeatAtTime()` move it. Starting a loop in one browser tab would then jump the bar lines in Live mid-song.

### One participant per browser

If every tab were a separate network participant, three tabs would be three peers flooding the network, and other devices could count a user's tabs. The browser takes part as one participant, its documents share that endpoint, and changes between tabs need no network round trip.

### Only one bit about peers

`hasPeers` tells a page whether anyone else is in the session. That's all the motivating cases need: "you're playing in time with your setup" or "turn on Link to play along". A count, or anything about which devices are present, would add to fingerprinting and reveal more about the user's network for little benefit. A browser can still show more in its own UI, such as how many devices it is synced with, without exposing it to pages.

### Workers and AudioWorklets

Serious audio engines run in an `AudioWorklet` or a Worker, which can't show a permission prompt or own a session. Rather than exposing the whole API there, `TempoSessionState` is serializable. The main thread captures and posts a snapshot when the timeline changes. The worker or processor schedules from it in its own clock: `currentTime` for a processor of the same context, or the worker's own `performance.now()`. It can post a modified snapshot back for the main thread to commit.

An open question is whether Workers should be able to request sessions directly, given that permission would already have been granted to the document.

### Time base mapping

`captureState(context)` returns times in `context.currentTime`. Without a context, times are in `performance.now()` seconds. The browser maps between these and its host clock. For audio, that means estimating drift between the audio device's clock and the host clock, and output latency. The browser should map to the time at which audio reaches the output, as `AudioContext.getOutputTimestamp()` does, and smooth the estimate.

### Android

The design is expected to carry over to Chrome on Android. Ableton Link already runs in Android apps (through the NDK), and the browser process, not the page, owns the protocol, as on desktop. The differences are in the platform around it:

* **Receiving multicast.** Android filters incoming multicast unless the app holds a `WifiManager.MulticastLock`, which needs the `CHANGE_WIFI_MULTICAST_STATE` permission. The browser would take the lock only while at least one tab has an open session, and release it when the last one closes, since holding it costs battery.
* **Local network permission.** Android is adding a runtime permission for local network access, previewed in Android 16. The browser would need it in addition to the per-origin `"tempo-sync"` prompt this proposal defines, and the two prompts should read as one decision to the user where possible. Chrome's Local Network Access permission for web pages is a related precedent worth aligning with.
* **Background tabs.** Chrome on Android throttles, freezes and may discard background tabs, and the OS can stop the browser process. A frozen page cannot schedule audio, so a session is only useful while its tab is visible or playing audio. A reasonable rule: the browser stays joined to the session while any tab with a session is in the foreground or audible, and leaves it when none is.
* **Audio latency.** Output latency is higher on Android and varies more between devices. That makes the `AudioContext` time mapping in `captureState()`, including the reported output latency, more important on Android than on desktop.
* **Networks.** Phones are often on networks where local sync cannot work: guest Wi-Fi and hotspots with client isolation, or mobile data. Pages should treat `hasPeers` being false as a normal state and say so, not as an error.

Open question: should the browser keep the session alive briefly after the last tab is backgrounded, so that switching apps mid-performance doesn't drop the device out of the session?

## Considered alternatives

Each of these works for someone today. None of them works without installing something, which rules out the motivating cases.

### 1. A browser extension with a native helper

We built this: [an extension and helper](https://baylesj.github.io/web-tempo-sync-demo/#setup) that give stable Chrome `navigator.tempoSync`. It plays in time with Live. Timing isn't the problem: the extension estimates the offset between the page's clock and the helper's from the fastest of many pings, and measured a best round trip of 0.3 ms (median about 2 ms), so its error is around a tenth of a millisecond.

* **Trade-off**: The user installs a native helper and an extension that can read every site. It can't run on Android, ChromeOS or iOS. An educational site can't ask a learner to do this.

### 2. A local helper app over WebSocket

The usual approach, and the one Strudel's Link issue proposed: a native or Node.js process joins Link and relays the timeline to the page over `ws://localhost`. A variant needs no new install for Live users: a Max for Live device in Live serving the timeline.

* **Trade-off**: Something must be installed and running. Public sites reaching `localhost` also go through Chrome's Local Network Access prompt. Desktop only.

### 3. MIDI clock over Web MIDI

On one machine, Live can send MIDI clock to a virtual MIDI port that a page reads with Web MIDI.

* **Trade-off**: Tempo and song position only, between two programs, set up by hand. There's no shared phase among several participants, and not every browser supports Web MIDI.

### 4. Direct Sockets in an Isolated Web App

An Isolated Web App can use Direct Sockets, including multicast, and could run a protocol implementation compiled to WebAssembly.

* **Trade-off**: Ordinary websites can't use Direct Sockets, and Isolated Web Apps are hard to distribute to most users today. Every app would also carry its own implementation of the protocol.

### 5. A native or desktop app

Wrap the web app in Electron or Tauri, or build a native app, and use Link's library directly.

* **Trade-off**: It's no longer the web: a download, per-platform builds, and an app store on mobile.

### 6. A web-only sync protocol over WebRTC

Pages could sync with each other through a signaling server.

* **Trade-off**: It only syncs browsers with browsers, not the DAWs, hardware and apps musicians already use.

## Privacy and security considerations

* **Permission.** Joining a session takes a per-origin permission. The prompt should say that the site will be able to tell whether music apps or devices on the network are playing along.
* **One bit of presence.** Pages learn only `hasPeers`. No counts, addresses, ports or device names.
* **One participant per browser.** Other devices can't count a user's tabs.
* **Disruption.** The browser rate-limits shared changes, and beat numbering is local, so a page can't move other people's bar lines except with `forceBeatAtTime()`.
* **Cross-origin.** Origins with sessions open share one timeline, so cooperating origins could signal through it, as they could through any device on the network. The session isn't an isolation boundary.
* **Embedding.** Secure contexts only. Iframes need `allow="tempo-sync"`.

## Stakeholder feedback

* **Ableton**: The motivating case is learn.ableton.com.
* **Strudel**: Its maintainers have wanted Link support since 2023 ([#611](https://github.com/tidalcycles/strudel/issues/611), [#394](https://github.com/tidalcycles/strudel/pull/394), [#719](https://github.com/tidalcycles/strudel/pull/719)), and a contributor is adding an external clock source ([uzu/strudel#2135](https://codeberg.org/uzu/strudel/pulls/2135)). We have not yet asked them about this proposal.
* **Others we plan to ask**: Hydra, Gibber, Flok and Estuary (live coding); Tone.js and Web Audio Modules (frameworks); Chrome Music Lab (education); web DAW vendors; hardware makers with browser companion apps.
* **Browser vendors**: Chromium has a prototype behind `--enable-blink-features=TempoSync`. Mozilla and WebKit positions are not yet requested.

See [OBJECTIONS.md](OBJECTIONS.md) for the objections we expect, and our answers.

## References

* [Ableton Link](https://www.ableton.com/link/) and its [source code](https://github.com/Ableton/link)
* [Web Audio API](https://www.w3.org/TR/webaudio/)
* [High Resolution Time](https://www.w3.org/TR/hr-time/)
* [Permissions Policy](https://w3c.github.io/webappsec-permissions-policy/)
* [Local Network Access](https://wicg.github.io/local-network-access/)
* [A Tale of Two Clocks: Lookahead Scheduling in Web Audio](https://web.dev/audio-scheduling/)
