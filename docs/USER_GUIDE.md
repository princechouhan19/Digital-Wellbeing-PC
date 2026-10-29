# Digital Wellbeing for Windows — User Guide

Welcome to **Digital Wellbeing for Windows** (v4.4.0). This guide covers everything you need to know to take back control of your screen time, eliminate digital distractions, manage focused tasks with our ambient dynamic island, protect sensitive applications, and browse safely.

---

## Table of Contents

1. [Introduction & Core Philosophy](#1-introduction--core-philosophy)
2. [Installation & First-Time Setup](#2-installation--first-time-setup)
3. [The Aurora Interface & Navigation](#3-the-aurora-interface--navigation)
4. [Smart To-Do List Integration](#4-smart-to-do-list-integration)
5. [Ambient Desktop Dynamic Notch](#5-ambient-desktop-dynamic-notch)
6. [Dashboard & Screen Time Analytics](#6-dashboard--screen-time-analytics)
7. [Focus Mode & Attention Cockpit](#7-focus-mode--attention-cockpit)
8. [SleepGuard with Media & Lecture Awareness](#8-sleepguard-with-media--lecture-awareness)
9. [Parental Controls & Doomscrolling Shield](#9-parental-controls--doomscrolling-shield)
10. [App & Website Timers](#10-app--website-timers)
11. [App Locker & Windows Hello](#11-app-locker--windows-hello)
12. [SafeBrowse Content Shield](#12-safebrowse-content-shield)
13. [Session Logs & System Diagnostics](#13-session-logs--system-diagnostics)
14. [Data Backup, Export & Privacy](#14-data-backup-export--privacy)
15. [Troubleshooting & FAQ](#15-troubleshooting--faq)

---

## 1. Introduction & Core Philosophy

Computers are powerful tools, but modern applications and websites are engineered to capture and hold your attention. Digital Wellbeing is designed to provide clarity and boundaries:

- **100% Local-First:** Your usage data never leaves your computer. No accounts, no cloud servers, and no tracking cookies.
- **System-Wide & Browser-Agnostic:** Protection works across all modern browsers (Chrome, Edge, Brave, Firefox, Opera, Vivaldi) and desktop software.
- **Apple-Grade Aesthetic:** Built with the Aurora design system, featuring fluid animations, Apple system colors, and clean typography.
- **Non-Intrusive Ambience:** Features an ambient top-screen dynamic notch inspired by macOS Dynamic Island and Nectar.

---

## 2. Installation & First-Time Setup

### Running the Installer
1. Download `DigitalWellbeingSetup-4.4.0.exe` from the official website or releases page.
2. Launch the installer. Follow the setup wizard prompts.
3. Once completed, Digital Wellbeing will launch automatically and add a shortcut to your Start Menu and Desktop.

### The 5-Step Onboarding Wizard
When launching Digital Wellbeing for the first time, an intuitive 5-step onboarding guide greets you:

1. **Welcome & Personalization:** Enter your name to personalize greetings and reports.
2. **Theme Selection:** Choose between **Dark Mode**, **Light Mode**, or follow your **Windows System Theme**.
3. **Daily Goals:** Set your desired daily screen time goal and choose primary focus categories.
4. **SafeBrowse Protection:** Choose whether to activate the system-wide adult content shield on setup.
5. **Ready to Begin:** Review your setup and enter the main dashboard.

---

## 3. The Aurora Interface & Navigation

The interface is structured around a streamlined sidebar navigation:

- **Dashboard:** Your daily usage snapshot, activity ring, top apps, and timeline.
- **Tasks:** Smart process-linked to-do list with time tracking and one-click Focus.
- **Activity:** Granular hourly and category breakdown with interactive `‹` `[Date]` `›` calendar navigation.
- **Focus:** Initiate timed, distraction-free work or study sessions with rounded cockpit controls.
- **App Locker:** Protect individual applications with Windows Hello biometrics or a PIN.
- **App Timers:** Enforce daily usage quotas on specific software.
- **Websites:** View browser domain usage and limits with historical date navigation.
- **Insights:** Interactive weekly, monthly, and yearly habit analytics and trend comparisons.
- **SleepGuard:** Redesigned bedtime hero with intelligent media/lecture detection.
- **Settings:** Parental controls, doomscrolling shield, productivity targets, theme, and data backups.
- **Session Logs:** Professional diagnostics panel with live WinEvent metrics and zero emojis.

---

## 4. Smart To-Do List Integration

The **Tasks** page brings Getting Things Done (GTD) principles directly into Digital Wellbeing:

- **Target Application Linking:** Link specific executables (such as `code.exe`, `cursor.exe`, `figma.exe`, `word.exe`) to your task.
- **Active Time Calibration:** Digital Wellbeing automatically measures how many seconds you spend actively working inside those specific tools vs. your estimated task duration.
- **One-Click Focus:** Click **Focus** on any task item to instantly engage Focus Mode configured to keep you immersed in that task's tools.
- **Priority & Status:** Assign priorities (*Low*, *Medium*, *High*, *Urgent*) and update status (*Pending*, *In Progress*, *Completed*).

---

## 5. Ambient Desktop Dynamic Notch

Digital Wellbeing features a floating, physics-animated screen-edge notch overlay inspired by [kua8/Nectar](https://github.com/kua8/Nectar):

- **Compact Resting Pill:** A sleek `260x32px` pill anchors seamlessly at the top edge of your primary screen. It displays the live Focus timer, active task name, and a pulsating reactive status dot.
- **Spring Expand-on-Hover:** Hovering over the notch smoothly expands it into an interactive command cockpit (`440x200px`) showing detailed session progress and target tools.
- **Fullscreen & Media Pass-Through:** The notch automatically stays unobtrusive and passes through input when playing fullscreen videos or games.

---

## 6. Dashboard & Screen Time Analytics

### Key Metrics
- **Total Screen Time:** Total active time spent working on foreground applications today.
- **Active Time vs. Idle Time:** Digital Wellbeing automatically pauses tracking when you step away from your keyboard and mouse for more than 5 minutes.
- **Top Applications:** Ranked list of applications by usage duration.
- **Category Donut Ring:** Interactive visual breakdown of time divided among Browsers, Productivity, Programming, Entertainment, Gaming, Communication, and System tools.
- **Interactive Date Navigation:** In both Activity and Websites pages, click `‹` and `›` to explore past days without tedious date pickers.
- **Period Insights:** In the Insights page, switch effortlessly between Weekly, Monthly, and Yearly views with automatic delta comparisons (`VS PREVIOUS PERIOD`) and peak day highlights.

---

## 7. Focus Mode & Attention Cockpit

Focus Mode eliminates interruptions when you need deep concentration.

### Focus Presets
- **Study:** Blocks gaming, entertainment, and social apps; allows code editors, PDF readers, and educational sites.
- **Work:** Blocks games and social feeds; keeps productivity suites, email, and browsers available.
- **Movie / Media:** Silences notification popups and timer alerts while watching content.
- **Deep Focus:** Strict allowlist mode — only explicitly permitted work applications remain accessible; all other apps and browser tabs are blocked.
- **Custom:** Tailor your exact allowlist and blocklist rules.

### Starting a Session
1. Navigate to **Focus** in the sidebar.
2. Choose your preferred profile and duration (e.g., 25 min Pomodoro, 50 min, or custom).
3. Click the pill-rounded **Start Focus** button.
4. If website blocking is enabled, Windows may display a single UAC prompt to update your hosts file.
5. While active, distracting applications are automatically minimized or closed, and unauthorized tabs are redirected.

---

## 8. SleepGuard with Media & Lecture Awareness

SleepGuard promotes healthy sleep hygiene and prevents PC burnout through a modernized hero card layout:

- **Bedtime Schedule:** Configure your target bedtime (e.g., 11:00 PM).
- **Intelligent Media Detection:** SleepGuard monitors active media players (VLC, MPV, MPC-HC, PotPlayer, Plex, Kodi) and browser streaming (YouTube, Netflix, Prime Video, Disney+). When you are watching video, SleepGuard avoids false-positive bedtime prompts.
- **Lecture & Study Protection:** Protects educational sessions on Coursera, edX, Udemy, Khan Academy, PDF textbooks, and note-taking apps (OneNote, Obsidian, Notion).
- **Inactivity Warning:** If you remain inactive near bedtime outside of media/lecture viewing, SleepGuard prompts a gentle reminder.
- **Automatic PC Sleep:** If the reminder is unanswered, SleepGuard safely locks your workstation or sleeps the PC.
- **Circadian Display Warm-Up:** Gradually warms display gamma over 90 minutes before bedtime.

---

## 9. Parental Controls & Doomscrolling Shield

Configure powerful attention guards in **Settings → Parental Controls**:

- **Block Short-Form Doomscrolling:** One-click blocking of YouTube Shorts (`youtube.com/shorts`), Instagram Reels (`instagram.com/reels`), and TikTok to curb mindless vertical scrolling.
- **Battle Royale & Gaming Blocker:** Restrict high-intensity games like Free Fire, PUBG, BGMI, Valorant, CS2, Fortnite, and Roblox.
- **Custom Content Blacklist:** Add arbitrary keywords, domains, or games to enforce strict household or study limits.
- **Productivity Defaults:** Configure daily maximum screen time thresholds and auto-engage Focus Mode on Windows startup.

---

## 10. App & Website Timers

Prevent excessive usage of time-sink applications and websites by configuring daily limits:

### Setting an App Limit
1. Navigate to **App Timers** in the sidebar.
2. Click **+ Add App Timer**.
3. Select an active application from the process picker or browse to its `.exe` file.
4. Set your daily quota (e.g., 1 hour 30 minutes).
5. Choose whether to receive a gentle warning notification when 80% of your time is spent.

### Setting a Website Limit
1. Navigate to **Websites** in the sidebar.
2. Click **+ Add Website Limit**.
3. Enter the root domain name (e.g., `reddit.com` or `x.com`).
4. Set your daily allowance.
5. When the limit is reached, Digital Wellbeing will alert you and help you close or redirect the tab.

---

## 11. App Locker & Windows Hello

App Locker prevents unauthorized access to sensitive software (financial apps, private browsers, messaging tools).

### Adding an App to App Locker
1. Open **App Locker** from the sidebar.
2. Click **+ Add Application** and select the executable.
3. Configure your **Authentication Frequency**:
   - *Every Launch:* Prompts every time the application gains focus.
   - *5 Minutes / 15 Minutes:* Grants a temporary grace period upon successful unlock.
   - *Until Application Closes:* Keeps the app unlocked until you completely quit it.

### Authentication Methods
- **Windows Hello Biometrics (Recommended):** Use your laptop's facial recognition camera or fingerprint scanner for instant, secure authentication.
- **Digital Wellbeing PIN:** If Windows Hello is not configured or unavailable, set a 4-to-8 digit PIN in **Settings → Privacy & Security**.

---

## 12. SafeBrowse Content Shield

SafeBrowse provides system-level adult content blocking across all browsers (including Private / Incognito windows) and desktop applications.

### How It Works
- Uses open-source community blocklists (StevenBlack hosts) containing hundreds of thousands of adult and malicious domains.
- Redirects blocked domains to `127.0.0.1` locally via the Windows hosts file.
- **100% Offline & Zero Packet Inspection:** Does not proxy your internet traffic, install local VPNs, or monitor unencrypted web packets.

### Enabling SafeBrowse
1. Navigate to **Settings** → **SafeBrowse Content Shield**.
2. Toggle SafeBrowse to **Enabled**.
3. Accept the Windows User Account Control (UAC) prompt to allow modifying the hosts file.
4. Blocklists are updated weekly in the background. You can also click **Sync Now** to refresh manually.

---

## 13. Session Logs & System Diagnostics

For power users and troubleshooting:
- Navigate to **Session Logs** in the sidebar.
- Inspect real-time **System Diagnostics** including WinEvent hook status, background event wakeups, flush ticks, and memory utilization.
- Search and filter local log output in an emoji-free, technical format.

---

## 14. Data Backup, Export & Privacy

Your data is yours. Digital Wellbeing makes data ownership straightforward:

### Exporting to CSV
1. Go to **Settings** → **Data Management**.
2. Click **Export History to CSV**.
3. Choose a save location to generate a spreadsheet compatible with Excel, Google Sheets, or Python pandas.

### Database Snapshot & Reset
- **Create Backup:** Click **Backup Database** to create a snapshot file (`.bak`).
- **Restore:** Load a previous database snapshot.
- **Reset:** Click **Reset All Data** to permanently delete all tracking history and restore factory settings.

---

## 15. Troubleshooting & FAQ

**Q: Does Digital Wellbeing slow down my PC?**  
*A:* No. Digital Wellbeing uses ultra-efficient Win32 hooks and event coalescing that typically consumes less than 0.2% CPU and around 40–80 MB of RAM.

**Q: Does SafeBrowse work in Incognito / Private browsing?**  
*A:* Yes. Because SafeBrowse operates at the Windows DNS resolution layer, it works identically across normal windows, private/incognito tabs, and all installed browsers.

**Q: Why doesn't SleepGuard turn off my screen while watching YouTube or VLC?**  
*A:* Digital Wellbeing v4.4.0 features intelligent media awareness that automatically detects active video streams and players, suppressing sleep triggers during playback.

**Q: How do I completely uninstall Digital Wellbeing?**  
*A:* Run the uninstaller via **Windows Settings → Apps → Installed Apps** or use `Uninstall Digital Wellbeing.exe`. Prior to uninstalling, toggle off SafeBrowse in Settings so your original Windows hosts file is cleanly restored.
