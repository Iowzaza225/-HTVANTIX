#!/usr/bin/env python3
from pathlib import Path
import sys

project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

def p(rel): return project_dir / rel
def read(rel): return p(rel).read_text(encoding="utf-8")
def write(rel, s): p(rel).write_text(s, encoding="utf-8")
def replace_once(s, old, new, label, already=None):
    if old in s:
        return s.replace(old, new, 1)
    if already and already in s:
        return s
    raise RuntimeError(f"Patch pattern not found: {label}")

# SettingsView current SwiftUI Section syntax
rel = "ThreeOneOSFive/views/SettingsView.swift"
s = read(rel)
if 'Section("License") {' in s:
    s = s.replace('Section("License") {', 'Section {', 1)
write(rel, s)

# HTVINTEX bypass onboarding while keeping the original flow in source
rel = "ThreeOneOSFive/App.swift"
s = read(rel)
s = s.replace(
    "@State private var showOnboarding = OnboardingStore.shouldShow()",
    "@State private var showOnboarding = false",
    1
)
write(rel, s)

# HTVINTEX re-arm automatic exploit after foreground loss
rel = "ThreeOneOSFive/App.swift"
s = read(rel)
old = """            } else if exploitStatus.isSuccess {
                exploitStatus = .notStarted
                log("app: sandbox access is no longer active")
            }"""
new = """            } else if exploitStatus.isSuccess {
                // Returning from Free Fire can drop the sandbox escape while the
                // app still remembers that it already tried once. Reset that
                // one-shot guard so detectSupport() can automatically re-run it.
                autoRunAttempted = false
                exploitStatus = .notStarted
                log("app: sandbox access is no longer active; re-arming automatic exploit")
            }"""
if old in s:
    s = s.replace(old, new, 1)
write(rel, s)

# Home-only production navigation; hidden routes stay in source
rel = "ThreeOneOSFive/helpers/AppTabNavigationState.swift"
s = read(rel)
s = replace_once(
    s,
    """        switch section {
        case .home, .installed:
            return true
        case .files, .new, .sources, .search:
            // Keep these features and routes in the project, but hide them from
            // the production tab bar. HTVINTEX 1.1.5 exposes Home + Installed only.
            return false
        }""",
    """        switch section {
        case .home:
            return true
        case .installed, .files, .new, .sources, .search:
            // Keep every route and feature in source, but production navigation
            // starts from Home. Game cards push directly into their patch lists.
            return false
        }""",
    "FeatureVisibility",
    "case .installed, .files, .new, .sources, .search:"
)
write(rel, s)

rel = "ThreeOneOSFive/ContentView.swift"
s = read(rel)
s = replace_once(
    s,
    """    private var compactLayout: some View {
        TabView(selection: tabSelection) {
            ForEach(featureVisibility.visibleSections) { section in
                sectionContent(section)
                    .tabItem {
                        CompactTabLabel(
                            title: language.text(section.titleKey),
                            systemImage: section.systemImage
                        )
                    }
                    .tag(section.rawValue)
            }
        }
    }""",
    """    private var compactLayout: some View {
        // Home is the production launcher. Hidden tabs remain in source.
        sectionContent(.home)
    }""",
    "compact navigation",
    "sectionContent(.home)"
)
write(rel, s)

# Home game cards -> direct filtered patch list
rel = "ThreeOneOSFive/views/RepositoryHomeView.swift"
s = read(rel)
if 'game: "ff",' not in s:
    s = s.replace(
        '                                systemImage: "scope",\n                                count: serverCatalog.items.filter { $0.game == "ff" }.count',
        '                                systemImage: "scope",\n                                game: "ff",\n                                count: serverCatalog.items.filter { $0.game == "ff" }.count',
        1
    )
if 'game: "ffmax",' not in s:
    s = s.replace(
        '                                systemImage: "bolt.shield.fill",\n                                count: serverCatalog.items.filter { $0.game == "ffmax" }.count',
        '                                systemImage: "bolt.shield.fill",\n                                game: "ffmax",\n                                count: serverCatalog.items.filter { $0.game == "ffmax" }.count',
        1
    )
