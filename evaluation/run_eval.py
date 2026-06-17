"""
run_eval.py — CLI Evaluation Runner
-------------------------------------
Run this script directly to evaluate the chatbot:

    python evaluation/run_eval.py

Make sure the server is running first:
    uvicorn backend.main:app --reload
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.evaluator import ChatbotEvaluator

TEST_CASES = [
    "नमस्ते",
    "तपाईंलाई कस्तो छ?",
    "तपाईंको नाम के हो?",
    "नेपालको राजधानी कुन हो?",
    "नेपालको सबैभन्दा अग्लो हिमाल कुन हो?",
    "नेपालका प्रमुख नदीहरूको नाम बताउनुहोस्।",
    "नेपालको राष्ट्रिय फूल के हो?",
    "नेपालको राष्ट्रिय खेल के हो?",
    "नेपालको प्रमुख चाडपर्वहरू के के हुन्?",
    "दशैं चाडको महत्त्व के छ?",
    "नेपाली संस्कृतिको विशेषता बताउनुहोस्।",
    "What is the population of Nepal?",
    "Tell me about Nepali cuisine.",
    "What languages are spoken in Nepal?",
    "नेपालको शिक्षा प्रणालीको बारेमा विस्तारमा बताउनुहोस्।",
    "नेपालको अर्थव्यवस्थाका प्रमुख क्षेत्रहरू के के हुन्?",
    "मलाई नेपाली भाषा सिक्न मद्दत गर्नुस्।",
    "नेपालमा पर्यटनको महत्त्व के छ?",
]


def main():
    print("\n🇳🇵 Nepali Chatbot — Thesis Evaluation")
    print("=========================================")
    print("Make sure the server is running at http://localhost:8000\n")

    base_url = os.getenv("EVAL_BASE_URL", "http://localhost:8000")
    evaluator = ChatbotEvaluator(base_url=base_url)

    results = evaluator.run(TEST_CASES, use_fresh_session=True)

    evaluator.print_summary(results)

    output_dir = os.getenv("EVAL_OUTPUT_DIR", "./evaluation/eval_results")
    summary_path = evaluator.save_report(results, output_dir=output_dir)

    print(f"📊 Full report saved to: {summary_path}")
    print("Use these results in your thesis evaluation chapter.\n")


if __name__ == "__main__":
    main()