import pcbnew
from pathlib import Path
out=Path(r"F:\防宿管雷达\hardware\kicad\DormRadar\output")
for name in ["DormRadar_TX","DormRadar_RX"]:
    for suffix in [".dsn",".ses","_routed.kicad_pcb","_routed-drc.rpt"]:
        p=out/f"{name}{suffix}"
        if p.exists(): p.unlink()
    board=pcbnew.LoadBoard(str(out/f"{name}.kicad_pcb"))
    ok=pcbnew.ExportSpecctraDSN(board,str(out/f"{name}.dsn"))
    print(name,ok)
