import json
import shutil
from pathlib import Path
from datetime import datetime

import source.config as config

from source.agents.team import create_team
from source.agents.orchestrator import make_orchestrator

from agents import (
    Runner,
    RunConfig,
    add_trace_processor,
    flush_traces,
)
from agents.tracing import TracingProcessor


class LocalTraceRecorder(TracingProcessor):
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.traces = {}
        self.spans = {}

    def on_trace_start(self, trace):
        self.traces[trace.trace_id] = {
            "trace": trace.export(),
            "spans": []
        }

    def on_trace_end(self, trace):
        trace_id = trace.trace_id

        if trace_id not in self.traces:
            self.traces[trace_id] = {
                "trace": trace.export(),
                "spans": []
            }

        self.traces[trace_id]["trace"] = trace.export()

        output_file = self.output_dir / f"{trace_id}.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(
                self.traces[trace_id],
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        print(f"[trace] Saved local trace: {output_file}")

    def on_span_start(self, span):
        pass

    def on_span_end(self, span):
        exported = span.export()
        trace_id = span.trace_id

        if trace_id not in self.traces:
            self.traces[trace_id] = {
                "trace": None,
                "spans": []
            }

        self.traces[trace_id]["spans"].append(exported)

    def shutdown(self):
        pass

    def force_flush(self):
        pass


def sanity_checks():

    required_paths = {
        "ABCA repository": config.ABCA_DIR,
        "input data": config.INPUT_DATA_DIR,
        "analysis Python": config.ANALYSIS_PYTHON,
    }

    for name, path in required_paths.items():
        if not path.exists():
            raise RuntimeError(
                f"Missing {name}: {path}"
            )

    if shutil.which("bwrap") is None:
        raise RuntimeError(
            "bubblewrap (bwrap) is required."
        )


def main():

    sanity_checks()

    config.ANALYSIS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ------------------------------------------------------------------
    # Build the active team from experiment_config.json
    # ------------------------------------------------------------------

    team = create_team()

    orchestrator = make_orchestrator(team)

    # ------------------------------------------------------------------
    # Run summary
    # ------------------------------------------------------------------

    print("=" * 72)
    print("ABCA AI AGENTS EXPERIMENT")
    print("=" * 72)

    print(f"Profile    : {config.ACTIVE_PROFILE_NAME}")
    print(f"Workflow   : {config.WORKFLOW}")
    print(
        "Agents     : "
        + ", ".join(
            f"{spec['id']}[{spec['role']}]"
            for spec in config.ACTIVE_AGENTS
        )
    )
    print(f"Prompts    : {config.ACTIVE_PROMPTS}")
    print(f"Repository : {config.ABCA_DIR}")
    print(f"Input data : {config.INPUT_DATA_DIR}")
    print(f"Analysis   : {config.ANALYSIS_DIR}")
    print(f"Plugin     : {config.PLUGIN_DIR}")
    print(f"Registry   : {config.REGISTRY_DIR}")
    print(f"Python lab : {config.ANALYSIS_PYTHON}")
    print(f"Max turns  : {config.MAX_TURNS}")

    # ------------------------------------------------------------------
    # Main orchestration run
    # ------------------------------------------------------------------

    TRACE_DIR = config.ANALYSIS_DIR / "traces"
    trace_recorder = LocalTraceRecorder(TRACE_DIR)
    add_trace_processor(trace_recorder)

    result = Runner.run_sync(
        orchestrator,
        config.INITIAL_EXPERIMENT_PROMPT,
        max_turns=config.MAX_TURNS,
        run_config=RunConfig(
            workflow_name=f"ABCA AI Agents - {config.ACTIVE_PROFILE_NAME}",
            trace_include_sensitive_data=True,
            trace_metadata={
                "profile": config.ACTIVE_PROFILE_NAME,
                "workflow": config.WORKFLOW,
            },
        ),
    )
    flush_traces()
    print()
    print("=" * 72)
    print("FINAL ORCHESTRATOR REPORT")
    print("=" * 72)

    print(result.final_output)


if __name__ == "__main__":
    main()
