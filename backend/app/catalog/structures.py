"""2D structures from SMILES (TZ 5.1, 12.1): a card without the manufacturer's photo shows the structural formula
drawn by RDKit in the storefront's colours instead of the vial placeholder.

The worker draws them in batches. A card is looked at again when its SMILES changes (the partial index
``ix_products_structure_pending`` keeps that queue cheap); a SMILES RDKit cannot read is remembered and not retried
until it changes. Photos and pictures set by hand are never replaced. The SVGs are content-addressed
(media/structures/<sha256>.svg): one molecule — one file, served at /api/v1/media/… (app.content.media).
"""

import hashlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import Product
from app.catalog.service import refresh_card
from app.core import files

logger = logging.getLogger('site.structures')
# #E7E7E7 on the dark preview window, as the brand's own structure drawings.
LINE = (0.906, 0.906, 0.906)
SIZE = 400
MAX_HEAVY_ATOMS = 200
PREFIX = '/api/v1/media/structures/'


def render(smiles: str | None) -> str | None:
    """The SVG of the molecule, or None for an empty, unreadable or too large one."""
    from rdkit import Chem, rdBase
    from rdkit.Chem import rdDepictor
    from rdkit.Chem.Draw import rdMolDraw2D

    rdBase.DisableLog('rdApp.*')
    if not smiles or len(smiles) > 2000:
        return None
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None or not 0 < mol.GetNumHeavyAtoms() <= MAX_HEAVY_ATOMS:
        return None
    rdDepictor.SetPreferCoordGen(True)
    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(SIZE, SIZE)
    # RDKit's bundled type stubs describe these properties wrongly.
    options: Any = drawer.drawOptions()
    options.clearBackground = False
    options.setAtomPalette({-1: LINE})
    options.bondLineWidth = 2
    options.padding = 0.08
    options.minFontSize = 14
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    svg: str = drawer.GetDrawingText()
    # Without the XML prolog the file is valid inline and in <img>; RDKit writes ISO-8859-1 there.
    return svg.split('?>', 1)[1].lstrip() if svg.startswith('<?xml') else svg


def is_drawn(image: Any) -> bool:
    return isinstance(image, dict) and image.get('kind') == 'structure' and str(image.get('src', '')).startswith(PREFIX)


def picture(product: Product) -> dict[str, str] | None:
    svg = render(product.smiles)
    if svg is None:
        return None
    data = svg.encode()
    digest = hashlib.sha256(data).hexdigest()
    key = f'media/structures/{digest[:2]}/{digest}.svg'
    store = files.storage()
    if not store.exists(key):
        store.put(key, data, 'image/svg+xml')
    name = product.name_ru or product.name_en
    return {'src': files.media_url(key), 'alt': f'Структурная формула: {name}'[:250], 'kind': 'structure'}


def draw_pending(db: Session, limit: int = 200) -> int:
    """Up to ``limit`` cards of the queue; returns how many pictures changed. Storage failures leave them queued."""
    rows = list(db.scalars(select(Product).where(Product.structure_smiles.is_distinct_from(Product.smiles))
                           .order_by(Product.id).limit(limit)))
    changed = 0
    for product in rows:
        images = list(product.images or [])
        mine = bool(images) and is_drawn(images[0])
        if 'images' in (product.manual_fields or []) or (images and not mine):
            product.structure_smiles = product.smiles
            continue
        try:
            drawn = picture(product)
        except files.StorageUnavailable as exc:
            logger.warning('{"event": "structure_storage_unavailable", "error": "%s"}', str(exc)[:200])
            break
        updated = ([drawn] if drawn else []) + (images[1:] if mine else images)
        product.structure_smiles = product.smiles
        if updated != images:
            product.images = updated
            refresh_card(db, product)
            changed += 1
    db.flush()
    return changed
