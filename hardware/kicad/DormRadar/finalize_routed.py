import pcbnew
from pathlib import Path
out=Path(r"F:\防宿管雷达\hardware\kicad\DormRadar\output")
for name in ["DormRadar_TX","DormRadar_RX"]:
    board=pcbnew.LoadBoard(str(out/f"{name}_routed.kicad_pcb"))
    changed=0
    for item in board.GetTracks():
        if item.GetWidth() < pcbnew.FromMM(0.20):
            item.SetWidth(pcbnew.FromMM(0.20))
            changed += 1
    final=out/f"{name}_final.kicad_pcb"
    pcbnew.SaveBoard(str(final),board)
    print(name,"width_fixed",changed,final)
