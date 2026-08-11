#!/usr/bin/env python3
"""generate_rca.py — Send incident context to a local Ollama LLM and save the RCA report.

Usage:
    python3 scripts/generate_rca.py --context prompts/incident_context.txt --model llama3.2:3b --output output/rca_report.md
    python3 scripts/generate_rca.py --context prompts/capstone_context.txt --model mistral:7b --output output/capstone_rca.md

    # Use OpenAI instead of Ollama (requires OPENAI_API_KEY env var):
    python3 scripts/generate_rca.py --context prompts/incident_context.txt --model gpt-4o --openai --output output/rca_gpt4o.md
"""

import argparse
import os
import sys
import time

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

OLLAMA_URL = "http://localhost:11434"

RCA_SYSTEM_PROMPT = """\
You are an expert Site Reliability Engineer specialising in root cause analysis
and incident investigation. Your task is to analyse the incident data provided
and produce a structured Root Cause Analysis (RCA) report.

IMPORTANT RULES:
- Base your analysis ONLY on the data provided. Do not invent metrics or events.
- If evidence is insufficient for a section, state "Insufficient data" rather than guessing.
- The root cause must be a single system-level cause, not "human error".
- The recommended fix must be a specific, executable action, not generic advice.
"""

RCA_USER_TEMPLATE = """\
INCIDENT DATA:
---
{incident_context}
---

Generate a Root Cause Analysis report with EXACTLY these six sections, in this order:

## Summary
One sentence describing the incident and its user impact.

## Timeline
Bullet list of events in chronological order based on the log timestamps provided.
Format: - **HH:MM:SSZ** — [event description]

## Root Cause
The single deepest root cause, supported by specific evidence from the data above.
Apply the 5 Whys approach. Do not stop at the surface symptom.

## Contributing Factors
Secondary factors that worsened the incident or slowed detection.
Bullet list, maximum 4 items.

## Affected Services
Table with two columns: Service | Impact.
List every service mentioned in the logs or alerts.

## Recommended Immediate Fix
The specific action that will resolve the incident right now.
Include the exact Ansible playbook command or shell command if applicable.

## Prevention Steps
Exactly three concrete systemic changes that prevent this class of incident in future.
Each step should be a specific configuration change, alert rule, or process change.
"""


def _call_ollama(model: str, context: str) -> str:
    """Call Ollama REST API and return the generated text."""
    user_prompt = RCA_USER_TEMPLATE.format(incident_context=context)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": RCA_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,   # Lower temperature = more deterministic, less hallucination
            "num_predict": 2048,  # Max tokens for the response
        },
    }

    print(f"  Calling Ollama ({model}) at {OLLAMA_URL}...")
    start = time.time()

    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    elapsed = round(time.time() - start, 1)
    print(f"  ✅ Response received in {elapsed}s "
          f"({data.get('eval_count', '?')} tokens generated)")
    return data["message"]["content"]


def _call_openai(model: str, context: str) -> str:
    """Call OpenAI API as a comparison (requires openai package and OPENAI_API_KEY)."""
    try:
        from openai import OpenAI
    except ImportError:
        print("Install openai: pip install openai")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY environment variable to use the OpenAI backend.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    user_prompt = RCA_USER_TEMPLATE.format(incident_context=context)

    print(f"  Calling OpenAI ({model})...")
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": RCA_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=2048,
    )
    elapsed = round(time.time() - start, 1)
    tokens = response.usage.completion_tokens
    print(f"  ✅ Response received in {elapsed}s ({tokens} tokens generated)")
    return response.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(description="Generate an LLM RCA report from incident context.")
    parser.add_argument("--context", required=True, help="Path to the incident context file")
    parser.add_argument("--model", default="llama3.2:3b",
                        help="Model name (default: llama3.2:3b, or gpt-4o with --openai)")
    parser.add_argument("--openai", action="store_true",
                        help="Use OpenAI API instead of local Ollama")
    parser.add_argument("--output", default="output/rca_report.md",
                        help="Output file path (default: output/rca_report.md)")
    args = parser.parse_args()

    # Read context
    if not os.path.exists(args.context):
        print(f"❌ Context file not found: {args.context}")
        print("   Run build_prompt.py first.")
        sys.exit(1)

    with open(args.context) as f:
        context = f.read()

    print(f"\n{'═'*65}")
    print(f"  LLM RCA Generator — Module 11")
    print(f"{'═'*65}")
    print(f"  Context file:  {args.context} ({len(context)} chars)")
    print(f"  Model:         {args.model}")
    print(f"  Backend:       {'OpenAI API' if args.openai else 'Ollama (local)'}")
    print(f"  Output:        {args.output}\n")

    # Generate
    if args.openai:
        rca = _call_openai(args.model, context)
    else:
        # Check Ollama is running
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).raise_for_status()
        except Exception:
            print(f"❌ Ollama not reachable at {OLLAMA_URL}")
            print("   Start it with: ollama serve")
            sys.exit(1)
        rca = _call_ollama(args.model, context)

    # Save output
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    header = f"<!-- Generated by generate_rca.py | Model: {args.model} | {__import__('datetime').datetime.utcnow().isoformat()}Z -->\n\n"
    with open(args.output, "w") as f:
        f.write(header + rca)

    print(f"\n{'═'*65}")
    print(f"  ✅ RCA saved to: {args.output}")
    print(f"     {len(rca.splitlines())} lines, {len(rca)} characters")
    print(f"{'═'*65}\n")
    print("First 20 lines of the report:")
    for line in rca.splitlines()[:20]:
        print(f"  {line}")
    if len(rca.splitlines()) > 20:
        print(f"  ... ({len(rca.splitlines()) - 20} more lines)")


if __name__ == "__main__":
    main()
