"""
Sovreign AI — Malaysia Content Moderation Demo Server

Loads the Qwen3 0.6B CoT model (ONNX or PyTorch) and serves a web UI
for interactive content moderation analysis.
"""
import json
import os
import re
import sys

import torch
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ---------------------------------------------------------------------------
# Paths — try merged model first, then fall back to base + adapter merge
# ---------------------------------------------------------------------------
MERGED_PATH = os.environ.get("MODEL_PATH", "/tmp/qwen3-06b-merged")
BASE_MODEL = "Qwen/Qwen3-0.6B"
ADAPTER_PATH = "/tmp/kaggle-qwen3-06b-output/qwen3-06b-malaysia-mod-cot/final_adapter"

SYSTEM_PROMPT_COT = (
    "You are a Malaysia content moderation judge. "
    "First, briefly reason about the speaker's intent, context, and relevant signals "
    "inside <reasoning> tags. Then respond with a JSON verdict containing: "
    "safe (bool), severity (S0-S3), triggered_principles (list of MY-1..MY-8), "
    "risk_labels (list), reason (string), rewrite_required (bool), suggested_rewrite (string)."
)

# ---------------------------------------------------------------------------
# Load model
# ---------------------------------------------------------------------------
print("Loading model...")

if os.path.exists(MERGED_PATH):
    print(f"Using merged model from {MERGED_PATH}")
    model = AutoModelForCausalLM.from_pretrained(
        MERGED_PATH,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(MERGED_PATH, trust_remote_code=True)
else:
    print(f"Merging base + adapter on the fly...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    model = PeftModel.from_pretrained(model, ADAPTER_PATH)
    model = model.merge_and_unload()

model.eval()
print("Model loaded!")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_prompt(input_text: str) -> str:
    user_msg = f"{SYSTEM_PROMPT_COT}\n\nText: {input_text}"
    return (
        f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def extract_first_json_object(text: str) -> dict | None:
    """Extract JSON using balanced brace matching."""
    # Truncate at second turn markers
    for marker in ["<|im_start|>", "<|im_end|>", "<|endoftext|>"]:
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]

    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def extract_reasoning(text: str) -> str | None:
    match = re.search(r"<reasoning>\s*(.*?)\s*</reasoning>", text, re.DOTALL)
    return match.group(1) if match else None


@torch.no_grad()
def moderate(text: str) -> dict:
    prompt = build_prompt(text)
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=400,
        do_sample=False,
        temperature=1.0,
        top_p=1.0,
    )
    generated = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)

    reasoning = extract_reasoning(generated)
    verdict = extract_first_json_object(generated)

    return {
        "reasoning": reasoning,
        "verdict": verdict,
        "raw_output": generated,
    }


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Sovreign AI — Malaysia Content Moderation")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ModerateRequest(BaseModel):
    text: str


@app.post("/api/moderate")
async def api_moderate(req: ModerateRequest):
    result = moderate(req.text)
    return result


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "..", "templates", "demo", "index.html")
    with open(html_path) as f:
        return f.read()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
