import subprocess

# Let's search Mach-O symbol table or use nm / strings
macho_path = r'extracted\Payload\client.app\client'

with open(macho_path, 'rb') as f:
    data = f.read(20000000) # read first 20MB or search string

# Let's find PyEval_EvalFrameEx or PyEval_EvalCodeEx in strings
idx = data.find(b'PyEval_EvalFrameEx')
print('PyEval_EvalFrameEx at offset:', idx)

idx2 = data.find(b'PyEval_EvalCodeEx')
print('PyEval_EvalCodeEx at offset:', idx2)
