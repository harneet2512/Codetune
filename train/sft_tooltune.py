"""Synthetic-trace SFT warmup for ToolTune."""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

from tooltune.io import load_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load reference data at module level for realistic tool observations
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent.parent / "tooltune_data"

WEATHER_DATA: dict[str, dict] = {}
FACTS_DATA: dict[str, str] = {}

if (_DATA_DIR / "weather.json").exists():
    with open(_DATA_DIR / "weather.json", encoding="utf-8") as f:
        WEATHER_DATA = json.load(f)

if (_DATA_DIR / "wikipedia_facts.json").exists():
    with open(_DATA_DIR / "wikipedia_facts.json", encoding="utf-8") as f:
        FACTS_DATA = json.load(f)

# ---------------------------------------------------------------------------
# Operation-word mapping for calculator expression extraction
# ---------------------------------------------------------------------------
_OP_WORDS = {
    "multiplied": "*",
    "times": "*",
    "plus": "+",
    "minus": "-",
    "divided": "/",
}


def _extract_expression(prompt: str) -> str:
    """Extract a math expression from a natural-language calculator prompt.

    Handles patterns like:
      - "What is 877 multiplied by 354?"
      - "Calculate 474 + 652."
      - "How much is 864 minus 375?"
    """
    # Pattern 1: explicit operator symbol  e.g. "Calculate 474 + 652."
    m = re.search(r"(\d+)\s*([+\-*/])\s*(\d+)", prompt)
    if m:
        return f"{m.group(1)} {m.group(2)} {m.group(3)}"

    # Pattern 2: operation word  e.g. "877 multiplied by 354"
    for word, op in _OP_WORDS.items():
        pattern = rf"(\d+)\s+{word}\s+(?:by\s+)?(\d+)"
        m = re.search(pattern, prompt, re.IGNORECASE)
        if m:
            return f"{m.group(1)} {op} {m.group(2)}"

    # Fallback: just grab the first two numbers
    nums = re.findall(r"\d+", prompt)
    if len(nums) >= 2:
        return f"{nums[0]} + {nums[1]}"
    return prompt


def _extract_city(prompt: str, metadata: dict) -> str:
    """Extract city from metadata or prompt."""
    if "city" in metadata:
        return metadata["city"]
    # Fallback: try to parse from prompt
    m = re.search(r"(?:weather|temperature)\s+(?:in|for)\s+(.+?)[\?\.]?$", prompt, re.IGNORECASE)
    if m:
        return m.group(1).strip().lower()
    return "tokyo"


# ---------------------------------------------------------------------------
# Trace builders
# ---------------------------------------------------------------------------

def _make_restraint_trace(prompt: str, answer: str) -> str:
    """Trace for tasks that need no tools (common knowledge)."""
    return (
        f"User: {prompt}\n"
        "<think>\nThis is common knowledge, no tools needed.\n</think>\n"
        f"<answer>\n{answer}\n</answer>"
    )


def _make_single_tool_trace(prompt: str, answer: str, tool_name: str, example: dict) -> str:
    """Trace for a single tool invocation with data-driven arguments."""
    metadata = example.get("metadata", {})

    if tool_name == "calculator":
        expression = _extract_expression(prompt)
        args_json = json.dumps({"expression": expression})
        think = f"I need to calculate {expression}."
        observation = str(answer)

    elif tool_name == "weather":
        city = _extract_city(prompt, metadata)
        args_json = json.dumps({"city": city})
        think = f"I need to look up the current weather in {city.title()}."
        weather_info = WEATHER_DATA.get(city)
        if weather_info:
            observation = json.dumps(weather_info)
        else:
            observation = json.dumps({"temp_celsius": 20, "temp_fahrenheit": 68.0, "conditions": "Clear"})

    elif tool_name == "wikipedia":
        query_key = metadata.get("query_key", prompt.lower())
        args_json = json.dumps({"query": query_key})
        think = f'I need to look up "{query_key}" using Wikipedia.'
        fact = FACTS_DATA.get(query_key)
        if fact:
            observation = fact
        else:
            observation = str(answer)

    elif tool_name == "unit_converter":
        value = metadata.get("value", 1)
        from_unit = metadata.get("from_unit", "celsius")
        to_unit = metadata.get("to_unit", "fahrenheit")
        args_json = json.dumps({"value": value, "from_unit": from_unit, "to_unit": to_unit})
        think = f"I need to convert {value} {from_unit} to {to_unit}."
        observation = str(answer)

    elif tool_name == "code_executor":
        code = metadata.get("code", "")
        args_json = json.dumps({"code": code})
        think = "I need to execute this Python code and return the output."
        observation = str(answer)

    else:
        # Generic fallback for unknown tools
        args_json = json.dumps({"query": prompt})
        think = f"I need to use the {tool_name} tool."
        observation = str(answer)

    tool_payload = f'{{"name": "{tool_name}", "arguments": {args_json}}}'

    return (
        f"User: {prompt}\n"
        f"<think>\n{think}\n</think>\n"
        f"<tool_call>\n{tool_payload}\n</tool_call>\n"
        f"<observation>\n{observation}\n</observation>\n"
        f"<answer>\n{answer}\n</answer>"
    )


