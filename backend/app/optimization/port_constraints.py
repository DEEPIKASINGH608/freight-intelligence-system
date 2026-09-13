from typing import Dict, Any, Tuple, List


# PORT CONSTRAINT DATABASE

PORT_CONSTRAINTS: Dict[str, Dict[str, Any]] = {

    "Paradip": {
        "max_draft_m": 17.0,
        "max_loa_m": 300.0,
        "max_beam_m": 48.0,
        "max_dwt": 180000,
        "supported_cargos": [
            "iron_ore",
            "coal",
            "bauxite"
        ]
    },

    "Vizag": {
        "max_draft_m": 16.5,
        "max_loa_m": 280.0,
        "max_beam_m": 45.0,
        "max_dwt": 150000,
        "supported_cargos": [
            "iron_ore",
            "coal"
        ]
    },

    "Gangavaram": {
        "max_draft_m": 18.1,
        "max_loa_m": 310.0,
        "max_beam_m": 50.0,
        "max_dwt": 200000,
        "supported_cargos": [
            "iron_ore",
            "coal",
            "limestone"
        ]
    }
}


# NORMALIZE PORT NAME

def normalize_port_name(port_name: str) -> str:
    """
    Normalize common port-name variations.

    Examples:
        'Paradip Port' -> 'Paradip'
        'PARADIP'      -> 'Paradip'
    """

    if not port_name:
        return ""

    normalized = port_name.strip().lower()

    aliases = {
        "paradip": "Paradip",
        "paradip port": "Paradip",

        "vizag": "Vizag",
        "vizag port": "Vizag",
        "visakhapatnam": "Vizag",
        "visakhapatnam port": "Vizag",

        "gangavaram": "Gangavaram",
        "gangavaram port": "Gangavaram"
    }

    return aliases.get(
        normalized,
        port_name.strip()
    )


# GET PORT CONSTRAINTS

def get_port_constraints(
    port_name: str
) -> Dict[str, Any]:

    normalized_port = normalize_port_name(
        port_name
    )

    port = PORT_CONSTRAINTS.get(
        normalized_port
    )

    if not port:
        return {
            "status": "UNKNOWN_PORT",
            "port": port_name,
            "message": (
                f"No constraint data is available "
                f"for port '{port_name}'."
            )
        }

    return {
        "status": "KNOWN_PORT",
        "port": normalized_port,
        "max_draft_m": port["max_draft_m"],
        "max_loa_m": port["max_loa_m"],
        "max_beam_m": port["max_beam_m"],
        "max_dwt": port["max_dwt"],
        "supported_cargos": port["supported_cargos"]
    }


# VALIDATE VESSEL AGAINST PORT

def validate_vessel_port_compatibility(
    vessel: dict,
    port_name: str,
    cargo_type: str = "iron_ore"
) -> Tuple[bool, List[str]]:

    normalized_port = normalize_port_name(
        port_name
    )

    port = PORT_CONSTRAINTS.get(
        normalized_port
    )

    # IMPORTANT:
    # Unknown ports should NOT automatically pass.
    if not port:
        return (
            False,
            [
                f"Unknown port '{port_name}'. "
                "Port constraint data is unavailable."
            ]
        )

    violations = []

    draft = float(
        vessel.get("draft_m", 0)
    )

    loa = float(
        vessel.get("loa_m", 0)
    )

    beam = float(
        vessel.get("beam_m", 0)
    )

    dwt = float(
        vessel.get("capacity_dwt", 0)
    )

    # DRAFT

    if draft > port["max_draft_m"]:

        violations.append(
            f"Vessel draft ({draft}m) exceeds "
            f"port max draft "
            f"({port['max_draft_m']}m)."
        )

    # LOA

    if loa > port["max_loa_m"]:

        violations.append(
            f"Vessel LOA ({loa}m) exceeds "
            f"port max LOA "
            f"({port['max_loa_m']}m)."
        )

    # BEAM

    if beam > port["max_beam_m"]:

        violations.append(
            f"Vessel beam ({beam}m) exceeds "
            f"port max beam "
            f"({port['max_beam_m']}m)."
        )

    # CARGO

    if cargo_type not in port["supported_cargos"]:

        violations.append(
            f"Cargo type '{cargo_type}' "
            f"is not supported at "
            f"{normalized_port} port."
        )

    # DWT

    if dwt > port["max_dwt"]:

        violations.append(
            f"Vessel DWT ({dwt} MT) exceeds "
            f"port maximum DWT "
            f"({port['max_dwt']} MT)."
        )

    return (
        len(violations) == 0,
        violations
    )


# EXPLAIN VESSEL PORT FIT

def evaluate_vessel_port_fit(
    vessel: dict,
    port_name: str,
    cargo_type: str = "iron_ore"
) -> Dict[str, Any]:

    normalized_port = normalize_port_name(
        port_name
    )

    port = PORT_CONSTRAINTS.get(
        normalized_port
    )

    if not port:

        return {
            "status": "UNKNOWN_PORT",
            "port": port_name,
            "vessel_id": vessel.get("id"),
            "vessel_name": vessel.get("name"),
            "compatible": False,
            "reasons": [
                f"Unknown port '{port_name}'. "
                "Port constraint data is unavailable."
            ]
        }

    compatible, violations = (
        validate_vessel_port_compatibility(
            vessel=vessel,
            port_name=normalized_port,
            cargo_type=cargo_type
        )
    )

    return {
        "status": "COMPATIBLE"
        if compatible
        else "INCOMPATIBLE",

        "port": normalized_port,

        "vessel_id":
            vessel.get("id"),

        "vessel_name":
            vessel.get("name"),

        "compatible":
            compatible,

        "cargo_type":
            cargo_type,

        "reasons":
            violations
            if violations
            else [
                "Vessel satisfies all available "
                "port constraints."
            ],

        "vessel_dimensions": {
            "draft_m":
                vessel.get("draft_m"),

            "loa_m":
                vessel.get("loa_m"),

            "beam_m":
                vessel.get("beam_m"),

            "capacity_dwt":
                vessel.get("capacity_dwt")
        },

        "port_limits": {
            "max_draft_m":
                port["max_draft_m"],

            "max_loa_m":
                port["max_loa_m"],

            "max_beam_m":
                port["max_beam_m"],

            "max_dwt":
                port["max_dwt"],

            "supported_cargos":
                port["supported_cargos"]
        }
    }