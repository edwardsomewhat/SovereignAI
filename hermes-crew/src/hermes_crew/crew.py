#!/usr/bin/env python3
"""Hermes Crew - Hierarchical multi-agent system for SovereignAI network.

14 specialist agents coordinated by a Supervisor using CrewAI's
hierarchical process. The Creative Department (6 agents: Scout, Director,
Image Studio, Video Studio, Copy Studio, Review Agent) graduated from
proven skills into autonomous agents. The Director orchestrates only —
all generation is delegated to specialist studios. Site Operator collapsed
from 4 website agents into one full-stack csweb administrator."""

import os
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from hermes_crew.tools import (
    AntigravityTool, OllamaCodeTool, ShinobiTool,
    run_node_command, health_check_all,
    list_environments, list_containers, manage_container, deploy_stack,
    # Image Studio tools
    txt2img, img2img, upscale, comfyui_status,
    # Video Studio tools
    txt2video, img2video,
    # Copy Studio tools
    generate_copy, humanize,
    # Review Agent tools
    review_image, review_video, inpaint, text_overlay,
    florence_mask, background_remove, color_correct,
    # Scout tools
    web_search, web_fetch,
)

# Load env from project root
load_dotenv()

# Route openai/ models to Conchai vLLM (openrouter/ models unaffected)
os.environ.setdefault("VLLM_BASE_URL", "http://100.69.153.16:8020/v1")
os.environ.setdefault("VLLM_API_KEY", "vllm-dummy-key")


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


def _get_local_llm(model: str = "ministral-3:14b") -> str:
    """Lightweight read-only agents: scouts, inventory keepers."""
    return f"ollama/{model}"


def _get_creative_llm(model: str = "qwen3.6-27b"):
    """Creative agents: Director, Scout, Image/Video/Copy Studio.

    Runs on Conchai vLLM (100.69.153.16:8020) — 27B int4, 96K ctx,
    MTP n=3 spec decode, native Qwen3 tool calling.

    Returns an LLM instance with enable_thinking=False to suppress
    Qwen3's default deep-thinking mode which would consume all tokens
    in reasoning before producing usable output.
    """
    return LLM(
        model=f"hosted_vllm/{model}",
        base_url="http://100.69.153.16:8020/v1",
        api_key="vllm-dummy-key",
        additional_params={
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}
        },
    )


def _get_review_llm(model: str = "qwen3-vl:8b") -> str:
    """Vision review agent — needs VL capability."""
    return f"ollama/{model}"


@CrewBase
class HermesCrew:
    """The full SovereignAI crew — 12 agents, hierarchical orchestration."""

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
    def site_operator(self) -> Agent:
        """Site Operator — full-stack csweb administrator for combustionsyndicate.com."""
        return Agent(
            config=self.agents_config["site_operator"],
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
    def scout(self) -> Agent:
        """Creative Scout — web research + asset collection. Qwen 27B on Conchai vLLM."""
        return Agent(
            config=self.agents_config["scout"],
            llm=_get_creative_llm(),  # Conchai vLLM 27B — fast tool calling
            tools=[web_search, web_fetch],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def creative_director(self) -> Agent:
        """Creative Director — orchestrates only. Qwen 27B on Conchai vLLM. Delegates to specialists."""
        return Agent(
            config=self.agents_config["creative_director"],
            llm=_get_creative_llm(),
            verbose=True,
            allow_delegation=True,
        )

    @agent
    def image_studio(self) -> Agent:
        """Image Studio — still-image generation via ComfyUI. gpt-oss:20b on hq-ai Ollama."""
        return Agent(
            config=self.agents_config["image_studio"],
            llm=_get_local_llm("gpt-oss:20b"),
            tools=[txt2img, img2img, upscale, comfyui_status],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def video_studio(self) -> Agent:
        """Video Studio — video generation via ComfyUI. gpt-oss:20b on hq-ai Ollama."""
        return Agent(
            config=self.agents_config["video_studio"],
            llm=_get_local_llm("gpt-oss:20b"),
            tools=[txt2video, img2video, comfyui_status],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def copy_studio(self) -> Agent:
        """Copy Studio — text creative generation. gpt-oss:20b on hq-ai Ollama."""
        return Agent(
            config=self.agents_config["copy_studio"],
            llm=_get_local_llm("gpt-oss:20b"),
            tools=[generate_copy, humanize],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def review_agent(self) -> Agent:
        """Review Agent — vision QC + fixes. qwen3-vl:8b on hq-ai Ollama."""
        return Agent(
            config=self.agents_config["review_agent"],
            llm=_get_review_llm(),
            tools=[review_image, review_video, inpaint, text_overlay, florence_mask, background_remove, color_correct],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def fab_studio(self) -> Agent:
        return Agent(
            config=self.agents_config["fab_studio"],
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
    def site_management(self) -> Task:
        return Task(config=self.tasks_config["site_management"])

    @task
    def code_implementation(self) -> Task:
        return Task(config=self.tasks_config["code_implementation"])

    @task
    def vision_analysis(self) -> Task:
        return Task(config=self.tasks_config["vision_analysis"])

    @task
    def creative_scouting(self) -> Task:
        return Task(config=self.tasks_config["creative_scouting"])

    @task
    def creative_direction(self) -> Task:
        return Task(config=self.tasks_config["creative_direction"])

    @task
    def image_generation(self) -> Task:
        return Task(config=self.tasks_config["image_generation"])

    @task
    def video_generation(self) -> Task:
        return Task(config=self.tasks_config["video_generation"])

    @task
    def copy_generation(self) -> Task:
        return Task(config=self.tasks_config["copy_generation"])

    @task
    def creative_review(self) -> Task:
        return Task(config=self.tasks_config["creative_review"])

    @task
    def fabrication(self) -> Task:
        return Task(config=self.tasks_config["fabrication"])

    @task
    def quality_gate(self) -> Task:
        return Task(config=self.tasks_config["quality_gate"])

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
            self.site_operator(),
            self.infra(),
            self.coders(),
            self.vision(),
            self.scout(),
            self.creative_director(),
            self.image_studio(),
            self.video_studio(),
            self.copy_studio(),
            self.review_agent(),
            self.fab_studio(),
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

    def creative_crew(self) -> Crew:
        """Creative Department only — Scout + Director + Studios + Review."""
        supervisor_agent = self.supervisor()

        creative_workers = [
            self.scout(),
            self.creative_director(),
            self.image_studio(),
            self.video_studio(),
            self.copy_studio(),
            self.review_agent(),
        ]

        creative_tasks = [
            self.creative_scouting(),
            self.creative_direction(),
            self.image_generation(),
            self.video_generation(),
            self.copy_generation(),
            self.creative_review(),
        ]

        return Crew(
            agents=creative_workers,
            tasks=creative_tasks,
            process=Process.sequential,
            verbose=True,
            planning=True,
            memory=True,
        )
