from pathlib import Path
import re
import uuid

SYM_DIR = Path(r"D:\Program Files\KiCad\10.0\share\kicad\symbols")
OUT = Path(r"F:\防宿管雷达\hardware\kicad\DormRadar\DormRadar.kicad_sch")
ROOT_UUID = str(uuid.uuid4())
PROJECT = "DormRadar"

def uid():
    return str(uuid.uuid4())

def balanced_block(text, start):
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise ValueError("Unbalanced block")

def load_symbol(lib, name):
    path = SYM_DIR / f"{lib}.kicad_sym"
    text = path.read_text(encoding="utf-8")
    start = text.find(f'(symbol "{name}"')
    if start < 0:
        raise ValueError(f"Symbol not found: {lib}:{name}")
    return balanced_block(text, start)

def get_extends(block):
    m = re.search(r'\(extends\s+"([^"]*)"\)', block)
    return m.group(1) if m else None

def symbol_pins(block):
    pins = []
    pattern = re.compile(r'\(pin\s+(?:input|output|bidirectional|passive|power_in|power_out|free|unspecified|no_connect)\s+')
    for m in pattern.finditer(block):
        pin_block = balanced_block(block, m.start())
        at = re.search(r'\(at\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\)', pin_block)
        name = re.search(r'\(name\s+"([^"]*)"', pin_block)
        number = re.search(r'\(number\s+"([^"]*)"', pin_block)
        if at and name and number:
            pins.append({"x": float(at.group(1)), "y": float(at.group(2)), "angle": float(at.group(3)), "name": name.group(1), "number": number.group(1)})
    return pins

def indented(block, levels=2):
    prefix = "\t" * levels
    return "\n".join(prefix + line for line in block.splitlines())

def fmt(v):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.4f}".rstrip("0").rstrip(".")

def wire(a, b):
    return ("\t(wire\n\t\t(pts\n" f"\t\t\t(xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])})\n" "\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n" f"\t\t(uuid \"{uid()}\")\n\t)\n")

def label(name, pos):
    return (f'\t(label "{name}"\n' f"\t\t(at {fmt(pos[0])} {fmt(pos[1])} 0)\n" "\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n" f"\t\t(uuid \"{uid()}\")\n\t)\n")

def no_connect(pos):
    return ("\t(no_connect\n" f"\t\t(at {fmt(pos[0])} {fmt(pos[1])})\n" f"\t\t(uuid \"{uid()}\")\n\t)\n")

def prop(name, value, pos, hide=False):
    h = "\n\t\t\t(hide yes)" if hide else ""
    return (f'\t\t(property "{name}" "{value}"\n' f"\t\t\t(at {fmt(pos[0])} {fmt(pos[1])} 0)\n" "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)" + h + "\n\t\t\t)\n\t\t)\n")

def instance(comp):
    out = []
    out.append("\t(symbol\n")
    out.append(f'\t\t(lib_id "{comp["lib"]}:{comp["symbol"]}")\n')
    out.append(f'\t\t(at {fmt(comp["at"][0])} {fmt(comp["at"][1])} 0)\n')
    out.append("\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n")
    out.append(f'\t\t(uuid "{uid()}")\n')
    ox, oy = comp["at"]
    out.append(prop("Reference", comp["ref"], (ox, oy - 5.08)))
    out.append(prop("Value", comp["value"], (ox, oy - 2.54)))
    out.append(prop("Footprint", comp.get("footprint", ""), (ox, oy), True))
    out.append(prop("Datasheet", "~", (ox, oy), True))
    out.append(prop("Description", comp.get("description", ""), (ox, oy), True))
    for pin in comp["pin_defs"]:
        out.append(f'\t\t(pin "{pin["number"]}"\n\t\t\t(uuid "{uid()}")\n\t\t)\n')
    out.append('\t\t(instances\n')
    out.append(f'\t\t\t(project "{PROJECT}"\n')
    out.append(f'\t\t\t\t(path "/{ROOT_UUID}"\n')
    out.append(f'\t\t\t\t\t(reference "{comp["ref"]}")\n\t\t\t\t\t(unit 1)\n')
    out.append('\t\t\t\t)\n\t\t\t)\n\t\t)\n')
    out.append("\t)\n")
    return "".join(out)

def transform(pin, origin, orientation=0):
    px, py = pin["x"], pin["y"]
    angle = orientation % 360
    if angle == 90:
        rx, ry = -py, px
    elif angle == 180:
        rx, ry = -px, -py
    elif angle == 270:
        rx, ry = py, -px
    else:
        rx, ry = px, py
    return (origin[0] + rx, origin[1] - ry)

def outward(pin, orientation=0):
    a = (pin["angle"] + orientation) % 360
    if a == 0:
        return (-1.0, 0.0)
    if a == 180:
        return (1.0, 0.0)
    if a == 90:
        return (0.0, 1.0)
    if a == 270:
        return (0.0, -1.0)
    return (1.0, 0.0)

