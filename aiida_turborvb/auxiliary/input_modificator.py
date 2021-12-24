import re

def input_modificator(src, changes):
    dest = []
    for line in src:
        for key, value in changes.items():
            if re.match("\s*!\s*"+key.lower()+"\s*=", line.lower()):
                line = f"{key}={value}"
            dest.append(line)
    return line
