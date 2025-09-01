# Subjective Beeper Real-Time Data Source

A [SubjectiveRealTimeDataSource](https://github.com/Subjective-Technologies/subjective-abstract-data-source-package) implementation that monitors Beeper's local SQLite database for new messages across all connected networks (WhatsApp, Telegram, LinkedIn, etc.).

## 🎯 Overview

This data source bypasses Matrix bridge reliability issues by directly reading from Beeper's local message cache, providing real-time access to messages from all connected chat networks.

## ✨ Features

- **🔍 Real-time Monitoring** - Detects new messages as they arrive in Beeper's database
- **🌐 Multi-Network Support** - WhatsApp, Telegram, LinkedIn, Matrix, and more
- **🧵 Thread Organization** - Groups messages by conversation threads
- **👤 Sender Information** - Real display names and contact details
- **🔐 Encryption Status** - Shows encrypted vs unencrypted messages
- **↪️ Reply Detection** - Identifies reply messages and conversation flow
- **📊 Rich Metadata** - Full JSON access for advanced processing
- **⚡ High Performance** - Direct database access for minimal latency

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Beeper desktop client installed
- Access to Beeper's SQLite database

### Installation

```bash
# Clone the repository
git clone https://github.com/Subjective-Technologies/subjective_beeper_realtime_datasource.git
cd subjective_beeper_realtime_datasource

# Install dependencies
conda env create -f environment.yml
conda activate subjective-beeper-realtime-datasource
```

### Configuration

The data source requires only one configuration field:

```python
{
    "name": "database_path",
    "type": "string",
    "label": "Beeper Database Path",
    "default": "~/.config/BeeperTexts/index.db",
    "required": True
}
```

### Usage

```python
from SubjectiveBeeperRealTimeDataSource import SubjectiveBeeperRealTimeDataSource

# Create and configure the data source
source = SubjectiveBeeperRealTimeDataSource()
source._session = {"database_path": "/path/to/beeper/database.db"}

# Test connection
if source.test_connection():
    print("✅ Database connection successful!")
    
    # Start monitoring
    await source.start()
```

## 📋 Message Format

Each message notification includes:

```python
{
    "room_id": "!roomID:beeper.local",
    "thread_id": "!roomID:beeper.local",  # Same as room_id for threading
    "thread_name": "WhatsApp: John Smith",
    "sender_id": "@userID:network.local",
    "sender_name": "John Smith",
    "network": "whatsapp",  # whatsapp, telegram, linkedin, matrix
    "text": "Hello world!",
    "timestamp": 1756687131000,
    "event_id": "$eventID:beeper.local",
    "message_type": "TEXT",  # TEXT, MEDIA, FILE, LOCATION, STICKER
    "is_sent_by_me": False,
    "is_encrypted": False,
    "is_reply": False,
    "reply_to_id": None,
    "human_time": "2025-08-31 21:38:51",
    "raw_message_data": {...},  # Full JSON message data
    "raw_sender_data": {...}    # Full sender information
}
```

## 🔧 Advanced Features

### Thread Management

```python
# Get all messages from a specific thread
messages = source.get_thread_messages("!roomID:beeper.local", limit=50)
```

### Network Detection

The data source automatically detects the network type:
- **WhatsApp** 📱 - `whatsapp`
- **Telegram** ✈️ - `telegram`
- **LinkedIn** 💼 - `linkedin`
- **Matrix** 🔗 - `matrix`

### Message Types

Supports multiple message types:
- **TEXT** - Regular text messages
- **MEDIA** - Images, videos, audio
- **FILE** - Document attachments
- **LOCATION** - Location sharing
- **STICKER** - Stickers and GIFs

## 🏗️ Architecture

This data source works by:

1. **Direct Database Access** - Reads from Beeper's SQLite database
2. **Real-time Polling** - Checks for new messages every second
3. **Metadata Enrichment** - Joins with user and account tables
4. **Framework Integration** - Uses SubjectiveRealTimeDataSource base class
5. **Notification System** - Sends real-time updates to subscribers

## 🔍 Database Schema

The data source queries these tables:
- `mx_room_messages` - Main message storage
- `users` - User/contact information
- `accounts` - Network/platform details

## 🛠️ Development

### Testing

```bash
# Run standalone test
python SubjectiveBeeperRealTimeDataSource.py

# Test connection only
python -c "
from SubjectiveBeeperRealTimeDataSource import SubjectiveBeeperRealTimeDataSource
source = SubjectiveBeeperRealTimeDataSource()
print('Connection:', source.test_connection())
"
```

### Environment Setup

```bash
# Create development environment
conda env create -f environment.yml
conda activate subjective-beeper-realtime-datasource

# Install development dependencies
pip install -r requirements-dev.txt
```

## 📦 Dependencies

- `subjective-abstract-data-source-package` - Base data source framework
- `brainboost-data-tools-logger-package` - Logging utilities
- `sqlite3` - Database access (built-in)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is part of the [Subjective Technologies](https://www.subjectivetechnologies.com) ecosystem.

## 🔗 Related Projects

- [Subjective Abstract Data Source Package](https://github.com/Subjective-Technologies/subjective-abstract-data-source-package)
- [BrainBoost Data Tools Logger Package](https://github.com/Subjective-Technologies/brainboost-data-tools-logger-package)
- [Subjective Technologies](https://github.com/orgs/Subjective-Technologies/)

## 📞 Support

For support and questions:
- Email: subjectivetechnologies@gmail.com
- Website: https://www.subjectivetechnologies.com
- GitHub: https://github.com/orgs/Subjective-Technologies/