components = [
    {"lib":"Connector_Generic","symbol":"Conn_01x02","ref":"J1","value":"BAT_1S","footprint":"Connector_JST:JST_VH_B2P-VH-B_1x02_P3.96mm_Vertical","at":(30,50),"nets":{"1":"VBAT","2":"GND"}},
    {"lib":"Device","symbol":"Fuse","ref":"F1","value":"2A","footprint":"Fuse:Fuse_1206_3216Metric","at":(55,50),"nets":{"1":"VBAT","2":"VBAT_F"}},
    {"lib":"Device","symbol":"C","ref":"C1","value":"100uF/10V","footprint":"Capacitor_SMD:C_1210_3225Metric","at":(30,75),"nets":{"1":"VBAT","2":"GND"}},
    {"lib":"Device","symbol":"C","ref":"C2","value":"22uF/10V","footprint":"Capacitor_SMD:C_1206_3216Metric","at":(50,75),"nets":{"1":"VBAT_F","2":"GND"}},
    {"lib":"Device","symbol":"L","ref":"L1","value":"22uH","footprint":"Inductor_SMD:L_12x12mm_H4.5mm","at":(80,35),"nets":{"1":"SW","2":"VBAT_F"}},
    {"lib":"Regulator_Switching","symbol":"MT3608","ref":"U3","value":"MT3608","footprint":"Package_TO_SOT_SMD:SOT-23-6","at":(80,60),"nets":{"1":"SW","2":"GND","3":"FB","4":"VBAT_F","5":"VBAT_F","6":None}},
    {"lib":"Device","symbol":"D_Schottky","ref":"D1","value":"SS34","footprint":"Diode_SMD:D_SMA","at":(110,35),"nets":{"1":"+5V","2":"SW"}},
    {"lib":"Device","symbol":"R","ref":"R1","value":"73.2k","footprint":"Resistor_SMD:R_0805_2012Metric","at":(110,60),"nets":{"1":"+5V","2":"FB"}},
    {"lib":"Device","symbol":"R","ref":"R2","value":"10k","footprint":"Resistor_SMD:R_0805_2012Metric","at":(110,78),"nets":{"1":"FB","2":"GND"}},
    {"lib":"Device","symbol":"C","ref":"C3","value":"22uF/10V","footprint":"Capacitor_SMD:C_1206_3216Metric","at":(135,35),"nets":{"1":"+5V","2":"GND"}},
    {"lib":"Device","symbol":"C","ref":"C4","value":"0.1uF","footprint":"Capacitor_SMD:C_0603_1608Metric","at":(150,35),"nets":{"1":"+5V","2":"GND"}},
    {"lib":"Regulator_Linear","symbol":"AP2112K-3.3","ref":"U2","value":"AP2112K-3.3","footprint":"Package_TO_SOT_SMD:SOT-23-5","at":(150,60),"nets":{"1":"+5V","2":"GND","3":"+5V","4":None,"5":"+3V3"}},
    {"lib":"Device","symbol":"C","ref":"C5","value":"1uF","footprint":"Capacitor_SMD:C_0805_2012Metric","at":(175,35),"nets":{"1":"+5V","2":"GND"}},
    {"lib":"Device","symbol":"C","ref":"C6","value":"1uF","footprint":"Capacitor_SMD:C_0805_2012Metric","at":(175,80),"nets":{"1":"+3V3","2":"GND"}},
    {"lib":"Device","symbol":"C","ref":"C7","value":"22uF/6.3V","footprint":"Capacitor_SMD:C_1206_3216Metric","at":(200,35),"nets":{"1":"+3V3","2":"GND"}},
    {"lib":"Device","symbol":"C","ref":"C8","value":"0.1uF","footprint":"Capacitor_SMD:C_0603_1608Metric","at":(215,35),"nets":{"1":"+3V3","2":"GND"}},
]

