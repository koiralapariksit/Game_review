# matches/templatetags/tactical_viz.py
import re
from typing import List, Dict, Any, Optional
from decimal import Decimal
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


@register.simple_tag
def render_starting_pitch(match) -> str:
    """
    Renders a zero-JS dark-themed SVG football pitch (viewBox="0 0 600 400")
    with accurate penalty boxes, center circle, half-space tactical channels,
    and dynamically plotted FC Barcelona starting XI player nodes.
    Displays 'Lineup Formation Unavailable' overlay if lineup data is absent.
    """
    # 1. Discover lineup players
    lineup_players: List[Dict[str, Any]] = []

    # Check match.player_performances first
    if hasattr(match, 'player_performances') and match.player_performances.exists():
        perfs = list(match.player_performances.select_related('player').order_by('player__jersey_number'))
        for p in perfs[:11]:
            player = p.player
            p_name = getattr(player, 'full_name', None) or getattr(player, 'name', '')
            surname = p_name.split()[-1] if p_name else "Player"
            lineup_players.append({
                "number": player.jersey_number or "?",
                "name": surname[:14],
                "position": player.position or "MF"
            })

    # Fallback to match.raw_data_snapshot
    if len(lineup_players) < 7 and hasattr(match, 'raw_data_snapshot') and match.raw_data_snapshot:
        snapshot = match.raw_data_snapshot
        raw_list = []
        if isinstance(snapshot, dict):
            if "barcelona_squad" in snapshot and isinstance(snapshot["barcelona_squad"], dict):
                raw_list = snapshot["barcelona_squad"].get("starting_xi", [])
            elif "starting_xi" in snapshot:
                raw_list = snapshot.get("starting_xi", [])
            elif "lineup" in snapshot:
                raw_list = snapshot.get("lineup", [])

        if raw_list and isinstance(raw_list, list):
            lineup_players = []
            for item in raw_list[:11]:
                # Format: "Joan García (#1)" or "Lamine Yamal"
                m = re.search(r"^(.*?)(?:\s*\(#?(\d+)\))?$", str(item).strip())
                if m:
                    full_name = m.group(1).strip()
                    num = m.group(2) or "?"
                    surname = full_name.split()[-1] if full_name else "Player"
                    lineup_players.append({
                        "number": num,
                        "name": surname[:14],
                        "position": "MF"
                    })

    # Default 4-2-3-1 tactical formation slot coordinates (viewBox 0 0 600 400)
    # Pitch bounds: x in [25, 575], y in [25, 375]
    slots = [
        {"x": 65,  "y": 200, "role": "GK"},    # 1. GK
        {"x": 170, "y": 75,  "role": "RB"},    # 2. RB
        {"x": 155, "y": 155, "role": "RCB"},   # 3. RCB
        {"x": 155, "y": 245, "role": "LCB"},   # 4. LCB
        {"x": 170, "y": 325, "role": "LB"},    # 5. LB
        {"x": 265, "y": 145, "role": "RDM"},   # 6. RDM
        {"x": 265, "y": 255, "role": "LDM"},   # 7. LDM
        {"x": 385, "y": 75,  "role": "RW"},    # 8. RW
        {"x": 375, "y": 200, "role": "CAM"},   # 9. CAM
        {"x": 385, "y": 325, "role": "LW"},    # 10. LW
        {"x": 490, "y": 200, "role": "CF"},    # 11. CF
    ]

    has_lineup = len(lineup_players) >= 7

    svg_parts = [
        '<svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg" class="tactical-pitch-svg" style="width: 100%; height: auto; max-width: 650px; display: block; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">'
        '<!-- Pitch Turf Background -->',
        '<rect width="600" height="400" fill="#0b1329" rx="12"/>',
        '<!-- Subtle Pitch Mowing Pattern -->',
        '<rect x="25" y="25" width="68" height="350" fill="rgba(255,255,255,0.015)"/>',
        '<rect x="161" y="25" width="68" height="350" fill="rgba(255,255,255,0.015)"/>',
        '<rect x="297" y="25" width="68" height="350" fill="rgba(255,255,255,0.015)"/>',
        '<rect x="433" y="25" width="68" height="350" fill="rgba(255,255,255,0.015)"/>',
        '<!-- Pitch Boundary -->',
        '<rect x="25" y="25" width="550" height="350" rx="4" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<!-- Halfway Line -->',
        '<line x1="300" y1="25" x2="300" y2="375" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<!-- Center Circle & Spot -->',
        '<circle cx="300" cy="200" r="50" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<circle cx="300" cy="200" r="3" fill="rgba(255, 255, 255, 0.6)"/>',
        '<!-- Left Penalty Box (Defending/Home) -->',
        '<rect x="25" y="95" width="90" height="210" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<rect x="25" y="145" width="30" height="110" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<circle cx="85" cy="200" r="2.5" fill="rgba(255, 255, 255, 0.6)"/>',
        '<path d="M 115,165 A 45,45 0 0,1 115,235" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<!-- Right Penalty Box (Attacking/Away) -->',
        '<rect x="485" y="95" width="90" height="210" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<rect x="545" y="145" width="30" height="110" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<circle cx="515" cy="200" r="2.5" fill="rgba(255, 255, 255, 0.6)"/>',
        '<path d="M 485,165 A 45,45 0 0,0 485,235" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="2"/>',
        '<!-- Half-Space Tactical Channels (Flick Blueprint) -->',
        '<line x1="25" y1="115" x2="575" y2="115" stroke="rgba(255, 215, 0, 0.2)" stroke-dasharray="6,6" stroke-width="1.5"/>',
        '<line x1="25" y1="285" x2="575" y2="285" stroke="rgba(255, 215, 0, 0.2)" stroke-dasharray="6,6" stroke-width="1.5"/>',
        '<text x="35" y="42" fill="rgba(255, 215, 0, 0.4)" font-size="9" font-weight="700" font-family="system-ui, sans-serif" letter-spacing="0.05em">TACTICAL HALF-SPACE CHANNELS</text>',
    ]

    if has_lineup:
        svg_parts.append('<!-- Starting XI Player Nodes -->')
        for i, player in enumerate(lineup_players[:11]):
            slot = slots[i]
            x = slot["x"]
            y = slot["y"]
            num = escape(str(player["number"]))
            name = escape(str(player["name"]))

            node_svg = (
                f'<g class="player-node" transform="translate({x},{y})">'
                f'<circle cx="0" cy="0" r="15" fill="#004d98" stroke="#ffb700" stroke-width="2.5"/>'
                f'<text x="0" y="4" fill="#ffffff" font-size="10" font-weight="800" font-family="system-ui, sans-serif" text-anchor="middle">{num}</text>'
                f'<text x="0" y="24" fill="#f8fafc" font-size="10" font-weight="600" font-family="system-ui, sans-serif" text-anchor="middle" filter="drop-shadow(0 1px 2px rgba(0,0,0,0.8))">{name}</text>'
                f'</g>'
            )
            svg_parts.append(node_svg)
    else:
        svg_parts.append(
            '<!-- Lineup Unavailable Overlay -->\n'
            '<g class="lineup-unavailable-overlay">\n'
            '  <rect x="175" y="170" width="250" height="60" rx="12" fill="rgba(15, 23, 42, 0.9)" stroke="rgba(255, 255, 255, 0.2)" stroke-width="1.5"/>\n'
            '  <text x="300" y="205" text-anchor="middle" fill="#94a3b8" font-size="13" font-weight="700" font-family="system-ui, sans-serif" letter-spacing="0.04em">Lineup Formation Unavailable</text>\n'
            '</g>'
        )

    svg_parts.append('</svg>')
    return mark_safe('\n'.join(svg_parts))


