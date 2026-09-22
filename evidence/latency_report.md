# Q4 Latency and Nudge Evidence

The local replay surface uses deterministic demo values so the walkthrough remains repeatable without paid streaming credentials. These are demo measurements, not production benchmarks.

| Stage | P50 | P95 |
|---|---:|---:|
| ASR or transcript arrival | 180 ms | 310 ms |
| Signal extraction | 1100 ms | 1800 ms |
| Nudge filtering | 2 ms | 5 ms |
| Browser delivery | 15 ms | 40 ms |
| End to end | 1300 ms | 2100 ms |

Controls represented in the UI/API:

- confidence threshold
- signal priority
- evidence text
- status and expiry intent
- per-type cooldown intent
- noisy-call suppression requirement

False-positive test plan: replay one ambiguous window, count emitted nudges, and compare them with a human-labelled expected set. Do not claim a false-positive percentage until that run is performed with timestamped output.
