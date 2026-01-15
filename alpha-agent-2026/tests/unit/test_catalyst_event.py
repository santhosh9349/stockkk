"""Unit tests for CatalystEvent model and time bucket classification."""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch

from src.models.catalyst_event import (
    CatalystEvent,
    TimeBucket,
    classify_time_bucket,
)


class TestTimeBucketClassification:
    """Test time bucket classification logic."""
    
    def test_today_bucket(self):
        """Test events scheduled for today."""
        today = date.today()
        bucket = classify_time_bucket(today)
        assert bucket == TimeBucket.TODAY
    
    def test_this_week_bucket(self):
        """Test events scheduled within this week (1-7 days)."""
        # 3 days from now
        event_date = date.today() + timedelta(days=3)
        bucket = classify_time_bucket(event_date)
        assert bucket == TimeBucket.THIS_WEEK
    
    def test_three_month_bucket(self):
        """Test events scheduled within 3 months (8-90 days)."""
        # 30 days from now
        event_date = date.today() + timedelta(days=30)
        bucket = classify_time_bucket(event_date)
        assert bucket == TimeBucket.THREE_MONTH
    
    def test_beyond_three_months(self):
        """Test events beyond 3 months still get classified."""
        # 120 days from now
        event_date = date.today() + timedelta(days=120)
        bucket = classify_time_bucket(event_date)
        # Should fall into BEYOND or default bucket
        assert bucket in [TimeBucket.THREE_MONTH, TimeBucket.BEYOND]
    
    def test_past_events(self):
        """Test past events get appropriate classification."""
        # Yesterday
        event_date = date.today() - timedelta(days=1)
        bucket = classify_time_bucket(event_date)
        # Past events should be marked as PAST
        assert bucket == TimeBucket.PAST


class TestCatalystEventModel:
    """Test CatalystEvent Pydantic model."""
    
    def test_create_catalyst_event(self):
        """Test creating a catalyst event."""
        event = CatalystEvent(
            ticker="NVDA",
            event_type="EARNINGS",
            event_date=date.today(),
            description="Q4 2025 Earnings Call",
            source="company_filings",
        )
        
        assert event.ticker == "NVDA"
        assert event.event_type == "EARNINGS"
        assert event.time_bucket == TimeBucket.TODAY
    
    def test_catalyst_event_with_datetime(self):
        """Test catalyst event with datetime object."""
        event_datetime = datetime.now() + timedelta(days=5)
        
        event = CatalystEvent(
            ticker="TSLA",
            event_type="FDA_APPROVAL",
            event_date=event_datetime.date(),
            description="Vehicle safety approval review",
            source="regulatory_filings",
        )
        
        assert event.time_bucket == TimeBucket.THIS_WEEK
    
    def test_catalyst_event_serialization(self):
        """Test catalyst event JSON serialization."""
        event = CatalystEvent(
            ticker="MRNA",
            event_type="CLINICAL_TRIAL",
            event_date=date.today() + timedelta(days=60),
            description="Phase 3 results announcement",
            source="clinicaltrials.gov",
        )
        
        data = event.model_dump()
        
        assert data["ticker"] == "MRNA"
        assert data["event_type"] == "CLINICAL_TRIAL"
        assert "time_bucket" in data
    
    def test_time_bucket_computed_field(self):
        """Test time_bucket is computed from event_date."""
        # Future event
        future_event = CatalystEvent(
            ticker="AAPL",
            event_type="PRODUCT_LAUNCH",
            event_date=date.today() + timedelta(days=14),
            description="iPhone 17 announcement",
            source="news",
        )
        
        assert future_event.time_bucket == TimeBucket.THIS_WEEK or \
               future_event.time_bucket == TimeBucket.THREE_MONTH


class TestCatalystEventTypes:
    """Test different catalyst event types."""
    
    @pytest.mark.parametrize("event_type", [
        "EARNINGS",
        "FDA_APPROVAL",
        "CLINICAL_TRIAL",
        "DIVIDEND",
        "SPLIT",
        "MERGER",
        "PRODUCT_LAUNCH",
        "REGULATORY",
    ])
    def test_valid_event_types(self, event_type):
        """Test various valid event types."""
        event = CatalystEvent(
            ticker="TEST",
            event_type=event_type,
            event_date=date.today(),
            description=f"Test {event_type} event",
            source="test",
        )
        
        assert event.event_type == event_type


class TestCatalystEventFiltering:
    """Test catalyst event filtering by time bucket."""
    
    def test_filter_today_events(self):
        """Test filtering events scheduled for today."""
        events = [
            CatalystEvent(
                ticker="NVDA",
                event_type="EARNINGS",
                event_date=date.today(),
                description="Today's earnings",
                source="test",
            ),
            CatalystEvent(
                ticker="AAPL",
                event_type="EARNINGS",
                event_date=date.today() + timedelta(days=7),
                description="Next week earnings",
                source="test",
            ),
            CatalystEvent(
                ticker="TSLA",
                event_type="EARNINGS",
                event_date=date.today() + timedelta(days=60),
                description="Future earnings",
                source="test",
            ),
        ]
        
        today_events = [e for e in events if e.time_bucket == TimeBucket.TODAY]
        assert len(today_events) == 1
        assert today_events[0].ticker == "NVDA"
