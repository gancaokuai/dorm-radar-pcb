import heapq
import math
import pcbnew

STEP_MM = 0.5
BOARD_MARGIN_MM = 1.0
SIGNAL_WIDTH_MM = 0.30
POWER_WIDTH_MM = 0.55
SIGNAL_CLEARANCE_MM = 0.25
POWER_CLEARANCE_MM = 0.35
VIA_SIZE_MM = 0.80
VIA_DRILL_MM = 0.40
POWER_NETS = {"VBAT", "VBAT_F", "+5V", "+3V3", "SW"}

def mm(v):
    return pcbnew.ToMM(v)

def pos(pad):
    p = pad.GetPosition()
    return (mm(p.x), mm(p.y))

def idx(v):
    return int(round(v / STEP_MM))

def coord(i):
    return i * STEP_MM

def layers_for_pad(pad):
    result = []
    if pad.IsOnLayer(pcbnew.F_Cu):
        result.append(pcbnew.F_Cu)
    if pad.IsOnLayer(pcbnew.B_Cu):
        result.append(pcbnew.B_Cu)
    return result or [pcbnew.F_Cu]

def mark_rect(blocked, cx, cy, half_x, half_y):
    x0 = math.floor((cx - half_x) / STEP_MM)
    x1 = math.ceil((cx + half_x) / STEP_MM)
    y0 = math.floor((cy - half_y) / STEP_MM)
    y1 = math.ceil((cy + half_y) / STEP_MM)
    for ix in range(x0, x1 + 1):
        for iy in range(y0, y1 + 1):
            blocked.add((ix, iy))

def mark_segment(blocked, ix1, iy1, ix2, iy2, radius=1):
    steps = max(abs(ix2 - ix1), abs(iy2 - iy1))
    for n in range(steps + 1):
        t = 0 if steps == 0 else n / steps
        ix = int(round(ix1 + (ix2 - ix1) * t))
        iy = int(round(iy1 + (iy2 - iy1) * t))
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                blocked.add((ix + dx, iy + dy))

def pad_half_size(pad, clearance):
    s = pad.GetSize()
    return (mm(s.x) / 2 + clearance, mm(s.y) / 2 + clearance)

def build_pad_blocks(board, excluded_net):
    blocked = {pcbnew.F_Cu: set(), pcbnew.B_Cu: set()}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNetname()
            if not net or net == excluded_net or net == "GND":
                continue
            clearance = POWER_CLEARANCE_MM if net in POWER_NETS else SIGNAL_CLEARANCE_MM
            cx, cy = pos(pad)
            hx, hy = pad_half_size(pad, clearance)
            for layer in layers_for_pad(pad):
                mark_rect(blocked[layer], cx, cy, hx, hy)
    return blocked

def is_blocked(ix, iy, layer, pad_blocks, routed_blocks, width, height):
    margin_i = math.ceil(BOARD_MARGIN_MM / STEP_MM)
    max_x = math.floor(width / STEP_MM) - margin_i
    max_y = math.floor(height / STEP_MM) - margin_i
    if ix < margin_i or iy < margin_i or ix > max_x or iy > max_y:
        return True
    if (ix, iy) in pad_blocks[layer]:
        return True
    if (ix, iy) in routed_blocks[layer]:
        return True
    return False

def astar(start, goals, pad_blocks, routed_blocks, width, height):
    goals = set(goals)
    target_cells = {(x, y) for x, y, _ in goals}
    open_heap = []
    heapq.heappush(open_heap, (0, 0, start, None))
    came_from = {}
    cost_so_far = {start: 0}
    goal = None
    while open_heap:
        _, cost, current, parent = heapq.heappop(open_heap)
        if parent is not None and current not in came_from:
            came_from[current] = parent
        if current in goals:
            goal = current
            break
        ix, iy, layer = current
        candidates = []
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny, nl = ix + dx, iy + dy, layer
            if not is_blocked(nx, ny, nl, pad_blocks, routed_blocks, width, height):
                candidates.append(((nx, ny, nl), 1))
        other_layer = pcbnew.B_Cu if layer == pcbnew.F_Cu else pcbnew.F_Cu
        if not is_blocked(ix, iy, other_layer, pad_blocks, routed_blocks, width, height):
            candidates.append(((ix, iy, other_layer), 8))
        for nxt, step_cost in candidates:
            new_cost = cost + step_cost
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                hx, hy = nxt[0], nxt[1]
                h = min(abs(hx - gx) + abs(hy - gy) for gx, gy in target_cells)
                heapq.heappush(open_heap, (new_cost + h, new_cost, nxt, current))
    if goal is None:
        return None
    path = [goal]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    path.reverse()
    return path

def add_track(board, a, b, layer, width, net):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pcbnew.VECTOR2I_MM(a[0], a[1]))
    track.SetEnd(pcbnew.VECTOR2I_MM(b[0], b[1]))
    track.SetWidth(pcbnew.FromMM(width))
    track.SetLayer(layer)
    track.SetNet(net)
    board.Add(track)

