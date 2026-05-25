#!/usr/bin/env python3
"""Hermes Crew - Hierarchical multi-agent system for SovereignAI network.

11 specialist agents coordinated by a Supervisor using CrewAI's
hierarchical process. The Coders agent (Pi Ninja) uses the Shinobi
protocol to deploy zero-footprint coding swarms:

  Primary: shinobi_code — packager → spawner → sub-ninjas → QA → vanish
  Fallback: agy_code (Antigravity CLI, cloud) + ollama_code (local hq-ai)

QA runs on DeepSeek V4 Flash at the same tier as the Supervisor
for independent quality judgment."""

import os
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from hermes_crew.tools import (
    AntigravityTool, OllamaCodeTool, ShinobiTool,
    run_node_command, health_check_all,
    list_environments, list_containers, manage_container, deploy_stack,
)

# Load env from project root
load_dotenv()


def _get_llm(model_override: str | None = None) -> str:
    """Build OpenRouter LLM model string."""
    model = model_override or os.getenv("CREW_MODEL", "deepseek/deepseek-chat")
    return f"openrouter/{model}"


def _get_manager_llm() -> str:
    """Stronger model for the hierarchical manager."""
    model = os.getenv("MANAGER_MODEL", "deepseek/deepseek-v4-flash")
    return f"openrouter/{model}"


def _get_qa_llm() -> str:
    """Strong model for quality assurance — same tier as manager."""
    model = os.getenv("QA_MODEL", os.getenv("MANAGER_MODEL", "deepseek/deepseek-v4-flash"))
    return f"openrouter/{model}"


@CrewBase
class HermesCrew:
    """The full SovereignAI crew — 11 agents, hierarchical orchestration."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ── Agents ────────────────────────────────────────────────────────

    @agent
    def supervisor(self) -> Agent:
        return Agent(
            config=self.agents_config["supervisor"],
            llm=_get_manager_llm(),
            verbose=True,
            allow_delegation=True,
        )

    @agent
    def n8n_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["n8n_manager"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def web_dev(self) -> Agent:
        return Agent(
            config=self.agents_config["web_dev"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def db_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["db_manager"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def cloudflare(self) -> Agent:
        return Agent(
            config=self.agents_config["cloudflare"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def payments(self) -> Agent:
        return Agent(
            config=self.agents_config["payments"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def infra(self) -> Agent:
        """Infrastructure operator — SSH into nodes, manage Docker, run health checks."""
        return Agent(
            config=self.agents_config["infra"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
            tools=[
                run_node_command,
                health_check_all,
                list_environments,
                list_containers,
                manage_container,
                deploy_stack,
            ],
        )

    @agent
    def coders(self) -> Agent:
        """Pi Ninja — deploys Shinobi swarms for coding tasks via the Shinobi protocol.

        Primary path: ShinobiTool (packager → spawner → sub-ninjas → QA → vanish).
        Fallback: agy_code (cloud) and ollama_code (local) for quick single-file tasks.
        """
        return Agent(
            config=self.agents_config["coders"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
            tools=[ShinobiTool(), AntigravityTool(), OllamaCodeTool()],
        )

    @agent
    def vision(self) -> Agent:
        return Agent(
            config=self.agents_config["vision"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def creative(self) -> Agent:
        return Agent(
            config=self.agents_config["creative"],
            llm=_get_llm(),
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def qa(self) -> Agent:
        """Quality gate — evaluates all crew outputs before delivery."""
        return Agent(
            config=self.agents_config["qa"],
            llm=_get_qa_llm(),
            verbose=True,
            allow_delegation=False,
        )

    # ── Tasks ─────────────────────────────────────────────────────────

    @task
    def infrastructure_audit(self) -> Task:
        return Task(config=self.tasks_config["infrastructure_audit"])

    @task
    def n8n_workflow_deploy(self) -> Task:
        return Task(config=self.tasks_config["n8n_workflow_deploy"])

    @task
    def web_service_deploy(self) -> Task:
        return Task(config=self.tasks_config["web_service_deploy"])

    @task
    def database_migration(self) -> Task:
        return Task(config=self.tasks_config["database_migration"])

    @task
    def dns_configure(self) -> Task:
        return Task(config=self.tasks_config["dns_configure"])

    @task
    def code_implementation(self) -> Task:
        return Task(config=self.tasks_config["code_implementation"])

    @task
    def vision_analysis(self) -> Task:
        return Task(config=self.tasks_config["vision_analysis"])

    @task
    def creative_generation(self) -> Task:
        return Task(config=self.tasks_config["creative_generation"])

    @task
    def quality_gate(self) -> Task:
        return Task(config=self.tasks_config["quality_gate"])

    @task
    def payment_integration(self) -> Task:
        return Task(config=self.tasks_config["payment_integration"])

    @task
    def code_review(self) -> Task:
        return Task(config=self.tasks_config["code_review"])

    @task
    def network_health_check(self) -> Task:
        return Task(config=self.tasks_config["network_health_check"])

    # ── Crew ──────────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        """Assemble the full crew with hierarchical process."""
        supervisor_agent = self.supervisor()

        worker_agents = [
            self.n8n_manager(),
            self.web_dev(),
            self.db_manager(),
            self.cloudflare(),
            self.payments(),
            self.infra(),
            self.coders(),
            self.vision(),
            self.creative(),
            self.qa(),
        ]

        return Crew(
            agents=worker_agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=supervisor_agent,
            manager_llm=_get_manager_llm(),
            verbose=True,
            planning=True,
            memory=True,
        )
