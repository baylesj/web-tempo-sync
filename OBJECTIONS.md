# Web Tempo Sync: the objections we expect

The "no"s this proposal is likely to hear, who would raise them, our answer, and what is still open. Keep this current. An objection we've answered goes in the [explainer](explainer.md) too; one we haven't stays here as work to do.

Status: **Answered** means the explainer or spec covers it. **Partial** means we have an answer but need evidence or a decision. **Open** means we don't have an answer yet.

## Is it needed?

### 1. "Too niche for the web platform"
*From: Blink API owners, TAG, other browser vendors.*

The motivating case is music education at scale (learn.ableton.com). Live coding is a second community with a documented, years-old need: Strudel's Link request ([#611](https://github.com/tidalcycles/strudel/issues/611)), two closed attempts, and an open external-clock PR ([uzu/strudel#2135](https://codeberg.org/uzu/strudel/pulls/2135)). The protocol it builds on is supported by most major DAWs, DJ software, and a lot of hardware and mobile apps, so web pages would join an existing ecosystem rather than start one.

**Status: Partial.** We need developers saying so in public: comments on the Audio Community Group proposal or letters from Ableton, live-coding projects, web DAWs, Chrome Music Lab. One stakeholder isn't enough.

### 2. "Use an extension, a helper app, or a native wrapper"
*From: anyone who asks why it has to be in the browser.*

We built the extension and helper. It plays in time with Live, and its timing error is around 0.1 ms. The problem is reach: it needs a native install and an extension with access to every site, and it can't run on Android, ChromeOS or iOS. The cases that matter (a lesson that just works, a phone, a school Chromebook) are the ones no install can reach. See the explainer's considered alternatives.

**Status: Answered.**

### 3. "Ableton can do this themselves"
*From: reviewers who notice that the main stakeholder makes Live.*

For Live users on desktop, yes: a Max for Live device could serve the timeline to the page over `localhost`. That leaves out everyone without Live installed and running, every phone, and every other Link device. learn.ableton.com is for people who don't own Live yet.

**Status: Answered.**

### 4. "Direct Sockets already gives you multicast"
*From: Chromium networking and capabilities folks.*

Only in Isolated Web Apps, which ordinary sites can't be and which most users can't easily install today. It would also have every app ship its own protocol implementation.

**Status: Answered.**

## Standards

### 5. "This bakes one company's protocol into the web"
*From: TAG, Mozilla, WebKit.*

The specification defines the timeline model and doesn't name a protocol. Link is how browsers would implement it today, and the reason it's worth doing, so it appears only in the explainer. A future protocol, or several, could sit behind the same API.

**Status: Partial.** In practice, "interoperable" means "speaks Link", and Link has no published protocol specification; our implementation follows our own clean-room notes. If Ableton changes the protocol, browsers have to follow. **Ask Ableton** whether they would publish a protocol document, and make a statement on patents, under terms a standards body can reference.

### 6. "Only one engine will ship it"
*From: Blink API owners, at intent to ship.*

Likely true at first. WebKit doesn't ship Web MIDI and has been cautious about local network access. Mozilla's position is unknown.

**Status: Open.** Request [Mozilla](https://github.com/mozilla/standards-positions) and [WebKit](https://github.com/WebKit/standards-positions) standards positions early, while the API is small and easy to change. Keep the surface small: it is one permission, one session, snapshots, and no new network primitives.

### 7. "What does the timing guarantee?"
*From: implementers and Web Audio WG reviewers.*

The specification says the user agent should map to output time and smooth the audio clock mapping, but gives no accuracy figure.

**Status: Open.** Decide whether to state a target, such as phase error under 1 ms on a quiet network, as a non-normative goal.

## Privacy and security

### 8. "It reveals what's on my network"
*From: privacy reviewers, the TAG.*

Pages get one bit after a permission prompt: whether anyone else is in the session. They get no count, addresses, ports or device names. The browser takes part as a single participant, so other devices can't count tabs.

**Status: Partial.** The prompt wording matters: it has to say the site can tell whether music devices on the network are playing along. It also needs to line up with Local Network Access and, on Android, the OS local-network permission, so users don't face two prompts.

### 9. "Two sites can talk to each other through the shared timeline"
*From: privacy reviewers.*

True for origins that both hold the permission. They could already do it through any device on the network, by changing its tempo. The spec says the session isn't an isolation boundary.

**Status: Answered.** Expect it to be discussed anyway.

### 10. "A page can wreck everyone's set"
*From: musicians, the TAG.*

Beat numbering is per page. Starting a loop waits for the next bar line instead of moving anyone's bar lines, and only `forceBeatAtTime()` moves them. Shared changes are rate-limited. Commits only write what the page changed, so they don't undo other participants' changes.

**Status: Partial.** A page can still change the tempo or stop the transport for everyone, which is what the feature is for. Consider whether a user-visible indicator or a per-site "follow only" mode is needed.

### 11. "Battery, background tabs and network chatter"
*From: Android and Chrome performance folks.*

The browser leaves the session when no page with a session is visible or audible, holds Android's multicast lock only while a session is open, and there's one network participant whatever the number of tabs.

**Status: Partial.** The rules are in the explainer, but the spec only has a SHOULD. Measure the battery cost on Android.

## API design

### 12. "Snapshots instead of live properties are unusual"
*From: API reviewers.*

Timing maths needs tempo, beat and time origins from one moment, and live properties would allow torn reads. Snapshots stay correct until the `timelinechange` or `playingchange` events fire, so pages capture once per change or once per scheduling pass.

**Status: Answered.**

### 13. "It has to work where audio engines run"
*From: web DAW and framework developers.*

Snapshots are serializable: post one to a Worker or AudioWorklet, schedule there in its own clock, post changes back for the main thread to commit.

**Status: Partial.** Decide whether Workers should also be able to request sessions directly.

### 14. "quantum is confusing"
*From: developers new to Link's model.*

It's what makes local beat numbering work across bar lengths. The explainer explains it, with a "start on the next bar" example.

**Status: Partial.** Get a few developers who haven't used Link to try it, and see where they trip.

### 15. "Isn't browser audio too laggy for live playing?"
*From: musicians.*

Sync aligns output time, not schedule time, so a page with high output latency still sounds in time, as long as the latency is reported accurately. Android is the hard case.

**Status: Open.** Measure the prototype against Live on desktop and Android, using the demo's latency-measurement mode, and publish the numbers.

## Next steps

Each is tracked as an [issue](https://github.com/baylesj/web-tempo-sync/issues).

1. Get public support from Ableton, and from at least two other projects ([issue #1](https://github.com/baylesj/web-tempo-sync/issues/1), a known blocker).
2. Ask Ableton about a published protocol document and a patent statement ([#2](https://github.com/baylesj/web-tempo-sync/issues/2)).
3. Request Mozilla and WebKit positions ([#3](https://github.com/baylesj/web-tempo-sync/issues/3)).
4. Publish latency measurements (objection 15, [#10](https://github.com/baylesj/web-tempo-sync/issues/10)) and decide on a timing target (objection 7, [#4](https://github.com/baylesj/web-tempo-sync/issues/4)).
5. Settle the open API questions (objections 10 and 13: [#6](https://github.com/baylesj/web-tempo-sync/issues/6), [#8](https://github.com/baylesj/web-tempo-sync/issues/8)).
