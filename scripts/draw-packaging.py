#!/usr/bin/env python3
"""Рисунки тары для карточек без фото (public/images/products/pack-*.svg).

Каждый вид тары — два слоя, как у исходной банки (vial-base.svg / vial-top.svg): base — всё, что под текстом
этикетки (свечение, тень, стекло или пластик, бумага этикетки с тёмной шапкой), top — всё, что поверх текста
(светотень этикетки, блики, крышка). Текст этикетки рисует src/components/product/VialPlaceholder.tsx в рамке
этикетки — её координаты здесь и в PACKS компонента должны совпадать (пропорция 110 × 84, как у эталона).

Стиль — по эталону заказчика для банки: тёмно-зелёная матовая ребристая крышка, янтарное стекло, тёплая бумага
этикетки, свет слева сверху, зелёное свечение фона окна. Без чужих логотипов: это наша иллюстрация упаковки.

    python3 scripts/draw-packaging.py      перерисовать файлы
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'public' / 'images' / 'products'
RATIO = 84 / 110


def label(x: float, y: float, w: float) -> dict[str, float]:
    return {'x': x, 'y': y, 'w': w, 'h': round(w * RATIO, 2)}


# Рамки этикеток: их же читает компонент (PACKS в VialPlaceholder.tsx)
LABELS = {
    'bottle': label(70, 136, 100),
    'jar': label(65, 132, 110),
    'solvent': label(78, 140, 84),
    'tube': label(85, 98, 70),
    'box': label(62, 132, 110),
}

AMBER = ('<linearGradient id="glass" x1="{x0}" y1="0" x2="{x1}" y2="0" gradientUnits="userSpaceOnUse">'
         '<stop offset="0%" stop-color="#1E0901"/><stop offset="18%" stop-color="#5A2006"/>'
         '<stop offset="38%" stop-color="#8C380F"/><stop offset="65%" stop-color="#4A1804"/>'
         '<stop offset="88%" stop-color="#2B0D02"/><stop offset="100%" stop-color="#160600"/></linearGradient>')
CAP = ('<linearGradient id="cap" x1="{x0}" y1="0" x2="{x1}" y2="0" gradientUnits="userSpaceOnUse">'
       '<stop offset="0%" stop-color="#122416"/><stop offset="22%" stop-color="#294A30"/>'
       '<stop offset="45%" stop-color="#355B3D"/><stop offset="75%" stop-color="#1A3220"/>'
       '<stop offset="100%" stop-color="#0E1C11"/></linearGradient>')
RIBS = ('<pattern id="ribs" width="{step}" height="80" patternUnits="userSpaceOnUse">'
        '<rect width="{dark}" height="80" fill="#000" fill-opacity="0.22"/>'
        '<rect x="{dark}" width="1.4" height="80" fill="#FFF" fill-opacity="0.06"/></pattern>')
GLOW = ('<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#2E5C3A" stop-opacity="0.45"/>'
        '<stop offset="100%" stop-color="#141714" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="floor" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#000" stop-opacity="0.85"/>'
        '<stop offset="60%" stop-color="#000" stop-opacity="0.4"/><stop offset="100%" stop-color="#000" stop-opacity="0"/>'
        '</radialGradient>')
SHEEN = ('<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#FFF" stop-opacity="0.24"/>'
         '<stop offset="100%" stop-color="#FFF" stop-opacity="0"/></linearGradient>')


def cylinder_shade(lab: dict[str, float], strength: float = 1.0) -> str:
    """Светотень этикетки на круглой таре: темнее к краям, светлая полоса левее центра."""
    x0, x1 = lab['x'], lab['x'] + lab['w']
    s = strength
    return (f'<linearGradient id="shade" x1="{x0}" y1="0" x2="{x1}" y2="0" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0%" stop-color="#000" stop-opacity="{0.30 * s:.2f}"/>'
            f'<stop offset="14%" stop-color="#000" stop-opacity="{0.05 * s:.2f}"/>'
            f'<stop offset="35%" stop-color="#FFF" stop-opacity="{0.09 * s:.2f}"/>'
            f'<stop offset="72%" stop-color="#000" stop-opacity="{0.08 * s:.2f}"/>'
            f'<stop offset="90%" stop-color="#000" stop-opacity="{0.25 * s:.2f}"/>'
            f'<stop offset="100%" stop-color="#000" stop-opacity="{0.45 * s:.2f}"/></linearGradient>')


def paper(lab: dict[str, float], shadow: float = 0.45) -> str:
    """Бумага этикетки с тёмной шапкой под бейдж бренда — пропорции эталона (шапка 18 из 84)."""
    x, y, w, h = lab['x'], lab['y'], lab['w'], lab['h']
    k = w / 110
    r, band = 5 * k, 18 * k
    return (f'<rect x="{x - k:.2f}" y="{y + k:.2f}" width="{w + 2 * k:.2f}" height="{h + 2 * k:.2f}" rx="{r:.2f}" '
            f'fill="#000" fill-opacity="{shadow}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r:.2f}" fill="#EAE7DF"/>'
            f'<path d="M{x} {y + r:.2f} C{x} {y + r * 0.44:.2f}, {x + r * 0.44:.2f} {y}, {x + r:.2f} {y} '
            f'H{x + w - r:.2f} C{x + w - r * 0.44:.2f} {y}, {x + w} {y + r * 0.44:.2f}, {x + w} {y + r:.2f} '
            f'V{y + band:.2f} H{x} Z" fill="#1A1A1A"/>')


def svg(defs: str, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 260" fill="none">\n<defs>\n{defs}\n</defs>\n'
            f'{body}\n</svg>\n')


def screw_cap(x: float, y: float, w: float, h: float, collar: float = 7) -> str:
    """Ребристая крышка с нижним кольцом: прямоугольник с рёбрами, кольцо чуть шире, блик по верхней кромке."""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="url(#cap)"/>'
            f'<rect x="{x + 2}" y="{y + 2}" width="{w - 4}" height="{h - collar - 6}" rx="3" fill="url(#ribs)"/>'
            f'<rect x="{x - 1}" y="{y + h - collar}" width="{w + 2}" height="{collar}" rx="2.5" fill="url(#cap)"/>'
            f'<path d="M{x} {y + h - collar} H{x + w}" stroke="#0B160D" stroke-width="1"/>'
            f'<path d="M{x + 6} {y + 1.5} H{x + w - 6}" stroke="#FFF" stroke-opacity="0.18" stroke-width="1.2" '
            f'stroke-linecap="round"/>')


# ── банка тёмного стекла с узким горлом, 25–250 г или мл ──
def bottle() -> tuple[str, str]:
    lab = LABELS['bottle']
    x0, x1 = 64, 176
    body = (f'M{x0} 128 C{x0} 112, 74 104, 92 98 C98 96, 100 94, 100 90 V80 H140 V90 C140 94, 142 96, 148 98 '
            f'C166 104, {x1} 112, {x1} 128 V222 C{x1} 231, 169 236, 158 236 H82 C71 236, {x0} 231, {x0} 222 Z')
    base = svg(GLOW + '\n' + AMBER.format(x0=x0, x1=x1) + '\n' + '<linearGradient id="neck" x1="98" y1="0" x2="142" '
               'y2="0" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#1E0901"/>'
               '<stop offset="40%" stop-color="#7A300C"/><stop offset="100%" stop-color="#1A0701"/></linearGradient>',
               '<circle cx="120" cy="138" r="96" fill="url(#glow)"/>\n'
               '<ellipse cx="120" cy="238" rx="66" ry="9" fill="url(#floor)"/>\n'
               f'<path d="{body}" fill="url(#glass)"/>\n'
               '<rect x="98" y="72" width="44" height="12" rx="2" fill="url(#neck)"/>\n'
               '<path d="M98 76 H142" stroke="#A84B18" stroke-opacity="0.45"/>\n'
               '<ellipse cx="120" cy="104" rx="34" ry="5" fill="#B84B14" fill-opacity="0.22"/>\n'
               '<ellipse cx="120" cy="229" rx="46" ry="4.5" fill="#B84B14" fill-opacity="0.3"/>\n'
               f'<path d="M{x0 + 4} 224 C88 230, 152 230, {x1 - 4} 224" stroke="#FF8A47" stroke-opacity="0.2" '
               'stroke-width="1.5"/>\n' + paper(lab))
    top = svg(cylinder_shade(lab) + '\n' + SHEEN + '\n' + CAP.format(x0=94, x1=146) + '\n' + RIBS.format(step=5, dark=1.8),
              f'<rect x="{lab["x"]}" y="{lab["y"]}" width="{lab["w"]}" height="{lab["h"]}" rx="5" fill="url(#shade)"/>\n'
              '<path d="M70 124 C70 112, 80 106, 92 101 L95 106 C84 110, 78 116, 78 126 V222 C78 226, 74 227, 72 224 Z" '
              'fill="url(#sheen)"/>\n'
              '<rect x="160" y="118" width="4" height="102" rx="2" fill="#FFF" fill-opacity="0.07"/>\n'
              + screw_cap(94, 36, 52, 40))
    return base, top


# ── широкая белая пластиковая банка, от 250 г и килограммы ──
def jar() -> tuple[str, str]:
    lab = LABELS['jar']
    x0, x1 = 56, 184
    plastic = ('<linearGradient id="hdpe" x1="56" y1="0" x2="184" y2="0" gradientUnits="userSpaceOnUse">'
               '<stop offset="0%" stop-color="#9AA19A"/><stop offset="12%" stop-color="#D9DDD8"/>'
               '<stop offset="34%" stop-color="#F4F5F2"/><stop offset="62%" stop-color="#DADDD8"/>'
               '<stop offset="88%" stop-color="#AEB4AD"/><stop offset="100%" stop-color="#858C85"/></linearGradient>')
    body = (f'M{x0} 112 C{x0} 102, 62 98, 70 96 H170 C178 98, {x1} 102, {x1} 112 V220 C{x1} 230, 176 236, 164 236 '
            f'H76 C64 236, {x0} 230, {x0} 220 Z')
    base = svg(GLOW + '\n' + plastic,
               '<circle cx="120" cy="140" r="98" fill="url(#glow)"/>\n'
               '<ellipse cx="120" cy="238" rx="74" ry="9" fill="url(#floor)"/>\n'
               f'<path d="{body}" fill="url(#hdpe)"/>\n'
               '<rect x="68" y="88" width="104" height="12" rx="3" fill="url(#hdpe)"/>\n'
               '<path d="M68 99 H172" stroke="#7E857E" stroke-opacity="0.6"/>\n'
               f'<path d="M{x0 + 2} 120 H{x1 - 2}" stroke="#8A918A" stroke-opacity="0.35"/>\n'
               f'<path d="M{x0 + 2} 222 H{x1 - 2}" stroke="#8A918A" stroke-opacity="0.3"/>\n' + paper(lab, 0.22))
    top = svg(cylinder_shade(lab, 0.7) + '\n' + SHEEN + '\n' + CAP.format(x0=58, x1=182) + '\n' + RIBS.format(step=6, dark=2),
              f'<rect x="{lab["x"]}" y="{lab["y"]}" width="{lab["w"]}" height="{lab["h"]}" rx="5" fill="url(#shade)"/>\n'
              '<rect x="62" y="108" width="10" height="112" rx="5" fill="#FFF" fill-opacity="0.35"/>\n'
              + screw_cap(58, 34, 124, 58, collar=9))
    return base, top


# ── бутыль для растворителей, от 250 мл и литры ──
def solvent() -> tuple[str, str]:
    lab = LABELS['solvent']
    x0, x1 = 72, 168
    body = (f'M{x0} 118 C{x0} 96, 92 86, 104 80 C108 78, 109 76, 109 72 V62 H131 V72 C131 76, 132 78, 136 80 '
            f'C148 86, {x1} 96, {x1} 118 V224 C{x1} 232, 162 237, 152 237 H88 C78 237, {x0} 232, {x0} 224 Z')
    base = svg(GLOW + '\n' + AMBER.format(x0=x0, x1=x1) + '\n' + '<linearGradient id="neck" x1="106" y1="0" x2="134" '
               'y2="0" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#1E0901"/>'
               '<stop offset="40%" stop-color="#7A300C"/><stop offset="100%" stop-color="#1A0701"/></linearGradient>',
               '<circle cx="120" cy="140" r="96" fill="url(#glow)"/>\n'
               '<ellipse cx="120" cy="239" rx="60" ry="8" fill="url(#floor)"/>\n'
               f'<path d="{body}" fill="url(#glass)"/>\n'
               '<rect x="107" y="54" width="26" height="12" rx="2" fill="url(#neck)"/>\n'
               '<ellipse cx="120" cy="88" rx="20" ry="3.5" fill="#B84B14" fill-opacity="0.22"/>\n'
               '<ellipse cx="120" cy="231" rx="40" ry="4" fill="#B84B14" fill-opacity="0.3"/>\n'
               f'<path d="M{x0 + 4} 226 C92 231, 148 231, {x1 - 4} 226" stroke="#FF8A47" stroke-opacity="0.2" '
               'stroke-width="1.5"/>\n' + paper(lab))
    top = svg(cylinder_shade(lab) + '\n' + SHEEN + '\n' + CAP.format(x0=104, x1=136) + '\n' + RIBS.format(step=4, dark=1.5),
              f'<rect x="{lab["x"]}" y="{lab["y"]}" width="{lab["w"]}" height="{lab["h"]}" rx="5" fill="url(#shade)"/>\n'
              '<path d="M78 112 C78 100, 88 92, 100 86 L102 90 C92 96, 86 104, 86 114 V224 C86 228, 81 229, 79 226 Z" '
              'fill="url(#sheen)"/>\n'
              '<rect x="156" y="112" width="3.5" height="108" rx="1.75" fill="#FFF" fill-opacity="0.07"/>\n'
              + screw_cap(104, 22, 32, 36, collar=6))
    return base, top


# ── пробирка 1,5 мл с защёлкивающейся крышкой: антитела, белки, плазмиды ──
def tube() -> tuple[str, str]:
    lab = LABELS['tube']
    poly = ('<linearGradient id="pp" x1="82" y1="0" x2="158" y2="0" gradientUnits="userSpaceOnUse">'
            '<stop offset="0%" stop-color="#C9CFC9" stop-opacity="0.55"/><stop offset="18%" stop-color="#EEF1EE" '
            'stop-opacity="0.75"/><stop offset="40%" stop-color="#FFFFFF" stop-opacity="0.82"/>'
            '<stop offset="70%" stop-color="#DCE1DC" stop-opacity="0.7"/><stop offset="100%" stop-color="#9FA69F" '
            'stop-opacity="0.6"/></linearGradient>'
            '<linearGradient id="liquid" x1="0" y1="200" x2="0" y2="236" gradientUnits="userSpaceOnUse">'
            '<stop offset="0%" stop-color="#E9D9A6" stop-opacity="0.85"/><stop offset="100%" stop-color="#C9B072" '
            'stop-opacity="0.95"/></linearGradient>')
    body = 'M84 84 H156 V176 C156 192, 132 226, 126 234 C123 238, 117 238, 114 234 C108 226, 84 192, 84 176 Z'
    base = svg(GLOW + '\n' + poly,
               '<circle cx="120" cy="140" r="92" fill="url(#glow)"/>\n'
               '<ellipse cx="120" cy="240" rx="34" ry="6" fill="url(#floor)"/>\n'
               f'<path d="{body}" fill="url(#pp)"/>\n'
               '<path d="M98 208 C106 222, 112 230, 114 233 C117 237, 123 237, 126 233 C128 230, 134 222, 142 208 Z" '
               'fill="url(#liquid)"/>\n'
               '<path d="M98 208 H142" stroke="#FFF" stroke-opacity="0.5"/>\n'
               '<rect x="80" y="76" width="80" height="10" rx="2" fill="#E7EBE7" fill-opacity="0.85"/>\n'
               + paper(lab, 0.18))
    top = svg(cylinder_shade(lab, 0.6) + '\n' + CAP.format(x0=76, x1=164),
              f'<rect x="{lab["x"]}" y="{lab["y"]}" width="{lab["w"]}" height="{lab["h"]}" rx="3.2" fill="url(#shade)"/>\n'
              '<rect x="89" y="90" width="6" height="96" rx="3" fill="#FFF" fill-opacity="0.45"/>\n'
              '<path d="M89 190 C94 204, 102 216, 110 226" stroke="#FFF" stroke-opacity="0.35" stroke-width="3" '
              'stroke-linecap="round"/>\n'
              # крышка-защёлка: колпачок с ободком, справа плоская перемычка-петля к пробирке, слева язычок
              '<path d="M160 58 H170 C173 58, 174 60, 174 63 V84 C174 87, 172 88, 169 88 H158 V80 H166 V66 H160 Z" '
              'fill="#1C3523"/>\n'
              '<path d="M166 66 V80" stroke="#000" stroke-opacity="0.35"/>\n'
              '<path d="M80 60 H72 C70 60, 69 61, 69 63 V67 C69 69, 70 70, 72 70 H80 Z" fill="#1C3523"/>\n'
              '<rect x="78" y="52" width="84" height="26" rx="7" fill="url(#cap)"/>\n'
              '<rect x="82" y="44" width="76" height="12" rx="5" fill="url(#cap)"/>\n'
              '<path d="M86 45.5 H154" stroke="#FFF" stroke-opacity="0.2" stroke-width="1.2" stroke-linecap="round"/>\n'
              '<path d="M78 70 H162" stroke="#0B160D"/>\n'
              '<path d="M84 55 H156" stroke="#000" stroke-opacity="0.25"/>')
    return base, top


# ── коробка: наборы, мультиупаковки, хроматография, оборудование ──
def box() -> tuple[str, str]:
    lab = LABELS['box']
    carton = ('<linearGradient id="front" x1="54" y1="0" x2="178" y2="0" gradientUnits="userSpaceOnUse">'
              '<stop offset="0%" stop-color="#D7DAD4"/><stop offset="45%" stop-color="#F1F2EE"/>'
              '<stop offset="100%" stop-color="#D0D4CD"/></linearGradient>'
              '<linearGradient id="side" x1="178" y1="0" x2="200" y2="0" gradientUnits="userSpaceOnUse">'
              '<stop offset="0%" stop-color="#9DA49C"/><stop offset="100%" stop-color="#7C847C"/></linearGradient>'
              '<linearGradient id="lid" x1="0" y1="66" x2="0" y2="84" gradientUnits="userSpaceOnUse">'
              '<stop offset="0%" stop-color="#FAFBF8"/><stop offset="100%" stop-color="#E2E5DF"/></linearGradient>'
              + CAP.format(x0=54, x1=178))
    base = svg(GLOW + '\n' + carton,
               '<circle cx="120" cy="142" r="98" fill="url(#glow)"/>\n'
               '<ellipse cx="126" cy="238" rx="82" ry="9" fill="url(#floor)"/>\n'
               # боковая грань и крышка в лёгкой перспективе
               '<path d="M178 84 L200 70 V220 L178 234 Z" fill="url(#side)"/>\n'
               '<path d="M54 84 L76 70 H200 L178 84 Z" fill="url(#lid)"/>\n'
               '<rect x="54" y="84" width="124" height="150" fill="url(#front)"/>\n'
               # зелёная полоса упаковки сверху и снизу
               '<rect x="54" y="84" width="124" height="30" fill="url(#cap)"/>\n'
               '<path d="M178 84 L200 70 V100 L178 114 Z" fill="#132418"/>\n'
               '<rect x="54" y="224" width="124" height="10" fill="url(#cap)"/>\n'
               '<path d="M178 224 L200 210 V220 L178 234 Z" fill="#132418"/>\n'
               '<path d="M64 99 H118" stroke="#FFF" stroke-opacity="0.35" stroke-width="2" stroke-linecap="round"/>\n'
               '<path d="M64 106 H96" stroke="#FFF" stroke-opacity="0.2" stroke-width="2" stroke-linecap="round"/>\n'
               + paper(lab, 0.15))
    top = svg('<linearGradient id="shade" x1="62" y1="0" x2="172" y2="0" gradientUnits="userSpaceOnUse">'
              '<stop offset="0%" stop-color="#000" stop-opacity="0.06"/><stop offset="45%" stop-color="#FFF" '
              'stop-opacity="0.06"/><stop offset="100%" stop-color="#000" stop-opacity="0.1"/></linearGradient>',
              f'<rect x="{lab["x"]}" y="{lab["y"]}" width="{lab["w"]}" height="{lab["h"]}" rx="5" fill="url(#shade)"/>\n'
              '<path d="M54 84 H178" stroke="#FFF" stroke-opacity="0.5"/>\n'
              '<path d="M178 84 V234" stroke="#000" stroke-opacity="0.18"/>\n'
              '<path d="M54 84 L76 70 H200" stroke="#FFF" stroke-opacity="0.6"/>')
    return base, top


def main() -> None:
    for kind, draw in {'bottle': bottle, 'jar': jar, 'solvent': solvent, 'tube': tube, 'box': box}.items():
        base, top = draw()
        (OUT / f'pack-{kind}-base.svg').write_text(base)
        (OUT / f'pack-{kind}-top.svg').write_text(top)
        print(kind, LABELS[kind])


if __name__ == '__main__':
    main()
