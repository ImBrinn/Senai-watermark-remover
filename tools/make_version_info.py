"""Writes the Windows version details for the .exe (PyInstaller --version-file).

They show in the file's Properties → Details, and code signing needs the
product name and version set:  python tools/make_version_info.py build/version_info.txt
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "SenAI Watermark Remover"

TEMPLATE = """\
VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('080904B0', [
      StringStruct('CompanyName', 'ImBrinn'),
      StringStruct('FileDescription', '{name}'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'SenAI-Watermark-Remover'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 Brinn. MIT licence.'),
      StringStruct('OriginalFilename', 'SenAI-Watermark-Remover.exe'),
      StringStruct('ProductName', '{name}'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [0x0809, 1200])])
  ]
)
"""


def version() -> str:
    text = (ROOT / "senai_remover" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "(\d+\.\d+\.\d+)"', text).group(1)


def render(v: str) -> str:
    nums = tuple(int(n) for n in v.split(".")) + (0,)
    return TEMPLATE.format(nums=nums, name=NAME, version=v)


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/version_info.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(version()), encoding="utf-8")
    print(f"Wrote {out} for version {version()}")


if __name__ == "__main__":
    main()
