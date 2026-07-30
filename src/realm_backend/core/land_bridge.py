"""Typed ``land.*`` verbs for the sandboxed ``land_registry`` extension.

Land is shared realm data with real invariants — one parcel per H3 cell, no
two parcels on the same coordinates, members may own only residential land,
organizations may own only non-residential land, an NFT is minted once. A
generic ``entity.update`` could express none of those, and would additionally
let the extension reassign ``owner_user`` to hand itself a parcel. Hence typed
verbs with the invariants enforced here.

The writes were already declared ``realm.admin`` in the extension's manifest,
but ``entry_access`` lives in a file the extension itself ships — the same
arrangement that let ``passport_verification`` declare its endpoints public.
Re-checking the operation here puts the decision somewhere the extension
cannot edit.
"""

import json

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 500

WRITE_OPERATION = "realm.admin"
READ_OPERATION = "realm.data_view"

# Fields ``land.update`` may set. ``owner_user`` and ``owner_organization``
# are deliberately absent: ownership moves only through ``land.set_owner``,
# which enforces the residential/organization split.
UPDATABLE = ("land_type", "status", "metadata", "registered_by")


def _metadata(land) -> dict:
    try:
        return json.loads(land.metadata) if land.metadata else {}
    except Exception:
        return {}


def _zones(land) -> list:
    try:
        return list(land.zones) if getattr(land, "zones", None) else []
    except Exception:
        return []


def project(land) -> dict:
    """A land parcel as plain data."""
    zones = [
        {
            "h3_index": z.h3_index,
            "name": z.name,
            "zone_type": getattr(z, "zone_type", None) or "unassigned",
        }
        for z in _zones(land)
    ]
    meta = _metadata(land)

    h3_indexes = [z["h3_index"] for z in zones if z.get("h3_index")]
    if not h3_indexes and meta.get("parent_zone"):
        h3_indexes = [str(meta["parent_zone"])]

    owner_user = getattr(land, "owner_user", None)
    owner_org = getattr(land, "owner_organization", None)

    return {
        "id": land.id,
        "x_coordinate": land.x_coordinate,
        "y_coordinate": land.y_coordinate,
        "land_type": land.land_type,
        "status": land.status,
        "size_width": land.size_width,
        "size_height": land.size_height,
        "metadata": land.metadata,
        "registered_by": land.registered_by,
        "nft_token_id": land.nft_token_id,
        "owner_user_id": owner_user.id if owner_user else None,
        "owner_organization_id": owner_org.id if owner_org else None,
        "owner_user_name": getattr(owner_user, "nickname", None) if owner_user else None,
        "owner_organization_name": getattr(owner_org, "name", None) if owner_org else None,
        "zones": zones,
        "h3_index": h3_indexes[0] if h3_indexes else None,
        "h3_indexes": h3_indexes,
        "price_realm_tokens": meta.get("price_realm_tokens"),
        "for_sale": meta.get("for_sale", False),
    }