marker = '                        Button(action: onOpenInstalled) {\n                            HStack(spacing: 12) {'
if marker in s:
    a = s.index(marker)
    b = s.index('                        footer', a)
    s = s[:a] + s[b:]
a = s.index("    private func gameCard(")
b = s.index("    private var serverStatusText", a)
if "game: String," not in s[a:b]:
    s = s[:a] + """    private func gameCard(
        title: String,
        subtitle: String,
        systemImage: String,
        game: String,
        count: Int
    ) -> some View {
        NavigationLink {
            PatchProjectsView(
                gameFilter: game,
                screenTitle: title,
                onOpenSettings: onOpenSettings,
                onOpenLogs: onOpenLogs
            )
        } label: {
            HStack(spacing: 14) {
                ZStack {
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(AppTheme.accent.opacity(0.10))
                        .frame(width: 56, height: 56)
                    Image(systemName: systemImage)
                        .font(.system(size: 24, weight: .bold))
                        .foregroundStyle(AppTheme.accent)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.headline.weight(.black))
                        .foregroundStyle(.white)
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Text("\\(count)")
                        .font(.title3.weight(.black))
                        .foregroundStyle(count > 0 ? Color.green : Color.secondary)
                    Text("FILES")
                        .font(.caption2.weight(.black))
                        .foregroundStyle(.secondary)
                }

                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(AppTheme.accent)
            }
            .htvDashboardCard()
        }
        .buttonStyle(.plain)
    }

""" + s[b:]
write(rel, s)

# Patch screen: filter per game, remove search/cleaner, back button, independent remote IDs
rel = "ThreeOneOSFive/views/PatchProjectsView.swift"
s = read(rel)
if "let gameFilter: String?" not in s:
    s = s.replace(
        "    let onOpenSettings: () -> Void\n    let onOpenLogs: () -> Void",
        "    let gameFilter: String?\n    let screenTitle: String?\n    let onOpenSettings: () -> Void\n    let onOpenLogs: () -> Void",
        1
    )
section = s[s.index("    private var filteredItems:"):s.index("    private var filteredRemoteItems:")]
if "guard gameFilter == nil else { return [] }" not in section:
    s = s.replace(
        "    private var filteredItems: [PatchLibraryItem] {\n        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)",
        "    private var filteredItems: [PatchLibraryItem] {\n        guard gameFilter == nil else { return [] }\n        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)",
        1
    )
s = replace_once(
    s,
    """    private var filteredRemoteItems: [PatchServerCatalog.RemoteItem] {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return serverCatalog.items }
        return serverCatalog.items.filter { remote in
            remote.name.localizedCaseInsensitiveContains(query)
                || remote.description.localizedCaseInsensitiveContains(query)
                || remote.version.localizedCaseInsensitiveContains(query)
                || serverCatalog.gameTitle(remote.game).localizedCaseInsensitiveContains(query)
                || serverCatalog.categoryTitle(remote.category).localizedCaseInsensitiveContains(query)
        }
    }""",
    """    private var filteredRemoteItems: [PatchServerCatalog.RemoteItem] {
        let scoped = serverCatalog.items.filter { remote in
            guard let gameFilter else { return true }
            return remote.game == gameFilter
        }
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return scoped }
        return scoped.filter { remote in
            remote.name.localizedCaseInsensitiveContains(query)
                || remote.description.localizedCaseInsensitiveContains(query)
                || remote.version.localizedCaseInsensitiveContains(query)
                || serverCatalog.gameTitle(remote.game).localizedCaseInsensitiveContains(query)
                || serverCatalog.categoryTitle(remote.category).localizedCaseInsensitiveContains(query)
        }
    }""",
    "remote game filter",
    "let scoped = serverCatalog.items.filter"
)
w = s.index("    private var filteredWallpaperPackages:")
if "guard gameFilter == nil else { return [] }" not in s[w:w+260]:
    s = s.replace(
        "    private var filteredWallpaperPackages: [WallpaperStagedPackage] {\n        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)",
        "    private var filteredWallpaperPackages: [WallpaperStagedPackage] {\n        guard gameFilter == nil else { return [] }\n        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)",
        1
    )
