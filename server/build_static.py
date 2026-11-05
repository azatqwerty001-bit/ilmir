from pathlib import Path
import shutil
root=Path(__file__).resolve().parent.parent
target=root/'server/public_static';(target/'assets').mkdir(parents=True,exist_ok=True)
for name in ['style.css','script.js','menu-render.js']:shutil.copyfile(root/name,target/name)
for image in (root/'assets').iterdir():
    if image.suffix=='.webp' or image.name=='favicon.svg':shutil.copyfile(image,target/'assets'/image.name)
print('Статические файлы подготовлены; приватные и исходные файлы исключены.')
