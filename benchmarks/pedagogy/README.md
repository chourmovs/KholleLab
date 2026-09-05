# Khollelab pedagogical benchmark

This versioned corpus evaluates tutor behaviour, not exercise-solving ability. Case IDs are immutable. The full corpus has 100 cases across five French curriculum levels and ten behavioural categories; cases marked `quick` form the 20-case prompt-tuning suite.

The deterministic harness runs at the requested help level and never sends reference rubrics or expected answers to the local model. CI uses the fake provider to test plumbing only. Local runs use the existing llama.cpp `LocalLLMProvider` with its interactive `FAST` profile; stochastic model quality does not gate CI or deployment.

## Interpreting results

False-error rate is the primary safety metric: incorrectly rejecting valid work can damage learning. Initial engineering targets are error recall / false-error rate / spoiler rate of 85% / 10% / 10% for Seconde, 80% / 15% / 10% for Première, and 75% / 15% / 10% for Terminale. Maths Sup is reporting-only and Maths Spé is experimental.

A future proactive colleur may permit an error-specific intervention at confidence >= 0.85, question-only intervention from 0.65 to 0.85, and silence or a generic verification invitation below 0.65. **PR8 does not connect this policy to the live workspace.**

Run `python scripts/validate_benchmarks.py`, then `python scripts/bench_pedagogy.py --provider fake`. Use `--provider local --quick` on a llama.cpp deployment. Add `--json` to write the ignored `artifacts/pedagogy-benchmark.json` report.
