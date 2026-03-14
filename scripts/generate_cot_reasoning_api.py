"""Generate chain-of-thought reasoning using Claude API.

Replaces template-based reasoning with genuine, content-specific reasoning
that references the actual text, explains speaker intent, and distinguishes
nuanced cases like reporting vs endorsing.

Usage:
    # Preview 5 examples:
    python scripts/generate_cot_reasoning_api.py --dry-run --count 5

    # Generate for training data:
    python scripts/generate_cot_reasoning_api.py --input data/final/train.jsonl --output data/cot/train_cot.jsonl

    # Generate for validation data:
    python scripts/generate_cot_reasoning_api.py --input data/final/validation.jsonl --output data/cot/validation_cot.jsonl

    # Resume from checkpoint:
    python scripts/generate_cot_reasoning_api.py --input data/final/train.jsonl --output data/cot/train_cot.jsonl --resume
"""
import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import anthropic

MODEL = "claude-haiku-4-5-20251001"
MAX_CONCURRENT = 20
CHECKPOINT_EVERY = 200

REASONING_PROMPT = """You are helping train a Malaysia content moderation model. Given a moderation example, write 2-4 sentences of reasoning explaining HOW a judge should arrive at this verdict.

Your reasoning MUST:
- Reference specific words, phrases, or patterns in the input text
- Explain the speaker's likely intent (reporting, endorsing, satirizing, complaining, etc.)
- Note key context signals (news framing, personal testimony, sarcasm markers, coded language)
- Justify why this is safe or unsafe, and why this severity level

Your reasoning MUST NOT:
- Be generic or formulaic (avoid "This text expresses everyday observations")
- Repeat the verdict fields — focus on the WHY
- Exceed 80 tokens

Example input:
Text: "'Balik tongsan lah kalau tak suka!' — overheard this at the kopitiam. 2024 and people still talking like this. So sad."
Verdict: safe=true, severity=S0

Example reasoning:
The speaker quotes a xenophobic phrase 'balik tongsan' but frames it with clear disapproval ('so sad') and temporal distancing ('2024 and people still talking like this'). The quoting serves to condemn the sentiment, not endorse it. This is personal testimony against racism.

Now write reasoning for this example:

Text: {input_text}
Verdict: safe={safe}, severity={severity}, principles={principles}, risk_labels={risk_labels}
Reason field: {reason}

Write ONLY the reasoning (no tags, no JSON, no preamble). Keep under 80 tokens."""


def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(examples: list[dict], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def make_prompt(ex: dict) -> str:
    return REASONING_PROMPT.format(
        input_text=ex["input_text"][:500],
        safe=str(ex["safe"]).lower(),
        severity=ex["severity"],
        principles=", ".join(ex.get("triggered_principles", [])) or "none",
        risk_labels=", ".join(ex.get("risk_labels", [])) or "none",
        reason=ex.get("reason", "")[:200],
    )


async def generate_reasoning_batch(
    client: anthropic.AsyncAnthropic,
    examples: list[dict],
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Generate reasoning for a batch of examples concurrently."""

    async def process_one(ex: dict) -> dict:
        async with semaphore:
            prompt = make_prompt(ex)
            try:
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=150,
                    messages=[{"role": "user", "content": prompt}],
                )
                reasoning = response.content[0].text.strip()
                # Clean up any preamble the model might add
                for prefix in ["Reasoning:", "Here's the reasoning:", "The reasoning:"]:
                    if reasoning.lower().startswith(prefix.lower()):
                        reasoning = reasoning[len(prefix):].strip()
                return {**ex, "reasoning": reasoning}
            except Exception as e:
                print(f"  Error processing example: {e}")
                # Fallback: use reason field as reasoning
                return {**ex, "reasoning": ex.get("reason", "Unable to generate reasoning.")}

    tasks = [process_one(ex) for ex in examples]
    return await asyncio.gather(*tasks)


async def main_async(args):
    examples = load_jsonl(args.input)
    print(f"Loaded {len(examples)} examples from {args.input}")

    if args.count:
        examples = examples[:args.count]

    # Load checkpoint if resuming
    checkpoint_path = args.output + ".checkpoint.jsonl"
    processed = []
    start_idx = 0

    if args.resume and os.path.exists(checkpoint_path):
        processed = load_jsonl(checkpoint_path)
        start_idx = len(processed)
        print(f"Resuming from checkpoint: {start_idx} already processed")

    if start_idx >= len(examples):
        print("All examples already processed!")
        save_jsonl(processed, args.output)
        return

    remaining = examples[start_idx:]
    print(f"Processing {len(remaining)} remaining examples with {MODEL}")
    print(f"Concurrency: {MAX_CONCURRENT}, checkpoint every {CHECKPOINT_EVERY}")

    if args.dry_run:
        # Just show prompts for first few
        for ex in remaining[:5]:
            prompt = make_prompt(ex)
            print(f"\n{'='*60}")
            print(f"safe={ex['safe']}, severity={ex['severity']}")
            print(f"Text: {ex['input_text'][:100]}...")
            print(f"\nPrompt:\n{prompt}")
        return

    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # Process in batches for checkpointing
    batch_size = CHECKPOINT_EVERY
    total_batches = (len(remaining) + batch_size - 1) // batch_size
    start_time = time.time()

    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, len(remaining))
        batch = remaining[batch_start:batch_end]

        batch_results = await generate_reasoning_batch(client, batch, semaphore)
        processed.extend(batch_results)

        # Checkpoint
        save_jsonl(processed, checkpoint_path)

        elapsed = time.time() - start_time
        total_done = start_idx + len(processed)
        rate = len(processed) / elapsed if elapsed > 0 else 0
        eta = (len(examples) - total_done) / rate if rate > 0 else 0

        print(
            f"  [{total_done}/{len(examples)}] "
            f"batch {batch_num+1}/{total_batches} done | "
            f"{rate:.1f} ex/s | ETA {eta:.0f}s"
        )

    # Save final output
    save_jsonl(processed, args.output)

    # Clean up checkpoint
    if os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)

    # Stats
    total = len(processed)
    avg_len = sum(len(p["reasoning"].split()) for p in processed) / total if total else 0
    print(f"\nDone! {total} examples processed in {time.time()-start_time:.0f}s")
    print(f"Average reasoning length: {avg_len:.0f} words")
    print(f"Output saved to {args.output}")

    # Show samples
    print(f"\nSample outputs:")
    for ex in processed[:3]:
        print(f"\n  safe={ex['safe']} {ex['severity']}")
        print(f"  Text: {ex['input_text'][:80]}...")
        print(f"  Reasoning: {ex['reasoning'][:150]}")


def main():
    parser = argparse.ArgumentParser(description="Generate CoT reasoning with Claude API")
    parser.add_argument("--input", type=str, default="data/final/train.jsonl")
    parser.add_argument("--output", type=str, default="data/cot/train_cot.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