def _page(from_id: int, page_size: int):
    """One page of parcels, plus the cursor for the next.

    Pagination stays host-side so a sandboxed extension cannot ask for the
    whole table in one call.
    """
    from ggg import Land

    page_size = max(1, min(int(page_size or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE))
    max_id = Land.max_id()
    batch = Land.load_some(from_id=max(1, int(from_id or 1)), count=page_size)

    next_from_id = (int(batch[-1]._id) + 1) if batch else None
    if next_from_id and next_from_id > max_id:
        next_from_id = None
    return batch, max_id, next_from_id


def _all_lands():
    from ggg import Land

    max_id = Land.max_id()
    from_id = 1
    while from_id <= max_id:
        batch = Land.load_some(from_id=from_id, count=MAX_PAGE_SIZE)
        if not batch:
            return
        for land in batch:
            yield land
        from_id = int(batch[-1]._id) + 1


def _zone_is_taken(h3_index: str) -> bool:
    from ggg import Zone

    try:
        zone = Zone[h3_index]
    except Exception:
        return False
    if not zone:
        return False
    try:
        return zone.land is not None
    except Exception:
        return False


def _synthetic_coords(h3_indexes: list):
    """Stable legacy x/y derived from H3 ids, for NFT token_id arithmetic."""
    primary = h3_indexes[0]
    return (
        int(abs(hash(primary)) % 900000) + 10000,
        int(abs(hash("".join(h3_indexes))) % 900000) + 10000,
    )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def v_list(caller="", from_id=1, page_size=DEFAULT_PAGE_SIZE, all=False,
           **kwargs) -> dict:
    if all:
        rows = [project(land) for land in _all_lands()]
        return {"lands": rows, "count": len(rows), "has_more": False}

    batch, max_id, next_from_id = _page(from_id, page_size)
    return {
        "lands": [project(land) for land in batch],
        "count": len(batch),
        "max_id": max_id,
        "next_from_id": next_from_id,
        "has_more": next_from_id is not None,
    }


def v_get(caller="", land_id="", **kwargs) -> dict:
    from ggg import Land

    if not land_id:
        raise ValueError("land_id is required")
    land = Land[land_id]
    if not land:
        raise ValueError("Land not found")
    return project(land)


def v_map(caller="", min_x=0, max_x=20, min_y=0, max_y=20, from_id=1,
          page_size=DEFAULT_PAGE_SIZE, **kwargs) -> dict:
    """Parcels within a coordinate window, keyed ``"x,y"`` for the map view."""
    batch, max_id, next_from_id = _page(from_id, page_size)

    lands = {}
    for land in batch:
        if not (min_x <= land.x_coordinate <= max_x
                and min_y <= land.y_coordinate <= max_y):
            continue
        owner_user = getattr(land, "owner_user", None)
        owner_org = getattr(land, "owner_organization", None)
        lands[f"{land.x_coordinate},{land.y_coordinate}"] = {
            "id": land.id,
            "x": land.x_coordinate,
            "y": land.y_coordinate,
            "type": land.land_type,
            "owner_type": (
                "user" if owner_user else "organization" if owner_org else "none"
            ),
            "owner_name": (
                owner_user.id if owner_user
                else getattr(owner_org, "name", None) if owner_org else None
            ),
        }

    return {
        "bounds": {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y},
        "lands": lands,
        "max_id": max_id,
        "next_from_id": next_from_id,
        "has_more": next_from_id is not None,
    }


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def _require_admin(caller: str, verb: str) -> None:
    from core.extension_bridge import caller_has_operation

    if not caller_has_operation(caller, WRITE_OPERATION):
        raise PermissionError(f"{verb} requires the '{WRITE_OPERATION}' operation")


def v_create(caller="", land_type=None, name="", id="", h3_index=None,
             h3_indexes=None, metadata=None, x_coordinate=None,
             y_coordinate=None, size_width=1, size_height=1, **kwargs) -> dict:
    """Register a parcel, either over H3 cells or at bare x/y coordinates.

    ``registered_by`` is set to the authenticated caller rather than taken as
    an argument, so the provenance of a parcel cannot be forged.
    """
    _require_admin(caller, "land.create")
    from ggg import Land, LandType, Zone

    land_type = land_type or LandType.UNASSIGNED

    cells = [str(c) for c in (h3_indexes or []) if c and "manual" not in str(c)]
    if h3_index and str(h3_index) not in cells and "manual" not in str(h3_index):
        cells.insert(0, str(h3_index))

    if cells:
        for cell in cells:
            if _zone_is_taken(cell):
                raise ValueError(f"Land parcel already exists at H3 cell {cell}")

        meta = metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta) if meta else {}
            except Exception:
                meta = {}
        meta.setdefault("parent_zone", cells[0])
        meta["h3_indexes"] = cells

        x_coord, y_coord = _synthetic_coords(cells)
        land = Land(
            x_coordinate=x_coord,
            y_coordinate=y_coord,
            land_type=land_type,
            size_width=max(1, len(cells)),
            size_height=1,
            metadata=json.dumps(meta),
            registered_by=caller,
        )
        land.id = str(id).strip() or f"land_{land._id}"

        for index, cell in enumerate(cells):
            label = (name or "").strip() or f"{land.id} parcel"
            if len(cells) > 1:
                label = f"{label} ({index + 1}/{len(cells)})"
            Zone(
                h3_index=cell,
                name=label,
                description=f"Land parcel {land.id}",
                zone_type=land_type,
                land=land,
            )

        return dict(project(land), created=True)

    if x_coordinate is None or y_coordinate is None:
        raise ValueError("x_coordinate and y_coordinate are required")

    for existing in _all_lands():
        if (existing.x_coordinate == x_coordinate
                and existing.y_coordinate == y_coordinate):
            raise ValueError("Land already exists at these coordinates")

    land = Land(
        x_coordinate=x_coordinate,
        y_coordinate=y_coordinate,
        land_type=land_type,
        size_width=size_width,
        size_height=size_height,
        metadata=metadata if isinstance(metadata, str) else json.dumps(
            metadata or {}
        ),
        registered_by=caller,
    )
    land.id = str(id).strip() or str(land._id)
    return dict(project(land), created=True)


