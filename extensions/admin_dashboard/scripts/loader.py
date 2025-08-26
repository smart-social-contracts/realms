#!/usr/bin/env python3
"""
Admin Dashboard Bulk Loader

A standalone Python utility for bulk uploading CSV files to the admin_dashboard extension
with smart batching, progress tracking, and detailed error reporting.

Usage:
    python loader.py <csv_file> --entity-type <type> [options]

Examples:
    python loader.py users.csv --entity-type users
    python loader.py orgs.csv --entity-type organizations --batch-size 25
    python loader.py data.csv --entity-type users --dry-run --verbose
    python loader.py mandates.csv --entity-type mandates --network ic
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple


class BulkUploader:
    """Handles bulk CSV uploads to admin_dashboard extension"""
    
    SUPPORTED_ENTITY_TYPES = [
        'users', 'humans', 'organizations', 'mandates', 'codexes', 'instruments'
    ]
    
    SUPPORTED_NETWORKS = ['local', 'testnet', 'ic']
    
    def __init__(self, csv_file: str, entity_type: str, batch_size: int = 50, 
                 network: str = 'local', dry_run: bool = False, verbose: bool = False):
        self.csv_file = Path(csv_file)
        self.entity_type = entity_type
        self.batch_size = batch_size
        self.network = network
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Validate inputs
        self._validate_inputs()
        
        # Statistics
        self.total_records = 0
        self.successful_batches = 0
        self.failed_batches = 0
        self.total_successful_records = 0
        self.total_failed_records = 0
        self.errors = []
    
    def _validate_inputs(self):
        """Validate input parameters"""
        if not self.csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file}")
        
        if not self.csv_file.suffix.lower() == '.csv':
            raise ValueError(f"File must be a CSV file: {self.csv_file}")
        
        if self.entity_type not in self.SUPPORTED_ENTITY_TYPES:
            raise ValueError(f"Unsupported entity type: {self.entity_type}. "
                           f"Supported types: {', '.join(self.SUPPORTED_ENTITY_TYPES)}")
        
        if self.network not in self.SUPPORTED_NETWORKS:
            raise ValueError(f"Unsupported network: {self.network}. "
                           f"Supported networks: {', '.join(self.SUPPORTED_NETWORKS)}")
        
        if self.batch_size <= 0:
            raise ValueError("Batch size must be greater than 0")
    
    def read_csv_data(self) -> List[Dict[str, Any]]:
        """Read and parse CSV data"""
        print(f"📖 Reading CSV file: {self.csv_file}")
        
        data = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Get fieldnames
                fieldnames = reader.fieldnames
                if not fieldnames:
                    raise ValueError("CSV file has no headers")
                
                if self.verbose:
                    print(f"📋 CSV Headers: {', '.join(fieldnames)}")
                
                # Read all rows
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                    # Skip empty rows
                    if not any(row.values()):
                        continue
                    
                    # Clean up row data (remove empty strings, strip whitespace)
                    cleaned_row = {}
                    for key, value in row.items():
                        if value is not None:
                            cleaned_value = str(value).strip()
                            if cleaned_value:  # Only add non-empty values
                                cleaned_row[key] = cleaned_value
                    
                    if cleaned_row:  # Only add rows with actual data
                        data.append(cleaned_row)
                
                self.total_records = len(data)
                print(f"✅ Successfully read {self.total_records} records from CSV")
                
                if self.verbose and data:
                    print(f"📄 Sample record: {json.dumps(data[0], indent=2)}")
                
                return data
                
        except Exception as e:
            raise Exception(f"Error reading CSV file: {str(e)}")
    
    def create_batches(self, data: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Split data into batches"""
        batches = []
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            batches.append(batch)
        
        print(f"📦 Created {len(batches)} batches (batch size: {self.batch_size})")
        return batches
    
    def convert_batch_to_csv_string(self, batch: List[Dict[str, Any]]) -> str:
        """Convert a batch of records back to CSV string format"""
        if not batch:
            return ""
        
        # Get all unique fieldnames from the batch
        fieldnames = set()
        for record in batch:
            fieldnames.update(record.keys())
        fieldnames = sorted(list(fieldnames))
        
        # Create CSV string
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(batch)
        
        return output.getvalue()
    
    def call_realms_cli(self, batch_data: str) -> Tuple[bool, Dict[str, Any]]:
        """Call the realms CLI to import a batch of data"""
        try:
            # Prepare the arguments for the CLI call
            args_json = json.dumps({
                "entity_type": self.entity_type,
                "format": "csv",
                "data": batch_data
            })
            
            # Build the command
            cmd = [
                "realms", "realm", "extension", "admin_dashboard", "import_data",
                "--network", self.network,
                "--args", args_json
            ]
            
            if self.verbose:
                print(f"🔧 Running command: {' '.join(cmd[:6])} --args '<json_data>'")
            
            # Execute the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = f"CLI command failed (exit code {result.returncode})"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                return False, {"error": error_msg, "stdout": result.stdout}
            
            # Parse the JSON response
            try:
                response = json.loads(result.stdout)
                return True, response
            except json.JSONDecodeError as e:
                return False, {"error": f"Invalid JSON response: {str(e)}", "stdout": result.stdout}
                
        except subprocess.TimeoutExpired:
            return False, {"error": "Command timed out after 5 minutes"}
        except Exception as e:
            return False, {"error": f"Unexpected error: {str(e)}"}
    
    def process_batch(self, batch_num: int, batch: List[Dict[str, Any]]) -> bool:
        """Process a single batch"""
        print(f"\n📤 Processing batch {batch_num} ({len(batch)} records)...")
        
        if self.dry_run:
            print(f"🔍 DRY RUN: Would upload {len(batch)} records")
            if self.verbose and batch:
                print(f"📄 Sample record from batch: {json.dumps(batch[0], indent=2)}")
            return True
        
        # Convert batch to CSV string
        csv_data = self.convert_batch_to_csv_string(batch)
        
        # Call the CLI
        success, response = self.call_realms_cli(csv_data)
        
        if success:
            # Parse response data
            data = response.get('data', {})
            successful = data.get('successful', 0)
            failed = data.get('failed', 0)
            errors = data.get('errors', [])
            
            print(f"✅ Batch {batch_num} completed: {successful} successful, {failed} failed")
            
            if errors and self.verbose:
                print(f"⚠️  Errors in batch {batch_num}:")
                for error in errors[:3]:  # Show first 3 errors
                    print(f"   - {error}")
                if len(errors) > 3:
                    print(f"   ... and {len(errors) - 3} more errors")
            
            # Update statistics
            self.total_successful_records += successful
            self.total_failed_records += failed
            if errors:
                self.errors.extend(errors)
            
            return True
        else:
            print(f"❌ Batch {batch_num} failed: {response.get('error', 'Unknown error')}")
            if self.verbose and 'stdout' in response:
                print(f"📄 CLI output: {response['stdout']}")
            
            # Update statistics
            self.total_failed_records += len(batch)
            error_msg = f"Batch {batch_num}: {response.get('error', 'Unknown error')}"
            self.errors.append(error_msg)
            
            return False
    
    def upload(self):
        """Main upload process"""
        print(f"🚀 Starting bulk upload to admin_dashboard extension")
        print(f"📊 Entity Type: {self.entity_type}")
        print(f"🌐 Network: {self.network}")
        print(f"📦 Batch Size: {self.batch_size}")
        if self.dry_run:
            print(f"🔍 Mode: DRY RUN (no actual uploads)")
        print("-" * 60)
        
        try:
            # Read CSV data
            data = self.read_csv_data()
            
            if not data:
                print("❌ No data to upload")
                return False
            
            # Create batches
            batches = self.create_batches(data)
            
            # Process each batch
            for i, batch in enumerate(batches, 1):
                success = self.process_batch(i, batch)
                if success:
                    self.successful_batches += 1
                else:
                    self.failed_batches += 1
            
            # Print final statistics
            self._print_final_statistics()
            
            return self.failed_batches == 0
            
        except Exception as e:
            print(f"❌ Upload failed: {str(e)}")
            return False
    
    def _print_final_statistics(self):
        """Print final upload statistics"""
        print("\n" + "=" * 60)
        print("📊 UPLOAD SUMMARY")
        print("=" * 60)
        print(f"📁 File: {self.csv_file}")
        print(f"📊 Entity Type: {self.entity_type}")
        print(f"🌐 Network: {self.network}")
        
        if self.dry_run:
            print(f"🔍 Mode: DRY RUN")
            print(f"📄 Total Records: {self.total_records}")
            print(f"📦 Total Batches: {len(self.create_batches([{}] * self.total_records))}")
        else:
            print(f"📄 Total Records: {self.total_records}")
            print(f"📦 Successful Batches: {self.successful_batches}")
            print(f"📦 Failed Batches: {self.failed_batches}")
            print(f"✅ Successful Records: {self.total_successful_records}")
            print(f"❌ Failed Records: {self.total_failed_records}")
            
            if self.errors:
                print(f"\n⚠️  ERRORS ({len(self.errors)} total):")
                for error in self.errors[:5]:  # Show first 5 errors
                    print(f"   - {error}")
                if len(self.errors) > 5:
                    print(f"   ... and {len(self.errors) - 5} more errors")
        
        print("=" * 60)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Bulk upload CSV data to admin_dashboard extension",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s users.csv --entity-type users
  %(prog)s orgs.csv --entity-type organizations --batch-size 25
  %(prog)s data.csv --entity-type users --dry-run --verbose
  %(prog)s mandates.csv --entity-type mandates --network ic
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to the CSV file to upload'
    )
    
    parser.add_argument(
        '--entity-type',
        required=True,
        choices=BulkUploader.SUPPORTED_ENTITY_TYPES,
        help='Type of entities to import'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of records per batch (default: 50)'
    )
    
    parser.add_argument(
        '--network',
        choices=BulkUploader.SUPPORTED_NETWORKS,
        default='local',
        help='Network to deploy to (default: local)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview the upload without executing it'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output and sample records'
    )
    
    args = parser.parse_args()
    
    try:
        uploader = BulkUploader(
            csv_file=args.csv_file,
            entity_type=args.entity_type,
            batch_size=args.batch_size,
            network=args.network,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        success = uploader.upload()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
