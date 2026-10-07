import ast
import hashlib
import json
import subprocess
from pathlib import Path

import black
import jsbeautifier

root = Path(__file__).resolve().parent.parent
report = {
    "python_files": [],
    "javascript_files": [],
    "encoding_cleanup": [],
    "python_ast_equal": True,
    "javascript_ast_equal": True,
}
backup = root / "outputs" / "formatting_before"
backup.mkdir(parents=True, exist_ok=True)


def js_tree(text):
    script = "const a=require('acorn');const fs=require('fs');const t=a.parse(fs.readFileSync(0,'utf8'),{ecmaVersion:'latest'});console.log(JSON.stringify(t,(k,v)=>['start','end','loc','raw'].includes(k)?undefined:v));"
    return json.loads(
        subprocess.run(
            ["node", "-e", script],
            input=text,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
    )


changes = []
for directory in ["backend", "tests", "scripts"]:
    for path in sorted((root / directory).rglob("*.py")):
        original = path.read_text(encoding="utf-8-sig")
        old = original.replace(chr(10) + chr(65279), chr(10))
        if old != original:
            report["encoding_cleanup"].append(str(path.relative_to(root)))
        new = black.format_str(
            old,
            mode=black.Mode(
                line_length=88, target_versions={black.TargetVersion.PY311}
            ),
        )
        assert ast.dump(ast.parse(old), include_attributes=False) == ast.dump(
            ast.parse(new), include_attributes=False
        ), str(path)
        if original != new:
            changes.append((path, original, new))
            report["python_files"].append(str(path.relative_to(root)))
options = jsbeautifier.default_options()
options.indent_size = 2
options.wrap_line_length = 100
options.end_with_newline = True
for path in [root / "voc-ui/dist/app.js", root / "voc-ui/dist/topics.js"]:
    old = path.read_text(encoding="utf-8-sig")
    new = jsbeautifier.beautify(old, options)
    assert js_tree(old) == js_tree(new), str(path)
    if old != new:
        changes.append((path, old, new))
        report["javascript_files"].append(str(path.relative_to(root)))
for path, old, new in changes:
    target = backup / path.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(old, encoding="utf-8")
    path.write_text(new, encoding="utf-8")
(root / "outputs" / "formatting_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False))
