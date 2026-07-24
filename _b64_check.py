import base64
for f in ['requirements.txt', 'app/routers/node.py', 'app/utils/minio_client.py']:
    raw = open(f, 'rb').read()
    stripped = raw.lstrip(b'\xef\xbb\xbf')
    b64 = base64.b64encode(stripped).decode()
    print('FILE:', f, 'size', len(raw), 'bom_stripped', len(stripped), 'starts_bom', raw[:3]==b'\xef\xbb\xbf')
