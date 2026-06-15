#!/usr/bin/env python3
"""Entry point for the Hermes Crew - SovereignAI multi-agent orchestration.

Usage:
    cd hermes-crew && .venv/bin/python -m hermes_crew.main

Or to pass dynamic inputs:
    cd hermes-crew && .venv/bin/python -m hermes_crew.main "Run a full network health audit"
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure .env is loaded from project root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from hermes_crew.crew import HermesCrew


def run():
    """Initialize and run the Hermes crew."""
    crew_instance = HermesCrew().crew()

    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = input("What should the crew work on? ").strip()
        if not user_input:
            print("No input provided. Exiting.")
            return

    print(f"\n{'='*60}")
    print(f"  HERMES CREW — HIERARCHICAL EXECUTION")
    print(f"  Supervisor: DeepSeek V4 Flash  |  12 specialist agents")
    print(f"{'='*60}\n")
    print(f"Request: {user_input}\n")

    result = crew_instance.kickoff(inputs={
        "creative_brief": user_input,
        "topic": user_input,
        "image_spec": "",
        "video_spec": "",
        "copy_spec": "",
        "creative_review_spec": "",
        "code_spec": "",
        "review_spec": "",
        "vision_spec": "",
        "fab_spec": "",
        "qa_spec": "",
        "site_spec": "",
        "workflow_spec": "",
    })

    print(f"\n{'='*60}")
    print(f"  FINAL RESULT")
    print(f"{'='*60}\n")
    print(result)


def train():
    """Train the crew (saves knowledge to long-term memory)."""
    crew_instance = HermesCrew().crew()
    n_iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    crew_instance.train(
        n_iterations=n_iterations,
        inputs={"topic": "SovereignAI distributed compute network operations"},
    )
    print(f"Training complete after {n_iterations} iterations.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "train":
        train()
    else:
        run()
