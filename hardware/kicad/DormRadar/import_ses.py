import pcbnew
from pathlib import Path
out=Path(r"F:\防宿管雷达\hardware\kicad\DormRadar\output")
for name in ["DormRadar_TX","DormRadar_RX"]:
    board=pcbnew.LoadBoard(str(out/f"{name}.kicad_pcb"))
    ok=pcbnew.ImportSpecctraSES(board,str(out/f"{name}.ses"))
    routed=out/f"{name}_routed.kicad_pcb"
    pcbnew.SaveBoard(str(routed),board)
    print(name,ok,routed)
