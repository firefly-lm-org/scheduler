import zipfile, os
os.makedirs(r'D:\firefly-scheduler\_e2e', exist_ok=True)
p = r'D:\firefly-scheduler\_e2e\sample_package.zip'
with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('config.json', '{"lr":2e-4,"epochs":1}')
    z.writestr('lora_base.safetensors', os.urandom(2048).hex())
print('OK', os.path.getsize(p), 'bytes')
