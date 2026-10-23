# W3C Self-Review Questionnaire: Security and Privacy

This document answers the questions from the [W3C Self-Review Questionnaire: Security and Privacy](https://www.w3.org/TR/security-privacy-questionnaire/) for the Web Tempo Sync API.

### 1. What information might this feature expose to Web sites or other parties, and for what purposes is that information exposed?

This feature exposes:
* The count of active tempo-sync peers on the local area network (`TempoSession.numPeers`).
* Shared musical timeline metadata (tempo in BPM, beat grid alignment, phase, and start/stop state).

This information is exposed to allow musical web applications to synchronize rhythm and playback with external instruments and software.

The feature does **not** expose:
* IP addresses, MAC addresses, or port numbers of local devices.
* Hostnames, device models, or hardware identifiers.
* Audio streams, MIDI event payloads, or user files.

### 2. Do features in this specification expose the minimum amount of information necessary to implement their intended functionality?

Yes. Only the aggregate count of peers and mathematical timing parameters (tempo, beat origin, time origin, and quantum) are exposed to the page.

### 3. How do the features in this specification deal with personal data, personally-identifiable information (PII), or information derived from them?

The specification does not handle or expose any personal data or personally-identifiable information.

### 4. How do the features in this specification deal with sensitive data?

The specification does not access or store sensitive user data (such as credentials, health data, financial data, or location).

### 5. Does this specification introduce state that might be persistent across browsing sessions?

No. The session state is ephemeral. When a document closes or the user leaves the page, the session terminates. The underlying network socket closes when no active browsing sessions remain.

### 6. Does this specification allow information to be shared between different visiting origins?

Yes, indirectly. If two origins are granted permission and join a tempo session on the same local network at the same time, they share the musical timeline. A state commit (such as a tempo change) from one origin is observed by the other origin.

Because this synchronization requires explicit user permission per origin, secure contexts, and active foreground execution, covert cross-origin communication bandwidth is low and strictly local.

### 7. Does this specification introduce state that could be used for fingerprinting?

The number of active local network peers (`numPeers`) could provide an additional entropy bit indicating whether a user is on a studio network with Link-enabled hardware.

Mitigations:
* The API requires an explicit permission prompt before any network communication begins.
* Origins cannot probe for peers silently.
* The browser exposes only an integer peer count without device details.

### 8. Does this specification expose information about the underlying platform, device, or network to the origins?

The API reveals the presence of other Ableton Link participants on the local area network via the `numPeers` attribute.

The API does not expose network interface names, subnet masks, local IP addresses, or gateway addresses.

### 9. Does this specification allow an origin to access sensors or peripheral devices?

The API does not access hardware sensors or physical peripheral devices directly. It coordinates timing with audio rendering hardware through `BaseAudioContext.currentTime`.

### 10. Does this specification allow an origin to send data to the network or device on the local network?

Yes. When an application commits a modified state (`session.commitState()`), the browser transmits Link protocol update packets over UDP multicast (port 20808) on the local subnet.

Mitigations:
* The page cannot send arbitrary byte payloads or craft network packets.
* The browser formats and validates all protocol messages in native code.
* The browser enforces rate limits on commit operations to prevent packet flooding.

### 11. Does this specification allow an origin to access local devices?

The API allows communication with local network devices that implement the Ableton Link protocol. Communication is restricted to tempo and transport synchronization. The browser does not permit arbitrary remote procedure calls or device configuration.

### 12. Does this specification allow an origin to spoof other applications or the browser?

No. The API does not provide UI spoofing mechanisms. On the local network, the browser appears as a standard Ableton Link peer. The user agent participates as a single peer representing the browser instance rather than individual tabs.

### 13. How does this specification allow the user to control the feature, and does it provide adequate information to make an informed decision?

* Access requires explicit user consent via a permission prompt (`tempo-sync`).
* The prompt clearly states that the web page is requesting access to synchronize with music devices on the local network.
* The user agent can provide a persistent indicator (such as an address bar icon) while a tempo session is active.
* Users can revoke permission at any time through standard browser site settings.

### 14. Does this specification introduce downgrade risks?

No. The API is only available in secure contexts (`https://` and `localhost`). It cannot be accessed over plain HTTP.

### 15. What security and privacy concerns have been raised during the development of this specification?

The primary security and privacy discussions focused on:
1. **Local Network Access (LNA)**: Preventing unauthorized probing of local networks. Mitigated by the permission prompt and absence of socket primitives.
2. **Denial of service and packet flooding**: Mitigated by browser-enforced commit rate limits and single-peer consolidation.
3. **Tab competition**: Mitigated by managing a single Link endpoint per browser profile.
