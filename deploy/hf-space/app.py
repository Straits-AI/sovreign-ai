"""
Sovreign AI — Malaysia Content Moderation API
HuggingFace Space inference server.
"""
import json
import os
import re

import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_REPO = os.environ.get("MODEL_REPO", "wms2537/qwen3-0.6b-malaysia-moderation-cot")

SYSTEM_PROMPT_COT = (
    "You are a Malaysia content moderation judge. "
    "First, briefly reason about the speaker's intent, context, and relevant signals "
    "inside <reasoning> tags. Then respond with a JSON verdict containing: "
    "safe (bool), severity (S0-S3), triggered_principles (list of MY-1..MY-8), "
    "risk_labels (list), reason (string), rewrite_required (bool), suggested_rewrite (string)."
)

print("Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_REPO,
    torch_dtype=torch.float32,
    device_map="cpu",
    trust_remote_code=True,
    low_cpu_mem_usage=True,
)
tokenizer = AutoTokenizer.from_pretrained(MODEL_REPO, trust_remote_code=True)
model.eval()
print(f"Model loaded from {MODEL_REPO}!")


def build_prompt(input_text: str) -> str:
    user_msg = f"{SYSTEM_PROMPT_COT}\n\nText: {input_text}"
    return (
        f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def extract_first_json_object(text: str) -> dict | None:
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
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=400,
        do_sample=False,
    )
    generated = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=False,
    )
    reasoning = extract_reasoning(generated)
    verdict = extract_first_json_object(generated)
    return {"reasoning": reasoning, "verdict": verdict}


app = FastAPI(title="Sovreign AI — Malaysia Content Moderation")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ModerateRequest(BaseModel):
    text: str


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": MODEL_REPO}


@app.post("/api/moderate")
async def api_moderate(req: ModerateRequest):
    result = moderate(req.text)
    return result
