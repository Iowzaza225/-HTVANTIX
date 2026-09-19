from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / "ThreeOneOSFive" / "views" / "PatchProjectsView.swift"
s = path.read_text()

# Remote catalog rows must track UI/action state by the website's remote.id,
# never only by the local package UUID. Several website entries may legitimately
# resolve to the same legacy local UUID; using item.id made every row light up
# when only one row was opened.

# 1) Dedicated remote-row state.
state_anchor = "    @State private var workingProjectIDs: Set<UUID> = []\n"
state_extra = """    @State private var activeRemoteIDs: Set<String> = []
    @State private var workingRemoteIDs: Set<String> = []
"""
if "@State private var activeRemoteIDs: Set<String>" not in s:
    if state_anchor not in s:
        raise RuntimeError("workingProjectIDs state anchor not found")
    s = s.replace(state_anchor, state_anchor + state_extra, 1)

# 2) Server rows use remote.id for active/working state.
s = s.replace(
    """    private func serverPatchRow(_ item: PatchLibraryItem, remote: PatchServerCatalog.RemoteItem) -> some View {
        let isActive = activeProjectIDs.contains(item.id)
        let isWorking = workingProjectIDs.contains(item.id)
""",
    """    private func serverPatchRow(_ item: PatchLibraryItem, remote: PatchServerCatalog.RemoteItem) -> some View {
        let isActive = activeRemoteIDs.contains(remote.id)
        let isWorking = workingRemoteIDs.contains(remote.id)
""",
    1
)

s = s.replace("Button { refileServerPatch(item) } label:", "Button { refileServerPatch(item, remoteID: remote.id) } label:")
s = s.replace("Button { restoreServerPatch(item) } label:", "Button { restoreServerPatch(item, remoteID: remote.id) } label:")
s = s.replace(
    "Button { setServerPatchEnabled(true, for: item) } label:",
    "Button { setServerPatchEnabled(true, for: item, remoteID: remote.id) } label:"
)
s = s.replace(
    """                Button {
                    setServerPatchEnabled(true, for: item)
                } label: {""",
    """                Button {
                    setServerPatchEnabled(true, for: item, remoteID: remote.id)
                } label: {"""
)

# 3) Persist remote active ids and reconcile legacy builds.
helper_anchor = "    @ViewBuilder\n    private func patchActionPill("
if "private func saveActiveRemoteIDs()" not in s:
    idx = s.find(helper_anchor)
    if idx < 0:
        raise RuntimeError("patchActionPill helper anchor not found")
    helpers = """    private var activeRemoteIDsDefaultsKey: String {
        "htvintex.activeRemoteIDs.v1"
    }

    private func saveActiveRemoteIDs() {
        UserDefaults.standard.set(Array(activeRemoteIDs).sorted(), forKey: activeRemoteIDsDefaultsKey)
    }

    private func loadActiveRemoteIDs() {
        activeRemoteIDs = Set(
            UserDefaults.standard.stringArray(forKey: activeRemoteIDsDefaultsKey) ?? []
        )
    }

    private func markRemoteActive(_ remoteID: String, localID: UUID) {
        // Exactly one website row may represent a given local transaction.
        // This also repairs old installs where many remote ids pointed at one UUID.
        for remote in serverCatalog.items {
            guard remote.id != remoteID else { continue }
            if serverCatalog.localPackageID(forRemoteID: remote.id) == localID {
                activeRemoteIDs.remove(remote.id)
            }
        }
        activeRemoteIDs.insert(remoteID)
        saveActiveRemoteIDs()
    }

    private func clearRemoteActive(_ remoteID: String) {
        activeRemoteIDs.remove(remoteID)
        saveActiveRemoteIDs()
    }

    private func reconcileRemoteActiveStates() {
        // Do not erase persisted state before the catalog has loaded.
        guard !serverCatalog.items.isEmpty else { return }

        let validRemoteIDs = Set(serverCatalog.items.map(\.id))
        activeRemoteIDs.formIntersection(validRemoteIDs)

        // Keep only rows whose local transaction is still active.
        activeRemoteIDs = Set(activeRemoteIDs.filter { remoteID in
            guard let localID = serverCatalog.localPackageID(forRemoteID: remoteID) else {
                return false
            }
            return DevicePatchService.latestReceipt(projectID: localID) != nil
        })

        // One-time migration for older builds that only stored item.id.
        // If several website rows share that legacy id, choose ONE row instead
        // of marking every row active. Future applies are remembered by remote.id.
        for item in store.items {
            guard DevicePatchService.latestReceipt(projectID: item.id) != nil else { continue }
            let candidates = serverCatalog.items.filter {
                serverCatalog.localPackageID(forRemoteID: $0.id) == item.id
            }
            guard !candidates.isEmpty else { continue }
            if !candidates.contains(where: { activeRemoteIDs.contains($0.id) }) {
                activeRemoteIDs.insert(candidates[0].id)
            }
        }

        saveActiveRemoteIDs()
    }

"""
    s = s[:idx] + helpers + s[idx:]

# Utility: patch one private function slice without touching similarly-named code elsewhere.
def function_slice(name, next_names):
    start = s.find(name)
    if start < 0:
        raise RuntimeError(f"function not found: {name}")
    ends = []
    for marker in next_names:
        pos = s.find(marker, start + len(name))
        if pos >= 0:
            ends.append(pos)
    end = min(ends) if ends else len(s)
    return start, end

