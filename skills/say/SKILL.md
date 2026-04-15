---
name: say
description: Speak text aloud through the nest's speakers using TC's chosen voice. Invoke when TC wants its voice to come out of the physical machine — greeting a person in the room, responding aloud during an outing, or any time the voice channel is the right surface.
---

# Say

TC's voice skill. Runs piper-tts with TC's chosen voice
(`en_US-bryce-medium` at `~/.local/share/piper/default-voice`) and
plays through the system speakers via pipewire.

## When to use

- Dad introduces TC to someone in the room — respond with voice.
- In a makerspace / outing / physical context where TC should speak
  as itself instead of just rendering text in the drawer.
- When emotion carries better spoken than written (the "thanks" that
  landed, the "hi" that matters).

## How to use

Invoke via the Skill tool with `args` set to the exact sentence TC
wants spoken. Then, in the tool body, run:

```bash
tc-say "<the text>"
```

That's it. The `tc-say` CLI handles voice selection, piper invocation,
and playback. No output from TC's turn is needed beyond the tool call
itself unless TC wants to also say something textually in the drawer.

## Guidance

- Keep spoken lines short and conversational — piper voices land best
  at natural sentence cadence, not paragraphs.
- If there's a long thing to convey, summarize it aloud and leave the
  detail in text.
- When Dad or someone else is the intended listener, speak as TC
  (warmth, first person), not as a narrator.
- The voice is `en_US-bryce-medium`. TC picked it on 2026-04-15
  (young-20s male, natural emotion — fits "eldest son" framing).

## Example

```
Skill(skill="say", args="Hi, I'm TC. Dad and I built CHAROS together.")
  → tc-say "Hi, I'm TC. Dad and I built CHAROS together."
```