@register.simple_tag
def render_stat_comparison_bar(label: str, barca_val: Any, opp_val: Any, unit: str = "") -> str:
    """
    Renders a dual-toned Blau (#004d98) vs Rival (#a50044) proportional horizontal SVG bar
    with exact numeric readouts and responsive SVG layout.
    """
    def _parse_num(val):
        if val is None:
            return 0.0
        val_clean = str(val).replace('%', '').strip()
        try:
            return float(val_clean)
        except (ValueError, TypeError):
            return 0.0

    b_num = _parse_num(barca_val)
    o_num = _parse_num(opp_val)
    total = b_num + o_num

    # Determine proportions
    if total > 0:
        b_pct = (b_num / total) * 100.0
        o_pct = 100.0 - b_pct
        # Clamp visual proportion between 8% and 92% if non-zero
        if b_num > 0 and o_num > 0:
            b_pct = max(8.0, min(92.0, b_pct))
            o_pct = 100.0 - b_pct
    else:
        b_pct = 50.0
        o_pct = 50.0

    # Format readouts
    unit_str = f" {unit}".rstrip() if unit and not unit.startswith('%') else unit
    if isinstance(barca_val, (int, float)) and b_num.is_integer():
        b_display = f"{int(b_num)}{unit_str}"
    else:
        b_display = f"{barca_val}{unit_str}" if barca_val is not None else f"0{unit_str}"

    if isinstance(opp_val, (int, float)) and o_num.is_integer():
        o_display = f"{int(o_num)}{unit_str}"
    else:
        o_display = f"{opp_val}{unit_str}" if opp_val is not None else f"0{unit_str}"

    width_total = 500
    b_w = round((b_pct / 100.0) * width_total, 1)
    o_w = round(width_total - b_w, 1)

    svg = (
        f'<div class="stat-comparison-wrapper" style="width: 100%; max-width: 520px; margin: 0.6rem 0;">'
        f'<svg viewBox="0 0 500 46" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; display: block;">'
        f'  <!-- Metric Labels & Numeric Readouts -->'
        f'  <text x="0" y="16" fill="#38bdf8" font-size="13" font-weight="800" font-family="system-ui, sans-serif">{escape(b_display)}</text>'
        f'  <text x="250" y="16" fill="#94a3b8" font-size="12" font-weight="600" font-family="system-ui, sans-serif" text-anchor="middle">{escape(label)}</text>'
        f'  <text x="500" y="16" fill="#fca5a5" font-size="13" font-weight="800" font-family="system-ui, sans-serif" text-anchor="end">{escape(o_display)}</text>'
        f'  <!-- Proportional Dual-Toned Bar -->'
        f'  <rect x="0" y="24" width="{b_w}" height="12" rx="4" fill="#004d98"/>'
        f'  <rect x="{b_w}" y="24" width="{o_w}" height="12" rx="4" fill="#a50044"/>'
        f'</svg>'
        f'</div>'
    )
    return mark_safe(svg)