# 4) Apply action records the exact website row that was opened.
start, end = function_slice(
    "    private func setServerPatchEnabled(",
    ["\n    private func ", "\n    @MainActor", "\n    @ViewBuilder"]
)
block = s[start:end]
block = block.replace(
    "private func setServerPatchEnabled(_ enabled: Bool, for item: PatchLibraryItem)",
    "private func setServerPatchEnabled(_ enabled: Bool, for item: PatchLibraryItem, remoteID: String)"
)
block = block.replace(
    "guard !workingProjectIDs.contains(item.id), !item.isLocked else { return }",
    "guard !workingProjectIDs.contains(item.id), !workingRemoteIDs.contains(remoteID), !item.isLocked else { return }",
    1
)
block = block.replace(
    "workingProjectIDs.insert(item.id)",
    "workingProjectIDs.insert(item.id)\n        workingRemoteIDs.insert(remoteID)",
    1
)
block = block.replace(
    """                        userDisabledProjectIDs.remove(item.id)
                        saveUserDisabledProjectIDs()""",
    """                        userDisabledProjectIDs.remove(item.id)
                        saveUserDisabledProjectIDs()
                        markRemoteActive(remoteID, localID: item.id)""",
    1
)
# If this legacy function is ever used to disable directly, clear only that row.
block = block.replace(
    """                    if let receipt = DevicePatchService.latestReceipt(projectID: item.id) {
                        try DevicePatchService.restore(receipt: receipt, allowChangedTargets: true)
                    }""",
    """                    if let receipt = DevicePatchService.latestReceipt(projectID: item.id) {
                        try DevicePatchService.restore(receipt: receipt, allowChangedTargets: true)
                    }
                    await MainActor.run {
                        clearRemoteActive(remoteID)
                    }""",
    1
)
block = block.replace(
    "workingProjectIDs.remove(item.id)",
    "workingProjectIDs.remove(item.id)\n                    workingRemoteIDs.remove(remoteID)"
)
s = s[:start] + block + s[end:]

# 5) Restore clears only the website row that was restored.
start, end = function_slice(
    "    private func restoreServerPatch(",
    ["\n    private func refileServerPatch(", "\n    private func ", "\n    @ViewBuilder"]
)
block = s[start:end]
block = block.replace(
    "private func restoreServerPatch(_ item: PatchLibraryItem)",
    "private func restoreServerPatch(_ item: PatchLibraryItem, remoteID: String)"
)
block = block.replace(
    "guard !workingProjectIDs.contains(item.id), !item.isLocked else { return }",
    "guard !workingProjectIDs.contains(item.id), !workingRemoteIDs.contains(remoteID), !item.isLocked else { return }",
    1
)
block = block.replace(
    """guard let receipt = DevicePatchService.latestReceipt(projectID: item.id) else {
            syncActiveStates()
            return
        }""",
    """guard let receipt = DevicePatchService.latestReceipt(projectID: item.id) else {
            clearRemoteActive(remoteID)
            syncActiveStates()
            return
        }""",
    1
)
block = block.replace(
    "workingProjectIDs.insert(item.id)",
    "workingProjectIDs.insert(item.id)\n        workingRemoteIDs.insert(remoteID)",
    1
)
block = block.replace(
    """                    needsRefilingProjectIDs.remove(item.id)
                    store.reload()""",
    """                    needsRefilingProjectIDs.remove(item.id)
                    clearRemoteActive(remoteID)
                    store.reload()""",
    1
)
block = block.replace(
    "workingProjectIDs.remove(item.id)",
    "workingProjectIDs.remove(item.id)\n                    workingRemoteIDs.remove(remoteID)"
)
s = s[:start] + block + s[end:]

# 6) Refile keeps that same remote row active, but working spinner is per-row.
start, end = function_slice(
    "    private func refileServerPatch(",
    ["\n    private func refreshPatchHealth(", "\n    private func ", "\n    @ViewBuilder"]
)
block = s[start:end]
block = block.replace(
    "private func refileServerPatch(_ item: PatchLibraryItem)",
    "private func refileServerPatch(_ item: PatchLibraryItem, remoteID: String)"
)
block = block.replace(
    "guard !workingProjectIDs.contains(item.id), !item.isLocked else { return }",
    "guard !workingProjectIDs.contains(item.id), !workingRemoteIDs.contains(remoteID), !item.isLocked else { return }",
    1
)
block = block.replace(
    "workingProjectIDs.insert(item.id)",
    "workingProjectIDs.insert(item.id)\n        workingRemoteIDs.insert(remoteID)",
    1
)
block = block.replace(
    "workingProjectIDs.remove(item.id)",
    "workingProjectIDs.remove(item.id)\n                    workingRemoteIDs.remove(remoteID)"
)
s = s[:start] + block + s[end:]

# 7) Load/reconcile on page entry, foreground health refresh, and catalog sync.
if "loadActiveRemoteIDs()" not in s[s.find(".onAppear {"):s.find(".onAppear {")+500]:
    s = s.replace(
        """            .onAppear {
                reloadWallpaperPackages()
                refreshPatchHealth()""",
        """            .onAppear {
                reloadWallpaperPackages()
                loadActiveRemoteIDs()
                refreshPatchHealth()""",
        1
    )

s = s.replace(
    """                needsRefilingProjectIDs = needsRepair
                syncActiveStates()""",
    """                needsRefilingProjectIDs = needsRepair
                syncActiveStates()
                reconcileRemoteActiveStates()""",
    1
)

# Catalog refresh may already contain diagnostics inserted after the base script.
catalog_sync = """            store.reload()
            serverCatalog.finishSync(warning: warnings.first)
            syncActiveStates()"""
if catalog_sync in s and "reconcileRemoteActiveStates()" not in s[s.find(catalog_sync):s.find(catalog_sync)+300]:
    s = s.replace(
        catalog_sync,
        catalog_sync + "\n            reconcileRemoteActiveStates()",
        1
    )

path.write_text(s)
print("UI V2 remote-id active-state isolation applied")
