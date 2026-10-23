# Digital Wellbeing for Windows — User Guide

Welcome to **Digital Wellbeing for Windows** (v4.2 "Attention"). This guide covers everything you need to know to take back control of your screen time, eliminate digital distractions, protect sensitive applications, and browse safely.

---

## Table of Contents

1. [Introduction & Core Philosophy](#1-introduction--core-philosophy)
2. [Installation & First-Time Setup](#2-installation--first-time-setup)
3. [The Aurora Interface](#3-the-aurora-interface)
4. [Dashboard & Screen Time Analytics](#4-dashboard--screen-time-analytics)
5. [App & Website Timers](#5-app--website-timers)
6. [Focus Mode](#6-focus-mode)
7. [App Locker & Windows Hello](#7-app-locker--windows-hello)
8. [SafeBrowse Content Shield](#8-safebrowse-content-shield)
9. [SleepGuard](#9-sleepguard)
10. [Data Backup, Export & Privacy](#10-data-backup-export--privacy)
11. [Troubleshooting & FAQ](#11-troubleshooting--faq)

---

## 1. Introduction & Core Philosophy

Computers are powerful tools, but modern applications and websites are engineered to capture and hold your attention. Digital Wellbeing is designed to provide clarity and boundaries:

- **100% Local-First:** Your usage data never leaves your computer. No accounts, no cloud servers, and no tracking cookies.
- **System-Wide & Browser-Agnostic:** Protection works across all modern browsers (Chrome, Edge, Brave, Firefox, Opera, Vivaldi) and desktop software.
- **Apple-Grade Aesthetic:** Built with the Aurora design system, featuring fluid animations, Apple system colors, and clean typography.

---

## 2. Installation & First-Time Setup

### Running the Installer
1. Download `DigitalWellbeingSetup-4.2.0.exe` from the official website or releases page.
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

## 3. The Aurora Interface

The interface is structured around a streamlined sidebar navigation:

- **Dashboard:** Your daily usage snapshot, activity ring, top apps, and timeline.
- **Activity:** Deep dive into hourly, daily, and category-level usage trends.
- **Focus:** Initiate timed, distraction-free work or study sessions.
- **App Locker:** Protect individual applications with Windows Hello biometrics or a PIN.
- **App Timers:** Enforce daily usage quotas on specific software.
- **Websites:** View browser domain usage and configure per-website time limits.
- **Insights:** Productivity analysis, weekly comparisons, and habit trends.
- **SleepGuard:** Nighttime workstation lock and sleep assistance.
- **Settings:** Customize appearance, interaction sounds, updates, and data backup.

---

## 4. Dashboard & Screen Time Analytics

### Key Metrics
- **Total Screen Time:** Total active time spent working on foreground applications today.
- **Active Time vs. Idle Time:** Digital Wellbeing automatically pauses tracking when you step away from your keyboard and mouse for more than 5 minutes.
- **Top Applications:** Ranked list of applications by usage duration.
- **Category Donut Ring:** Interactive visual breakdown of time divided among Browsers, Productivity, Programming, Entertainment, Gaming, Communication, and System tools.

---

## 5. App & Website Timers

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
3. Enter the root domain name (e.g., `reddit.com` or `youtube.com`).
4. Set your daily allowance.
5. When the limit is reached, Digital Wellbeing will alert you and help you close or redirect the tab.

---

## 6. Focus Mode

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
3. Click **Start Focus**.
4. If website blocking is enabled, Windows may display a single UAC prompt to update your hosts file.
5. While active, distracting applications are automatically minimized or closed.

---

## 7. App Locker & Windows Hello

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

## 8. SafeBrowse Content Shield

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

## 9. SleepGuard

SleepGuard promotes healthy sleep hygiene and prevents PC burnout.

- **Bedtime Schedule:** Configure your target bedtime (e.g., 11:00 PM).
- **Inactivity Warning:** If you remain inactive near or after your bedtime (such as falling asleep during a late-night video), SleepGuard prompts you with a gentle reminder.
- **Automatic PC Sleep:** If the prompt is unanswered, SleepGuard automatically locks your workstation or puts the computer to sleep to conserve energy and reduce morning screen exhaustion.

---

## 10. Data Backup, Export & Privacy

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

## 11. Troubleshooting & FAQ

**Q: Does Digital Wellbeing slow down my PC?**  
*A:* No. Digital Wellbeing uses ultra-efficient Win32 hooks and polling that typically consumes less than 0.5% CPU and around 40–80 MB of RAM.

**Q: Does SafeBrowse work in Incognito / Private browsing?**  
*A:* Yes. Because SafeBrowse operates at the Windows DNS resolution layer, it works identically across normal windows, private/incognito tabs, and all installed browsers.

**Q: How do I completely uninstall Digital Wellbeing?**  
*A:* Uninstall normally via **Windows Settings → Apps → Installed Apps**. Prior to uninstalling, toggle off SafeBrowse in Settings so your original Windows hosts file is cleanly restored.