s = replace_once(
    s,
    """    private var hasLocalContent: Bool {
        !serverCatalog.items.isEmpty || !localOnlyItems.isEmpty || !wallpaperPackages.isEmpty
    }""",
    """    private var hasLocalContent: Bool {
        if gameFilter != nil { return !filteredRemoteItems.isEmpty }
        return !serverCatalog.items.isEmpty || !localOnlyItems.isEmpty || !wallpaperPackages.isEmpty
    }""",
    "scoped content",
    "if gameFilter != nil { return !filteredRemoteItems.isEmpty }"
)
s = replace_once(
    s,
    """    init(
        onOpenSettings: @escaping () -> Void = {},
        onOpenLogs: @escaping () -> Void = {}
    ) {
        self.onOpenSettings = onOpenSettings
        self.onOpenLogs = onOpenLogs""",
    """    init(
        gameFilter: String? = nil,
        screenTitle: String? = nil,
        onOpenSettings: @escaping () -> Void = {},
        onOpenLogs: @escaping () -> Void = {}
    ) {
        self.gameFilter = gameFilter
        self.screenTitle = screenTitle
        self.onOpenSettings = onOpenSettings
        self.onOpenLogs = onOpenLogs""",
    "PatchProjects init",
    "gameFilter: String? = nil"
)
s = s.replace(
    """            VStack(spacing: 0) {
                AppSearchField(
                    text: $searchText,
                    prompt: language.text("installed.search"),
                    clearLabel: language.text("common.clear")
                )
                Divider()
                List {""",
    """            VStack(spacing: 0) {
                List {""",
    1
)
s = s.replace(
    """                    if cleanerEnabled {
                        Section(language.text("repository.utilities")) {
                            cleanerRow
                        }
                    }
""",
    "",
    1
)
s = s.replace(
    '.navigationTitle(language.text("tab.installed"))\n            .navigationBarTitleDisplayMode(.inline)',
    '.navigationTitle(screenTitle ?? language.text("tab.installed"))\n            .navigationBarTitleDisplayMode(.inline)\n            .toolbar(.hidden, for: .tabBar)',
    1
)

# HTVINTEX present patch-row errors
alert_anchor = """            .onAppear {
                reloadWallpaperPackages()"""
alert_replacement = """            .alert(item: $store.alert) { alert in
                Alert(
                    title: Text(language.text(alert.titleKey)),
                    message: Text(alert.message(language: language)),
                    dismissButton: .default(Text(language.text("common.ok")))
                )
            }
            .onAppear {
                reloadWallpaperPackages()"""
if alert_anchor in s and ".alert(item: $store.alert)" not in s:
    s = s.replace(alert_anchor, alert_replacement, 1)
s = s.replace(
    ".disabled(store.isBusy || isWorking)",
    ".disabled(isWorking)",
    1
)

