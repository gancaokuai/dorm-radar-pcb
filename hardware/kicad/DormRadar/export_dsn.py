import pcbnew
from pathlib import Path
out=Path(r"F:\防宿管雷达\hardware\kicad\DormRadar\output")
for name in ["DormRadar_TX","DormRadar_RX"]:
    board=pcbnew.LoadBoard(str(out/f"{name}.kicad_pcb"))
    dsn=out/f"{name}.dsn"
    ok=pcbnew.ExportSpecctraDSN(board,str(dsn))
    print(name,ok,dsn)