def v_update(caller="", land_id="", **fields) -> dict:
    """Update a parcel's own attributes. Ownership is not among them."""
    _require_admin(caller, "land.update")
    from ggg import Land

    if not land_id:
        raise ValueError("land_id is required")
    land = Land[land_id]
    if not land:
        raise ValueError("Land not found")

    updated = []
    for field in UPDATABLE:
        if field in fields:
            setattr(land, field, fields[field])
            updated.append(field)

    rejected = sorted(
        set(fields) - set(UPDATABLE) - {"caller", "capabilities", "ext_id"}
    )
    if rejected:
        raise ValueError(
            f"land.update cannot set {', '.join(rejected)}; "
            f"ownership changes go through land.set_owner"
        )

    return dict(project(land), updated_fields=updated)


def v_set_owner(caller="", land_id="", owner_user_id=None,
                owner_organization_id=None, **kwargs) -> dict:
    """Transfer, or clear, ownership of a parcel.

    Enforces the two rules the realm cares about: a parcel has at most one
    owner, and residential land belongs to members while everything else
    belongs to organizations.
    """
    _require_admin(caller, "land.set_owner")
    from ggg import Land, LandType, Organization, User

    if not land_id:
        raise ValueError("land_id is required")
    land = Land.load(land_id)
    if not land:
        raise ValueError("Land not found")

    if owner_user_id and owner_organization_id:
        raise ValueError("Land cannot be owned by both user and organization")

    if owner_user_id:
        if land.land_type != LandType.RESIDENTIAL:
            raise ValueError("Members can only own residential land")
        user = User.load(owner_user_id)
        if not user:
            raise ValueError("User not found")
        land.owner_user = user
        land.owner_organization = None
    elif owner_organization_id:
        if land.land_type == LandType.RESIDENTIAL:
            raise ValueError("Organizations cannot own residential land")
        org = Organization.load(owner_organization_id)
        if not org:
            raise ValueError("Organization not found")
        land.owner_organization = org
        land.owner_user = None
    else:
        land.owner_user = None
        land.owner_organization = None

    return project(land)


def v_prepare_nft(caller="", land_id="", owner_principal="", **kwargs) -> dict:
    """Mark a parcel active and ready to mint, refusing a second mint."""
    _require_admin(caller, "land.prepare_nft")
    from ggg import Land, LandStatus

    if not land_id:
        raise ValueError("land_id is required")
    if not owner_principal:
        raise ValueError("owner_principal is required")

    land = Land[land_id]
    if not land:
        raise ValueError("Land not found")
    if land.nft_token_id:
        raise ValueError(
            f"Land already has NFT minted (token_id: {land.nft_token_id})"
        )

    land.registered_by = caller
    land.status = LandStatus.ACTIVE
    return {
        "land_id": land_id,
        "owner_principal": owner_principal,
        "x_coordinate": land.x_coordinate,
        "y_coordinate": land.y_coordinate,
        "requires_mint": True,
    }


def v_set_nft_token(caller="", land_id="", nft_token_id="", **kwargs) -> dict:
    """Record the token id after a successful mint. Write-once."""
    _require_admin(caller, "land.set_nft_token")
    from ggg import Land

    if not land_id:
        raise ValueError("land_id is required")
    if not nft_token_id:
        raise ValueError("nft_token_id is required")

    land = Land[land_id]
    if not land:
        raise ValueError("Land not found")
    if land.nft_token_id and str(land.nft_token_id) != str(nft_token_id):
        raise ValueError(
            f"Land already has NFT token {land.nft_token_id}; "
            f"refusing to overwrite with {nft_token_id}"
        )

    land.nft_token_id = str(nft_token_id)
    return {"land_id": land_id, "nft_token_id": land.nft_token_id}


READS = {
    "land.list": v_list,
    "land.get": v_get,
    "land.map": v_map,
}

WRITES = {
    "land.create": v_create,
    "land.update": v_update,
    "land.set_owner": v_set_owner,
    "land.prepare_nft": v_prepare_nft,
    "land.set_nft_token": v_set_nft_token,
}

VERBS = dict(READS, **WRITES)
