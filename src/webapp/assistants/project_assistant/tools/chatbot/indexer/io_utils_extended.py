# AUTO-GENERATED shim: herexporteert functies uit opgesplitste modules
# Controleer handmatig voordat je commit

# WARNING: find_files_in_dir not found; leave placeholder
find_files_in_dir = None

# WARNING: read_and_meta not found; leave placeholder
read_and_meta = None

if not (find_files_in_dir and read_and_meta):
    missing = [n for n in ['find_files_in_dir','read_and_meta'] if not globals().get(n)]
    raise ImportError('io_utils_extended shim: missing functions: ' + ','.join(missing))
