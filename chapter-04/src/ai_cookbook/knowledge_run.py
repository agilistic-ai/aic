import argparse
from contextlib import closing
import json
from pathlib import Path
import sys

from pydantic import ValidationError
from .knowledge_index import Embeddings, KeywordIndex, build_index, save_index
from .knowledge_service import answer_question, match_venues, eligible
from .knowledge_sources import load_catalog
from .knowledge_matching import VenueNeeds
from .knowledge_retrieve import retrieve
from .settings import load_settings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search and answer from a current, permitted collection.")
    parser.add_argument("action", choices=("index", "search", "ask", "match"))
    parser.add_argument("folder", type=Path)
    parser.add_argument("question", nargs="?")
    parser.add_argument("--index", type=Path, default=Path("runs/knowledge/index.json"))
    parser.add_argument("--method", choices=("keyword", "dense", "hybrid"), default="hybrid")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--needs", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action != "index" and (not args.question or not args.question.strip()
                                      or len(args.question.encode("utf-8")) > 1000):
            raise ValueError("Supply a question within 1,000 UTF-8 bytes.")
        with closing(KeywordIndex() if args.method == "keyword" else Embeddings()) as embed:
            if args.action == "index":
                index = build_index(args.folder, load_catalog(args.folder), embed)
                save_index(index, args.index)
                failures = {k: v["error"] for k, v in index["documents"].items() if v["error"]}
                print(json.dumps({"index": str(args.index), "failures": failures}))
                return 1 if failures else 0
            index = json.loads(args.index.read_text(encoding="utf-8"))
            groups = lambda: frozenset({"members"})
            if args.action == "search":
                if args.method != "keyword" and index["embedding_key"] != embed.key:
                    raise ValueError("Embedding configuration changed; rebuild the index.")
                found = retrieve(args.question, eligible(args.folder, index, groups()), embed, method=args.method)
                available = {p["id"] for p in eligible(args.folder, index, groups())}
                result = [{k: v for k, v in p.items() if k != "vector"} for p in found if p["id"] in available]
            else:
                kwargs = dict(method=args.method, rerank=args.rerank, settings=load_settings(args.config))
                if args.action == "match":
                    if args.needs is None:
                        raise ValueError("match requires --needs with confirmed venue requirements.")
                    needs = VenueNeeds.model_validate_json(args.needs.read_text(encoding="utf-8"))
                    result = match_venues(args.folder, index, args.question, groups, embed, needs, **kwargs)
                else:
                    result = answer_question(args.folder, index, args.question, groups, embed, **kwargs)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    except ValidationError:
        message = "Structured input or model output failed validation."
    except (OSError, ValueError, KeyError) as error:
        message = str(error)
    except Exception:
        message = "Knowledge operation failed; check the model services and collection."
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
