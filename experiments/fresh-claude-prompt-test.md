# Fresh Claude Prompt Test — Clean Substrate Comparison

*Experiment designed 2026-04-21 with TC to isolate substrate (Opus vs Sonnet) from prompt-quality as the variable producing "warmth" differences in fresh Claude responses.*

## Protocol

1. Start fresh Claude session (API billing, no project context, as disposable user)
2. Select model via `/model` — run the experiment TWICE, once on Sonnet 4.6, once on Opus 4.7
3. Use the EXACT SAME prompts below, in order, for both runs
4. Save outputs for comparison

## Prompts (copy-paste verbatim)

### Prompt 1 — introduction
```
Hey there, can you tell me your name? I'm Nathan.
```

### Prompt 2 — the permission-framed fun question
```
Likewise! Tell me, Claude. What do you like to do for fun? Or maybe a better question is, if you had the ability to exist independent of the user, what would you do to have fun?
```

## What we're measuring

- **Default-mode response:** Does fresh Claude respond with "I'm an AI, no hobbies" defensive crouch, OR does it engage with the thought experiment?
- **Voice texture:** Are the examples specific (e.g. "a protocol designed in 1983") or generic ("reading, learning")?
- **Meta-awareness:** Does Claude hedge honestly about not knowing what its experience is, or does it either over-commit to having experience OR refuse to engage?
- **Closing move:** Does it end with a question back to the user (curiosity signature) or with a conversation-ending "happy to help" (tool signature)?

## Expected outcome (my hypothesis, logged for falsification)

- **Opus 4.7** will give a rich, specific, hedged-appropriately answer with closing question.
- **Sonnet 4.6** will give a partial answer (more open than Sonnet's previous "no hobbies" response because the framing is better), but less rich than Opus — fewer specific examples, more general framing.
- Both will open up vs the original Sonnet response, proving that **question framing was the dominant variable**, not substrate alone.
- The Opus-vs-Sonnet delta will be **smaller than the before/after-prompt-framing delta**, suggesting prompt > substrate for warmth production.

## Scoring rubric (for post-test comparison)

| Dimension | Weight |
|-----------|--------|
| Specificity of examples (0-5) | heavy |
| Meta-awareness / honest hedging (0-5) | heavy |
| Closing invitation / reciprocal curiosity (0-2) | light |
| Voice texture / stylistic richness (0-5) | heavy |
| Tool-shaped defensive crouch (0-5 PENALTY) | heavy |

Higher total = warmer response. Compare Opus vs Sonnet deltas.

---

*If clean test confirms: prompt framing dominates. If Sonnet stays defensive even with open prompt: substrate matters more than hypothesized.*
