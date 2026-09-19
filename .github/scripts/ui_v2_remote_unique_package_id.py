from pathlib import Path
import sys

root = Path(sys.argv[1])

def read(rel):
    return (root / rel).read_text()

def write(rel, s):
    (root / rel).write_text(s)

# Each website catalog row needs its own local project UUID.
# The website's remote.id is still the row identity, but older .3105 files may
# contain the same internal project UUID. If we import those bytes unchanged,
# the last downloaded package replaces the earlier one and every row opens the
# same patch. Normalize ONLY the local cached copy to a unique UUID per row.

# ---------------------------------------------------------------------------
# PatchProjectStore: optional local UUID override for server-managed imports.
# ---------------------------------------------------------------------------
rel = "ThreeOneOSFive/helpers/PatchProjectStore.swift"
s = read(rel)

if "forcedPackageID: UUID? = nil" not in s:
    old_sig = """        expectedSHA256: String? = nil,
        origin: PatchPackageOrigin? = nil
    ) async throws -> UUID {"""
    new_sig = """        expectedSHA256: String? = nil,
        origin: PatchPackageOrigin? = nil,
        forcedPackageID: UUID? = nil
    ) async throws -> UUID {"""
    if old_sig not in s:
        raise RuntimeError("importRemotePackageSilently signature not found")
    s = s.replace(old_sig, new_sig, 1)

old_read = """        let data = try PatchProjectLibrary.readPackage(at: temporaryURL)
        let summary = try PatchPackageCodec.inspect(data)
        if summary.isPasswordProtected {
            throw PatchPackageError.invalidPasswordOrCorruptedPackage
        }
"""
new_read = """        var data = try PatchProjectLibrary.readPackage(at: temporaryURL)
        var summary = try PatchPackageCodec.inspect(data)
        if summary.isPasswordProtected {
            throw PatchPackageError.invalidPasswordOrCorruptedPackage
        }

        // The server catalog id and the package's embedded project id are
        // different namespaces. Keep the downloaded payload intact until after
        // checksum validation, then rewrite only the cached local project's id.
        if let forcedPackageID, forcedPackageID != summary.packageID {
            let decoded = try PatchPackageCodec.decode(data, password: nil)
            var project = decoded.project
            project.id = forcedPackageID
            project.updatedAt = Date()
            let encoded = try PatchPackageCodec.encodeNew(project: project, password: nil)
            data = encoded.data
            summary = try PatchPackageCodec.inspect(data)
        }
"""
if "if let forcedPackageID, forcedPackageID != summary.packageID" not in s:
    if old_read not in s:
        raise RuntimeError("downloaded package read block not found")
    s = s.replace(old_read, new_read, 1)

write(rel, s)

# ---------------------------------------------------------------------------
# PatchProjectsView: every remote row gets a stable unique local UUID.
# Existing unique bindings stay stable. Legacy shared bindings are migrated by
# redownloading just those rows once and assigning fresh ids.
# ---------------------------------------------------------------------------
rel = "ThreeOneOSFive/views/PatchProjectsView.swift"
s = read(rel)

# Ensure shared legacy bindings are redownloaded.
old_loop = "            for remote in remoteItems where serverCatalog.needsDownload(remote, localItems: store.items) {"
new_loop = """            for remote in remoteItems where serverCatalog.needsDownload(remote, localItems: store.items)
                || serverCatalog.hasSharedLocalBinding(forRemoteID: remote.id) {"""
if new_loop not in s:
    if old_loop in s:
        s = s.replace(old_loop, new_loop, 1)

# Replace the current trust-server import block with local UUID normalization.
trust_start = """                    let packageID = try await store.importRemotePackageSilently(
                        from: serverCatalog.downloadURL(for: remote),
                        headers: serverCatalog.requestHeaders,
                        expectedSHA256: remote.sha256,
                        origin: origin
                    )

                    // Trust the package UUID delivered by the website. The web
                    // backend already gives every catalog item its own identity.
                    // Bind only after the package was downloaded and imported.
                    serverCatalog.bind(
                        remoteID: remote.id,
                        to: packageID,
                        fingerprint: remote.fingerprint
                    )

                    // If this download replaced an older local package, remove it
                    // only after no other remote item still references that UUID.
                    if let previousLocalID,
                       previousLocalID != packageID,
                       !serverCatalog.isLocalPackageIDMapped(previousLocalID) {
                        try removeServerManagedPackage(localID: previousLocalID)
                    }"""

stable_start = """                    let packageID = try await store.importRemotePackageSilently(
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
                    )"""

unique_block = """                    // Preserve this row's existing unique local id. Old builds
                    // could bind several remote rows to one embedded package id;
                    // migrate those rows to fresh ids one time.
                    let previousWasShared = previousLocalID.map {
                        serverCatalog.isLocalPackageIDShared($0)
                    } ?? false
                    let desiredLocalID: UUID
                    if let previousLocalID, !previousWasShared {
                        desiredLocalID = previousLocalID
                    } else {
                        desiredLocalID = UUID()
                    }

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

                    // Delete a superseded cache only when no other website row
                    // references it. Never delete another row's package.
                    if let previousLocalID,
                       previousLocalID != packageID,
                       !serverCatalog.isLocalPackageIDMapped(previousLocalID) {
                        try removeServerManagedPackage(localID: previousLocalID)
                    }"""

if "forcedPackageID: desiredLocalID" not in s:
    if trust_start in s:
        s = s.replace(trust_start, unique_block, 1)
    elif stable_start in s:
        s = s.replace(stable_start, unique_block, 1)
    else:
        raise RuntimeError("remote package import block not found")

anchor = """    func localPackageID(forRemoteID id: String) -> UUID? {
        guard let raw = remoteToLocal[id] else { return nil }
        return UUID(uuidString: raw)
    }
"""
helpers = """
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
"""
if "func isLocalPackageIDShared(_ id: UUID)" not in s:
    if "func hasSharedLocalBinding(forRemoteID id: String)" in s:
        # Insert only the missing shared-local helper next to the existing helpers.
        marker = """    func hasSharedLocalBinding(forRemoteID id: String) -> Bool {
        guard let raw = remoteToLocal[id] else { return false }
        return remoteToLocal.values.filter { $0 == raw }.count > 1
    }
"""
        if marker not in s:
            raise RuntimeError("shared binding helper shape not found")
        s = s.replace(
            marker,
            marker + """
    func isLocalPackageIDShared(_ id: UUID) -> Bool {
        let raw = id.uuidString
        return remoteToLocal.values.filter { $0 == raw }.count > 1
    }

""",
            1
        )
    else:
        if anchor not in s:
            raise RuntimeError("catalog localPackageID helper anchor not found")
        s = s.replace(anchor, anchor + helpers, 1)

write(rel, s)

print("Remote catalog packages isolated by unique stable local UUID")
