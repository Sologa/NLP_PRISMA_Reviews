#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

MAPPING = {
    "2303.13365": "Requirement formalisation is the task of converting informal natural-language software or system requirements into precise, formal, machine-interpretable representations such as logic, models, or specifications.",
    "2306.12834": "Natural language processing in electronic health records for healthcare decision-making is the use of computational language methods to extract, classify, summarize, or translate information from free-text clinical records so that it can support clinical or administrative decisions.",
    "2307.05527": "The ethical implications of generative audio models are the moral, legal, and social issues created by systems that synthesize speech, music, or other audio, including deception, fraud, copyright infringement, consent, bias, and misuse.",
    "2310.07264": "Dysarthria severity classification is the task of assigning dysarthric speech to severity levels, typically by analyzing acoustic, prosodic, or learned speech representations to support objective assessment.",
    "2312.05172": "NLP techniques for taming long sentences are methods that improve the readability and comprehensibility of overly long sentences, chiefly through sentence compression and sentence splitting while preserving meaning.",
    "2401.09244": "Cross-lingual offensive language detection is the task of identifying offensive or harmful text in one language by leveraging data, representations, or models transferred from one or more other languages.",
    "2405.15604": "Text generation is the automatic production of coherent natural-language output by computational models across tasks such as open-ended generation, summarization, translation, paraphrasing, and question answering.",
    "2407.17844": "Speech-based deep learning for Parkinson's disease classification is the use of neural models to analyze speech signals and distinguish speech associated with Parkinson's disease from non-Parkinsonian speech for screening or diagnostic support.",
    "2409.13738": "Automated process extraction is the task of transforming natural-language descriptions of activities, actors, and control flow into structured process representations or process models using natural language processing.",
    "2503.04799": "Direct speech-to-speech translation is the translation of spoken input into spoken output with little or no explicit intermediate text representation, ideally preserving both meaning and salient speech characteristics such as prosody or speaker identity.",
    "2507.07741": "Code-switching in end-to-end automatic speech recognition is the recognition of multilingual speech that alternates between languages within an utterance using a single model that maps audio directly to transcriptions.",
    "2507.18910": "Retrieval-augmented generation is an architecture that combines external information retrieval with generative language models so that outputs are conditioned on retrieved evidence rather than only on parametric model memory.",
    "2509.11446": "Requirements engineering with large language models is the application of large language models to language-intensive requirements tasks such as elicitation, analysis, specification, validation, and related work over requirements artefacts.",
    "2510.01145": "Automatic speech recognition for African low-resource languages is the development and evaluation of speech-to-text systems for African languages that have limited labeled data, tooling, benchmark coverage, or other linguistic and computational resources.",
    "2511.13936": "Preference-based learning in audio is the training or evaluation of audio systems using relative judgments or rankings—often from humans or reward models—to optimize subjective qualities such as naturalness, quality, or musicality.",
    "2601.19926": "Syntactic knowledge in language models is the extent to which language models encode, represent, and use grammatical structure and dependencies, while interpretability research investigates how and where that knowledge is manifested inside the model.",
}

def update_payload(obj: dict) -> bool:
    changed = False
    target = obj.get("structured_payload") if isinstance(obj.get("structured_payload"), dict) else obj
    if not isinstance(target, dict):
        return False
    topic = target.get("topic")
    for stem, definition in MAPPING.items():
        if isinstance(topic, str) and stem in topic:
            if target.get("topic_definition") != definition:
                target["topic_definition"] = definition
                changed = True
            return changed
    return False

def main() -> int:
    repo_root = Path(".").resolve()
    criteria_dir = repo_root / "criteria_jsons"
    if not criteria_dir.exists():
        raise SystemExit(f"Cannot find criteria_jsons at: {criteria_dir}")

    changed_files = []
    for json_path in sorted(criteria_dir.glob("*.json")):
        stem = json_path.stem
        if stem not in MAPPING:
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        target = payload.get("structured_payload") if isinstance(payload.get("structured_payload"), dict) else payload
        if not isinstance(target, dict):
            continue
        new_definition = MAPPING[stem]
        if target.get("topic_definition") != new_definition:
            target["topic_definition"] = new_definition
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed_files.append(str(json_path))

    print(f"updated_files={len(changed_files)}")
    for path in changed_files:
        print(path)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
