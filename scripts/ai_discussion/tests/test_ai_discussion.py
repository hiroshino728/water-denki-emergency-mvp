from __future__ import annotations

import json
import os
import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import classify  # noqa: E402
import discuss  # noqa: E402
import issue_builder  # noqa: E402
import router  # noqa: E402


def round_value(status: str, classification_name: str = "implementation_task") -> dict:
    return {
        "status": status,
        "position": "具体的な提案または批評",
        "agreements": ["目的に合意"],
        "unresolved_points": [] if status == "converged" else ["制約条件の確認が必要"],
        "proposed_synthesis": "統合した実装案" if status == "converged" else None,
        "decision_classification": classification_name,
        "classification_reason": "設計変更を伴わない実装作業だから",
        "objective": "安全な自動化を実装する",
        "scope": ["workflow", "Python scripts"],
        "acceptance_criteria": ["期待するIssueが生成される"],
        "test_cases": ["mock APIで正常系を実行する"],
    }


DISCUSSION_ENV = {
    "MAX_ROUNDS": "3",
    "MAX_OUTPUT_TOKENS": "1000",
    "OPENAI_DISCUSSION_MODEL": "openai-test-model",
    "ANTHROPIC_DISCUSSION_MODEL": "anthropic-test-model",
    "OPENAI_API_KEY": "test-openai-secret",
    "ANTHROPIC_API_KEY": "test-anthropic-secret",
    "OPENAI_DISCUSSION_INPUT_USD_PER_MTOK": "1",
    "OPENAI_DISCUSSION_OUTPUT_USD_PER_MTOK": "2",
    "ANTHROPIC_DISCUSSION_INPUT_USD_PER_MTOK": "3",
    "ANTHROPIC_DISCUSSION_OUTPUT_USD_PER_MTOK": "4",
}