def add_via(board, p, net, power=False):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I_MM(p[0], p[1]))
    via.SetWidth(pcbnew.FromMM(1.0 if power else VIA_SIZE_MM))
    via.SetDrill(pcbnew.FromMM(0.5 if power else VIA_DRILL_MM))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(net)
    board.Add(via)

def emit_path(board, path, net, routed_blocks, start_pad=None, end_pad=None, power=False):
    width = POWER_WIDTH_MM if power else SIGNAL_WIDTH_MM
    if not path:
        return
    segment_start = path[0]
    for previous, current in zip(path, path[1:]):
        if current[2] != segment_start[2]:
            if segment_start != previous:
                add_track(board, (coord(segment_start[0]), coord(segment_start[1])), (coord(previous[0]), coord(previous[1])), segment_start[2], width, net)
                mark_segment(routed_blocks[segment_start[2]], segment_start[0], segment_start[1], previous[0], previous[1])
            add_via(board, (coord(previous[0]), coord(previous[1])), net, power)
            mark_segment(routed_blocks[pcbnew.F_Cu], previous[0], previous[1], previous[0], previous[1], 1)
            mark_segment(routed_blocks[pcbnew.B_Cu], previous[0], previous[1], previous[0], previous[1], 1)
            segment_start = current
    add_track(board, (coord(segment_start[0]), coord(segment_start[1])), (coord(path[-1][0]), coord(path[-1][1])), segment_start[2], width, net)
    mark_segment(routed_blocks[segment_start[2]], segment_start[0], segment_start[1], path[-1][0], path[-1][1])
    if start_pad is not None:
        px, py = pos(start_pad)
        gx, gy = coord(path[0][0]), coord(path[0][1])
        if abs(px-gx) > 1e-6 or abs(py-gy) > 1e-6:
            add_track(board, (px, py), (gx, gy), path[0][2], width, net)
    if end_pad is not None:
        px, py = pos(end_pad)
        gx, gy = coord(path[-1][0]), coord(path[-1][1])
        if abs(px-gx) > 1e-6 or abs(py-gy) > 1e-6:
            add_track(board, (gx, gy), (px, py), path[-1][2], width, net)

def all_pads_by_net(board):
    groups = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNetname()
            if net:
                groups.setdefault(net, []).append(pad)
    return groups

def pad_state(pad):
    layers = layers_for_pad(pad)
    layer = pcbnew.F_Cu if pcbnew.F_Cu in layers else layers[0]
    x, y = pos(pad)
    return (idx(x), idx(y), layer)

def route_board(board, width, height, skip_nets=None):
    if skip_nets is None:
        skip_nets = set()
    groups = all_pads_by_net(board)
    net_order = sorted(
        [n for n in groups if n != "GND" and n not in skip_nets and len(groups[n]) > 1],
        key=lambda n: (0 if n in POWER_NETS else 1, len(groups[n]), n)
    )
    routed_blocks = {pcbnew.F_Cu: set(), pcbnew.B_Cu: set()}
    routed_nets = []
    failed = []
    for net_name in net_order:
        pads = groups[net_name]
        net = pads[0].GetNet()
        power = net_name in POWER_NETS
        pad_blocks = build_pad_blocks(board, net_name)
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            pad_blocks[layer] |= routed_blocks[layer]
        anchor = min(pads, key=lambda p: (pos(p)[0], pos(p)[1]))
        tree_nodes = {pad_state(anchor)}
        remaining = [p for p in pads if p is not anchor]
        for pad in remaining:
            start = pad_state(pad)
            goals = set(tree_nodes)
            path = astar(start, goals, pad_blocks, routed_blocks, width, height)
            if not path:
                failed.append((net_name, pad.GetNumber()))
                continue
            emit_path(board, path, net, routed_blocks, start_pad=pad, end_pad=None, power=power)
            tree_nodes.update(path)
        routed_nets.append(net_name)
    return routed_nets, failed

def add_gnd_vias(board):
    groups = all_pads_by_net(board)
    gnd_pads = groups.get("GND", [])
    gnd_net = gnd_pads[0].GetNet() if gnd_pads else None
    count = 0
    if gnd_net is None:
        return count
    for pad in gnd_pads:
        if pad.HasHole():
            continue
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pad.GetPosition())
        via.SetWidth(pcbnew.FromMM(VIA_SIZE_MM))
        via.SetDrill(pcbnew.FromMM(VIA_DRILL_MM))
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNet(gnd_net)
        board.Add(via)
        count += 1
    return count

def apply_low_drill_rules(board):
    settings = board.GetDesignSettings()
    settings.m_MinThroughDrill = pcbnew.FromMM(0.2)
    settings.m_MicroViasMinDrill = pcbnew.FromMM(0.2)
