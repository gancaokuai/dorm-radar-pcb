import pcbnew
for name in ["DormRadar_TX","DormRadar_RX"]:
    b=pcbnew.LoadBoard(rf"F:\防宿管雷达\hardware\kicad\DormRadar\output\{name}.kicad_pcb")
    fp=b.FindFootprintByReference("U1")
    print(name)
    zones=fp.Zones()
    try:
        it=iter(zones)
    except Exception:
        it=[]
    for i,z in enumerate(it):
        bb=z.GetBoundingBox()
        print(i,"keepout_bbox_mm",pcbnew.ToMM(bb.GetX()),pcbnew.ToMM(bb.GetY()),pcbnew.ToMM(bb.GetRight()),pcbnew.ToMM(bb.GetBottom()))
