content = open('/Users/investimenti/Projects/nexus/parse_vzc_v4.py').read()
old = "pm = re.search(r'Fakturované období:\\s*[\\d\\.]+\\s*[-\\u2013]\\s*(\\d+)\\.(\\d+)\\.(\\d{4})', result.stdout)"
new = "pm = re.search(r'Fakturovan.*[-\\u2013]\\s*(\\d+)\\.\\s*(\\d+)\\.\\s*(\\d{4})', result.stdout)"
if old in content:
    content = content.replace(old, new)
    print('Replaced (exact)')
else:
    # Try line-based
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'Fakturované' in line and 'pm = re.search' in line:
            lines[i] = "    pm = re.search(r'Fakturovan.*[-\\u2013]\\s*(\\d+)\\.\\s*(\\d+)\\.\\s*(\\d{4})', result.stdout)"
            print(f'Replaced line {i}')
    content = '\n'.join(lines)
open('/Users/investimenti/Projects/nexus/parse_vzc_v4.py', 'w').write(content)
print('Done')