# HTVINTEX keep toggle visible while working
s = s.replace(
    """            if isWorking {
                ProgressView()
                    .controlSize(.small)
                    .frame(width: 48)
            } else if item.isLocked {""",
    """            if item.isLocked {""",
    1
)
s = s.replace(
    """                .labelsHidden()
                .disabled(store.isBusy || isWorking)
                .tint(AppTheme.accent)""",
    """                .labelsHidden()
                .disabled(isWorking)
                .opacity(isWorking ? 0.55 : 1)
                .tint(AppTheme.accent)""",
    1
)
s = s.replace(
    ".disabled(store.isBusy || isWorking)",
    ".disabled(isWorking)",
    1
)
s = s.replace(
    "            for remote in remoteItems where serverCatalog.needsDownload(remote, localItems: store.items) {",
    "            for remote in remoteItems where serverCatalog.needsDownload(remote, localItems: store.items)\n                || serverCatalog.hasSharedLocalBinding(forRemoteID: remote.id) {",
    1
)
s = replace_once(
    s,
    """                    let packageID = try await store.importRemotePackageSilently(
                        from: serverCatalog.downloadURL(for: remote),
                        headers: serverCatalog.requestHeaders,
                        expectedSHA256: remote.sha256,
                        origin: origin
                    )

                    // A new upload may carry a new package UUID. Remove the old
                    // cached package after the replacement has downloaded safely.
                    if let previousLocalID, previousLocalID != packageID {
                        try removeServerManagedPackage(localID: previousLocalID)
                    }

                    serverCatalog.bind(
                        remoteID: remote.id,
                        to: packageID,
                        fingerprint: remote.fingerprint
                    )""",
    """                    let sharedBinding = previousLocalID.map {
                        serverCatalog.isLocalPackageIDShared($0)
                    } ?? false
                    let desiredLocalID = sharedBinding ? UUID() : (previousLocalID ?? UUID())
                    let packageID = try await store.importRemotePackageSilently(
                        from: serverCatalog.downloadURL(for: remote),
                        headers: serverCatalog.requestHeaders,
                        expectedSHA256: remote.sha256,
                        origin: origin,
                        forcedPackageID: desiredLocalID
                    )

                    serverCatalog.bind(
                        remoteID: remote.id,
                        to: packageID,
                        fingerprint: remote.fingerprint
                    )

                    // Migrate old builds where multiple web files shared one UUID.
                    if let previousLocalID,
                       previousLocalID != packageID,
                       !serverCatalog.isLocalPackageIDMapped(previousLocalID) {
                        try removeServerManagedPackage(localID: previousLocalID)
                    }""",
    "unique remote package ID",
    "forcedPackageID: desiredLocalID"
)
# Optimistically reflect the switch immediately, then sync to the receipt.
toggle_func_start = s.index("    private func setServerPatchEnabled")
toggle_func_end = s.index("    private func syncActiveStates", toggle_func_start)
toggle_func = s[toggle_func_start:toggle_func_end]
toggle_marker = """        workingProjectIDs.insert(item.id)

        Task.detached(priority: .userInitiated) {"""
toggle_replacement = """        workingProjectIDs.insert(item.id)

        // Optimistically reflect the switch immediately.
        if enabled {
            activeProjectIDs.insert(item.id)
        } else {
            activeProjectIDs.remove(item.id)
        }

        Task.detached(priority: .userInitiated) {"""
if toggle_marker in toggle_func:
    toggle_func = toggle_func.replace(toggle_marker, toggle_replacement, 1)
s = s[:toggle_func_start] + toggle_func + s[toggle_func_end:]

needle = """                    if let receipt = DevicePatchService.latestReceipt(projectID: item.id) {
                        // The switch is the user's explicit request to turn the patch off.
                        // Restore first, including targets that changed after apply, and only
                        // persist the disabled state after the restore has actually succeeded.
                        try DevicePatchService.restore(
                            receipt: receipt,
                            allowChangedTargets: true
                        )
                    }
                    await MainActor.run {"""
if needle in s:
    s = s.replace(
        needle,
        """                    if DevicePatchService.latestReceipt(projectID: item.id) != nil {
                        try restoreServerPatchFully(projectID: item.id)
                    }
                    await MainActor.run {""",
        1
    )
s = s.replace(
    """                    if !enabled {
                        userDisabledProjectIDs.insert(item.id)
                        saveUserDisabledProjectIDs()
                    }""",
    """                    if !enabled {
                        userDisabledProjectIDs.remove(item.id)
                        saveUserDisabledProjectIDs()
                    }"""
)
sandbox_wait_marker = "    private func syncActiveStates() {"
if "private func waitForSandboxRestoreAccess" not in s:
    helper = """    private func waitForSandboxRestoreAccess(timeout: TimeInterval = 35) throws {
        guard KernelExploit.requiresSandboxEscape else { return }
        if KernelExploit.hasSandboxAccess() { return }

        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if KernelExploit.hasSandboxAccess() { return }
            Thread.sleep(forTimeInterval: 0.20)
        }

        throw PatchPackageError.restoreFailed
    }

"""
    s = s.replace(sandbox_wait_marker, helper + sandbox_wait_marker, 1)

