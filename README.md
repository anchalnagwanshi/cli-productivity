
# ProdCLI: Your Command-Line Productivity Suite 🚀

ProdCLI is a powerful and versatile command-line application designed to help you manage various aspects of your daily productivity right from your terminal. It offers modules for ToDo list management, focused work sessions, time tracking, learning progress tracking, and a consolidated dashboard view.

---

## 📋 Table of Contents

- [Features ✨](#-features)
- [Prerequisites](#-prerequisites)
- [Installation 🛠️](#-installation)
- [Usage 🚀](#-usage)
- [Project Structure 📁](#-project-structure)
- [Contributing 🤝](#-contributing)

---

## ✨ Features

- ✅ **ToDo Management**: Add, list, update, complete, delete, and search tasks. Supports due dates, priorities, recurrence, sub-tasks, and aliases.
- 🧘 **Focus Mode**: Timed focus sessions with optional scheduled breaks and motivational quotes.
- 📊 **Focus Statistics**: Track and view your daily focus session durations.
- ⏱️ **Time Tracking**: Track time across projects with timers, manual entries, summaries, and sheets.
- 🧠 **Learning Tracker**: Manage coding problems, difficulty, status, tags, notes, and URLs.
- 📅 **Productivity Dashboard**: Weekly calendar view and summary of activities.

---

## 📋 Prerequisites

Ensure you have:

- Python 3.8+
- pip (Python package installer)

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/anchalnagwanshi/cli-productivity.git
cd cli-productivity
```

Or unzip and go to the root folder:

```bash
cd "C:\Users\ancha\OneDrive\Desktop\cli productivity"
```

### 2. Verify directory structure

Ensure you have this structure:

```
.
├── pyproject.toml
├── README.md
└── src/
    ├── __init__.py
    └── prodcli/
        ├── __init__.py
        ├── cli.py
        ├── FOCUS_MODE/
        ├── TODO/
        ├── TIMETRACK/
        └── LEARNING/
```

### 3. Install in editable mode

```bash
pip install -e .
```

---

## 🚀 Usage

### Main Help

```bash
prodcli --help
```

### 📌 ToDo Commands

```bash
prodcli todo --help
prodcli todo add "Write report" --due 2025-07-15 --priority high
prodcli todo list
prodcli todo update report --status done
```

### 🧘 Focus Mode

```bash
prodcli focus start --minutes 25 --break-every 50 --break-duration 10
```

### 📊 Stats

```bash
prodcli stats
```

### 📅 Dashboard

```bash
prodcli dashboard weekly
```

### ⏱️ Time Tracking

```bash
prodcli timetrack sheet add "Client Project A"
prodcli timetrack start "Work on feature"
prodcli timetrack stop
prodcli timetrack display
```

### 🧠 Learning Tracker

```bash
prodcli learning add --url https://example.com --name "Example" --platform "LC" --difficulty Easy --status Solved
prodcli learning list --platform LC
```

---

## 📁 Project Structure

```
src/
└── prodcli/
    ├── cli.py
    ├── FOCUS_MODE/
    ├── TODO/
    ├── TIMETRACK/
    └── LEARNING/
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature-name`
3. Commit: `git commit -m "Add feature"`
4. Push: `git push origin feature-name`
5. Open a Pull Request

---
