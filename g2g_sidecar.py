"""Text-only subprocess that owns gr-nlp-toolkit outside the frozen Windows EXE.

The GUI's installer verifies the model before writing verified.json. Normal
searches run this companion with offline Hugging Face flags and keep it alive
for repeated conversions. No MP3/audio or lyrics files are read or modified.
"""
from __future__ import annotations
import argparse
import json
import sys

MAGIC = "@@LRC_G2G@@"
SAMPLE = "O Volos kai h Larisa einai sth Thessalia"


def emit(data):
    print(MAGIC + json.dumps(data, ensure_ascii=False), flush=True)


def load_model(model):
    from gr_nlp_toolkit import Pipeline
    # CPU avoids VRAM exhaustion on modest graphics cards (e.g. GTX 1650 4 GB).
    return Pipeline(model, use_cpu=True)


def main(argv=None):
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--serve", action="store_true")
    group.add_argument("--self-test", action="store_true")
    parser.add_argument("--model", choices=["g2g","g2g_lite"], default="g2g")
    args=parser.parse_args(argv)
    try:
        nlp=load_model(args.model)
        sample=nlp(SAMPLE)
        sample_text=str(getattr(sample,"text",sample)).strip()
        if not any("\u0370" <= c <= "\u03ff" for c in sample_text):
            raise RuntimeError("The installed model did not output Greek text")
        if args.self_test:
            print("G2G TEST PASSED: "+sample_text,flush=True)
            return 0
        emit({"status":"ready"})
        for line in sys.stdin:
            try:
                request=json.loads(line)
                original=request.get("text")
                if not isinstance(original,str) or len(original)>400:
                    emit({"error":"Invalid or too-long input"})
                    continue
                doc=nlp(original)
                emit({"text":str(getattr(doc,"text",doc)).strip()})
            except (ValueError,TypeError,RuntimeError) as exc:
                emit({"error":type(exc).__name__+": "+str(exc)[:180]})
        return 0
    except (ImportError,OSError,ValueError,RuntimeError,MemoryError) as exc:
        emit({"error":type(exc).__name__+": "+str(exc)[:180]})
        return 2


if __name__=="__main__":
    raise SystemExit(main())
