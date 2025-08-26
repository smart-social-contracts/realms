import csv
import json
import traceback
from io import StringIO
from typing import Any, Dict, List

from ggg import Codex, Human, Instrument, Mandate, Organization, User
from kybra import Record
from kybra_simple_logging import get_logger

logger = get_logger("bulk_importer.entry")


class ResponseBulkImporter(Record):
    data: str


def get_templates(args: str):
    """Get CSV templates for different entity types."""
    try:
        templates = {
            "users": {
                "headers": ["name", "profile_picture_url"],
                "example": [
                    ["alice_smith", "https://i.pravatar.cc/150?img=1"],
                    ["bob_jones", "https://i.pravatar.cc/150?img=2"],
                ],
            },
            "humans": {
                "headers": ["name"],
                "example": [["Alice Smith"], ["Bob Jones"]],
            },
            "organizations": {
                "headers": ["name"],
                "example": [["Tech Corp"], ["Finance Inc"]],
            },
            "mandates": {
                "headers": ["name", "metadata"],
                "example": [
                    [
                        "Tax Collection",
                        '{"description": "Annual tax collection mandate"}',
                    ],
                    [
                        "License Renewal",
                        '{"description": "Driver license renewal process"}',
                    ],
                ],
            },
            "codexes": {
                "headers": ["name", "code"],
                "example": [
                    ["Age Verification", "if human.age >= 18: return True"],
                    ["Tax Calculator", "return income * 0.15"],
                ],
            },
            "instruments": {
                "headers": ["name"],
                "example": [["Bitcoin"], ["USD Token"]],
            },
        }
        return json.dumps(templates, indent=2)
    except Exception as e:
        error_msg = f"Error getting templates: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg


def import_data(args: str):
    """Import data from CSV or JSON format."""
    try:
        args = args or "{}"
        args = json.loads(args)

        entity_type = args.get("entity_type")
        data_content = args.get("data")
        data_format = args.get("format", "csv")  # csv or json
        batch_size = args.get("batch_size", 50)  # Keep batches small for ICP

        if not entity_type or not data_content:
            return "Error: 'entity_type' and 'data' parameters are required"

        if entity_type not in [
            "users",
            "humans",
            "organizations",
            "mandates",
            "codexes",
            "instruments",
        ]:
            return f"Error: Invalid entity_type '{entity_type}'. Valid types: users, humans, organizations, mandates, codexes, instruments"

        logger.info(f"Starting import of {entity_type} in {data_format} format")

        # Parse data based on format
        if data_format == "csv":
            records = _parse_csv(data_content)
        elif data_format == "json":
            records = _parse_json(data_content)
        else:
            return f"Error: Invalid format '{data_format}'. Use 'csv' or 'json'"

        if not records:
            return "Error: No valid records found in data"

        # Process in batches
        total_created = 0
        total_records = len(records)
        errors = []

        for i in range(0, total_records, batch_size):
            batch = records[i : i + batch_size]
            try:
                created_count = _create_entities(entity_type, batch)
                total_created += created_count
                logger.info(
                    f"Created batch {i//batch_size + 1}: {created_count} {entity_type}"
                )
            except Exception as e:
                error_msg = f"Error in batch {i//batch_size + 1}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        result = f"Import completed: {total_created}/{total_records} {entity_type} created successfully"
        if errors:
            result += f"\nErrors encountered: {len(errors)} batches failed"
            result += f"\nFirst error: {errors[0]}"

        return result

    except Exception as e:
        error_msg = f"Error importing data: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg


def _parse_csv(csv_content: str) -> List[Dict[str, str]]:
    """Parse CSV content into list of dictionaries."""
    records = []
    csv_file = StringIO(csv_content)
    reader = csv.DictReader(csv_file)

    for row in reader:
        # Remove empty values and strip whitespace
        clean_row = {k.strip(): v.strip() for k, v in row.items() if v.strip()}
        if clean_row:  # Only add non-empty rows
            records.append(clean_row)

    return records


def _parse_json(json_content: str) -> List[Dict[str, str]]:
    """Parse JSON content into list of dictionaries."""
    data = json.loads(json_content)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        raise ValueError("JSON must be an object or array of objects")


def _create_entities(entity_type: str, records: List[Dict[str, str]]) -> int:
    """Create entities from parsed records."""
    created_count = 0

    for record in records:
        try:
            if entity_type == "users":
                User(
                    name=record.get("name", ""),
                    profile_picture_url=record.get("profile_picture_url", ""),
                )
            elif entity_type == "humans":
                Human(name=record.get("name", ""))
            elif entity_type == "organizations":
                Organization(name=record.get("name", ""))
            elif entity_type == "mandates":
                Mandate(
                    name=record.get("name", ""), metadata=record.get("metadata", "{}")
                )
            elif entity_type == "codexes":
                Codex(name=record.get("name", ""), code=record.get("code", ""))
            elif entity_type == "instruments":
                Instrument(name=record.get("name", ""))

            created_count += 1

        except Exception as e:
            logger.error(f"Error creating {entity_type} from record {record}: {e}")
            # Continue with next record instead of failing entire batch
            continue

    return created_count
