# Digital Wellbeing App Locker — Manual QA Checklist

## Pre-Test Setup
- [ ] Install `dist/DigitalWellbeingSetup-4.3.1.exe` (or build/run from source)
- [ ] Launch Digital Wellbeing from Start Menu / Desktop shortcut
- [ ] Ensure a Digital Wellbeing PIN is set (Settings → Privacy & Security → PIN)

---

## 1. App Locker Page Navigation
- [ ] Sidebar shows "🔒 App Locker" between Focus and Settings
- [ ] Clicking App Locker navigates to the App Locker page
- [ ] Settings still navigates to the Settings page (footer button)
- [ ] Focus still works (page 2, sidebar)
- [ ] Ctrl+Shift+D → Dev Mode page (page 5)

---

## 2. Windows Hello Availability Badge
- [ ] Badge shows "✅ Windows Hello available on this device" (green)
- [ ] If badge is absent, test Digital Wellbeing PIN fallback path

---

## 3. Enable / Disable App Locker
- [ ] Toggle OFF→ON: no auth required
- [ ] Toggle ON→OFF: authentication dialog appears
  - [ ] Cancel → App Locker remains ON
  - [ ] Correct Windows Hello → App Locker turns OFF
  - [ ] Correct Digital Wellbeing PIN → App Locker turns OFF
  - [ ] Wrong PIN → App Locker remains ON

---

## 4. Add Application
- [ ] Click "+ Add Application" → Process Picker opens
- [ ] "Running Processes" tab lists active user apps
- [ ] `explorer.exe` does NOT appear in the list
- [ ] `digitalwellbeing.exe` does NOT appear in the list
- [ ] Select "Brave Browser" (brave.exe) → "Add to App Locker" enabled
- [ ] Double-click process → adds immediately without clicking Add
- [ ] "Browse .exe File" tab → browse to Brave.exe → selected correctly
- [ ] After adding: Brave appears in locked apps list with 🔒 icon

---

## 5. Remove Application
- [ ] Click "Remove" next to Brave → authentication dialog appears
  - [ ] Cancel → Brave remains in the list
  - [ ] Correct auth → Brave removed from list

---

## 6. App Locker Enforcement (Brave Browser locked)
### Windows Hello as primary
- [ ] Enable App Locker, lock Brave, launch Brave
- [ ] Lock dialog appears with "🔒 Application Locked"
- [ ] Dialog shows "Use Windows Hello" button
- [ ] Windows Hello FACE/Fingerprint → dialog closes, Brave accessible, 15-min grant given
- [ ] Within 15 min: launch Brave again → no dialog (grant valid)
- [ ] After 15 min (or grant expired): dialog appears again

### Windows Hello cancel
- [ ] Launch Brave → dialog appears
- [ ] Click Windows Hello → click Cancel on the Windows Hello prompt
- [ ] Dialog shows "Windows Hello canceled." error
- [ ] Brave remains inaccessible (user can retry or use PIN)

### Windows Hello failure
- [ ] Launch Brave → click Windows Hello → fail biometric (wrong face/finger)
- [ ] Dialog shows appropriate error message
- [ ] Brave remains inaccessible

### Digital Wellbeing PIN fallback
- [ ] Click "Use Digital Wellbeing PIN instead" link
- [ ] PIN field appears
- [ ] Enter WRONG PIN → "Incorrect PIN. Try again." shown, field cleared
- [ ] Enter CORRECT PIN → dialog closes, Brave accessible

### Cancel (neither auth)
- [ ] Launch Brave → dialog appears → click "Cancel"
- [ ] Dialog closes, Brave accessible?
  - **NOTE:** App Locker shows the dialog but cannot forcibly close the app without permission.
  - The temporary grant is NOT given. Dialog reappears on next foreground event.

---

## 7. Authentication Duration Options
- [ ] Set to "Every launch": each time Brave is foregrounded, dialog appears
- [ ] Set to "5 minutes": grant lasts 5 min
- [ ] Set to "15 minutes" (default): grant lasts 15 min
- [ ] Set to "Until application closes": grant lasts until Brave is closed
- [ ] Changing duration requires authentication

---

## 8. Authentication Method Options
- [ ] Set to "Windows Hello only": no PIN option shown in lock dialog
- [ ] Set to "Digital Wellbeing PIN only": Windows Hello button hidden, PIN shown
- [ ] Set to "Hello then PIN" (default): Hello button shown, PIN toggle available
- [ ] Changing method requires authentication

---

## 9. Focus Mode Independence
- [ ] Enable App Locker, lock Brave
- [ ] Start Focus Mode
- [ ] Focus ends → Brave remains App-Locker protected
- [ ] Stopping Focus Mode does NOT disable App Locker
- [ ] App Locker grant for Brave not affected by Focus start/stop

---

## 10. System Safety
- [ ] Open Process Picker → `explorer.exe` NOT in list
- [ ] Open Process Picker → `dwm.exe` NOT in list
- [ ] Open Process Picker → `digitalwellbeing.exe` NOT in list
- [ ] Browse to system32 → add csrss.exe → rejected with error message

---

## 11. Restart Recovery
- [ ] Lock Brave → close Digital Wellbeing → restart Digital Wellbeing
- [ ] Brave still appears in locked apps list ✅
- [ ] Auth method/duration settings preserved ✅
- [ ] App Locker still enabled ✅
- [ ] No temporary grants carried over (Brave prompts again) ✅

---

## 12. Light Mode
- [ ] Switch to Light Theme (Settings → Appearance → Light Theme)
- [ ] App Locker page: background white/light, text dark — readable ✅
- [ ] Locked app rows: light background, dark text ✅
- [ ] Authentication dialog: light background, visible text ✅
- [ ] Process picker dialog: light mode ✅
- [ ] No black text on dark surfaces
- [ ] No white text on white surfaces

---

## 13. Dark Mode
- [ ] Switch to Dark Theme
- [ ] App Locker page: dark background, light text ✅
- [ ] Authentication dialog: dark card ✅
- [ ] All buttons readable ✅

---

## 14. CPU / Performance
- [ ] Enable App Locker, lock Brave
- [ ] Open Task Manager → Digital Wellbeing CPU usage < 2% while idle
- [ ] Lock dialog appears within ~1 second of Brave being foregrounded

---

## 15. Windows Hello Physical Test (packaged .exe only)
- [ ] `DigitalWellbeing.exe` (installed): lock Brave → Windows Hello FACE works ✅ / ❌
- [ ] `DigitalWellbeing.exe` (installed): lock Brave → Windows Hello PIN works ✅ / ❌
- [ ] Result: ____________

---

## Sign-off

| Check | Status |
|---|---|
| App Locker page visible | |
| Add/Remove application | |
| Auth dialog Windows Hello | |
| Auth dialog Digital Wellbeing PIN | |
| Grant duration works | |
| Focus separation | |
| System safety | |
| Restart recovery | |
| Light mode | |
| Dark mode | |
| CPU performance | |
| Windows Hello physical (packaged exe) | |

**Tester:** ____________  **Date:** ____________
