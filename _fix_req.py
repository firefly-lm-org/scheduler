import io
p = 'requirements.txt'
s = io.open(p, encoding='utf-8-sig').read()
if 'bcrypt==' not in s:
    s = s.replace(
        'passlib[bcrypt]==1.7.4',
        'passlib[bcrypt]==1.7.4\nbcrypt==4.0.1  # pin: bcrypt>=4.1 breaks passlib backend detection'
    )
io.open(p, 'w', encoding='utf-8-sig').write(s)
print('bcrypt pinned:', 'bcrypt==4.0.1' in s)
