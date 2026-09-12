from __future__ import annotations

import json
import time

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from agent.forms import AgentQueryForm, ChallengeQueryForm, ToolPlaygroundForm
from agent.models import AgentExecution, Challenge, ChallengeAttempt, ToolExecution
from agent.services import agent_service, tool_registry
from agent.services.challenge_evaluator import evaluate_challenge

SAMPLE_PROMPTS = [
    "Calculate 25% of 480",
    "What's the weather in Hyderabad?",
    "Search for the latest AI news",
    "Convert 10 km to miles",
    "What time is it in Tokyo?",
    "Analyze this text: AgentLab teaches tool calling with Django.",
    "Convert 100 USD to INR",
    'Validate this JSON: {"ok": true, "count": 3}',
]


def _metrics():
    executions = AgentExecution.objects.all()
    total = executions.count()
    successful = executions.filter(status=AgentExecution.STATUS_SUCCESS).count()
    failed = executions.filter(status=AgentExecution.STATUS_FAILED).count()
    tool_calls = ToolExecution.objects.count()
    multi_tool = executions.filter(tool_call_count__gte=2).count()
    return {
        "total_executions": total,
        "successful": successful,
        "failed": failed,
        "tool_calls": tool_calls,
        "multi_tool_tasks": multi_tool,
    }


def _api_status():
    gemini_ok = bool(getattr(settings, "GEMINI_API_KEY", "") or "")
    serp_ok = bool(getattr(settings, "SERPAPI_API_KEY", "") or "")
    weather_ok = bool(getattr(settings, "OPENWEATHERMAP_API_KEY", "") or "")
    currency_ok = bool(getattr(settings, "CURRENCY_API_KEY", "") or "")
    return {
        "gemini": {"configured": gemini_ok, "label": "Connected" if gemini_ok else "Not Configured"},
        "serpapi": {"configured": serp_ok, "label": "Connected" if serp_ok else "Not Configured"},
        "openweather": {
            "configured": weather_ok,
            "label": "Connected" if weather_ok else "Not Configured",
        },
        "currency": {
            "configured": currency_ok,
            "label": "Connected" if currency_ok else "Demo Mode",
        },
    }


@require_http_methods(["GET", "POST"])
def dashboard(request):
    execution = None
    if request.method == "POST":
        form = AgentQueryForm(request.POST)
        if form.is_valid():
            execution = agent_service.run_agent(form.cleaned_data["query"])
            if execution.status == AgentExecution.STATUS_SUCCESS:
                messages.success(request, "The agent completed this request.")
            else:
                messages.error(request, execution.final_response or "The agent could not complete this request.")
            return redirect(f"/?run={execution.pk}#agent-response")
        messages.error(request, "Please enter a valid question.")
    else:
        initial = {}
        prefill = request.GET.get("q", "").strip()
        if prefill:
            initial["query"] = prefill
        form = AgentQueryForm(initial=initial)
        run_id = request.GET.get("run")
        if run_id:
            execution = (
                AgentExecution.objects.filter(pk=run_id)
                .prefetch_related("tool_executions")
                .first()
            )

    if not execution:
        form.fields["query"].widget.attrs["autofocus"] = True

    return render(
        request,
        "dashboard.html",
        {
            "form": form,
            "execution": execution,
            "metrics": _metrics(),
            "sample_prompts": SAMPLE_PROMPTS,
            "page_title": "Dashboard",
        },
    )


def tools_page(request):
    return render(
        request,
        "tools.html",
        {
            "tools": tool_registry.list_tools(),
            "page_title": "Tools",
        },
    )


@require_http_methods(["GET", "POST"])
def playground(request):
    choices = [(tool.name, f"{tool.name} — {tool.description[:60]}") for tool in tool_registry.list_tools()]
    result = None
    result_pretty = None
    selected_tool = None
    parsed_args = None
    elapsed = None

    if request.method == "POST":
        form = ToolPlaygroundForm(request.POST, tool_choices=choices)
        if form.is_valid():
            selected_tool = tool_registry.get_tool(form.cleaned_data["tool"])
            raw_input = form.cleaned_data["input_data"]
            try:
                parsed_args = tool_registry.parse_playground_input(selected_tool, raw_input)
                started = time.perf_counter()
                result = tool_registry.execute_tool(selected_tool.name, parsed_args)
                elapsed = round(time.perf_counter() - started, 4)
                result_pretty = json.dumps(result.get("data") or {}, indent=2, ensure_ascii=False, default=str)
                if result.get("success"):
                    messages.success(request, f"{selected_tool.name} finished successfully.")
                else:
                    messages.error(request, result.get("error") or "The tool could not complete this request.")
            except ValueError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Please choose a tool and provide valid input.")
    else:
        initial = {}
        tool_name = request.GET.get("tool", "").strip()
        if tool_name:
            initial["tool"] = tool_name
        if request.GET.get("input"):
            initial["input_data"] = request.GET.get("input")
        form = ToolPlaygroundForm(initial=initial, tool_choices=choices)

    return render(
        request,
        "playground.html",
        {
            "form": form,
            "result": result,
            "result_pretty": result_pretty,
            "selected_tool": selected_tool,
            "parsed_args": parsed_args,
            "elapsed": elapsed,
            "page_title": "Tool Playground",
        },
    )


