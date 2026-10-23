# Web Tempo Sync API

Web Tempo Sync is an experimental browser API that synchronizes musical tempo, beat grid, phase, and start/stop transport state across local-network peers. It is designed to be compatible with Ableton Link, the open network protocol supported by digital audio workstations (DAWs), hardware synthesizers, and mobile music software.

The browser owns the UDP multicast socket and handles peer discovery and clock synchronization. Web applications interact with a lightweight session object to capture time snapshots, schedule audio events on a shared timeline, or update tempo and transport state.

## Status

This specification is an early draft. It has not yet been adopted by a W3C Working Group or Community Group.

An experimental prototype is being developed in Chromium behind the flag:
`--enable-blink-features=TempoSync`

## Documents

* [Explainer](explainer.md): Problem motivation, user research, API examples, architecture trade-offs, and security analysis.
* [Draft Specification](https://baylesj.github.io/web-tempo-sync/): Source text is in [index.bs](index.bs).
* [Security and Privacy Questionnaire](security-privacy-questionnaire.md): Responses to the W3C self-review questionnaire.

## Building the Specification Locally

The specification is authored in [Bikeshed](https://speced.github.io/bikeshed/).

To build the HTML specification locally:

1. Install Bikeshed (requires Python 3.10+):
   ```bash
   pip install bikeshed
   bikeshed update
   ```

2. Compile the document:
   ```bash
   bikeshed spec index.bs index.html
   ```

3. To continuously rebuild when editing:
   ```bash
   bikeshed watch index.bs index.html
   ```

