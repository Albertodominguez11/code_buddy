"""Comprehensive unit tests for ventas.py - Sales Pipeline

These tests cover:
1. load_sales_data - CSV loading functionality
2. parse_record - Data validation and parsing
3. compute_metrics - Aggregate calculations
4. detect_anomalies - Statistical anomaly detection
5. run_pipeline - End-to-end integration
6. Edge cases and error conditions
"""

import csv
import os
import statistics
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, mock_open

import ventas


class TestLoadSalesData(unittest.TestCase):
    """Test suite for load_sales_data function"""

    def setUp(self):
        """Create temporary CSV files for testing"""
        self.temp_dir = tempfile.mkdtemp()

    def test_load_valid_csv(self):
        """Test loading a valid CSV file"""
        filepath = os.path.join(self.temp_dir, "sales.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sale_id", "amount", "quantity", "date", "region", "product"])
            writer.writeheader()
            writer.writerow({
                "sale_id": "001",
                "amount": "100.50",
                "quantity": "5",
                "date": "2024-01-15",
                "region": "North",
                "product": "Widget"
            })
        
        records = ventas.load_sales_data(filepath)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["sale_id"], "001")

    def test_load_empty_csv(self):
        """Test loading an empty CSV file"""
        filepath = os.path.join(self.temp_dir, "empty.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sale_id", "amount", "quantity", "date", "region", "product"])
            writer.writeheader()
        
        records = ventas.load_sales_data(filepath)
        self.assertEqual(len(records), 0)

    def test_load_multiple_records(self):
        """Test loading multiple records from CSV"""
        filepath = os.path.join(self.temp_dir, "multi.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sale_id", "amount", "quantity", "date", "region", "product"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({
                    "sale_id": f"00{i}",
                    "amount": str(100 * i),
                    "quantity": str(i),
                    "date": "2024-01-15",
                    "region": "North",
                    "product": "Widget"
                })
        
        records = ventas.load_sales_data(filepath)
        self.assertEqual(len(records), 10)

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file raises error"""
        with self.assertRaises(FileNotFoundError):
            ventas.load_sales_data("/nonexistent/path/file.csv")


class TestParseRecord(unittest.TestCase):
    """Test suite for parse_record function"""

    def test_parse_valid_record(self):
        """Test parsing a valid record"""
        row = {
            "sale_id": "001",
            "amount": "100.50",
            "quantity": "5",
            "date": "2024-01-15",
            "region": "North",
            "product": "Widget"
        }
        result = ventas.parse_record(row)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["sale_id"], "001")
        self.assertEqual(result["amount"], 100.50)
        self.assertEqual(result["quantity"], 5)
        self.assertEqual(result["date"], datetime(2024, 1, 15))
        self.assertEqual(result["region"], "North")
        self.assertEqual(result["product"], "Widget")

    def test_parse_with_whitespace(self):
        """Test parsing record with extra whitespace"""
        row = {
            "sale_id": "001",
            "amount": "100.50",
            "quantity": "5",
            "date": "2024-01-15",
            "region": "  North  ",
            "product": "  Widget  "
        }
        result = ventas.parse_record(row)
        
        self.assertEqual(result["region"], "North")
        self.assertEqual(result["product"], "Widget")

    def test_parse_invalid_amount(self):
        """Test parsing with invalid amount returns None"""
        row = {
            "sale_id": "001",
            "amount": "invalid",
            "quantity": "5",
            "date": "2024-01-15",
            "region": "North",
            "product": "Widget"
        }
        result = ventas.parse_record(row)
        self.assertIsNone(result)

    def test_parse_invalid_quantity(self):
        """Test parsing with invalid quantity returns None"""
        row = {
            "sale_id": "001",
            "amount": "100.50",
            "quantity": "five",
            "date": "2024-01-15",
            "region": "North",
            "product": "Widget"
        }
        result = ventas.parse_record(row)
        self.assertIsNone(result)

    def test_parse_invalid_date(self):
        """Test parsing with invalid date format returns None"""
        row = {
            "sale_id": "001",
            "amount": "100.50",
            "quantity": "5",
            "date": "15-01-2024",
            "region": "North",
            "product": "Widget"
        }
        result = ventas.parse_record(row)
        self.assertIsNone(result)

    def test_parse_missing_field(self):
        """Test parsing with missing field returns None"""
        row = {
            "sale_id": "001",
            "amount": "100.50",
            "date": "2024-01-15",
            "region": "North"
            # Missing quantity and product
        }
        result = ventas.parse_record(row)
        self.assertIsNone(result)


class TestComputeMetrics(unittest.TestCase):
    """Test suite for compute_metrics function"""

    def test_compute_metrics_empty_list(self):
        """Test computing metrics on empty list returns empty dict"""
        result = ventas.compute_metrics([])
        self.assertEqual(result, {})

    def test_compute_metrics_single_record(self):
        """Test computing metrics with single record"""
        records = [{
            "sale_id": "001",
            "amount": 100.0,
            "quantity": 5,
            "date": datetime(2024, 1, 15),
            "region": "North",
            "product": "Widget"
        }]
        
        result = ventas.compute_metrics(records)
        
        self.assertEqual(result["total_revenue"], 100.0)
        self.assertEqual(result["average_sale"], 100.0)
        self.assertEqual(result["num_transactions"], 1)
        self.assertEqual(result["top_region"], "North")
        self.assertEqual(result["region_totals"], {"North": 100.0})
        self.assertIn("Widget", result["product_summary"])

    def test_compute_metrics_multiple_records(self):
        """Test computing metrics with multiple records"""
        records = [
            {"amount": 100.0, "quantity": 5, "region": "North", "product": "Widget"},
            {"amount": 200.0, "quantity": 10, "region": "South", "product": "Widget"},
            {"amount": 150.0, "quantity": 7, "region": "North", "product": "Gadget"},
        ]
        
        result = ventas.compute_metrics(records)
        
        self.assertEqual(result["total_revenue"], 450.0)
        self.assertEqual(result["average_sale"], 150.0)
        self.assertEqual(result["num_transactions"], 3)
        self.assertEqual(result["top_region"], "North")
        self.assertEqual(result["region_totals"]["North"], 250.0)
        self.assertEqual(result["region_totals"]["South"], 200.0)

    def test_compute_metrics_product_aggregation(self):
        """Test product revenue and units aggregation"""
        records = [
            {"amount": 100.0, "quantity": 5, "region": "North", "product": "Widget"},
            {"amount": 200.0, "quantity": 10, "region": "South", "product": "Widget"},
            {"amount": 150.0, "quantity": 7, "region": "North", "product": "Gadget"},
        ]
        
        result = ventas.compute_metrics(records)
        
        self.assertEqual(result["product_summary"]["Widget"]["revenue"], 300.0)
        self.assertEqual(result["product_summary"]["Widget"]["units"], 15)
        self.assertEqual(result["product_summary"]["Gadget"]["revenue"], 150.0)
        self.assertEqual(result["product_summary"]["Gadget"]["units"], 7)


class TestDetectAnomalies(unittest.TestCase):
    """Test suite for detect_anomalies function"""

    def test_detect_anomalies_empty_list(self):
        """Test anomaly detection on empty list raises error"""
        # This tests the bug found in code review
        with self.assertRaises(ZeroDivisionError):
            ventas.detect_anomalies([])

    def test_detect_anomalies_single_record(self):
        """Test anomaly detection with single record raises error"""
        # This tests the bug - stdev needs at least 2 values
        records = [{"amount": 100.0}]
        with self.assertRaises(statistics.StatisticsError):
            ventas.detect_anomalies(records)

    def test_detect_anomalies_no_outliers(self):
        """Test anomaly detection when no outliers exist"""
        records = [
            {"amount": 100.0},
            {"amount": 105.0},
            {"amount": 95.0},
            {"amount": 102.0},
            {"amount": 98.0},
        ]
        
        anomalies = ventas.detect_anomalies(records, threshold=2.0)
        self.assertEqual(len(anomalies), 0)

    def test_detect_anomalies_with_outlier(self):
        """Test anomaly detection with clear outlier"""
        records = [
            {"amount": 100.0},
            {"amount": 105.0},
            {"amount": 95.0},
            {"amount": 102.0},
            {"amount": 1000.0},  # Clear outlier
        ]
        
        anomalies = ventas.detect_anomalies(records, threshold=2.0)
        self.assertGreater(len(anomalies), 0)
        self.assertEqual(anomalies[0]["amount"], 1000.0)

    def test_detect_anomalies_custom_threshold(self):
        """Test anomaly detection with custom threshold"""
        records = [
            {"amount": 100.0},
            {"amount": 100.0},
            {"amount": 100.0},
            {"amount": 150.0},
        ]
        
        # With lower threshold, should detect more anomalies
        anomalies_low = ventas.detect_anomalies(records, threshold=1.0)
        anomalies_high = ventas.detect_anomalies(records, threshold=3.0)
        
        self.assertGreaterEqual(len(anomalies_low), len(anomalies_high))

    def test_detect_anomalies_identical_values(self):
        """Test anomaly detection when all values are identical"""
        # This tests the zero standard deviation bug
        records = [
            {"amount": 100.0},
            {"amount": 100.0},
            {"amount": 100.0},
        ]
        
        # Standard deviation will be 0, causing division by zero
        with self.assertRaises(ZeroDivisionError):
            ventas.detect_anomalies(records)


class TestRunPipeline(unittest.TestCase):
    """Test suite for run_pipeline function - End-to-end integration"""

    def setUp(self):
        """Create temporary directory for test files"""
        self.temp_dir = tempfile.mkdtemp()

    def test_run_pipeline_valid_data(self):
        """Test complete pipeline with valid data"""
        filepath = os.path.join(self.temp_dir, "sales.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sale_id", "amount", "quantity", "date", "region", "product"])
            writer.writeheader()
            writer.writerow({
                "sale_id": "001",
                "amount": "100.50",
                "quantity": "5",
                "date": "2024-01-15",
                "region": "North",
                "product": "Widget"
            })
            writer.writerow({
                "sale_id": "002",
                "amount": "200.75",
                "quantity": "10",
                "date": "2024-01-16",
                "region": "South",
                "product": "Gadget"
            })
        
        result = ventas.run_pipeline(filepath)
        
        self.assertIn("metrics", result)
        self.assertIn("anomalies", result)
        self.assertIn("skipped_records", result)
        self.assertEqual(result["skipped_records"], 0)

    def test_run_pipeline_with_invalid_records(self):
        """Test pipeline with some invalid records"""
        filepath = os.path.join(self.temp_dir, "mixed.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sale_id", "amount", "quantity", "date", "region", "product"])
            writer.writeheader()
            writer.writerow({
                "sale_id": "001",
                "amount": "100.50",
                "quantity": "5",
                "date": "2024-01-15",
                "region": "North",
                "product": "Widget"
            })
            writer.writerow({
                "sale_id": "002",
                "amount": "invalid",  # Invalid amount
                "quantity": "10",
                "date": "2024-01-16",
                "region": "South",
                "product": "Gadget"
            })
            writer.writerow({
                "sale_id": "003",
                "amount": "150.00",
                "quantity": "7",
                "date": "2024-01-17",
                "region": "East",
                "product": "Widget"
            })
        
        result = ventas.run_pipeline(filepath)
        
        self.assertEqual(result["skipped_records"], 1)
        self.assertEqual(result["metrics"]["num_transactions"], 2)

    def test_run_pipeline_empty_file(self):
        """Test pipeline with empty CSV file"""
        filepath = os.path.join(self.temp_dir, "empty.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sale_id", "amount", "quantity", "date", "region", "product"])
            writer.writeheader()
        
        result = ventas.run_pipeline(filepath)
        
        self.assertEqual(result["metrics"], {})
        self.assertEqual(result["skipped_records"], 0)

    def test_run_pipeline_all_invalid(self):
        """Test pipeline when all records are invalid"""
        filepath = os.path.join(self.temp_dir, "invalid.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sale_id", "amount", "quantity", "date", "region", "product"])
            writer.writeheader()
            writer.writerow({
                "sale_id": "001",
                "amount": "invalid",
                "quantity": "bad",
                "date": "wrong",
                "region": "North",
                "product": "Widget"
            })
        
        result = ventas.run_pipeline(filepath)
        
        self.assertEqual(result["skipped_records"], 1)
        self.assertEqual(result["metrics"], {})


if __name__ == "__main__":
    unittest.main()
