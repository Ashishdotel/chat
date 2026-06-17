"""
evaluator.py — Chatbot Evaluation Module
-----------------------------------------
Collects quantitative metrics for the thesis evaluation chapter.
"""

import os
import json
import time
import statistics
from datetime import datetime
from typing import List, Dict, Optional
import httpx

from backend.utils.logger import get_logger

logger = get_logger(__name__)

PRICING = {
    "gpt-4o": {
        "input":  2.50,
        "output": 10.00
    },
    "gpt-4o-mini": {
        "input":  0.15,
        "output": 0.60
    }
}


class ChatbotEvaluator:

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url   = base_url
        self.session_id = None
        self.client     = httpx.Client(timeout=60.0)

    def _send_message(self, message: str) -> Dict:
        payload = {
            "message":    message,
            "session_id": self.session_id
        }

        start  = time.time()
        result = {
            "query":             message,
            "response":          None,
            "response_time_ms":  None,
            "prompt_tokens":     None,
            "completion_tokens": None,
            "total_tokens":      None,
            "rag_used":          False,
            "response_length":   None,
            "query_length":      len(message),
            "error":             None,
            "timestamp":         datetime.utcnow().isoformat()
        }

        try:
            r = self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            elapsed_ms = round((time.time() - start) * 1000, 2)

            server_time = r.headers.get("X-Response-Time", "")

            if r.status_code == 200:
                data = r.json()
                self.session_id = data.get("session_id")

                result.update({
                    "response":         data.get("reply", ""),
                    "response_time_ms": elapsed_ms,
                    "rag_used":         data.get("rag_used", False),
                    "response_length":  len(data.get("reply", "")),
                    "model_used":       data.get("model_used", "unknown"),
                    "server_time":      server_time,
                })
            else:
                result["error"] = f"HTTP {r.status_code}: {r.text[:200]}"
                result["response_time_ms"] = elapsed_ms

        except Exception as e:
            result["error"] = str(e)
            result["response_time_ms"] = round((time.time() - start) * 1000, 2)

        return result

    def run(
        self,
        test_cases: List[str],
        use_fresh_session: bool = True
    ) -> List[Dict]:
        results = []
        total   = len(test_cases)

        logger.info(f"Starting evaluation: {total} test cases")
        print(f"\n{'='*60}")
        print(f"  Nepali Chatbot Evaluation — {total} Test Cases")
        print(f"{'='*60}\n")

        for i, query in enumerate(test_cases, 1):
            if use_fresh_session:
                self.session_id = None

            print(f"[{i:02d}/{total}] Query: {query[:60]}{'...' if len(query) > 60 else ''}")
            result = self._send_message(query)

            status_icon = "✓" if not result["error"] else "✗"
            time_str    = f"{result['response_time_ms']}ms" if result["response_time_ms"] else "N/A"
            rag_str     = "📄RAG" if result["rag_used"] else "    "

            print(
                f"       {status_icon} {time_str:>8} | {rag_str} | "
                f"reply: {len(result['response'] or '')} chars"
            )

            if result["error"]:
                print(f"       ERROR: {result['error']}")

            results.append(result)
            time.sleep(0.5)

        return results

    def compute_summary(self, results: List[Dict]) -> Dict:
        successful = [r for r in results if not r["error"]]
        failed     = [r for r in results if r["error"]]

        if not successful:
            return {"error": "All queries failed"}

        times    = [r["response_time_ms"] for r in successful]
        lengths  = [r["response_length"]  for r in successful if r["response_length"]]
        rag_used = [r for r in successful if r["rag_used"]]

        summary = {
            "total_queries":      len(results),
            "successful":         len(successful),
            "failed":             len(failed),
            "success_rate":       round(len(successful) / len(results) * 100, 1),

            "response_time": {
                "mean":   round(statistics.mean(times), 1),
                "median": round(statistics.median(times), 1),
                "min":    round(min(times), 1),
                "max":    round(max(times), 1),
                "stdev":  round(statistics.stdev(times), 1) if len(times) > 1 else 0,
            },

            "response_length": {
                "mean":   round(statistics.mean(lengths), 1) if lengths else 0,
                "median": round(statistics.median(lengths), 1) if lengths else 0,
                "min":    min(lengths) if lengths else 0,
                "max":    max(lengths) if lengths else 0,
            },

            "rag": {
                "queries_using_rag": len(rag_used),
                "rag_usage_rate":    round(len(rag_used) / len(successful) * 100, 1),
            },

            "evaluated_at": datetime.utcnow().isoformat()
        }

        return summary

    def save_report(self, results: List[Dict], output_dir: str = "./evaluation/eval_results"):
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        results_path = os.path.join(output_dir, f"eval_{timestamp}_results.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        summary = self.compute_summary(results)
        summary_path = os.path.join(output_dir, f"eval_{timestamp}_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"Report saved: {results_path}")
        logger.info(f"Summary saved: {summary_path}")
        return summary_path

    def print_summary(self, results: List[Dict]):
        summary = self.compute_summary(results)

        print(f"\n{'='*60}")
        print("  EVALUATION SUMMARY")
        print(f"{'='*60}")
        print(f"  Total queries:     {summary['total_queries']}")
        print(f"  Successful:        {summary['successful']} ({summary['success_rate']}%)")
        print(f"  Failed:            {summary['failed']}")
        print()
        print("  Response Time (ms):")
        rt = summary["response_time"]
        print(f"    Mean:   {rt['mean']}ms")
        print(f"    Median: {rt['median']}ms")
        print(f"    Min:    {rt['min']}ms")
        print(f"    Max:    {rt['max']}ms")
        print(f"    StDev:  {rt['stdev']}ms")
        print()
        print("  Response Length (chars):")
        rl = summary["response_length"]
        print(f"    Mean:   {rl['mean']}")
        print(f"    Median: {rl['median']}")
        print()
        print("  RAG:")
        print(f"    Queries using RAG: {summary['rag']['queries_using_rag']}")
        print(f"    RAG usage rate:    {summary['rag']['rag_usage_rate']}%")
        print(f"{'='*60}\n")