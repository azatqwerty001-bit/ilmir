"""Запуск бота: токен хранится на этом компьютере, вне сайта и Git."""
from pathlib import Path
import os,subprocess,sys,re
root=Path(__file__).resolve().parent
venv=root/'.cafe-venv';python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
env=os.environ.copy();env['DJANGO_DEBUG']='1'
state=Path(env.get('CAFE_DATA_DIR',str(root.parent/'.ilmir-production')))
state.mkdir(parents=True,exist_ok=True)
if sys.version_info<(3,10):raise SystemExit('Нужен Python 3.10 или новее.')
def run(args):
    result=subprocess.run(args,cwd=root,env=env)
    if result.returncode:raise SystemExit(result.returncode)
if not python.exists():subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
run([str(python),'-m','pip','install','-r','server/requirements.txt'])
run([str(python),'server/manage.py','migrate','--noinput'])
run([str(python),'server/manage.py','import_menu'])
if not env.get('TELEGRAM_BOT_TOKEN') and (not (state/'telegram-token.txt').exists() or '--reset-token' in sys.argv):
    token=None
    try:
        import tkinter as tk
        from tkinter import messagebox
        window=tk.Tk();window.title('Подключить Telegram-бота');window.geometry('560x260')
        tk.Label(window,text='Вставьте токен, который выдал BotFather.\nОн сохранится только на этом компьютере, вне сайта.',justify='left',wraplength=520).pack(padx=20,pady=20)
        value=tk.StringVar();entry=tk.Entry(window,textvariable=value,show='*',width=65);entry.pack(padx=20,pady=5);entry.focus_set()
        show=tk.BooleanVar();tk.Checkbutton(window,text='Показать токен (не делайте скриншот с ним)',variable=show,command=lambda:entry.config(show='' if show.get() else '*')).pack(pady=8)
        def save():
            global token
            proposed=value.get().strip()
            if not re.fullmatch(r'\d{5,20}:[A-Za-z0-9_-]{20,}',proposed):messagebox.showerror('Проверьте токен','Вставьте токен целиком, без пробелов.');return
            token=proposed;window.destroy()
        tk.Button(window,text='Сохранить и запустить бота',command=save).pack(pady=10)
        window.mainloop()
    except Exception:
        import getpass
        token=getpass.getpass('Вставьте токен BotFather (ввод скрыт): ').strip()
    if not token:raise SystemExit('Подключение отменено. Токен не сохранён.')
    if not re.fullmatch(r'\d{5,20}:[A-Za-z0-9_-]{20,}',token):raise SystemExit('Токен неверного формата.')
    file=state/'telegram-token.txt';file.write_text(token);os.chmod(file,0o600)
print('Подключаем Telegram-бота. Токен в журнал не выводится.',flush=True)
run([str(python),'server/manage.py','runbot'])
