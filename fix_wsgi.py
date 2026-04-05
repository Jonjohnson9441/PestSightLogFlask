import os

wsgi_path = '/var/www/jonjohnson9441_pythonanywhere_com_wsgi.py'
app_path = '/home/Jonjohnson9441/pestsightlog'

lines = [
    'import sys\n',
    'path = \'' + app_path + '\'\n',
    'if path not in sys.path:\n',
    '    sys.path.insert(0, path)\n',
    'from app import app as application\n',
]

with open(wsgi_path, 'w') as f:
    f.writelines(lines)

print('WSGI file written successfully.')
print('Now go to the Web tab and click Reload.')
