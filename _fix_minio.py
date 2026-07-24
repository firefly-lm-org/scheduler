import io
p = 'app/utils/minio_client.py'
s = io.open(p, encoding='utf-8').read()
if 'from datetime import timedelta' not in s:
    s = s.replace('from minio import Minio', 'from datetime import timedelta\nfrom minio import Minio', 1)
n = s.count('expires=expires_sec,')
s = s.replace('expires=expires_sec,', 'expires=timedelta(seconds=expires_sec),')
io.open(p, 'w', encoding='utf-8').write(s)
print('replaced', n)
print('import_ok', 'from datetime import timedelta' in s)
print('left', s.count('expires=expires_sec,'))
