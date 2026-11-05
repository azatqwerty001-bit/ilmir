"""Бесплатный запуск учебной Django-версии на своём компьютере."""
from pathlib import Path
import os,subprocess,sys,threading,webbrowser
root=Path(__file__).resolve().parent
venv=root/'.cafe-venv'
python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if sys.version_info<(3,10):raise SystemExit('Установите Python 3.10 или новее.')
def run(args):subprocess.run(args,cwd=root,env=env,check=True)
env=os.environ.copy();env['DJANGO_DEBUG']='1'
print('Подготавливаем бесплатный локальный сайт. Хостинг не подключается.',flush=True)
if not python.exists():subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
run([str(python),'-m','pip','install','-r','server/requirements.txt'])
run([str(python),'server/build_static.py'])
run([str(python),'server/manage.py','migrate','--noinput'])
run([str(python),'server/manage.py','import_menu'])
check=subprocess.run([str(python),'server/manage.py','shell','-c','from django.contrib.auth import get_user_model; print("CUSTOMER_EXISTS" if get_user_model().objects.filter(is_staff=True).exists() else "NEED_CUSTOMER")'],cwd=root,env=env,capture_output=True,text=True,check=True)
if 'NEED_CUSTOMER' in check.stdout:
 print('Придумайте логин и пароль. Пароль при вводе не отображается.',flush=True)
 run([str(python),'server/manage.py','create_customer'])
print('Сейчас откроется админка. Не закрывайте это окно, пока работает сайт.',flush=True)
threading.Timer(3,lambda:webbrowser.open('http://127.0.0.1:8001/admin/')).start()
run([str(python),'server/manage.py','runserver','127.0.0.1:8001','--noreload'])
