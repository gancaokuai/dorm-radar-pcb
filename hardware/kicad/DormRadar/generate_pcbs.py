import pcbnew
from pathlib import Path
import generate_schematic as gd
import autoroute

OUT_DIR = Path(r"F:\防宿管雷达\hardware\kicad\DormRadar\output")
FP_ROOT = Path(r"D:\Program Files\KiCad\10.0\share\kicad\footprints")
FP_LIBS = {
    "Connector_JST": FP_ROOT / "Connector_JST.pretty",
    "Connector_PinHeader_1.27mm": FP_ROOT / "Connector_PinHeader_1.27mm.pretty",
    "Connector_PinHeader_2.54mm": FP_ROOT / "Connector_PinHeader_2.54mm.pretty",
    "Capacitor_SMD": FP_ROOT / "Capacitor_SMD.pretty",
    "Diode_SMD": FP_ROOT / "Diode_SMD.pretty",
    "Fuse": FP_ROOT / "Fuse.pretty",
    "Inductor_SMD": FP_ROOT / "Inductor_SMD.pretty",
    "LED_SMD": FP_ROOT / "LED_SMD.pretty",
    "Package_TO_SOT_SMD": FP_ROOT / "Package_TO_SOT_SMD.pretty",
    "RF_Module": FP_ROOT / "RF_Module.pretty",
    "Resistor_SMD": FP_ROOT / "Resistor_SMD.pretty",
    "MountingHole": FP_ROOT / "MountingHole.pretty",
}

def mm(x, y):
    return pcbnew.VECTOR2I_MM(x, y)

def add_outline(board, width, height):
    pts = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
    for a, b in zip(pts, pts[1:]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(mm(*a))
        seg.SetEnd(mm(*b))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        board.Add(seg)

def add_ground_zone(board, width, height, gnd_net):
    zone = pcbnew.ZONE(board)
    zone.SetNet(gnd_net)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetLocalClearance(pcbnew.FromMM(0.30))
    zone.SetMinThickness(pcbnew.FromMM(0.25))
    poly = zone.Outline()
    poly.NewOutline()
    for x, y in [(1, 1), (width - 1, 1), (width - 1, height - 1), (1, height - 1)]:
        poly.Append(pcbnew.VECTOR2I_MM(x, y))
    board.Add(zone)

def load_footprint(footprint_id):
    lib, name = footprint_id.split(":", 1)
    path = FP_LIBS.get(lib)
    if path is None:
        raise ValueError(f"Unsupported footprint library: {lib}")
    fp = pcbnew.FootprintLoad(str(path), name)
    if fp is None:
        raise ValueError(f"Footprint not found: {footprint_id}")
    return fp

def add_mounting_hole(board, ref, x, y):
    fp = pcbnew.FootprintLoad(str(FP_LIBS["MountingHole"]), "MountingHole_2.7mm_M2.5")
    if fp is None:
        raise ValueError("Mounting hole footprint not found")
    fp.SetReference(ref)
    fp.SetValue("M2.5")
    fp.SetPosition(mm(x, y))
    board.Add(fp)

def build_board(name, width, height, refs, placements):
    board = pcbnew.BOARD()
    autoroute.apply_low_drill_rules(board)
    add_outline(board, width, height)
    selected = [c for c in gd.components if c["ref"] in refs and c.get("footprint")]
    net_names = sorted({net for c in selected for net in c["nets"].values() if net})
    nets = {}
    for net_name in net_names:
        net = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(net)
        nets[net_name] = net
    for comp in selected:
        fp = load_footprint(comp["footprint"])
        x, y, rot = placements[comp["ref"]]
        fp.SetReference(comp["ref"])
        fp.SetValue(comp["value"])
        fp.SetPosition(mm(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            net_name = comp["nets"].get(pad.GetNumber())
            if net_name:
                pad.SetNet(nets[net_name])
        board.Add(fp)
    for ref, x, y in [
        ("H1", 3, 3), ("H2", width - 3, 3),
        ("H3", 3, height - 3), ("H4", width - 3, height - 3),
    ]:
        add_mounting_hole(board, ref, x, y)
    add_ground_zone(board, width, height, nets["GND"])
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    out = OUT_DIR / f"{name}.kicad_pcb"
    pcbnew.SaveBoard(str(out), board)
    return out

tx_placements = {
    "J1": (16, 38, 0), "F1": (25, 28, 0), "L1": (8, 22, 0), "U3": (22, 22, 0),
    "D1": (33, 22, 0), "U2": (30, 16, 0), "C1": (7, 32, 0), "C2": (13, 32, 0),
    "R1": (29, 31, 0), "R2": (34, 33, 0), "C3": (31, 38, 0), "C4": (37, 38, 0),
    "C5": (24, 13, 0), "C6": (37, 13, 0), "C7": (24, 19, 0), "C8": (37, 19, 0),
    "U1": (50, 8, 0), "R3": (42, 20, 0), "C9": (47, 20, 0), "R4": (52, 20, 0),
    "C10": (45, 36, 0), "J2": (63, 24, 90), "J3": (51, 39, 90),
}

rx_placements = {
    "J1": (34, 36, 0), "F1": (22, 22, 0), "L1": (9, 15, 0), "U3": (22, 14, 0),
    "D1": (33, 14, 0), "U2": (29, 23, 0), "C1": (8, 29, 0), "C2": (14, 29, 0),
    "R1": (18, 34, 0), "R2": (24, 35, 0), "C3": (45, 37, 0), "C4": (51, 37, 0),
    "C5": (24, 26, 0), "C6": (31, 26, 0), "C7": (24, 30, 0), "C8": (31, 30, 0),
    "U1": (50, 7, 0), "R3": (41, 27, 0), "C9": (47, 27, 0), "R4": (53, 27, 0),
    "R5": (8, 35, 0), "LED1": (14, 35, 0), "J3": (57, 27, 0),
}

tx_refs = {
    "J1","F1","L1","U3","D1","U2","C1","C2","R1","R2","C3","C4",
    "C5","C6","C7","C8","U1","R3","C9","R4","C10","J2","J3"
}
rx_refs = {
    "J1","F1","L1","U3","D1","U2","C1","C2","R1","R2","C3","C4",
    "C5","C6","C7","C8","U1","R3","C9","R4","R5","LED1","J3"
}

if __name__ == "__main__":
    print(build_board("DormRadar_TX", 70, 42, tx_refs, tx_placements))
    print(build_board("DormRadar_RX", 68, 42, rx_refs, rx_placements))