def _make_multi_step_trace(prompt: str, answer: str, expected_tools: list[str], example: dict) -> str:
    """Trace for multi-step tool chains with data-driven arguments."""
    metadata = example.get("metadata", {})
    pattern = metadata.get("pattern", "")

    # Build a numbered plan
    tool_names_unique = list(dict.fromkeys(expected_tools))
    plan_lines = [f"{i+1}. Use {t} tool." for i, t in enumerate(tool_names_unique)]
    plan_lines.append(f"{len(tool_names_unique)+1}. Combine results and answer.")
    plan_text = "\n".join(plan_lines)

    blocks = [
        f"User: {prompt}\n"
        f"<think>\nPlan:\n{plan_text}\n</think>"
    ]

    if pattern == "weather_convert":
        # Step 1: weather lookup
        city = _extract_city(prompt, metadata)
        weather_info = WEATHER_DATA.get(city)
        if weather_info:
            temp_c = weather_info["temp_celsius"]
            weather_obs = json.dumps(weather_info)
        else:
            temp_c = 20
            weather_obs = json.dumps({"temp_celsius": 20, "temp_fahrenheit": 68.0, "conditions": "Clear"})

        w_args = json.dumps({"city": city})
        blocks.append(
            f"<think>\nStep 1: Look up the weather in {city.title()}.\n</think>\n"
            f'<tool_call>\n{{"name": "weather", "arguments": {w_args}}}\n</tool_call>\n'
            f"<observation>\n{weather_obs}\n</observation>"
        )

        # Step 2: unit conversion
        uc_args = json.dumps({"value": temp_c, "from_unit": "celsius", "to_unit": "fahrenheit"})
        blocks.append(
            f"<think>\nStep 2: Convert {temp_c}C to Fahrenheit.\n</think>\n"
            f'<tool_call>\n{{"name": "unit_converter", "arguments": {uc_args}}}\n</tool_call>\n'
            f"<observation>\n{answer}\n</observation>"
        )

    elif pattern == "pop_ratio":
        entity_a = metadata.get("entity_a", "A")
        entity_b = metadata.get("entity_b", "B")
        query_a = metadata.get("query_a", f"population of {entity_a.lower()}")
        query_b = metadata.get("query_b", f"population of {entity_b.lower()}")

        fact_a = FACTS_DATA.get(query_a, f"The population of {entity_a} is approximately X.")
        fact_b = FACTS_DATA.get(query_b, f"The population of {entity_b} is approximately Y.")

        # Step 1: look up entity A
        args_a = json.dumps({"query": query_a})
        blocks.append(
            f"<think>\nStep 1: Look up the population of {entity_a}.\n</think>\n"
            f'<tool_call>\n{{"name": "wikipedia", "arguments": {args_a}}}\n</tool_call>\n'
            f"<observation>\n{fact_a}\n</observation>"
        )

        # Step 2: look up entity B
        args_b = json.dumps({"query": query_b})
        blocks.append(
            f"<think>\nStep 2: Look up the population of {entity_b}.\n</think>\n"
            f'<tool_call>\n{{"name": "wikipedia", "arguments": {args_b}}}\n</tool_call>\n'
            f"<observation>\n{fact_b}\n</observation>"
        )

        # Step 3: calculate ratio
        calc_expr = f"population_{entity_a.lower()} / population_{entity_b.lower()}"
        calc_args = json.dumps({"expression": calc_expr})
        blocks.append(
            f"<think>\nStep 3: Calculate the ratio of {entity_a}'s population to {entity_b}'s population.\n</think>\n"
            f'<tool_call>\n{{"name": "calculator", "arguments": {calc_args}}}\n</tool_call>\n'
            f"<observation>\n{answer}\n</observation>"
        )

    elif pattern == "distance_cost":
        query_key = metadata.get("query_key", "")
        miles = metadata.get("miles", 0)
        mpg = metadata.get("mpg", 30)
        price = metadata.get("price", 3.50)

        fact = FACTS_DATA.get(query_key, f"The driving distance is approximately {miles} miles.")

        # Step 1: look up driving distance
        wiki_args = json.dumps({"query": query_key})
        blocks.append(
            f"<think>\nStep 1: Look up the driving distance.\n</think>\n"
            f'<tool_call>\n{{"name": "wikipedia", "arguments": {wiki_args}}}\n</tool_call>\n'
            f"<observation>\n{fact}\n</observation>"
        )

        # Step 2: calculate gas cost
        calc_expr = f"({miles} / {mpg}) * {price}"
        calc_args = json.dumps({"expression": calc_expr})
        blocks.append(
            f"<think>\nStep 2: Calculate gas cost: ({miles} miles / {mpg} mpg) * ${price}/gallon.\n</think>\n"
            f'<tool_call>\n{{"name": "calculator", "arguments": {calc_args}}}\n</tool_call>\n'
            f"<observation>\n{answer}\n</observation>"
        )

    else:
        # Generic multi-step: emit one think+tool_call+observation per expected tool
        for i, tool_name in enumerate(expected_tools, 1):
            t_args = json.dumps({"query": prompt})
            blocks.append(
                f"<think>\nStep {i}: Use {tool_name}.\n</think>\n"
                f'<tool_call>\n{{"name": "{tool_name}", "arguments": {t_args}}}\n</tool_call>\n'
                f"<observation>\n{answer}\n</observation>"
            )

    # Final answer
    blocks.append(f"<answer>\n{answer}\n</answer>")

    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

