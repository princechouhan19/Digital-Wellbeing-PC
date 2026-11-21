import { Diagram, Drop, LayerLabel, Node } from "./figure"

/**
 * docs/ARCHITECTURE.md section 1, drawn. Four layers, which is the document's
 * own structure: the Qt interface, the tracking and protection core, the
 * privileged and OS pieces, and the local store. The only arrows that cross a
 * privilege boundary are called out in alert tone, because that boundary is
 * the security argument of the whole design.
 */
export function ArchitectureFlow() {
  return (
    <Diagram
      id="diagram-architecture"
      title="System architecture"
      source="docs/ARCHITECTURE.md, section 1"
      caption="The application layer never talks to Windows directly. Anything that needs administrator rights leaves through one helper, and the helper only accepts four named actions."
    >
      <div className="min-w-[34rem]">
        {/* 1. Interface */}
        <LayerLabel aside="PySide6, main thread">Interface</LayerLabel>
        <div className="grid grid-cols-3 gap-2">
          <Node name="MainWindow" detail="Sidebar, 13 pages" />
          <Node name="Dynamic notch" detail="WASAPI peaks, battery" />
          <Node name="Onboarding" detail="5 steps, first run" />
          <Node name="Aurora design system" detail="Tokens, theme engine" />
          <Node name="Custom widgets" detail="Rings, spline, hydration" />
          <Node name="Settings manager" detail="JSON config, defaults" />
        </div>

        <Drop label="Qt signals, never direct calls" />

        {/* 2. Core */}
        <LayerLabel aside="worker threads">Tracking and protection</LayerLabel>
        <div className="grid grid-cols-4 gap-2">
          <Node name="TrackingManager" detail="Daemon, 2.0 s tick" tone="accent" />
          <Node name="ForegroundTracker" detail="WinEvent hook" />
          <Node name="IdleTracker" detail="GetLastInputInfo" />
          <Node name="DomainTracker" detail="UI Automation" />
          <Node name="FocusManager" detail="Allowlist, hosts" tone="accent" />
          <Node name="AppLocker" detail="Hello, PIN, grants" tone="accent" />
          <Node name="SafeBrowse" detail="StevenBlack lists" tone="accent" />
          <Node name="SleepGuard" detail="Bedtime, media aware" />
        </div>

        <Drop label="one elevated subprocess, allowlisted actions" />

        {/* 3. OS boundary */}
        <LayerLabel aside="privileged">Windows</LayerLabel>
        <div className="grid grid-cols-3 gap-2">
          <Node name="Elevated helper" detail="focus-apply, safebrowse-apply" tone="alert" />
          <Node name="hosts file" detail="hosts.dw.bak, flushdns" tone="alert" />
          <Node name="Windows Hello" detail="WinRT consent verifier" />
          <Node name="Toast subsystem" detail="Session reminders" />
          <Node name="Loopback bridge" detail="127.0.0.1, token, MV3" />
          <Node name="Gamma ramp" detail="6500 K to 3400 K" />
        </div>

        <Drop label="WAL writes, 30 s heartbeat" />

        {/* 4. Storage */}
        <LayerLabel aside="local only">Disk</LayerLabel>
        <div className="grid grid-cols-3 gap-2">
          <Node name="Repository" detail="Transactions, migrations" />
          <Node name="digital_wellbeing.db" detail="SQLite, WAL mode" tone="accent" />
          <Node name="blocklist cache" detail="%LOCALAPPDATA%" />
        </div>

        <p className="mt-4 border-t border-line pt-2.5 font-mono text-[0.625rem] leading-relaxed text-muted">
          No cloud, no account, no remote endpoint. The two requests that can leave this machine are
          the optional blocklist download and an opt-in heartbeat.
        </p>
      </div>
    </Diagram>
  )
}
