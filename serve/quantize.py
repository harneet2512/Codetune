"""Model quantization: GPTQ INT8, AWQ INT4, and GGUF conversion."""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def quantize_gptq(model_path: str, output_path: str, bits: int = 8) -> None:
    """Quantize model using GPTQ."""
    from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
    from transformers import AutoTokenizer

    logger.info(f"GPTQ {bits}-bit quantization: {model_path} → {output_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_path)

    quantize_config = BaseQuantizeConfig(
        bits=bits,
        group_size=128,
        desc_act=False,
    )

    model = AutoGPTQForCausalLM.from_pretrained(
        model_path,
        quantize_config=quantize_config,
    )

    # Calibration data
    from datasets import load_dataset
    calibration_ds = load_dataset("json", data_files="data/processed/train.jsonl", split="train")
    calibration_data = [tokenizer(ex["text"], return_tensors="pt") for ex in calibration_ds.select(range(128))]

    logger.info("Running GPTQ calibration...")
    model.quantize(calibration_data)

    model.save_quantized(output_path)
    tokenizer.save_pretrained(output_path)
    logger.info(f"GPTQ model saved to {output_path}")


def quantize_awq(model_path: str, output_path: str) -> None:
    """Quantize model using AWQ (4-bit)."""
    from awq import AutoAWQForCausalLM
    from transformers import AutoTokenizer

    logger.info(f"AWQ 4-bit quantization: {model_path} → {output_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoAWQForCausalLM.from_pretrained(model_path)

    quant_config = {
        "zero_point": True,
        "q_group_size": 128,
        "w_bit": 4,
        "version": "GEMM",
    }

    logger.info("Running AWQ quantization...")
    model.quantize(tokenizer, quant_config=quant_config)

    model.save_quantized(output_path)
    tokenizer.save_pretrained(output_path)
    logger.info(f"AWQ model saved to {output_path}")


def convert_gguf(model_path: str, output_path: str, quantization: str = "q4_k_m") -> None:
    """Convert model to GGUF format for llama.cpp."""
    import subprocess

    logger.info(f"Converting to GGUF ({quantization}): {model_path} → {output_path}")

    # First convert to f16 GGUF
    f16_path = output_path.replace(".gguf", "-f16.gguf")

    # Try to find llama.cpp convert script
    convert_script = shutil.which("convert_hf_to_gguf") or "convert_hf_to_gguf.py"

    subprocess.run(
        ["python", convert_script, model_path, "--outfile", f16_path, "--outtype", "f16"],
        check=True,
    )

    # Quantize
    llama_quantize = shutil.which("llama-quantize") or "llama-quantize"
    subprocess.run(
        [llama_quantize, f16_path, output_path, quantization.upper()],
        check=True,
    )

    # Clean up f16
    Path(f16_path).unlink(missing_ok=True)
    logger.info(f"GGUF model saved to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantize a model")
    parser.add_argument("--model", required=True, help="Input model path")
    parser.add_argument("--output", required=True, help="Output path")
    parser.add_argument(
        "--method", required=True, choices=["gptq", "awq", "gguf"],
        help="Quantization method",
    )
    parser.add_argument("--bits", type=int, default=8, help="Bit width (GPTQ only)")
    parser.add_argument(
        "--gguf-quant", default="q4_k_m",
        help="GGUF quantization type (e.g., q4_k_m, q8_0)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.method == "gptq":
        quantize_gptq(args.model, args.output, args.bits)
    elif args.method == "awq":
        quantize_awq(args.model, args.output)
    elif args.method == "gguf":
        convert_gguf(args.model, args.output, args.gguf_quant)


if __name__ == "__main__":
    main()
