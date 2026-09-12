import pcbnew
for token in ["SPEC","DSN","ROUT","FREEROUT"]:
    names=[n for n in dir(pcbnew) if token in n.upper()]
    print(token,names)
print("BOARD", [n for n in dir(pcbnew.BOARD) if 'SPEC' in n.upper() or 'DSN' in n.upper() or 'ROUT' in n.upper()])