# Only the OFF path needs to wait for recovered access. Keep ON behavior unchanged.
toggle_start = s.index("    private func setServerPatchEnabled")
toggle_end = s.index("    private func syncActiveStates", toggle_start)
toggle_block = s[toggle_start:toggle_end]
old = """                } else {
                    if DevicePatchService.latestReceipt(projectID: item.id) != nil {
                        try restoreServerPatchFully(projectID: item.id)
                    }"""
new = """                } else {
                    try waitForSandboxRestoreAccess()
                    if DevicePatchService.latestReceipt(projectID: item.id) != nil {
                        try restoreServerPatchFully(projectID: item.id)
                    }"""
if old in toggle_block:
    toggle_block = toggle_block.replace(old, new, 1)
s = s[:toggle_start] + toggle_block + s[toggle_end:]

restore_helper_marker = "    private func syncActiveStates() {"
if "private func restoreServerPatchFully(projectID: UUID) throws" not in s:
    helper = """    private func restoreServerPatchFully(projectID: UUID) throws {
        guard let receipt = DevicePatchService.latestReceipt(projectID: projectID) else {
            return
        }
        let inspection = try DevicePatchService.inspectRestore(receipt: receipt)
        try DevicePatchService.restore(
            receipt: receipt,
            allowChangedTargets: !inspection.changedTargets.isEmpty
        )

        guard DevicePatchService.latestReceipt(projectID: projectID) == nil else {
            throw PatchPackageError.restoreFailed
        }
    }

"""
    s = s.replace(restore_helper_marker, helper + restore_helper_marker, 1)

old_sync = """    private func syncActiveStates() {
        activeProjectIDs = Set(
            store.items.compactMap { item in
                guard !userDisabledProjectIDs.contains(item.id) else { return nil }
                return DevicePatchService.latestReceipt(projectID: item.id) == nil ? nil : item.id
            }
        )
    }"""
if old_sync in s:
    s = s.replace(
        old_sync,
        """    private func syncActiveStates() {
        activeProjectIDs = Set(
            store.items.compactMap { item in
                DevicePatchService.latestReceipt(projectID: item.id) == nil ? nil : item.id
            }
        )
    }""",
        1
    )
s = s.replace(
    "try DevicePatchService.restore(receipt: receipt)\n        }\n        if let item = store.items.first",
    "try restoreServerPatchFully(projectID: localID)\n        }\n        if let item = store.items.first",
    1
)
s = s.replace(
    "try DevicePatchService.restore(receipt: receipt, allowChangedTargets: true)\n        }\n        if let item = store.items.first",
    "try restoreServerPatchFully(projectID: localID)\n        }\n        if let item = store.items.first",
    1
)
anchor = """    func localPackageID(forRemoteID id: String) -> UUID? {
        guard let raw = remoteToLocal[id] else { return nil }
        return UUID(uuidString: raw)
    }
"""
if "func hasSharedLocalBinding(forRemoteID id: String)" not in s:
    s = s.replace(
        anchor,
        anchor + """
    func hasSharedLocalBinding(forRemoteID id: String) -> Bool {
        guard let raw = remoteToLocal[id] else { return false }
        return remoteToLocal.values.filter { $0 == raw }.count > 1
    }

    func isLocalPackageIDShared(_ id: UUID) -> Bool {
        let raw = id.uuidString
        return remoteToLocal.values.filter { $0 == raw }.count > 1
    }

    func isLocalPackageIDMapped(_ id: UUID) -> Bool {
        remoteToLocal.values.contains(id.uuidString)
    }
""",
        1
    )
write(rel, s)

# HTVINTEX detail restore auto-second-pass
rel = "ThreeOneOSFive/views/PatchProjectsView.swift"
s = read(rel)

# Hide the legacy tab bar while viewing an individual patch.
detail_title = """.navigationTitle(item?.project?.name ?? language.text("patch.title"))
        .navigationBarTitleDisplayMode(.inline)"""
