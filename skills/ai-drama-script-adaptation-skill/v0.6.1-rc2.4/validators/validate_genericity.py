#!/usr/bin/env python3
from common import *
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--forbidden-terms", required=True); ap.add_argument("--report", required=True); args=ap.parse_args()
    root=Path(args.root); terms=[t for t in Path(args.forbidden_terms).read_text(encoding="utf-8").splitlines() if t.strip()]
    violations=[]
    for p in root.rglob("*"):
        if not p.is_file(): continue
        rel=str(p.relative_to(root))
        if rel.startswith("fix"+"tures/") or rel.startswith("vendor/") or rel.startswith("test-reports/") or rel.endswith("forbidden-terms.txt") or rel.endswith(".pyc"): continue
        if p.suffix not in [".md",".json",".py",".yaml",".yml",".txt"]: continue
        text=p.read_text(encoding="utf-8", errors="ignore")
        for term in terms:
            if term in text: violations.append({"path":rel,"term":term})
    if violations: emit("fail","ERR_GENERICITY","forbidden terms in generic files",args.report,violations=violations)
    emit("pass","","genericity valid",args.report,forbidden_term_count=len(terms))
if __name__=="__main__": main()