@require_http_methods(["GET", "POST"])
def agent_playground(request):
    execution = None
    if request.method == "POST":
        form = AgentQueryForm(request.POST)
        if form.is_valid():
            execution = agent_service.run_agent(form.cleaned_data["query"])
            if execution.status == AgentExecution.STATUS_SUCCESS:
                messages.success(request, "Agent playground run complete.")
            else:
                messages.error(request, execution.final_response or "The agent run failed.")
        else:
            messages.error(request, "Please enter a valid query.")
    else:
        form = AgentQueryForm(initial={"query": request.GET.get("q", "").strip()})

    if not execution:
        form.fields["query"].widget.attrs["autofocus"] = True

    return render(
        request,
        "agent_playground.html",
        {
            "form": form,
            "execution": execution,
            "page_title": "Agent Playground",
        },
    )


def tasks(request):
    challenges = Challenge.objects.all()
    grouped = {
        "beginner": challenges.filter(difficulty=Challenge.BEGINNER),
        "intermediate": challenges.filter(difficulty=Challenge.INTERMEDIATE),
        "advanced": challenges.filter(difficulty=Challenge.ADVANCED),
    }
    return render(
        request,
        "tasks.html",
        {
            "grouped": grouped,
            "page_title": "Learning Challenges",
        },
    )


@require_http_methods(["GET", "POST"])
def challenge_detail(request, pk: int):
    challenge = get_object_or_404(Challenge, pk=pk)
    if request.method == "POST":
        form = ChallengeQueryForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data["query"]
            execution = agent_service.run_agent(query)
            attempt = evaluate_challenge(challenge, execution, query)
            if attempt.success:
                messages.success(request, f"Challenge scored {attempt.score}/100.")
            else:
                messages.warning(request, f"Challenge scored {attempt.score}/100. Review the feedback and try again.")
            return redirect("challenge_result", pk=attempt.pk)
        messages.error(request, "Please submit a valid challenge query.")
    else:
        initial = {}
        if request.GET.get("use_sample") == "1" and challenge.sample_query:
            initial["query"] = challenge.sample_query
        form = ChallengeQueryForm(initial=initial)

    recent = challenge.attempts.all()[:5]
    return render(
        request,
        "challenge_detail.html",
        {
            "challenge": challenge,
            "form": form,
            "recent_attempts": recent,
            "page_title": challenge.title,
        },
    )


def challenge_result(request, pk: int):
    attempt = get_object_or_404(ChallengeAttempt.objects.select_related("challenge", "agent_execution"), pk=pk)
    return render(
        request,
        "challenge_result.html",
        {
            "attempt": attempt,
            "execution": attempt.agent_execution,
            "page_title": "Challenge Result",
        },
    )


def activity(request):
    queryset = AgentExecution.objects.prefetch_related("tool_executions")
    paginator = Paginator(queryset, getattr(settings, "HISTORY_PAGE_SIZE", 8))
    page = paginator.get_page(request.GET.get("page") or 1)
    return render(
        request,
        "activity.html",
        {
            "page": page,
            "page_title": "Activity",
        },
    )


def activity_detail(request, pk: int):
    execution = get_object_or_404(AgentExecution.objects.prefetch_related("tool_executions"), pk=pk)
    return render(
        request,
        "activity_detail.html",
        {
            "execution": execution,
            "page_title": f"Execution #{execution.pk}",
        },
    )


def history(request):
    queryset = AgentExecution.objects.prefetch_related("tool_executions")
    paginator = Paginator(queryset, getattr(settings, "HISTORY_PAGE_SIZE", 8))
    page = paginator.get_page(request.GET.get("page") or 1)
    return render(
        request,
        "history.html",
        {
            "page": page,
            "page_title": "History",
        },
    )


def settings_page(request):
    return render(
        request,
        "settings.html",
        {
            "api_status": _api_status(),
            "model": getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash"),
            "max_tool_calls": getattr(settings, "AGENT_MAX_TOOL_CALLS", 8),
            "page_title": "Settings",
        },
    )


def learning(request):
    return render(request, "learning.html", {"page_title": "Learning Mode"})


def developer(request):
    tools = tool_registry.list_tools()
    usage = {
        row["tool_name"]: row["total"]
        for row in ToolExecution.objects.values("tool_name").annotate(total=Count("id"))
    }
    failed = {
        row["tool_name"]: row["total"]
        for row in ToolExecution.objects.filter(status=ToolExecution.STATUS_FAILED)
        .values("tool_name")
        .annotate(total=Count("id"))
    }
    tool_rows = []
    for tool in tools:
        tool_rows.append(
            {
                "tool": tool,
                "schema_pretty": json.dumps(tool.gemini_declaration(), indent=2),
                "usage": usage.get(tool.name, 0),
                "failed": failed.get(tool.name, 0),
            }
        )

    challenge_stats = {
        "total": Challenge.objects.count(),
        "attempts": ChallengeAttempt.objects.count(),
        "passed": ChallengeAttempt.objects.filter(success=True).count(),
        "average_score": 0,
    }
    scores = list(ChallengeAttempt.objects.values_list("score", flat=True))
    if scores:
        challenge_stats["average_score"] = round(sum(scores) / len(scores), 1)

    return render(
        request,
        "developer.html",
        {
            "tool_rows": tool_rows,
            "api_status": _api_status(),
            "challenge_stats": challenge_stats,
            "failed_executions": AgentExecution.objects.filter(status=AgentExecution.STATUS_FAILED).count(),
            "page_title": "Developer Console",
        },
    )


def add_tool_guide(request):
    return render(request, "add_tool.html", {"page_title": "Add a Tool"})