def make_trace(example: dict) -> str:
    """Build a synthetic training trace from a task example.

    Dispatches to specialised helpers based on the task structure so that
    tool arguments, observations, and reasoning are data-driven rather than
    hardcoded.
    """
    prompt = example["prompt"]
    answer = example["ground_truth"]
    expected_tools = example["expected_tools"]

    if not expected_tools:
        return _make_restraint_trace(prompt, answer)

    if len(expected_tools) == 1:
        return _make_single_tool_trace(prompt, answer, expected_tools[0], example)

    return _make_multi_step_trace(prompt, answer, expected_tools, example)


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------

def build_dataset(task_files: list[str]) -> Dataset:
    examples: list[dict] = []
    for path in task_files:
        for item in load_json(path):
            # Only keep 'text'; don't include 'prompt' — TRL 0.29+ treats datasets
            # with a 'prompt' column as conversational format and expects 'completion'.
            examples.append({"text": make_trace(item)})
    return Dataset.from_list(examples)


# ---------------------------------------------------------------------------
# Fine-tuning
# ---------------------------------------------------------------------------

def finetune(base_model: str, task_files: list[str], output_dir: str) -> None:
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        ),
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    train_ds = build_dataset(task_files)
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_ds,
        peft_config=lora_config,
        processing_class=tokenizer,
        args=SFTConfig(
            output_dir=output_dir,
            num_train_epochs=1,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            logging_steps=5,
            max_length=2048,
            report_to="none",
            dataset_text_field="text",
            fp16=True,
        ),
    )
    trainer.train()
    trainer.save_model(str(Path(output_dir) / "final_adapter"))
    tokenizer.save_pretrained(str(Path(output_dir) / "final_adapter"))


def main() -> None:
    parser = argparse.ArgumentParser(description="ToolTune SFT warmup")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--output-dir", default="outputs/tooltune-sft-checkpoints")
    parser.add_argument(
        "--task-files",
        nargs="+",
        default=["tasks/tier1_single_tool.json", "tasks/tier2_restraint.json", "tasks/tier3_multi_step.json"],
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    finetune(args.base_model, args.task_files, args.output_dir)


if __name__ == "__main__":
    main()
