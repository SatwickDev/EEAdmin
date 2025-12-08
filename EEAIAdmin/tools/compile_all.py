import py_compile
import glob
import sys

files = glob.glob('**/*.py', recursive=True)
errs = 0
for f in files:
    try:
        # Skip files that contain null bytes (likely binary or backup files)
        with open(f, 'rb') as fh:
            data = fh.read()
            if b'\x00' in data:
                print('SKIP (binary/null bytes):', f)
                continue

        py_compile.compile(f, doraise=True)
    except Exception as e:
        print('ERROR:', f, e)
        errs += 1

if errs:
    print('\nDone: found', errs, 'file(s) with errors')
    sys.exit(1)

print('All Python files compiled successfully')
