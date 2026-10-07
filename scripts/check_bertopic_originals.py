import hashlib, json, zipfile
from pathlib import Path

root = Path("/home/ubuntu/VOC-System_2안")
desktop = Path("/mnt/c/Users/win/Desktop")
checks = {}
for name in ["voc_dummy_2500_v3_해설판.xlsx", "korail_voc_routing_master.xlsx"]:
    checks[name] = (
        hashlib.sha256((desktop / name).read_bytes()).hexdigest()
        == hashlib.sha256((root / "data" / name).read_bytes()).hexdigest()
    )
with zipfile.ZipFile(desktop / "voc-ui.zip") as archive:
    names = [n for n in archive.namelist() if n.endswith("/dist/styles.css")]
    assert len(names) == 1, names
    checks["original_styles_css_unchanged"] = (
        archive.read(names[0]) == (root / "voc-ui/dist/styles.css").read_bytes()
    )
assert all(checks.values()), checks
(root / "outputs/bertopic_original_checks.json").write_text(
    json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(checks, ensure_ascii=False))