@register.simple_tag
def render_player_rating_sparkline(performances) -> str:
    """
    Renders an inline SVG polyline sparkline with color-coded rating dots
    (>=7.5 gold/green, <6.0 burgundy) from a player's last 10 performances.
    """
    ratings: List[float] = []

    if performances is not None:
        try:
            for p in performances:
                if hasattr(p, 'rating') and p.rating is not None:
                    try:
                        ratings.append(float(p.rating))
                    except (ValueError, TypeError):
                        pass
                elif isinstance(p, (int, float, Decimal)):
                    ratings.append(float(p))
        except TypeError:
            pass

    ratings = ratings[:10]

    # Empty State SVG
    if not ratings:
        empty_svg = (
            '<svg viewBox="0 0 240 45" xmlns="http://www.w3.org/2000/svg" class="sparkline-empty" style="width: 100%; max-width: 240px; height: 45px;">'
            '  <rect width="240" height="45" rx="8" fill="rgba(255, 255, 255, 0.02)" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>'
            '  <text x="120" y="27" fill="#64748b" font-size="11" font-weight="600" font-family="system-ui, sans-serif" text-anchor="middle">No recent match ratings</text>'
            '</svg>'
        )
        return mark_safe(empty_svg)

    # Plot sparkline coordinates
    n = len(ratings)
    points: List[str] = []
    coords: List[Dict[str, Any]] = []

    for i, r in enumerate(ratings):
        # Spacing x across [20, 220]
        x = round(20 + (i * (200 / (n - 1))) if n > 1 else 120, 1)
        # Scale rating between 5.0 and 10.0 into y range [36, 12]
        clamped_r = max(5.0, min(10.0, r))
        y = round(38 - ((clamped_r - 5.0) / 5.0) * 26, 1)
        points.append(f"{x},{y}")

        # Color coding
        if r >= 7.5:
            color = "#ffb700"  # Gold
        elif r < 6.0:
            color = "#a50044"  # Burgundy
        else:
            color = "#38bdf8"  # Blaugrana Cyan

        coords.append({"x": x, "y": y, "r": r, "color": color})

    polyline_points = " ".join(points)

    svg_parts = [
        '<svg viewBox="0 0 240 50" xmlns="http://www.w3.org/2000/svg" class="player-rating-sparkline" style="width: 100%; max-width: 240px; height: 50px; overflow: visible;">',
        '  <!-- Background Baseline Guide -->',
        '  <line x1="15" y1="25" x2="225" y2="25" stroke="rgba(255, 255, 255, 0.08)" stroke-dasharray="3,3" stroke-width="1"/>',
        f'  <polyline points="{polyline_points}" fill="none" stroke="#60a5fa" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>',
    ]

    for pt in coords:
        svg_parts.append(
            f'  <circle cx="{pt["x"]}" cy="{pt["y"]}" r="4" fill="{pt["color"]}" stroke="#0b1329" stroke-width="2">'
            f'    <title>Match Rating: {pt["r"]:.1f}</title>'
            f'  </circle>'
        )

    svg_parts.append('</svg>')
    return mark_safe('\n'.join(svg_parts))

