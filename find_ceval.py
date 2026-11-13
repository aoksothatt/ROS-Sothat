with open(r'extracted\Payload\client.app\client', 'rb') as f:
    data = f.read()

targets = [
    b'unknown opcode',
    b'XXX unknown opcode',
    b'eval_frame',
    b'PyEval_EvalFrame',
    b'PyEval_EvalFrameEx',
    b'LOAD_FAST',
    b'STORE_FAST',
    b'CALL_FUNCTION',
    b'MAKE_CLOSURE',
    b'LOAD_GLOBAL',
    b'bad operand',
    b'no mem for sys.tracebacklimit',
    b'unhashable type',
    b'pop from an empty deque',
    b'SystemError: %s:%d'
]

for t in targets:
    off = 0
    matches = []
    while True:
        idx = data.find(t, off)
        if idx == -1: break
        matches.append(idx)
        off = idx + len(t)
    if matches:
        print(f"Found {t}: {[hex(m) for m in matches[:5]]}")
