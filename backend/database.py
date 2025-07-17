import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                # Fallback for local development
                database_url = "postgresql://localhost/transport_sentiment"
            
            self.connection = psycopg2.connect(database_url)
            logger.info("✅ Connected to PostgreSQL database")
            self.create_tables()
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.connection = None
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            
            # Create tweets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tweet_sentiment (
                    id VARCHAR(255) PRIMARY KEY,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sentiment VARCHAR(20) DEFAULT 'neutral',
                    region VARCHAR(255) DEFAULT 'India',
                    source VARCHAR(50) DEFAULT 'unknown',
                    transport_type VARCHAR(20) DEFAULT 'bus',
                    sentiment_score DECIMAL(3,2) DEFAULT 0.0,
                    confidence DECIMAL(3,2) DEFAULT 0.5
                )
            """)
            
            # Create states summary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_summary (
                    state VARCHAR(255) PRIMARY KEY,
                    total_messages INTEGER DEFAULT 0,
                    positive_count INTEGER DEFAULT 0,
                    negative_count INTEGER DEFAULT 0,
                    neutral_count INTEGER DEFAULT 0,
                    avg_sentiment DECIMAL(3,2) DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.connection.commit()
            logger.info("✅ Database tables created/verified")
            
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            self.connection.rollback()
    
    def insert_tweet(self, tweet_data):
        """Insert a tweet into the database"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO tweet_sentiment 
                (id, text, created_at, sentiment, region, source, transport_type, sentiment_score, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                tweet_data['id'],
                tweet_data['text'],
                tweet_data.get('created_at'),
                tweet_data.get('sentiment', 'neutral'),
                tweet_data.get('region', 'India'),
                tweet_data.get('source', 'unknown'),
                tweet_data.get('transport_type', 'bus'),
                tweet_data.get('sentiment_score', 0.0),
                tweet_data.get('confidence', 0.5)
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inserting tweet: {e}")
            self.connection.rollback()
            return False
    
    def get_recent_tweets(self, limit=100):
        """Get recent tweets from database"""
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM tweet_sentiment 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"❌ Error fetching tweets: {e}")
            return []
    
    def get_state_summary(self):
        """Get aggregated data by state"""
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT 
                    region as state,
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count,
                    SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                    AVG(sentiment_score) as avg_sentiment,
                    COUNT(CASE WHEN transport_type = 'bus' THEN 1 END) as bus_count,
                    COUNT(CASE WHEN transport_type = 'metro' THEN 1 END) as metro_count,
                    COUNT(CASE WHEN transport_type = 'train' THEN 1 END) as train_count,
                    COUNT(CASE WHEN transport_type = 'auto' THEN 1 END) as auto_count,
                    COUNT(CASE WHEN transport_type = 'taxi' THEN 1 END) as taxi_count
                FROM tweet_sentiment 
                GROUP BY region
                ORDER BY total_messages DESC
            """)
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"❌ Error fetching state summary: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

# Global database instance
db = Database()