class RouterTests(unittest.TestCase):
    def test_forced_first_mover_skips_api_configuration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = router.route_topic("技術議題", "claude")
        self.assertEqual(result["first_mover"], "claude")
        self.assertTrue(result["forced"])
        self.assertEqual(result["api_calls"], 0)

    def test_auto_route_returns_usage_and_cost(self) -> None:
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {"first_mover": "chatgpt", "reason": "発散が有効", "confidence": 0.8}
                            ),
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        env = {
            "ROUTER_MODEL": "router-test-model",
            "MAX_OUTPUT_TOKENS": "1000",
            "OPENAI_API_KEY": "test-secret",
            "ROUTER_INPUT_USD_PER_MTOK": "1",
            "ROUTER_OUTPUT_USD_PER_MTOK": "2",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(router, "post_json", return_value=response):
            result = router.route_topic("市場アイデア", "auto")
        self.assertEqual(result["first_mover"], "chatgpt")
        self.assertEqual(result["api_calls"], 1)
        self.assertEqual(result["usage"], {"input_tokens": 100, "output_tokens": 50})
        self.assertAlmostEqual(result["estimated_cost_usd"], 0.0002)


class DiscussionTests(unittest.TestCase):
    def test_anthropic_uses_supported_output_config_schema(self) -> None:
        response = {
            "content": [{"type": "text", "text": json.dumps(round_value("unresolved"))}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        with patch.object(discuss, "post_json", return_value=response) as post:
            value, usage = discuss.call_anthropic("prompt", "claude-test", 1000, "secret")
        payload = post.call_args.args[1]
        output_format = payload["output_config"]["format"]
        self.assertEqual(output_format["type"], "json_schema")
        self.assertNotIn("minLength", json.dumps(output_format["schema"]))
        self.assertEqual(value["status"], "unresolved")
        self.assertEqual(usage, {"input_tokens": 10, "output_tokens": 5})

    def test_openai_invalid_json_preserves_stop_metadata_and_usage(self) -> None:
        response = {
            "id": "resp-test",
            "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"status":'}],
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 1000},
        }
        with patch.object(discuss, "post_json", return_value=response):
            with self.assertRaises(discuss.ModelJSONError) as raised:
                discuss.call_openai("prompt", "openai-test", 1000, "secret")
        self.assertEqual(raised.exception.raw_response, '{"status":')
        self.assertEqual(raised.exception.usage, {"input_tokens": 10, "output_tokens": 1000})
        self.assertEqual(
            raised.exception.metadata["incomplete_details"],
            {"reason": "max_output_tokens"},
        )

    def test_first_exchange_converges_after_two_api_call_rounds(self) -> None:
        speakers: list[str] = []

        def chatgpt(prompt: str, model: str, max_tokens: int, key: str):
            speakers.append("chatgpt")
            return round_value("converged"), {"input_tokens": 10, "output_tokens": 5}

        def claude(prompt: str, model: str, max_tokens: int, key: str):
            speakers.append("claude")
            return round_value("converged"), {"input_tokens": 20, "output_tokens": 10}

        with patch.dict(os.environ, DISCUSSION_ENV, clear=True):
            result = discuss.run_discussion(
                "合意しやすい議題",
                {"first_mover": "chatgpt"},
                {"chatgpt": chatgpt, "claude": claude},
            )
        self.assertEqual(speakers, ["chatgpt", "claude"])
        self.assertEqual(result["status"], "converged")
        self.assertEqual(result["rounds_completed"], 2)
        self.assertEqual(result["api_calls"], 2)
        self.assertEqual(result["rounds"][0]["status"], "unresolved")
        self.assertEqual(result["rounds"][1]["status"], "converged")

    def test_invalid_json_retries_once_and_counts_failed_usage(self) -> None:
        chatgpt_attempts = 0

        def chatgpt(prompt: str, model: str, max_tokens: int, key: str):
            nonlocal chatgpt_attempts
            chatgpt_attempts += 1
            if chatgpt_attempts == 1:
                raise discuss.ModelJSONError(
                    "Discussion model returned invalid JSON at line 1 column 8",
                    '{"status":',
                    {"input_tokens": 7, "output_tokens": 3},
                )
            return round_value("unresolved"), {"input_tokens": 10, "output_tokens": 5}

        def claude(prompt: str, model: str, max_tokens: int, key: str):
            return round_value("converged"), {"input_tokens": 20, "output_tokens": 10}

        with patch.dict(os.environ, DISCUSSION_ENV, clear=True), redirect_stderr(StringIO()):
            result = discuss.run_discussion(
                "再試行する議題",
                {"first_mover": "chatgpt"},
                {"chatgpt": chatgpt, "claude": claude},
            )

        self.assertEqual(chatgpt_attempts, 2)
        self.assertEqual(result["rounds_completed"], 2)
        self.assertEqual(result["api_calls"], 3)
        self.assertEqual(result["calls"][0]["api_calls"], 2)
        self.assertEqual(result["calls"][0]["retry_count"], 1)
        self.assertEqual(result["calls"][0]["input_tokens"], 17)
        self.assertEqual(result["calls"][0]["output_tokens"], 8)
        self.assertEqual(result["estimated_cost_usd"], 0.000133)

    def test_invalid_json_log_is_single_line_truncated_and_secret_redacted(self) -> None:
        secret = "test-openai-secret"
        raw_response = f'{{"position":"{secret}"\n::warning::untrusted'

        def invalid(prompt: str, model: str, max_tokens: int, key: str):
            raise discuss.ModelJSONError(
                "Discussion model returned invalid JSON at line 1 column 30",
                raw_response,
                {"input_tokens": 11, "output_tokens": 12},
            )

        stderr = StringIO()
        with patch.dict(os.environ, {"OPENAI_API_KEY": secret}, clear=True), redirect_stderr(stderr):
            with self.assertRaisesRegex(RuntimeError, "after 1 attempt"):
                discuss.call_with_json_retry(
                    invalid,
                    prompt="prompt",
                    model="openai-test-model",
                    max_output_tokens=1000,
                    api_key=secret,
                    provider="openai",
                    round_number=1,
                    max_attempts=1,
                    log_max_chars=40,
                )

        log_lines = stderr.getvalue().splitlines()
        self.assertEqual(len(log_lines), 1)
        self.assertNotIn(secret, stderr.getvalue())
        event = json.loads(log_lines[0])
        self.assertEqual(event["event"], "discussion_model_json_failure")
        self.assertTrue(event["raw_response_truncated"])
        self.assertIn("***REDACTED***", event["raw_response"])
        self.assertEqual(event["input_tokens"], 11)
        self.assertEqual(event["output_tokens"], 12)

    def test_invalid_json_stops_after_configured_attempts(self) -> None:
        attempts = 0

        def invalid(prompt: str, model: str, max_tokens: int, key: str):
            nonlocal attempts
            attempts += 1
            raise discuss.ModelJSONError("Discussion model returned invalid JSON", "not-json")

        with redirect_stderr(StringIO()):
            with self.assertRaisesRegex(RuntimeError, "after 2 attempt"):
                discuss.call_with_json_retry(
                    invalid,
                    prompt="prompt",
                    model="anthropic-test-model",
                    max_output_tokens=1000,
                    api_key="secret",
                    provider="anthropic",
                    round_number=2,
                    max_attempts=2,
                    log_max_chars=100,
                )
        self.assertEqual(attempts, 2)

    def test_http_error_is_not_retried(self) -> None:
        attempts = 0

        def http_error(prompt: str, model: str, max_tokens: int, key: str):
            nonlocal attempts
            attempts += 1
            raise RuntimeError("Model API returned HTTP 429")

        with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
            discuss.call_with_json_retry(
                http_error,
                prompt="prompt",
                model="openai-test-model",
                max_output_tokens=1000,
                api_key="secret",
                provider="openai",
                round_number=1,
                max_attempts=2,
                log_max_chars=100,
            )
        self.assertEqual(attempts, 1)

    def test_rejects_max_rounds_below_one_two_model_exchange(self) -> None:
        env = {**DISCUSSION_ENV, "MAX_ROUNDS": "1"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(discuss.ConfigurationError, "at least 2"):
                discuss.run_discussion("2AI討議", {"first_mover": "chatgpt"})

    def test_converged_with_unresolved_classification_continues_as_unresolved(self) -> None:
        value = discuss.validate_round(round_value("converged", "unresolved"), 2)
        self.assertEqual(value["status"], "unresolved")
        self.assertIsNone(value["proposed_synthesis"])
        self.assertTrue(value["unresolved_points"])

    def test_converged_without_synthesis_continues_as_unresolved(self) -> None:
        model_value = round_value("converged")
        model_value["proposed_synthesis"] = None
        value = discuss.validate_round(model_value, 2)
        self.assertEqual(value["status"], "unresolved")
        self.assertIsNone(value["proposed_synthesis"])
        self.assertTrue(value["unresolved_points"])

    def test_converged_with_unresolved_points_continues_as_unresolved(self) -> None:
        model_value = round_value("converged")
        model_value["unresolved_points"] = ["導入日の確認が必要"]
        value = discuss.validate_round(model_value, 2)
        self.assertEqual(value["status"], "unresolved")
        self.assertIsNone(value["proposed_synthesis"])
        self.assertEqual(value["unresolved_points"], ["導入日の確認が必要"])

    def test_unresolved_runs_to_max_rounds_without_synthesis(self) -> None:
        def unresolved(prompt: str, model: str, max_tokens: int, key: str):
            return round_value("unresolved"), {"input_tokens": 1, "output_tokens": 1}

        with patch.dict(os.environ, DISCUSSION_ENV, clear=True):
            result = discuss.run_discussion(
                "対立する議題",
                {"first_mover": "claude"},
                {"chatgpt": unresolved, "claude": unresolved},
            )
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["rounds_completed"], 3)
        self.assertTrue(result["unresolved_points"])
        self.assertTrue(all(item["proposed_synthesis"] is None for item in result["rounds"]))


class ClassificationAndBuilderTests(unittest.TestCase):
    def test_unresolved_overrides_model_classification(self) -> None:
        discussion = {"status": "unresolved", "rounds": [round_value("unresolved")]}
        result = classify.classify_discussion(discussion)
        self.assertEqual(result["classification"], "unresolved")

    def test_builds_separate_template_compliant_implementation_issue(self) -> None:
        routing = {
            "first_mover": "claude",
            "reason": "制約重視",
            "confidence": 0.9,
            "forced": False,
            "model": "router-test-model",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "api_calls": 1,
            "estimated_cost_usd": 0.0,
        }
        discussion = {
            "status": "converged",
            "rounds_completed": 2,
            "max_rounds": 3,
            "rounds": [
                {"round": 1, "speaker": "claude", **round_value("unresolved")},
                {"round": 2, "speaker": "chatgpt", **round_value("converged")},
            ],
            "unresolved_points": [],
            "calls": [],
        }
        classification_result = classify.classify_discussion(discussion)
        proposal = issue_builder.build_proposal(
            "安全なworkflowを作る", routing, discussion, classification_result
        )
        implementation = issue_builder.build_implementation(proposal["body"], 35)
        self.assertTrue(proposal["title"].startswith("[AI Discussion]"))
        self.assertIn("status:hold", proposal["labels"])
        self.assertIn("## Acceptance Criteria", implementation["body"])
        self.assertIn("## Latest Handoff", implementation["body"])
        self.assertIn("<!-- ai-discussion-source:#35 -->", implementation["body"])
        self.assertEqual(
            implementation["labels"],
            ["status:todo", "ready:true", "owner:unassigned", "execution:tbd"],
        )

    def test_summary_counts_physical_retry_calls(self) -> None:
        routing = {
            "api_calls": 1,
            "usage": {"input_tokens": 2, "output_tokens": 1},
            "model": "router-model",
            "estimated_cost_usd": 0.00001,
        }
        discussion = {
            "status": "converged",
            "calls": [
                {
                    "provider": "openai",
                    "speaker": "chatgpt",
                    "model": "discussion-model",
                    "api_calls": 2,
                    "retry_count": 1,
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "estimated_cost_usd": 0.00004,
                }
            ],
        }
        summary = issue_builder.build_summary(routing, discussion)
        self.assertIn("- API calls: `3`", summary)
        self.assertIn("| chatgpt | openai | `discussion-model` | 2 | 1 |", summary)


class WorkflowContractTests(unittest.TestCase):
    def test_public_content_confirmation_is_fail_closed_before_api_steps(self) -> None:
        workflow = (
            SCRIPT_DIR.parents[1] / ".github" / "workflows" / "ai_discussion_pipeline.yml"
        ).read_text()
        self.assertIn("public_content_confirmed:", workflow)
        self.assertIn("default: false", workflow)
        self.assertIn("inputs.public_content_confirmed != true", workflow)
        self.assertLess(
            workflow.index("Enforce Public repository content gate"),
            workflow.index("Route first speaker"),
        )


if __name__ == "__main__":
    unittest.main()
