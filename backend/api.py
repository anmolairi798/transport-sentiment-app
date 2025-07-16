from flask import Flask, jsonify
from flask_cors import CORS
import mysql.connector
from collections import defaultdict
import datetime

app = Flask(__name__)
CORS(app)

# --- MySQL Configuration ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'gadheullu12',  # your password if any
    'database': 'transport_sentiment_app'
}

# --- Helper Functions ---
def determine_transport_type(text):
    """Enhanced transport type detection"""
    text = text.lower()
    if any(keyword in text for keyword in ['metro', 'मेट्रो', 'subway', 'dmrc']):
        return "metro"
    elif any(keyword in text for keyword in ['train', 'ट्रेन', 'railway', 'irctc', 'local train']):
        return "train"
    elif any(keyword in text for keyword in ['auto', 'ऑटो', 'rickshaw', 'three wheeler']):
        return "auto"
    elif any(keyword in text for keyword in ['taxi', 'टैक्सी', 'cab', 'ola', 'uber']):
        return "taxi"
    else:
        return "bus"  # default fallback

def determine_sentiment_score(label):
    return {
        'positive': 0.5,
        'negative': -0.5,
        'neutral': 0
    }.get(label.lower(), 0)

def extract_state_from_region(region):
    """Extract state name from region field"""
    if ',' in region:
        return region.split(',')[-1].strip()
    return region

def get_db_connection():
    """Get database connection with error handling"""
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# --- Routes ---

@app.route('/api/status')
def status():
    """API health check"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tweet_sentiment")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'API is running!',
                'database': 'connected',
                'total_tweets': count
            })
        else:
            return jsonify({
                'status': 'API is running!',
                'database': 'disconnected',
                'total_tweets': 0
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'API is running!',
            'database': 'error',
            'error': str(e)
        }), 500

@app.route('/api/tweets')
def get_tweets():
    """Get recent tweets with sentiment analysis"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM tweet_sentiment 
            ORDER BY created_at DESC 
            LIMIT 100
        """)
        rows = cursor.fetchall()

        tweets = []
        for row in rows:
            sentiment_label = row.get('sentiment', 'neutral')
            transport_type = determine_transport_type(row.get('text', ''))
            region = row.get('region', 'India')
            
            # Extract state and city from region
            if ',' in region:
                city, state = region.split(',', 1)
                city = city.strip()
                state = state.strip()
            else:
                state = region
                city = region
            
            tweets.append({
                "id": row['id'],
                "text": row['text'],
                "timestamp": row['created_at'].isoformat() if row['created_at'] else datetime.datetime.now().isoformat(),
                "location": region,
                "state": state,
                "city": city,
                "transportType": transport_type,
                "sentiment": {
                    "polarity": determine_sentiment_score(sentiment_label),
                    "label": sentiment_label,
                    "confidence": 0.85  # dummy value, can be enhanced
                }
            })

        cursor.close()
        conn.close()
        return jsonify(tweets)

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/states')
def get_states_summary():
    """Get aggregated sentiment data by state"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                region,
                COUNT(*) as total_messages,
                SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count,
                SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_count
            FROM tweet_sentiment 
            GROUP BY region
            ORDER BY total_messages DESC
        """)
        rows = cursor.fetchall()

        # Group by state
        state_data = defaultdict(lambda: {
            'total_messages': 0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'transport_breakdown': {'bus': 0, 'metro': 0, 'train': 0, 'auto': 0, 'taxi': 0}
        })

        # Get all tweets for transport type analysis
        cursor.execute("SELECT text, region FROM tweet_sentiment")
        all_tweets = cursor.fetchall()
        
        for tweet in all_tweets:
            transport_type = determine_transport_type(tweet['text'])
            state = extract_state_from_region(tweet['region'])
            state_data[state]['transport_breakdown'][transport_type] += 1

        states_data = []
        for row in rows:
            region = row['region']
            state = extract_state_from_region(region)
            
            # Aggregate data by state
            state_info = state_data[state]
            state_info['total_messages'] += row['total_messages']
            state_info['positive_count'] += row['positive_count']
            state_info['negative_count'] += row['negative_count']
            state_info['neutral_count'] += row['neutral_count']

        # Convert to final format
        for state, data in state_data.items():
            if data['total_messages'] > 0:
                sentiment_score = (data['positive_count'] - data['negative_count']) / data['total_messages']
                
                states_data.append({
                    "state": state,
                    "sentimentScore": sentiment_score,
                    "totalMessages": data['total_messages'],
                    "transportBreakdown": data['transport_breakdown'],
                    "sentimentBreakdown": {
                        "positive": data['positive_count'],
                        "negative": data['negative_count'],
                        "neutral": data['neutral_count']
                    }
                })

        cursor.close()
        conn.close()
        return jsonify(states_data)

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/states/<state_name>')
def get_state_details(state_name):
    """Get detailed data for a specific state"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                region,
                text,
                sentiment,
                created_at
            FROM tweet_sentiment 
            WHERE region LIKE %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (f'%{state_name}%',))
        rows = cursor.fetchall()

        # Process the data
        result = []
        for row in rows:
            transport_type = determine_transport_type(row['text'])
            result.append({
                'region': row['region'],
                'text': row['text'],
                'sentiment': row['sentiment'],
                'transport_type': transport_type,
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })

        cursor.close()
        conn.close()
        return jsonify(result)

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/analytics/trends')
def get_sentiment_trends():
    """Get sentiment trends over time"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                HOUR(created_at) as hour,
                region,
                sentiment,
                COUNT(*) as message_count
            FROM tweet_sentiment 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at), HOUR(created_at), region, sentiment
            ORDER BY date DESC, hour DESC
        """)
        rows = cursor.fetchall()

        # Process trends data
        trends = []
        for row in rows:
            state = extract_state_from_region(row['region'])
            sentiment_score = determine_sentiment_score(row['sentiment'])
            
            trends.append({
                'date': row['date'].isoformat() if row['date'] else None,
                'hour': row['hour'],
                'state': state,
                'sentiment': sentiment_score,
                'message_count': row['message_count']
            })

        cursor.close()
        conn.close()
        return jsonify(trends)

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# --- Run Server ---
if __name__ == '__main__':
    print("🚀 Starting Indian Transport Sentiment API...")
    print("📊 Serving data for all Indian states")
    print("🔗 API endpoints:")
    print("   - /api/status - Health check")
    print("   - /api/tweets - Recent tweets")
    print("   - /api/states - State-wise summary")
    print("   - /api/states/<state> - State details")
    print("   - /api/analytics/trends - Sentiment trends")
    app.run(debug=True, host='0.0.0.0', port=5000)