detail_title_new = """.navigationTitle(item?.project?.name ?? language.text("patch.title"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.hidden, for: .tabBar)"""
if detail_title in s and detail_title_new not in s:
    s = s.replace(detail_title, detail_title_new, 1)

old_prepare = """    private func prepareRestore() {
        guard let receipt else { return }
        isWorking = true
        Task.detached(priority: .userInitiated) {
            do {
                let inspection = try DevicePatchService.inspectRestore(receipt: receipt)
                if inspection.changedTargets.isEmpty {
                    try DevicePatchService.restore(receipt: receipt)
                    await MainActor.run {
                        isWorking = false
                        actionAlert = PatchStoreAlert(
                            titleKey: "common.done",
                            messageKey: "patch.restored_message"
                        )
                    }
                } else {
                    await MainActor.run {
                        isWorking = false
                        restoreChangedPaths = inspection.changedTargets.map(\.displayPath)
                        showChangedRestoreConfirmation = true
                    }
                }
            } catch let error as PatchPackageError {
                await MainActor.run {
                    isWorking = false
                    actionAlert = PatchStoreAlert(
                        titleKey: "common.failed",
                        messageKey: privateErrorKey(for: error),
                        messageArgument: privateErrorArgument(for: error)
                    )
                }
            } catch {
                await MainActor.run {
                    isWorking = false
                    actionAlert = PatchStoreAlert(
                        titleKey: "common.failed",
                        messageKey: "patch.error.restore"
                    )
                }
            }
        }
    }

    private func restore(allowChangedTargets: Bool) {
        guard let receipt else { return }
        isWorking = true
        Task.detached(priority: .userInitiated) {
            do {
                try DevicePatchService.restore(
                    receipt: receipt,
                    allowChangedTargets: allowChangedTargets
                )
                await MainActor.run {
                    isWorking = false
                    actionAlert = PatchStoreAlert(titleKey: "common.done", messageKey: "patch.restored_message")
                }
            } catch let error as PatchPackageError {
                await MainActor.run {
                    isWorking = false
                    actionAlert = PatchStoreAlert(
                        titleKey: "common.failed",
                        messageKey: privateErrorKey(for: error),
                        messageArgument: privateErrorArgument(for: error)
                    )
                }
            } catch {
                await MainActor.run {
                    isWorking = false
                    actionAlert = PatchStoreAlert(titleKey: "common.failed", messageKey: "patch.error.restore")
                }
            }
        }
    }"""

new_prepare = """    private func prepareRestore() {
        // The user already confirmed Restore Originals in the first dialog.
        // This build does not ask for a second confirmation when the first
        // restore pass detects changed targets; it completes the required
        // second restore pass automatically.
        restore(allowChangedTargets: true)
    }

    private func restore(allowChangedTargets: Bool) {
        guard DevicePatchService.latestReceipt(projectID: projectID) != nil else { return }
        isWorking = true
        Task.detached(priority: .userInitiated) {
            do {
                guard let activeReceipt = DevicePatchService.latestReceipt(projectID: projectID) else {
                    await MainActor.run {
                        store.reload()
                        isWorking = false
                    }
                    return
                }
                let inspection = try DevicePatchService.inspectRestore(receipt: activeReceipt)
                try DevicePatchService.restore(
                    receipt: activeReceipt,
                    allowChangedTargets: allowChangedTargets || !inspection.changedTargets.isEmpty
                )

                guard DevicePatchService.latestReceipt(projectID: projectID) == nil else {
                    throw PatchPackageError.restoreFailed
                }

                await MainActor.run {
                    store.reload()
                    isWorking = false
                    actionAlert = PatchStoreAlert(
                        titleKey: "common.done",
                        messageKey: "patch.restored_message"
                    )
                }
            } catch let error as PatchPackageError {
                await MainActor.run {
                    isWorking = false
                    actionAlert = PatchStoreAlert(
                        titleKey: "common.failed",
                        messageKey: privateErrorKey(for: error),
                        messageArgument: privateErrorArgument(for: error)
                    )
                }
            } catch {
                await MainActor.run {
                    isWorking = false
                    actionAlert = PatchStoreAlert(
                        titleKey: "common.failed",
                        messageKey: "patch.error.restore"
                    )
                }
            }
        }
    }"""

