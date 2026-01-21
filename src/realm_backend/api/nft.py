"""NFT API for minting and managing LAND NFTs."""

import json
from typing import Optional

from kybra import (
    Async,
    CallResult,
    Opt,
    Principal,
    Record,
    Service,
    Variant,
    Vec,
    blob,
    ic,
    nat,
    null,
    service_update,
    text,
)
from kybra_simple_logging import get_logger

logger = get_logger("api.nft")


# Candid types for NFT canister interface
class Account(Record):
    owner: Principal
    subaccount: Opt[blob]


class MetadataValue(Variant, total=False):
    Int: int
    Nat: nat
    Blob: blob
    Text: text


class MintArg(Record):
    token_id: nat
    owner: Account
    metadata: Opt[Vec[tuple[text, MetadataValue]]]


class GenericError(Record):
    message: text
    error_code: nat


class MintError(Variant, total=False):
    GenericError: GenericError
    SupplyCapReached: null
    Unauthorized: null
    TokenIdAlreadyExists: null


class MintResult(Variant, total=False):
    Ok: nat
    Err: MintError


# NFT canister service interface
class NFTService(Service):
    @service_update
    def mint(self, arg: MintArg) -> MintResult:
        ...


def mint_land_nft(
    nft_canister_id: str,
    token_id: int,
    owner_principal: str,
    land_id: str,
    x_coordinate: int,
    y_coordinate: int,
    land_type: str = "",
):
    """
    Mint a LAND NFT for a registered land parcel.

    Makes an inter-canister call to the realm's NFT canister to mint
    an NFT representing ownership of a land parcel.

    Args:
        nft_canister_id: Canister ID of the realm's NFT backend
        token_id: Unique token ID for the NFT
        owner_principal: Principal ID of the land owner
        land_id: ID of the land parcel in the realm
        x_coordinate: X coordinate of the land
        y_coordinate: Y coordinate of the land
        land_type: Type of land (residential, agricultural, etc.)

    Returns:
        Dictionary with success status and token_id or error
    """
    logger.info(
        f"Minting LAND NFT: token_id={token_id}, owner={owner_principal}, "
        f"land_id={land_id}, coords=({x_coordinate},{y_coordinate})"
    )

    try:
        # Build metadata for the NFT
        metadata_list = [
            ("land_id", {"Text": land_id}),
            ("x_coordinate", {"Nat": x_coordinate}),
            ("y_coordinate", {"Nat": y_coordinate}),
            ("realm_canister", {"Text": str(ic.id())}),
        ]
        if land_type:
            metadata_list.append(("land_type", {"Text": land_type}))

        # Create the mint argument
        owner_account = {
            "owner": Principal.from_str(owner_principal),
            "subaccount": None,
        }

        mint_arg = {
            "token_id": token_id,
            "owner": owner_account,
            "metadata": metadata_list,
        }

        logger.info(f"Calling NFT canister {nft_canister_id} with mint arg")

        # Make inter-canister call to NFT canister
        nft_service = NFTService(Principal.from_str(nft_canister_id))
        result: CallResult[MintResult] = yield nft_service.mint(mint_arg)

        logger.info(f"NFT mint result: {result}")

        # Parse the CallResult
        if hasattr(result, "Ok"):
            inner_result = result.Ok
            if hasattr(inner_result, "Ok"):
                minted_token_id = inner_result.Ok
                logger.info(f"Successfully minted LAND NFT with token_id={minted_token_id}")
                return {
                    "success": True,
                    "token_id": str(minted_token_id),
                    "nft_canister_id": nft_canister_id,
                    "land_id": land_id,
                }
            elif hasattr(inner_result, "Err"):
                error = inner_result.Err
                error_msg = str(error)
                if hasattr(error, "GenericError"):
                    error_msg = error.GenericError.message
                elif hasattr(error, "SupplyCapReached"):
                    error_msg = "NFT supply cap reached"
                elif hasattr(error, "Unauthorized"):
                    error_msg = "Unauthorized to mint NFT"
                elif hasattr(error, "TokenIdAlreadyExists"):
                    error_msg = f"Token ID {token_id} already exists"
                logger.error(f"NFT mint error: {error_msg}")
                return {"success": False, "error": error_msg}
            else:
                logger.error(f"Unexpected inner result: {inner_result}")
                return {"success": False, "error": f"Unexpected result: {inner_result}"}
        elif hasattr(result, "Err"):
            error = result.Err
            logger.error(f"Inter-canister call failed: {error}")
            return {"success": False, "error": f"Call failed: {error}"}
        else:
            logger.error(f"Unexpected response: {result}")
            return {"success": False, "error": f"Unexpected response: {result}"}

    except Exception as e:
        logger.error(f"Error minting LAND NFT: {str(e)}")
        return {"success": False, "error": f"Failed to mint: {str(e)}"}


def get_nft_canister_id() -> Optional[str]:
    """
    Get the NFT canister ID for this realm from config.

    Returns:
        NFT canister ID string or None if not configured
    """
    try:
        from config import CANISTER_IDS
        return CANISTER_IDS.get("nft_backend")
    except Exception as e:
        logger.warning(f"Could not get NFT canister ID from config: {e}")
        return None
