"""Build a Blender Extension zip from an explicit source file allowlist."""
from pathlib import Path
import zipfile
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'gen3d_factory'
OUT=ROOT/'Gen3D_build'
FILES=['blender_manifest.toml','__init__.py','core.py','mesh_checks.py','demo.py','delivery.py','README.md','LICENSE']
if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    version=re.search(r'^version = "([^"]+)"',(SOURCE/'blender_manifest.toml').read_text(),re.M).group(1)
    archive=OUT/f'gen3d_factory-{version}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
        for name in FILES:
            output.write(SOURCE/name,name)
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise RuntimeError('Archive verification failed')
    print(archive)
