"""Generate deterministic ToolTune task suites across all 5 tools."""

from __future__ import annotations

import itertools
import random
import re

from tooltune.contracts import TaskRecord
from tooltune.io import dump_json, load_json
from tooltune.paths import CONFIGS_DIR, DATA_DIR, TASKS_DIR

FACTS = load_json(DATA_DIR / "wikipedia_facts.json")
WEATHER = load_json(DATA_DIR / "weather.json")
RESTRAINT = load_json(DATA_DIR / "restraint_questions.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_number(text: str) -> float | None:
    """Extract the first meaningful number from a fact string.

    Handles patterns like:
      "approximately 68.4 million" -> 68.4
      "approximately 1440 million" -> 1440.0
      "approximately 299792458 meters" -> 299792458.0
      "approximately $27.4 trillion" -> 27.4  (trillion kept as-is, caller interprets)
      "in 1969" -> 1969.0
      "8849 m" -> 8849.0
    """
    # Remove dollar signs and commas for cleaner parsing
    cleaned = text.replace("$", "").replace(",", "")
    match = re.search(r"([\d]+\.?\d*)", cleaned)
    if match:
        return float(match.group(1))
    return None


def _unique_facts_by_prefix(prefix: str) -> list[tuple[str, str]]:
    """Return deduplicated (key, value) pairs where key starts with prefix."""
    seen_values: set[str] = set()
    results: list[tuple[str, str]] = []
    for key, value in FACTS.items():
        if key.startswith(prefix) and value not in seen_values:
            seen_values.add(value)
            results.append((key, value))
    return results


def _city_distance_pairs() -> list[tuple[str, str, str, float]]:
    """Extract city-to-city distance pairs: (city_a, city_b, query_key, miles)."""
    pairs = []
    seen = set()
    for key, value in FACTS.items():
        if "distance" not in key:
            continue
        # Match patterns like "distance X to Y" or "driving distance X to Y"
        m = re.match(r"(?:driving )?distance (.+?) to (.+?)$", key)
        if not m:
            continue
        city_a, city_b = m.group(1).strip(), m.group(2).strip()
        pair_key = tuple(sorted([city_a, city_b]))
        if pair_key in seen:
            continue
        seen.add(pair_key)
        miles = _extract_number(value)
        if miles and miles < 10000:  # filter out astronomical distances
            pairs.append((city_a, city_b, key, miles))
    return pairs


# ---------------------------------------------------------------------------
# Tier 1: Single-tool tasks
# ---------------------------------------------------------------------------

CALC_TEMPLATES = [
    "What is {a} {op_word} {b}?",
    "Calculate {a} {op_symbol} {b}.",
    "How much is {a} {op_word} {b}?",
    "Compute {a} {op_symbol} {b}.",
]

OP_MAP = {
    "multiplied by": ("*", lambda a, b: a * b),
    "plus": ("+", lambda a, b: a + b),
    "minus": ("-", lambda a, b: a - b),
    "divided by": ("/", lambda a, b: a / b),
}


def _build_calculator_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    tasks = []
    ops = list(OP_MAP.items())
    for i in range(count):
        op_word, (op_symbol, fn) = ops[i % len(ops)]
        if op_word == "divided by":
            b = rng.randint(2, 50)
            a = b * rng.randint(2, 100)  # ensure clean division
        else:
            a = rng.randint(10, 999)
            b = rng.randint(2, 999)
        template = CALC_TEMPLATES[i % len(CALC_TEMPLATES)]
        prompt = template.format(a=a, b=b, op_word=op_word, op_symbol=op_symbol)
        result = fn(a, b)
        ground_truth = str(int(result)) if float(result).is_integer() else str(round(result, 4))
        tasks.append(TaskRecord(
            id=f"tier1-calc-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["calculator"],
            metadata={"category": "calculator", "tool": "calculator"},
        ))
    return tasks


WIKI_TEMPLATES_POP = [
    "What is the population of {entity}?",
    "How many people live in {entity}?",
    "What is {entity}'s population?",
]

WIKI_TEMPLATES_GENERAL = [
    "What is {query}?",
    "Tell me about {query}.",
    "Look up {query}.",
]


def _build_wikipedia_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    tasks = []
    pop_facts = _unique_facts_by_prefix("population of ")
    # Filter to country-level populations (short keys)
    pop_facts = [(k, v) for k, v in pop_facts if len(k.split()) <= 4 and "europe" not in k]
    other_facts = []
    for key, value in FACTS.items():
        if value not in [v for _, v in pop_facts] and value not in [v for _, v in other_facts]:
            if not any(k.startswith("population") for k, _ in [(key, value)]):
                other_facts.append((key, value))

    all_wiki = pop_facts + other_facts[:30]
    rng.shuffle(all_wiki)

    for i, (key, value) in enumerate(itertools.islice(itertools.cycle(all_wiki), count)):
        if key.startswith("population of "):
            entity = key.replace("population of ", "").title()
            template = WIKI_TEMPLATES_POP[i % len(WIKI_TEMPLATES_POP)]
            prompt = template.format(entity=entity)
        else:
            template = WIKI_TEMPLATES_GENERAL[i % len(WIKI_TEMPLATES_GENERAL)]
            prompt = template.format(query=key)
        tasks.append(TaskRecord(
            id=f"tier1-wiki-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=value,
            expected_tools=["wikipedia"],
            metadata={"category": "wikipedia", "tool": "wikipedia", "query_key": key},
        ))
    return tasks[:count]


WEATHER_TEMPLATES = [
    "What's the current weather in {city}?",
    "What is the temperature in {city}?",
    "What are the weather conditions in {city} right now?",
    "How's the weather in {city}?",
]


def _build_weather_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    tasks = []
    cities = list(WEATHER.keys())
    rng.shuffle(cities)
    for i, city in enumerate(itertools.islice(itertools.cycle(cities), count)):
        data = WEATHER[city]
        template = WEATHER_TEMPLATES[i % len(WEATHER_TEMPLATES)]
        prompt = template.format(city=city.title())
        ground_truth = f"{data['conditions']}, {data['temp_celsius']}C"
        tasks.append(TaskRecord(
            id=f"tier1-weather-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["weather"],
            metadata={"category": "weather", "tool": "weather", "city": city},
        ))
    return tasks[:count]


CONVERT_SPECS = [
    ("celsius", "fahrenheit", 0, 40),
    ("fahrenheit", "celsius", 32, 104),
    ("pounds", "kilograms", 1, 500),
    ("kilometers", "miles", 1, 1000),
    ("miles", "kilometers", 1, 600),
    ("gallons", "liters", 1, 100),
]

CONVERT_TEMPLATES = [
    "Convert {value} {from_unit} to {to_unit}.",
    "How many {to_unit} is {value} {from_unit}?",
    "What is {value} {from_unit} in {to_unit}?",
]


def _build_unit_converter_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    from tools.unit_converter import run as convert_run

    tasks = []
    for i in range(count):
        from_unit, to_unit, lo, hi = CONVERT_SPECS[i % len(CONVERT_SPECS)]
        value = rng.randint(lo, hi)
        template = CONVERT_TEMPLATES[i % len(CONVERT_TEMPLATES)]
        prompt = template.format(value=value, from_unit=from_unit, to_unit=to_unit)
        ground_truth = convert_run(float(value), from_unit, to_unit)
        tasks.append(TaskRecord(
            id=f"tier1-convert-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["unit_converter"],
            metadata={"category": "unit_converter", "tool": "unit_converter",
                       "value": value, "from_unit": from_unit, "to_unit": to_unit},
        ))
    return tasks[:count]


CODE_SNIPPETS = [
    ("print(sum(range({n})))", lambda n: str(sum(range(n)))),
    ("print(len('{s}'))", lambda s: str(len(s))),
    ("print([x**2 for x in range({n})])", lambda n: str([x**2 for x in range(n)])),
    ("print(sum([x for x in range({n}) if x % 2 == 0]))", lambda n: str(sum(x for x in range(n) if x % 2 == 0))),
    ("print(len(range({a}, {b})))", lambda a, b: str(len(range(a, b)))),
]

CODE_TEMPLATES = [
    "Run this Python code and tell me the output: `{code}`",
    "What does this Python code print? `{code}`",
    "Execute this code: `{code}`",
]


def _build_code_executor_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    tasks = []
    words = ["hello", "world", "python", "programming", "artificial", "intelligence",
             "machine", "learning", "neural", "network", "algorithm", "function",
             "variable", "compiler", "database", "testing", "debugging", "refactor"]

    for i in range(count):
        snippet_idx = i % len(CODE_SNIPPETS)
        code_template, fn = CODE_SNIPPETS[snippet_idx]

        if snippet_idx == 0:  # sum(range(n))
            n = rng.randint(5, 50)
            code = code_template.format(n=n)
            ground_truth = fn(n)
        elif snippet_idx == 1:  # len(string)
            s = words[i % len(words)]
            code = code_template.format(s=s)
            ground_truth = fn(s)
        elif snippet_idx == 2:  # list comprehension squares
            n = rng.randint(4, 10)
            code = code_template.format(n=n)
            ground_truth = fn(n)
        elif snippet_idx == 3:  # sum of evens
            n = rng.randint(5, 30)
            code = code_template.format(n=n)
            ground_truth = fn(n)
        else:  # len(range(a,b))
            a = rng.randint(0, 20)
            b = a + rng.randint(5, 30)
            code = code_template.format(a=a, b=b)
            ground_truth = fn(a, b)

        template = CODE_TEMPLATES[i % len(CODE_TEMPLATES)]
        prompt = template.format(code=code)
        tasks.append(TaskRecord(
            id=f"tier1-code-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["code_executor"],
            metadata={"category": "code_executor", "tool": "code_executor", "code": code},
        ))
    return tasks[:count]


def build_tier1(count: int) -> list[TaskRecord]:
    rng = random.Random(42)
    calc_count = count * 25 // 100
    wiki_count = count * 25 // 100
    weather_count = count * 20 // 100
    convert_count = count * 15 // 100
    code_count = count - calc_count - wiki_count - weather_count - convert_count

    tasks: list[TaskRecord] = []
    tasks.extend(_build_calculator_tasks(calc_count, rng))
    tasks.extend(_build_wikipedia_tasks(wiki_count, rng))
    tasks.extend(_build_weather_tasks(weather_count, rng))
    tasks.extend(_build_unit_converter_tasks(convert_count, rng))
    tasks.extend(_build_code_executor_tasks(code_count, rng))
    rng.shuffle(tasks)
    return tasks[:count]


# ---------------------------------------------------------------------------
# Tier 2: Restraint (no tool needed)
# ---------------------------------------------------------------------------


def build_tier2(count: int) -> list[TaskRecord]:
    rng = random.Random(42)
    questions = list(RESTRAINT)
    rng.shuffle(questions)
    records = []
    for i, item in enumerate(itertools.islice(itertools.cycle(questions), count)):
        records.append(TaskRecord(
            id=f"tier2-restraint-{i+1}",
            tier="tier2_restraint",
            prompt=item["prompt"],
            ground_truth=item["ground_truth"],
            expected_tools=[],
            metadata={"category": "restraint"},
        ))
    return records[:count]


# ---------------------------------------------------------------------------
# Tier 3: Multi-step tool chaining
# ---------------------------------------------------------------------------


def _build_pop_ratio_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    """Pattern 1: wikipedia + wikipedia + calculator (population ratios)."""
    pop_facts = _unique_facts_by_prefix("population of ")
    pop_facts = [(k, v) for k, v in pop_facts if "europe" not in k and _extract_number(v)]
    rng.shuffle(pop_facts)

    tasks = []
    pairs_used: set[str] = set()
    for i in range(count):
        idx_a = i % len(pop_facts)
        idx_b = (i + 1 + i // len(pop_facts)) % len(pop_facts)
        if idx_a == idx_b:
            idx_b = (idx_b + 1) % len(pop_facts)
        key_a, val_a = pop_facts[idx_a]
        key_b, val_b = pop_facts[idx_b]

        pair_key = "|".join(sorted([key_a, key_b]))
        while pair_key in pairs_used and len(pairs_used) < len(pop_facts) * (len(pop_facts) - 1) // 2:
            idx_b = (idx_b + 1) % len(pop_facts)
            key_b, val_b = pop_facts[idx_b]
            pair_key = "|".join(sorted([key_a, key_b]))
        pairs_used.add(pair_key)

        entity_a = key_a.replace("population of ", "").title()
        entity_b = key_b.replace("population of ", "").title()
        num_a = _extract_number(val_a)
        num_b = _extract_number(val_b)

        if num_a and num_b and num_b != 0:
            ground_truth = str(round(num_a / num_b, 2))
        else:
            ground_truth = "unknown"

        templates = [
            f"What is the population of {entity_a} divided by the population of {entity_b}?",
            f"How many times larger is the population of {entity_a} compared to {entity_b}?",
            f"Calculate the ratio of {entity_a}'s population to {entity_b}'s population.",
        ]
        prompt = templates[i % len(templates)]
        tasks.append(TaskRecord(
            id=f"tier3-pop-ratio-{i+1}",
            tier="tier3_multi_step",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["wikipedia", "wikipedia", "calculator"],
            metadata={"category": "multi_step", "pattern": "pop_ratio",
                       "entity_a": entity_a, "entity_b": entity_b,
                       "query_a": key_a, "query_b": key_b},
        ))
    return tasks[:count]


def _build_weather_convert_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    """Pattern 2: weather + unit_converter (temperature conversion)."""
    cities = list(WEATHER.keys())
    rng.shuffle(cities)
    tasks = []
    for i, city in enumerate(itertools.islice(itertools.cycle(cities), count)):
        data = WEATHER[city]
        # Convert C to F
        ground_truth = str(data["temp_fahrenheit"])
        templates = [
            f"Convert the current temperature in {city.title()} from Celsius to Fahrenheit.",
            f"What is the temperature in {city.title()} in Fahrenheit?",
            f"Look up the temperature in {city.title()} and convert it to Fahrenheit.",
        ]
        prompt = templates[i % len(templates)]
        tasks.append(TaskRecord(
            id=f"tier3-weather-convert-{i+1}",
            tier="tier3_multi_step",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["weather", "unit_converter"],
            metadata={"category": "multi_step", "pattern": "weather_convert", "city": city},
        ))
    return tasks[:count]


def _build_distance_cost_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    """Pattern 3: wikipedia + calculator (driving cost from distance)."""
    dist_pairs = _city_distance_pairs()
    if not dist_pairs:
        return []
    rng.shuffle(dist_pairs)
    tasks = []
    mpg_options = [25, 28, 30, 32, 35]
    price_options = [3.0, 3.25, 3.50, 3.75, 4.0]
    for i in range(count):
        city_a, city_b, query_key, miles = dist_pairs[i % len(dist_pairs)]
        mpg = mpg_options[i % len(mpg_options)]
        price = price_options[i % len(price_options)]
        cost = round(miles / mpg * price, 2)
        ground_truth = str(cost)
        templates = [
            f"How much would gas cost to drive from {city_a.title()} to {city_b.title()} at ${price}/gallon if my car gets {mpg} mpg?",
            f"What's the fuel cost for driving from {city_a.title()} to {city_b.title()} at {mpg} mpg with gas at ${price}/gallon?",
            f"Calculate the gas cost to drive from {city_a.title()} to {city_b.title()}: {mpg} mpg, ${price}/gallon.",
        ]
        prompt = templates[i % len(templates)]
        tasks.append(TaskRecord(
            id=f"tier3-dist-cost-{i+1}",
            tier="tier3_multi_step",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["wikipedia", "calculator"],
            metadata={"category": "multi_step", "pattern": "distance_cost",
                       "query_key": query_key, "miles": miles, "mpg": mpg, "price": price},
        ))
    return tasks[:count]


def _build_temp_diff_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    """Pattern 4: weather + weather + calculator (temperature difference)."""
    cities = list(WEATHER.keys())
    rng.shuffle(cities)
    tasks = []
    pairs_used: set[str] = set()
    for i in range(count):
        idx_a = i % len(cities)
        idx_b = (i + 1) % len(cities)
        if idx_a == idx_b:
            idx_b = (idx_b + 1) % len(cities)
        city_a = cities[idx_a]
        city_b = cities[idx_b]
        pair_key = "|".join(sorted([city_a, city_b]))
        while pair_key in pairs_used and len(pairs_used) < len(cities) * (len(cities) - 1) // 2:
            idx_b = (idx_b + 1) % len(cities)
            city_b = cities[idx_b]
            pair_key = "|".join(sorted([city_a, city_b]))
        pairs_used.add(pair_key)

        diff = abs(WEATHER[city_a]["temp_celsius"] - WEATHER[city_b]["temp_celsius"])
        ground_truth = str(diff)
        templates = [
            f"What's the temperature difference between {city_a.title()} and {city_b.title()} in Celsius?",
            f"How many degrees Celsius apart are {city_a.title()} and {city_b.title()} right now?",
        ]
        prompt = templates[i % len(templates)]
        tasks.append(TaskRecord(
            id=f"tier3-temp-diff-{i+1}",
            tier="tier3_multi_step",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["weather", "weather", "calculator"],
            metadata={"category": "multi_step", "pattern": "temp_diff",
                       "city_a": city_a, "city_b": city_b},
        ))
    return tasks[:count]


def _build_wiki_code_tasks(count: int, rng: random.Random) -> list[TaskRecord]:
    """Pattern 5: wikipedia + code_executor (fact-based computation)."""
    pop_facts = _unique_facts_by_prefix("population of ")
    pop_facts = [(k, v) for k, v in pop_facts if "europe" not in k and _extract_number(v)]
    rng.shuffle(pop_facts)

    tasks = []
    rates = [1.5, 2.0, 2.5, 3.0, 1.0]
    years = [5, 10, 15, 20, 25]

    for i in range(count):
        key, value = pop_facts[i % len(pop_facts)]
        entity = key.replace("population of ", "").title()
        pop = _extract_number(value)
        rate = rates[i % len(rates)]
        n_years = years[i % len(years)]

        if pop:
            future_pop = round(pop * (1 + rate / 100) ** n_years, 2)
            ground_truth = str(future_pop)
        else:
            ground_truth = "unknown"

        prompt = (
            f"The population of {entity} grows at {rate}% per year. "
            f"Write Python code to calculate what the population will be in {n_years} years, "
            f"starting from its current population."
        )
        tasks.append(TaskRecord(
            id=f"tier3-wiki-code-{i+1}",
            tier="tier3_multi_step",
            prompt=prompt,
            ground_truth=ground_truth,
            expected_tools=["wikipedia", "code_executor"],
            metadata={"category": "multi_step", "pattern": "wiki_code",
                       "entity": entity, "query_key": key, "rate": rate, "years": n_years},
        ))
    return tasks[:count]


def build_tier3(count: int) -> list[TaskRecord]:
    rng = random.Random(42)
    pop_ratio_count = count * 30 // 100
    weather_convert_count = count * 25 // 100
    dist_cost_count = count * 25 // 100
    temp_diff_count = count * 10 // 100
    wiki_code_count = count - pop_ratio_count - weather_convert_count - dist_cost_count - temp_diff_count

    tasks: list[TaskRecord] = []
    tasks.extend(_build_pop_ratio_tasks(pop_ratio_count, rng))
    tasks.extend(_build_weather_convert_tasks(weather_convert_count, rng))
    tasks.extend(_build_distance_cost_tasks(dist_cost_count, rng))
    tasks.extend(_build_temp_diff_tasks(temp_diff_count, rng))
    tasks.extend(_build_wiki_code_tasks(wiki_code_count, rng))
    rng.shuffle(tasks)
    return tasks[:count]


# ---------------------------------------------------------------------------
# Tier 4: Error recovery (tier 3 + error injection)
# ---------------------------------------------------------------------------


def build_tier4(count: int) -> list[TaskRecord]:
    base = build_tier3(max(count, 1))
    rng = random.Random(99)
    records = []
    for index, item in enumerate(base[:count], start=1):
        prob = round(rng.uniform(0.15, 0.4), 2)
        records.append(TaskRecord(
            id=f"tier4-recovery-{index}",
            tier="tier4_error_recovery",
            prompt=item.prompt,
            ground_truth=item.ground_truth,
            expected_tools=item.expected_tools,
            metadata={**item.metadata, "category": "error_recovery"},
            error_injection_policy={
                "enabled": True,
                "probability": prob,
                "seed": index,
            },
        ))
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    config = load_json(CONFIGS_DIR / "task_config.json")
    counts = config["tier_counts"]
    suites = {
        "tier1_single_tool.json": [r.to_dict() for r in build_tier1(counts["tier1_single_tool"])],
        "tier2_restraint.json": [r.to_dict() for r in build_tier2(counts["tier2_restraint"])],
        "tier3_multi_step.json": [r.to_dict() for r in build_tier3(counts["tier3_multi_step"])],
        "tier4_error_recovery.json": [r.to_dict() for r in build_tier4(counts["tier4_error_recovery"])],
    }
    total = 0
    for filename, payload in suites.items():
        dump_json(TASKS_DIR / filename, payload)
        print(f"Wrote {filename} ({len(payload)} tasks)")
        total += len(payload)
    print(f"Total: {total} tasks")


if __name__ == "__main__":
    main()
