# 🎯 MICRO - AI-Powered Multi-Modal Accessibility Assistant

<div align="center">

![MICRO Logo](https://img.shields.io/badge/MICRO-AI%20Assistant-667EEA?style=for-the-badge&logo=artificial-intelligence&logoColor=white)
![Version](https://img.shields.io/badge/Version-1.0.0-success?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20Mobile-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

### 🌟 *Empowering Lives Through AI Technology* 🌟

**An intelligent accessibility solution combining FPGA-accelerated computer vision, voice AI, and multi-modal sensing to assist visually impaired users in their daily lives.**

[🌐 Website](#-website-features) • [📱 Mobile App](#-mobile-app-features) • [🚀 Quick Start](#-quick-start) • [📖 Documentation](#-api-documentation)

---

</div>

## 📋 Table of Contents

- [✨ Overview](#-overview)
- [ Website Features](#-website-features)
- [📱 Mobile App Features](#-mobile-app-features)
- [🏗️ Architecture](#️-architecture)
- [🛠️ Tech Stack](#️-tech-stack)
- [🚀 Quick Start](#-quick-start)
- [📖 API Documentation](#-api-documentation)
- [🎯 Use Cases](#-use-cases)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## ✨ Overview

**MICRO** is a comprehensive AI-powered assistant designed to help visually impaired individuals navigate their daily lives with greater independence. The system combines:

| Component | Description |
|-----------|-------------|
| 🖥️ **Backend Server** | Flask-based API running on FPGA-accelerated hardware |
| 🌐 **Web Interface** | Responsive HTML5 dashboard for all features |
| 📱 **Mobile App** | Flutter-based Android application with voice control |
| 🤖 **AI Engine** | Google Gemini 2.0 Flash for intelligent responses |
| 📷 **Computer Vision** | YOLO object detection + OpenCV processing |
| 🎤 **Voice Interface** | Speech-to-Text and Text-to-Speech integration |

---

##  Website Features

Access all features through a beautiful, responsive web interface at `http://<board-ip>:5000`

### 🏠 Main Dashboard (`ui.html`)

<details>
<summary><b>🎙️ Voice AI Chatbot</b> - Click to expand</summary>

- **Real-time Voice Interaction**: Talk naturally with the AI assistant
- **Gemini 2.0 Flash Integration**: Powered by Google's latest AI model
- **Smart Command Recognition**: Understands context and intent
- **Text-to-Speech Responses**: Hear responses spoken aloud
- **Continuous Listening Mode**: Hands-free operation

```
💡 Try saying: "What can you help me with today?"
```

</details>

<details>
<summary><b>🔍 Object Detection</b> - Click to expand</summary>

- **Real-time Camera Feed**: Live video stream from board camera
- **YOLO-powered Detection**: Identifies 80+ object classes
- **FPGA Acceleration**: Hardware-optimized for speed
- **Audio Descriptions**: Speaks detected objects aloud
- **Proximity Alerts**: Warns about nearby obstacles

```
💡 Point camera at objects and hear: "I see a chair, a table, and a person"
```

</details>

<details>
<summary><b>📝 OCR Text Reader</b> - Click to expand</summary>

- **Document Scanning**: Read printed text from documents
- **Multi-language Support**: Supports various languages
- **Real-time Processing**: Instant text extraction
- **Voice Output**: Reads extracted text aloud
- **High Accuracy**: Advanced text recognition

```
💡 Hold a document to the camera to have it read aloud
```

</details>

### 📍 Location Tracker (`location.html`)

<details>
<summary><b>🗺️ GPS Navigation</b> - Click to expand</summary>

| Feature | Description |
|---------|-------------|
| 📍 **Real-time GPS** | Current location with high accuracy |
| 🎯 **Voice Navigation** | Say "Navigate to [destination]" |
| 🏨 **Places Search** | "Find hotels near me", "Restaurants nearby" |
| 🗣️ **Turn-by-Turn Directions** | Audio guidance for each step |
| 🗺️ **Interactive Map** | Google Maps integration with route display |
| ⏱️ **5-Second Voice Recording** | Quick voice commands |

```
💡 Say: "Navigate to MIT Pune" or "Find restaurants near me"
```

</details>

### 📒 Diary Module (`diary.html`)

<details>
<summary><b>✍️ Voice Journal</b> - Click to expand</summary>

- **Voice-to-Text Entries**: Speak your diary entries
- **Automatic Timestamps**: Date and time recorded
- **Entry Management**: View, edit, delete entries
- **Search Function**: Find past entries quickly
- **Mood Tracking**: Optional emotion tagging

```
💡 Say: "Today I went to the park and enjoyed the sunshine"
```

</details>

### 🏥 Medical Assistant (`medical.html`)

<details>
<summary><b>💊 Health Management</b> - Click to expand</summary>

| Feature | Description |
|---------|-------------|
| 💊 **Medication Reminders** | Voice-activated pill tracking |
| 📋 **Symptom Logging** | Record health symptoms by voice |
| 📅 **Appointment Notes** | Never miss a doctor's visit |
| 📊 **Health History** | Access past medical notes |
| 🚨 **Emergency Info** | Quick access to vital information |

```
💡 Say: "Add medication reminder for aspirin at 9 AM"
```

</details>

### 🧠 Mental Health (`mental.html`)

<details>
<summary><b>😊 Emotional Wellness</b> - Click to expand</summary>

- **Voice Emotion Detection**: Analyzes tone and sentiment
- **Facial Expression Analysis**: Detects emotions from face
- **Mood History Charts**: Track emotional patterns over time
- **Wellness Tips**: AI-powered suggestions based on mood
- **Calming Exercises**: Guided breathing and relaxation

```
💡 The system detects: "You sound happy today! Keep up the positive energy!"
```

</details>

### 👨‍👩‍👧 Parental Control (`parental.html`)

<details>
<summary><b>📊 Usage Analytics</b> - Click to expand</summary>

| Feature | Description |
|---------|-------------|
| 📈 **Pie Chart Breakdown** | Visual usage by module |
| ⏱️ **Active Minutes** | Total daily screen time |
| 📋 **Activity Timeline** | Chronological usage log |
| 🏆 **Most Used Module** | Identify favorites |
| 📅 **Daily Summaries** | Quick stats overview |

</details>

---

## 📱 Mobile App Features

**Native Android app built with Flutter** - Download APK from `build/app/outputs/flutter-apk/app-release.apk`

### 🏠 Home Screen

<div align="center">

| Feature | Icon | Description |
|:-------:|:----:|:-----------:|
| **MICRO Branding** | 🎯 | Stylish gradient header with "MICRO" title |
| **Voice Chatbot** | 🎙️ | Large floating mic button for voice commands |
| **Quick Access Grid** | 📱 | 7 module cards with one-tap access |
| **Online Status** | 🟢 | Real-time backend connection indicator |
| **Settings** | ⚙️ | Configure backend IP address |

</div>

### 📱 Module Cards

```
┌─────────────────────────────────────────────────────────────┐
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  📒     │  │  🏥     │  │  🧠     │  │  👨‍👩‍👧    │        │
│  │ Diary   │  │ Medical │  │ Mental  │  │Parental │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │  📝     │  │  🔍     │  │  📍     │                     │
│  │  OCR    │  │ Detect  │  │Location │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### 🎙️ Voice Assistant Features

| Feature | Description |
|---------|-------------|
| 🎤 **Continuous Listening** | Keeps recording until you tap stop |
| 🔊 **TTS Responses** | Speaks all AI responses aloud |
| 🛑 **Voice Stop Button** | Red FAB on every screen to stop voice |
| 🤖 **Gemini AI** | Intelligent conversation powered by Gemini 2.0 |
| 📍 **Board Microphone** | Uses FPGA board's mic for better pickup |

### ⚙️ Settings Dialog

```
┌──────────────────────────────────────┐
│  ⚙️ Server Settings                  │
├──────────────────────────────────────┤
│  Configure the backend server        │
│                                      │
│  IP Address: [192.168.0.105    ]     │
│  Port:       [5000             ]     │
│                                      │
│  ℹ️ Current: http://192.168.0.105:5000│
│                                      │
│  [Reset]  [Cancel]  [Save]           │
└──────────────────────────────────────┘
```

### 🛑 Voice Stop Button

Every module screen has a **floating red stop button** to instantly stop any voice/TTS output:

- 📒 Diary → 🛑 Stop Button
- 🏥 Medical → 🛑 Stop Button  
- 🧠 Mental Health → 🛑 Stop Button
- 👨‍👩‍👧 Parental → 🛑 Stop Button
- 📝 OCR → 🛑 Stop Button
- 🔍 Object Detection → 🛑 Stop Button
- 📍 Location → 🛑 Stop Button + 🎤 Mic Button

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────────┐
                    │            USER DEVICES                 │
                    │   ┌─────────────┐  ┌─────────────┐     │
                    │   │  📱 Mobile  │  │  💻 Browser │     │
                    │   │  Flutter    │  │   HTML/JS   │     │
                    │   └──────┬──────┘  └──────┬──────┘     │
                    └──────────┼────────────────┼─────────────┘
                               │    HTTP/REST   │
                               ▼                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      🖥️ FPGA BOARD (Backend)                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Flask Server (app.py)                   │  │
│  │                      Port 5000                             │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │  │
│  │  │ 📷 Camera│ │ 🎤 Audio │ │ 🤖 YOLO  │ │ 📝 OCR   │      │  │
│  │  │  Feed    │ │ Capture  │ │ Detect   │ │ Engine   │      │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │  │
│  │  │ 🧠 Gemini│ │ 🗣️ STT   │ │ 😊 Emotion│ │ 📊 Analytics│   │  │
│  │  │   API    │ │ Engine   │ │ Analysis │ │ Logger   │      │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │                    SQLite Databases                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │  │
│  │  │diary.db  │ │medical.db│ │mental.db │ │activity.db│     │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   ☁️ External APIs   │
                    │  ┌───────────────┐  │
                    │  │ Google Gemini │  │
                    │  │ Google Maps   │  │
                    │  │ Places API    │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

---

## 🛠️ Tech Stack

<div align="center">

### Backend
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)

### AI/ML
![Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)
![YOLO](https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)

### Frontend
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

### Mobile
![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)
![Dart](https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)
![Android](https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white)

### Hardware
![FPGA](https://img.shields.io/badge/FPGA-FF0000?style=for-the-badge&logo=xilinx&logoColor=white)
![Camera](https://img.shields.io/badge/USB%20Camera-333333?style=for-the-badge&logo=camera&logoColor=white)
![Microphone](https://img.shields.io/badge/USB%20Mic-666666?style=for-the-badge&logo=audio&logoColor=white)

</div>

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+
python --version

# Flutter SDK (for mobile app)
flutter --version

# Required Python packages
pip install flask opencv-python google-generativeai pyaudio speechrecognition
```

### 1️⃣ Start the Backend Server

```bash
# Navigate to project directory
cd edgesight

# Set your Gemini API key
export GEMINI_API_KEY="your-api-key-here"

# Run the Flask server
python app.py
```

Server starts at `http://0.0.0.0:5000` 🎉

### 2️⃣ Access Web Interface

Open your browser and navigate to:

| Module | URL |
|--------|-----|
| 🏠 Main Dashboard | `http://<board-ip>:5000/` |
| 🎙️ Voice Chat | `http://<board-ip>:5000/ui` |
| 📍 Location | `http://<board-ip>:5000/location` |
| 📒 Diary | `http://<board-ip>:5000/diary` |
| 🏥 Medical | `http://<board-ip>:5000/medical` |
| 🧠 Mental Health | `http://<board-ip>:5000/mental` |
| 👨‍👩‍👧 Parental | `http://<board-ip>:5000/parental` |
| 🔍 Object Detection | `http://<board-ip>:5000/detect` |
| 📝 OCR | `http://<board-ip>:5000/ocr` |

### 3️⃣ Build & Install Mobile App

```bash
# Navigate to Flutter app
cd edgesight_app

# Get dependencies
flutter pub get

# Build release APK
flutter build apk --release

# APK location
# build/app/outputs/flutter-apk/app-release.apk
```

### 4️⃣ Configure Mobile App

1. Install APK on Android device
2. Open the app
3. Tap ⚙️ **Settings** icon (top right)
4. Enter your board's IP address (e.g., `192.168.0.105`)
5. Tap **Save**

---

## 📖 API Documentation

### Core Endpoints

<details>
<summary><b>🎙️ Voice & Chat APIs</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send text to Gemini AI |
| `/process_audio` | POST | Process audio and get AI response |
| `/start_recording` | GET | Start audio recording |
| `/stop_recording` | POST | Stop recording and transcribe |

**Example: Chat Request**
```bash
curl -X POST http://192.168.0.105:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it?"}'
```

</details>

<details>
<summary><b>🔍 Object Detection APIs</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/video_feed` | GET | Live camera stream (MJPEG) |
| `/detect_objects` | GET | Get current detections |
| `/detected_objects` | GET | List of detected objects |

</details>

<details>
<summary><b>📝 OCR APIs</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ocr_capture` | GET | Capture image for OCR |
| `/ocr_text` | GET | Get extracted text |
| `/ocr_result.jpg` | GET | Get annotated image |

</details>

<details>
<summary><b>📍 Location APIs</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/start_nav_recording` | GET | Start voice recording |
| `/stop_nav_recording` | POST | Stop and get navigation |
| `/get_places` | POST | Search nearby places |
| `/get_navigation` | POST | Get route directions |

**Example: Navigation Request**
```bash
curl -X POST http://192.168.0.105:5000/stop_nav_recording \
  -H "Content-Type: application/json" \
  -d '{"lat": 18.5196, "lng": 73.8553}'
```

</details>

<details>
<summary><b>📊 Analytics APIs</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/log_activity` | POST | Log module usage |
| `/analytics/daily_summary` | GET | Get today's usage summary |
| `/analytics/module_details` | GET | Get detailed breakdown |
| `/analytics/most_used` | GET | Get most used module |

</details>

<details>
<summary><b>📒 Diary APIs</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/diary/entries` | GET | List all entries |
| `/diary/add` | POST | Add new entry |
| `/diary/delete/<id>` | DELETE | Delete entry |

</details>

<details>
<summary><b>🏥 Medical APIs</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/medical/notes` | GET | List all notes |
| `/medical/add` | POST | Add medical note |
| `/medical/delete/<id>` | DELETE | Delete note |

</details>

<details>
<summary><b>🧠 Mental Health APIs</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze_emotion` | POST | Analyze voice emotion |
| `/analyze_face_emotion` | GET | Analyze facial expression |
| `/mental/history` | GET | Get emotion history |

</details>

---

## 🎯 Use Cases

### 👨‍🦯 For Visually Impaired Users

| Scenario | How MICRO Helps |
|----------|-----------------|
| **Reading Mail** | Point camera at letter → OCR reads it aloud |
| **Finding Objects** | "Where is my phone?" → Object detection locates it |
| **Navigation** | "Navigate to pharmacy" → Turn-by-turn voice directions |
| **Daily Journal** | Speak diary entries → Saved automatically |
| **Medication** | Voice reminders for pills and appointments |

### 👴 For Elderly Users

| Scenario | How MICRO Helps |
|----------|-----------------|
| **Simple Interface** | Large buttons, voice-first design |
| **Health Tracking** | Log symptoms and medications by voice |
| **Emergency Info** | Quick access to vital health information |
| **Stay Connected** | Voice chat for companionship |

### 👨‍👩‍👧 For Caregivers/Parents

| Scenario | How MICRO Helps |
|----------|-----------------|
| **Usage Monitoring** | Pie charts show time spent per module |
| **Activity Timeline** | See exactly when features were used |
| **Safety Alerts** | Know when navigation is being used |

---

## 📁 Project Structure

```
edgesight/
├── 📄 app.py                    # Flask backend server
├── 📄 README.md                 # This file
├── 🌐 ui.html                   # Main voice chat interface
├── 🌐 location.html             # GPS & navigation
├── 🌐 diary.html                # Voice journal
├── 🌐 medical.html              # Medical assistant
├── 🌐 mental.html               # Mental health tracker
├── 🌐 parental.html             # Usage analytics
├── 🌐 detect.html               # Object detection
├── 🌐 ocr.html                  # Text reader
├── 📁 edgesight_app/            # Flutter mobile app
│   ├── 📄 pubspec.yaml          # Dependencies
│   ├── 📄 .env                  # Configuration
│   └── 📁 lib/
│       ├── 📄 main.dart         # App entry point
│       ├── 📁 core/
│       │   ├── 📁 services/     # API, Speech, Settings
│       │   ├── 📁 theme/        # App theming
│       │   ├── 📁 providers/    # State management
│       │   └── 📁 widgets/      # Reusable widgets
│       └── 📁 features/
│           ├── 📁 home/         # Main screen
│           ├── 📁 diary/        # Diary module
│           ├── 📁 medical/      # Medical module
│           ├── 📁 mental_health/# Mental health module
│           ├── 📁 parental/     # Parental control
│           ├── 📁 ocr/          # OCR module
│           ├── 📁 object_detection/ # Detection module
│           └── 📁 location/     # Location module
└── 📁 databases/                # SQLite databases
    ├── diary.db
    ├── medical.db
    ├── mental.db
    └── activity.db
```

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. 🍴 **Fork** the repository
2. 🌿 Create a **feature branch** (`git checkout -b feature/AmazingFeature`)
3. 💾 **Commit** your changes (`git commit -m 'Add AmazingFeature'`)
4. 📤 **Push** to the branch (`git push origin feature/AmazingFeature`)
5. 🔃 Open a **Pull Request**

### 💡 Ideas for Contribution

- [ ] iOS app development
- [ ] Multi-language support
- [ ] Offline mode capabilities
- [ ] Wearable device integration
- [ ] Smart home integration
- [ ] More object detection classes

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Gemini** - For powerful AI capabilities
- **YOLOv8** - For object detection
- **OpenCV** - For computer vision
- **Flask** - For simple yet powerful backend

---

## Team Members:
1. [Senbagaseelan V](https://github.com/Senbagaseelan18)
2. [Ragul T](https://github.com/Ragul-2005)
3. [Praveen R](https://github.com/PRAVEENRAMU14)
4. [Tharun Babu V](https://github.com/TharunBabu-05)

<div align="center">
  
### 🌟 Star this repo if you find it helpful! 🌟

Made with ❤️ for accessibility

**MICRO** - *Making the world more accessible, one voice command at a time.*

![Footer](https://img.shields.io/badge/Built%20with-Love%20%26%20AI-ff69b4?style=for-the-badge)

</div>

