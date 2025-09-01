#!/usr/bin/env python3
"""
Subjective Beeper Real-Time Data Source

A SubjectiveRealTimeDataSource implementation that monitors Beeper's local SQLite database
for new messages across all connected networks (WhatsApp, Telegram, LinkedIn, etc.).

This approach bypasses Matrix bridge reliability issues by directly reading from 
Beeper's local message cache.
"""

import asyncio
import json
import sqlite3
import time
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from subjective_abstract_data_source_package import SubjectiveRealTimeDataSource
    from brainboost_data_tools_logger_package import BBLogger
except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    print("Please install: subjective-abstract-data-source-package, brainboost-data-tools-logger-package")
    exit(1)


class SubjectiveBeeperRealTimeDataSource(SubjectiveRealTimeDataSource):
    """
    Real-time data source that monitors Beeper's SQLite database for new messages
    across all connected chat networks.
    """

    def __init__(self):
        super().__init__()
        self.db_path = None
        self.last_timestamp = int(time.time() * 1000)  # Start from current time
        self.running = False
        self._monitoring_task = None

    def get_name(self) -> str:
        """Return the name of this data source"""
        return "Beeper Database Listener"

    def get_description(self) -> str:
        """Return description of this data source"""
        return ("Real-time message listener for Beeper that monitors the local SQLite database "
                "for new messages from WhatsApp, Telegram, LinkedIn, and other connected networks. "
                "Bypasses Matrix bridge reliability issues by reading directly from Beeper's cache.")

    def get_icon(self) -> str:
        """Return SVG icon for this data source"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.svg")
            if os.path.exists(icon_path):
                with open(icon_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            BBLogger.log(f"Could not load icon: {e}")
        
        # Fallback SVG icon
        return '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" 
                  fill="#4A90E2" stroke="#2C5282" stroke-width="2"/>
            <circle cx="7" cy="9" r="1.5" fill="white"/>
            <circle cx="12" cy="9" r="1.5" fill="white"/>
            <circle cx="17" cy="9" r="1.5" fill="white"/>
            <path d="M7 13C8.5 14 10.5 14 12 13C13.5 14 15.5 14 17 13" 
                  stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>'''

    def get_connection_data(self) -> List[Dict[str, Any]]:
        """Return connection configuration fields"""
        return [
            {
                "name": "database_path",
                "type": "string",
                "label": "Beeper Database Path",
                "description": "Path to Beeper's SQLite database file (usually ~/.config/BeeperTexts/index.db)",
                "default": os.path.expanduser("~/.config/BeeperTexts/index.db"),
                "required": True,
                "placeholder": "/home/user/.config/BeeperTexts/index.db"
            }
        ]

    def _cfg(self, key: str, default: Any = None) -> Any:
        """Get configuration value from session or environment"""
        # Try session first, then environment, then default
        if hasattr(self, '_session') and self._session:
            value = self._session.get(key)
            if value is not None:
                return value
        
        # Try environment with BEEPER_ prefix
        env_key = f"BEEPER_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
            
        return default

    async def _start_monitoring(self) -> None:
        """Start the database monitoring loop"""
        self.db_path = self._cfg("database_path", os.path.expanduser("~/.config/BeeperTexts/index.db"))
        
        if not os.path.exists(self.db_path):
            BBLogger.log(f"❌ Database not found: {self.db_path}")
        return

        BBLogger.log(f"🔍 Starting Beeper database monitoring...")
        BBLogger.log(f"📁 Database: {self.db_path}")
        BBLogger.log(f"📊 Only showing messages NEWER than: {datetime.fromtimestamp(self.last_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.running = True
        
        try:
            while self.running:
                messages = self._get_recent_messages(limit=50)
                
                for message in messages:
                    # Send notification to framework subscribers
                    self.send_notification(message)
                    
                    # Also log for debugging
                    network_emojis = {
                        'whatsapp': '📱',
                        'telegram': '✈️', 
                        'linkedin': '💼',
                        'matrix': '🔗',
                        'unknown': '❓'
                    }
                    
                    network_emoji = network_emojis.get(message['network'], '❓')
                    reply_indicator = "↪️ " if message['is_reply'] else ""
                    encrypted_indicator = "🔐 " if message['is_encrypted'] else ""
                    sent_by_me = "📤 " if message['is_sent_by_me'] else "📥 "
                    
                    BBLogger.log(f"🆕 [{message['human_time']}] {network_emoji} {message['network'].upper()}")
                    BBLogger.log(f"   👤 {message['sender_name']}")
                    BBLogger.log(f"   {sent_by_me}{reply_indicator}{encrypted_indicator}💬 {message['text'][:100]}{'...' if len(message['text']) > 100 else ''}")
                    BBLogger.log(f"   🧵 Thread: {message['thread_name']}")
                
                await asyncio.sleep(1.0)  # Check every second
                
        except asyncio.CancelledError:
            BBLogger.log("🛑 Monitoring cancelled")
        except Exception as e:
            BBLogger.log(f"❌ Monitoring error: {e}")
        finally:
            self.running = False

    def _get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from Beeper's database with enhanced metadata"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enhanced query with JOIN to get network/platform info
            query = """
            SELECT 
                m.roomID,
                m.senderContactID,
                m.message,
                m.timestamp,
                m.eventID,
                m.type,
                m.isSentByMe,
                m.isEncrypted,
                m.inReplyToID,
                m.text_content,
                m.text_formattedContent,
                u.user as sender_user_json,
                a.platformName as network_type
            FROM mx_room_messages m
            LEFT JOIN users u ON m.senderContactID = u.userID
            LEFT JOIN accounts a ON u.accountID = a.accountID
            WHERE m.timestamp > ? 
            AND m.type IN ('TEXT', 'MEDIA', 'FILE', 'LOCATION', 'STICKER')
            AND m.isDeleted = 0
            ORDER BY m.timestamp DESC
            LIMIT ?
            """
            
            cursor.execute(query, (self.last_timestamp, limit))
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                (room_id, sender_id, message_json, timestamp, event_id, msg_type, 
                 is_sent_by_me, is_encrypted, in_reply_to, text_content, formatted_content,
                 sender_user_json, network_type) = row
                
                # Parse message JSON to extract text and media info
                message_data = {}
                try:
                    message_data = json.loads(message_json) if message_json else {}
                except (json.JSONDecodeError, TypeError):
                    message_data = {}
                
                # Extract text content with priority order
                text = (text_content or 
                       formatted_content or 
                       message_data.get('text', '') or 
                       message_data.get('body', '') or 
                       message_data.get('filename', '') or
                       str(message_data) if message_data else '')
                
                # Skip if no meaningful content
                if not text or text.strip() == "":
                    continue
                
                # Parse sender information
                sender_name = sender_id  # Default fallback
                sender_data = {}
                try:
                    if sender_user_json:
                        sender_data = json.loads(sender_user_json)
                        sender_name = (sender_data.get('displayName') or 
                                     sender_data.get('name') or 
                                     sender_data.get('username') or 
                                     sender_id)
                except (json.JSONDecodeError, TypeError):
                    pass
                
                # Determine network/platform
                network = network_type or "unknown"
                if sender_id:
                    if "whatsapp" in sender_id.lower():
                        network = "whatsapp"
                    elif "telegram" in sender_id.lower():
                        network = "telegram" 
                    elif "linkedin" in sender_id.lower():
                        network = "linkedin"
                    elif "beeper.com" in sender_id:
                        network = "matrix"
                    elif "local-whatsapp" in sender_id:
                        network = "whatsapp"
                
                # Generate thread info from room_id
                thread_id = room_id  # Room ID IS the thread ID
                thread_name = self._generate_thread_name(room_id, network, sender_data)
                
                # Enhanced message object
                message = {
                    "room_id": room_id,
                    "thread_id": thread_id,
                    "thread_name": thread_name,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "network": network,
                    "text": text,
                    "timestamp": timestamp,
                    "event_id": event_id,
                    "message_type": msg_type,
                    "is_sent_by_me": bool(is_sent_by_me),
                    "is_encrypted": bool(is_encrypted),
                    "is_reply": bool(in_reply_to),
                    "reply_to_id": in_reply_to,
                    "human_time": datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                    "raw_message_data": message_data,
                    "raw_sender_data": sender_data
                }
                messages.append(message)
                
                # Update last timestamp
                if timestamp > self.last_timestamp:
                    self.last_timestamp = timestamp
            
            conn.close()
            return messages
            
        except Exception as e:
            BBLogger.log(f"❌ Database error: {e}")
            return []

    def _generate_thread_name(self, room_id: str, network: str, sender_data: dict) -> str:
        """Generate a human-readable thread name from room info"""
        try:
            # Try to extract meaningful thread name
            if network == "whatsapp":
                # For WhatsApp, try to get contact name or group name
                if sender_data:
                    contact_name = sender_data.get('displayName') or sender_data.get('name')
                    if contact_name:
                        return f"WhatsApp: {contact_name}"
                return "WhatsApp Chat"
            
            elif network == "telegram":
                # For Telegram, could be bot, channel, or chat
                if "telegram_" in room_id:
                    return "Telegram Bot/Channel"
                return "Telegram Chat"
            
            elif network == "linkedin":
                return "LinkedIn Chat"
            
            elif network == "matrix":
                return "Matrix/Beeper Chat"
            
            else:
                # Fallback: use shortened room ID
                return f"Chat ({room_id[:8]}...)"
                
        except Exception:
            return f"Thread ({room_id[:8]}...)"

    def get_thread_messages(self, thread_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all messages from a specific thread/room"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
            SELECT 
                m.roomID,
                m.senderContactID,
                m.message,
                m.timestamp,
                m.eventID,
                m.type,
                m.isSentByMe,
                m.isEncrypted,
                m.inReplyToID,
                m.text_content,
                m.text_formattedContent,
                u.user as sender_user_json,
                a.platformName as network_type
            FROM mx_room_messages m
            LEFT JOIN users u ON m.senderContactID = u.userID
            LEFT JOIN accounts a ON u.accountID = a.accountID
            WHERE m.roomID = ? 
            AND m.type IN ('TEXT', 'MEDIA', 'FILE', 'LOCATION', 'STICKER')
            AND m.isDeleted = 0
            ORDER BY m.timestamp ASC
            LIMIT ?
            """
            
            cursor.execute(query, (thread_id, limit))
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                (room_id, sender_id, message_json, timestamp, event_id, msg_type, 
                 is_sent_by_me, is_encrypted, in_reply_to, text_content, formatted_content,
                 sender_user_json, network_type) = row
                
                # Parse message data (same logic as _get_recent_messages)
                message_data = {}
                try:
                    message_data = json.loads(message_json) if message_json else {}
                except (json.JSONDecodeError, TypeError):
                    message_data = {}
                
                text = (text_content or 
                       formatted_content or 
                       message_data.get('text', '') or 
                       message_data.get('body', '') or 
                       message_data.get('filename', '') or
                       str(message_data) if message_data else '')
                
                if not text or text.strip() == "":
                    continue
                
                # Parse sender info
                sender_name = sender_id
                sender_data = {}
                try:
                    if sender_user_json:
                        sender_data = json.loads(sender_user_json)
                        sender_name = (sender_data.get('displayName') or 
                                     sender_data.get('name') or 
                                     sender_data.get('username') or 
                                     sender_id)
                except (json.JSONDecodeError, TypeError):
                    pass
                
                # Determine network
                network = network_type or "unknown"
                if sender_id:
                    if "whatsapp" in sender_id.lower():
                        network = "whatsapp"
                    elif "telegram" in sender_id.lower():
                        network = "telegram" 
                    elif "linkedin" in sender_id.lower():
                        network = "linkedin"
                    elif "beeper.com" in sender_id:
                        network = "matrix"
                    elif "local-whatsapp" in sender_id:
                        network = "whatsapp"
                
                thread_name = self._generate_thread_name(room_id, network, sender_data)
                
                message = {
                    "room_id": room_id,
                    "thread_id": thread_id,
                    "thread_name": thread_name,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "network": network,
                    "text": text,
                    "timestamp": timestamp,
                    "event_id": event_id,
                    "message_type": msg_type,
                    "is_sent_by_me": bool(is_sent_by_me),
                    "is_encrypted": bool(is_encrypted),
                    "is_reply": bool(in_reply_to),
                    "reply_to_id": in_reply_to,
                    "human_time": datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                    "raw_message_data": message_data,
                    "raw_sender_data": sender_data
                }
                messages.append(message)
            
            conn.close()
            return messages
            
        except Exception as e:
            BBLogger.log(f"❌ Error reading thread: {e}")
            return []

    async def start(self) -> None:
        """Start the data source"""
        BBLogger.log("🚀 Starting Beeper Real-Time Data Source...")
        
        # Start monitoring in background task
        self._monitoring_task = asyncio.create_task(self._start_monitoring())
        
        try:
            await self._monitoring_task
        except asyncio.CancelledError:
            BBLogger.log("🛑 Data source stopped")
        except Exception as e:
            BBLogger.log(f"❌ Data source error: {e}")

    async def stop(self) -> None:
        """Stop the data source"""
        BBLogger.log("🛑 Stopping Beeper Real-Time Data Source...")
        self.running = False
        
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    def test_connection(self) -> bool:
        """Test if the database connection is working"""
        try:
            db_path = self._cfg("database_path", os.path.expanduser("~/.config/BeeperTexts/index.db"))
            
            if not os.path.exists(db_path):
                BBLogger.log(f"❌ Database file not found: {db_path}")
                return False
            
            # Try to connect and query
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM mx_room_messages LIMIT 1")
            count = cursor.fetchone()[0]
            conn.close()
            
            BBLogger.log(f"✅ Database connection successful. Found {count} messages.")
            return True
            
        except Exception as e:
            BBLogger.log(f"❌ Database connection failed: {e}")
            return False


# Test function for standalone usage
async def main():
    """Test the data source standalone"""
    print("🧪 Testing Beeper Database Listener...")
    
    source = SubjectiveBeeperRealTimeDataSource()
    
    # Test connection
    if not source.test_connection():
        print("❌ Connection test failed!")
        return
    
    print("✅ Connection test passed!")
    
    # Start monitoring
    try:
        await source.start()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        await source.stop()


if __name__ == "__main__":
    asyncio.run(main())
