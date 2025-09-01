#!/usr/bin/env python
import sqlite3
import json
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any

class BeeperDatabaseListener:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default Beeper database path
            self.db_path = os.path.expanduser("~/.config/BeeperTexts/index.db")
        else:
            self.db_path = db_path
        
        # Start from current time - only show NEW messages
        self.last_timestamp = int(time.time() * 1000)
        self.running = False
        
    def get_recent_messages(self, limit: int = 10) -> list:
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
            print(f"Error reading database: {e}")
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
    
    def get_thread_messages(self, thread_id: str, limit: int = 50) -> list:
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
                
                # Parse message data (same logic as get_recent_messages)
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
            print(f"Error reading thread: {e}")
            return []
    
    def get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific room"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
            SELECT 
                t.thread,
                t.timestamp
            FROM threads t
            WHERE t.threadID = ?
            LIMIT 1
            """
            
            cursor.execute(query, (room_id,))
            row = cursor.fetchone()
            
            if row:
                thread_data = json.loads(row[0]) if row[0] else {}
                return {
                    "room_id": room_id,
                    "thread_data": thread_data,
                    "last_activity": row[1]
                }
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"Error getting room info: {e}")
            return None
    
    def start_monitoring(self, interval: float = 1.0):
        """Start monitoring the database for new messages"""
        print(f"🔍 Starting Beeper database monitoring...")
        print(f"📁 Database: {self.db_path}")
        print(f"⏱️  Check interval: {interval}s")
        print(f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Only showing messages NEWER than: {datetime.fromtimestamp(self.last_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')}")
        print("🚀 Waiting for NEW messages...")
        print("-" * 60)
        
        self.running = True
        
        try:
            while self.running:
                messages = self.get_recent_messages(limit=50)
                
                if messages:
                    for msg in messages:
                        # Network emoji mapping
                        network_emojis = {
                            'whatsapp': '📱',
                            'telegram': '✈️',
                            'linkedin': '💼',
                            'matrix': '🔗',
                            'unknown': '❓'
                        }
                        
                        network_emoji = network_emojis.get(msg['network'], '❓')
                        reply_indicator = "↪️ " if msg['is_reply'] else ""
                        encrypted_indicator = "🔐 " if msg['is_encrypted'] else ""
                        sent_by_me = "📤 " if msg['is_sent_by_me'] else "📥 "
                        
                        print(f"🆕 [{msg['human_time']}] {network_emoji} {msg['network'].upper()}")
                        print(f"   👤 {msg['sender_name']}")
                        print(f"   {sent_by_me}{reply_indicator}{encrypted_indicator}💬 {msg['text'][:100]}{'...' if len(msg['text']) > 100 else ''}")
                        print(f"   🧵 Thread: {msg['thread_name']}")
                        print(f"   🔗 Thread ID: {msg['thread_id'][:20]}...")
                        print(f"   📋 Type: {msg['message_type']} | Event: {msg['event_id'][:8]}...")
                        print("-" * 60)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
        finally:
            self.running = False
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False

if __name__ == "__main__":
    listener = BeeperDatabaseListener()
    
    try:
        listener.start_monitoring(interval=1.0)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