components.extend([
    {"lib":"RF_Module","symbol":"ESP32-C3-WROOM-02","ref":"U1","value":"ESP32-C3-WROOM-02","footprint":"RF_Module:ESP32-C3-WROOM-02","at":(210,105),"nets":{"1":"+3V3","2":"EN","3":"RADAR_TX","4":"RADAR_RX","5":None,"6":"LED_CTRL","7":None,"8":"BOOT","9":"GND","10":None,"11":"UART_RX","12":"UART_TX","13":None,"14":None,"15":None,"16":None,"17":None,"18":None,"19":"GND"}},
    {"lib":"Device","symbol":"R","ref":"R3","value":"10k","footprint":"Resistor_SMD:R_0805_2012Metric","at":(240,75),"nets":{"1":"+3V3","2":"EN"}},
    {"lib":"Device","symbol":"C","ref":"C9","value":"1uF","footprint":"Capacitor_SMD:C_0805_2012Metric","at":(255,75),"nets":{"1":"EN","2":"GND"}},
    {"lib":"Device","symbol":"R","ref":"R4","value":"10k","footprint":"Resistor_SMD:R_0805_2012Metric","at":(240,130),"nets":{"1":"+3V3","2":"BOOT"}},
    {"lib":"Device","symbol":"R","ref":"R5","value":"470R","footprint":"Resistor_SMD:R_0805_2012Metric","at":(240,50),"nets":{"1":"+3V3","2":"LED_A"}},
    {"lib":"Device","symbol":"LED","ref":"LED1","value":"RED","footprint":"LED_SMD:LED_0805_2012Metric","at":(260,50),"nets":{"1":"LED_CTRL","2":"LED_A"}},
    {"lib":"Device","symbol":"C","ref":"C10","value":"10uF/10V","footprint":"Capacitor_SMD:C_0805_2012Metric","at":(300,70),"nets":{"1":"+5V","2":"GND"}},
    {"lib":"Connector_Generic","symbol":"Conn_01x05","ref":"J2","value":"LD2450","footprint":"Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical","at":(330,70),"nets":{"1":"+5V","2":"GND","3":"RADAR_TX","4":"RADAR_RX","5":None}},
    {"lib":"Connector_Generic","symbol":"Conn_01x05","ref":"J3","value":"PROG","footprint":"Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical","at":(330,130),"nets":{"1":"GND","2":"EN","3":"BOOT","4":"UART_RX","5":"UART_TX"}},
    {"lib":"power","symbol":"PWR_FLAG","ref":"#FLG01","value":"PWR_FLAG","footprint":"","at":(15,20),"nets":{"1":"GND"}},
    {"lib":"power","symbol":"PWR_FLAG","ref":"#FLG02","value":"PWR_FLAG","footprint":"","at":(15,30),"nets":{"1":"VBAT_F"}},
    {"lib":"power","symbol":"PWR_FLAG","ref":"#FLG03","value":"PWR_FLAG","footprint":"","at":(15,40),"nets":{"1":"+5V"}},
    {"lib":"power","symbol":"PWR_FLAG","ref":"#FLG04","value":"PWR_FLAG","footprint":"","at":(15,10),"nets":{"1":"+3V3"}},
])

def collect_symbols(lib, name, seen=None, ordered=None):
    if seen is None:
        seen = set()
    if ordered is None:
        ordered = []
    key = (lib, name)
    if key in seen:
        return ordered
    block = load_symbol(lib, name)
    base = get_extends(block)
    if base:
        collect_symbols(lib, base, seen, ordered)
    seen.add(key)
    ordered.append((lib, name, block))
    return ordered

all_symbols = []
seen_symbols = set()
for comp in components:
    for lib, name, block in collect_symbols(comp["lib"], comp["symbol"]):
        key = (lib, name)
        if key not in seen_symbols:
            seen_symbols.add(key)
            all_symbols.append((lib, name, block))

for comp in components:
    block = load_symbol(comp["lib"], comp["symbol"])
    comp["pin_defs"] = symbol_pins(block)
    base = get_extends(block)
    if not comp["pin_defs"] and base:
        comp["pin_defs"] = symbol_pins(load_symbol(comp["lib"], base))
    pin_numbers = {p["number"] for p in comp["pin_defs"]}
    unknown = set(comp["nets"].keys()) - pin_numbers
    if unknown:
        raise ValueError(f'{comp["ref"]}: unknown pins {sorted(unknown)}')

wires = []
labels = []
no_connects = []
symbol_instances = []

for comp in components:
    for pin in comp["pin_defs"]:
        pos = transform(pin, comp["at"])
        direction = outward(pin)
        end = (pos[0] + direction[0] * 2.54, pos[1] + direction[1] * 2.54)
        net = comp["nets"].get(pin["number"])
        if net:
            wires.append(wire(pos, end))
            labels.append(label(net, end))
        else:
            no_connects.append(no_connect(pos))
    symbol_instances.append(instance(comp))

lines = []
lines.append("(kicad_sch")
lines.append("\t(version 20250114)")
lines.append('\t(generator "eeschema")')
lines.append('\t(generator_version "10.0")')
lines.append(f'\t(uuid "{ROOT_UUID}")')
lines.append('\t(paper "A3")')
lines.append("\t(title_block")
lines.append('\t\t(title "DormRadar Universal Node")')
lines.append('\t\t(date "2026-09-12")')
lines.append('\t\t(rev "v0.1")')
lines.append('\t\t(company "F:/防宿管雷达")')
lines.append('\t\t(comment 1 "TX: populate LD2450 J2. RX: leave J2 unpopulated and use LED.")')
lines.append("\t)")
lines.append("\t(lib_symbols")
for lib, name, block in all_symbols:
    block = block.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    lines.append(indented(block, 2))
lines.append("\t)")
lines.extend(chunk.rstrip("\n") for chunk in wires)
lines.extend(chunk.rstrip("\n") for chunk in labels)
lines.extend(chunk.rstrip("\n") for chunk in no_connects)
lines.extend(chunk.rstrip("\n") for chunk in symbol_instances)
lines.append("\t(sheet_instances")
lines.append('\t\t(path "/"')
lines.append('\t\t\t(page "1")')
lines.append("\t\t)")
lines.append("\t)")
lines.append("\t(embedded_fonts no)")
lines.append(")")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {OUT}")