if old_prepare in s:
    s = s.replace(old_prepare, new_prepare, 1)
elif "while attempts < 2," not in s[s.index("private struct PatchProjectDetailView"):]:
    raise RuntimeError("Detail restore functions not found")

write(rel, s)

# Server download gets a unique stable local package ID
rel = "ThreeOneOSFive/helpers/PatchProjectStore.swift"
s = read(rel)
if "forcedPackageID: UUID? = nil" not in s:
    s = s.replace(
        """        expectedSHA256: String? = nil,
        origin: PatchPackageOrigin? = nil
    ) async throws -> UUID {""",
        """        expectedSHA256: String? = nil,
        origin: PatchPackageOrigin? = nil,
        forcedPackageID: UUID? = nil
    ) async throws -> UUID {""",
        1
    )
s = replace_once(
    s,
    """        let data = try PatchProjectLibrary.readPackage(at: temporaryURL)
        let summary = try PatchPackageCodec.inspect(data)
        if summary.isPasswordProtected {
            throw PatchPackageError.invalidPasswordOrCorruptedPackage
        }

        let existingURL = items.first(where: { $0.id == summary.packageID })?.packageURL
            ?? PatchProjectLibrary.load().first(where: { $0.id == summary.packageID })?.packageURL

        if let pending = try Self.persistImportedPackage(
            data: data,
            summary: summary,""",
    """        var data = try PatchProjectLibrary.readPackage(at: temporaryURL)
        var summary = try PatchPackageCodec.inspect(data)
        if summary.isPasswordProtected {
            throw PatchPackageError.invalidPasswordOrCorruptedPackage
        }

        if let forcedPackageID, forcedPackageID != summary.packageID {
            let decoded = try PatchPackageCodec.decode(data, password: nil)
            var project = decoded.project
            project.id = forcedPackageID
            project.updatedAt = Date()
            let encoded = try PatchPackageCodec.encodeNew(project: project, password: nil)
            data = encoded.data
            summary = try PatchPackageCodec.inspect(data)
        }

        let existingURL = items.first(where: { $0.id == summary.packageID })?.packageURL
            ?? PatchProjectLibrary.load().first(where: { $0.id == summary.packageID })?.packageURL

        if let pending = try Self.persistImportedPackage(
            data: data,
            summary: summary,""",
    "normalize remote UUID",
    "if let forcedPackageID, forcedPackageID != summary.packageID"
)
write(rel, s)

# Allow alternative server packages with overlapping paths to coexist in library.
# PatchTransaction still blocks applying conflicting alternatives simultaneously.
rel = "ThreeOneOSFive/helpers/PatchProjectLibrary.swift"
s = read(rel)
s = replace_once(
    s,
    """        if let occupiedPath = overlappingTargetPath(
            in: decoded.project,
            excludingPackageID: summary.packageID,
            fileManager: fileManager
        ) {
            if decoded.project.isPrivate, !authorCopy {
                throw PatchPackageError.privateOperationFailed
            }
            throw PatchPackageError.targetOccupied(occupiedPath)
        }""",
    """        let isServerManaged = origin?.repositoryName == "HTVINTEX Server"
        if !isServerManaged, let occupiedPath = overlappingTargetPath(
            in: decoded.project,
            excludingPackageID: summary.packageID,
            fileManager: fileManager
        ) {
            if decoded.project.isPrivate, !authorCopy {
                throw PatchPackageError.privateOperationFailed
            }
            throw PatchPackageError.targetOccupied(occupiedPath)
        }""",
    "server alternatives overlap",
    'let isServerManaged = origin?.repositoryName == "HTVINTEX Server"'
)
write(rel, s)

print("HTVINTEX navigation / restore / independent-toggle patch applied")
