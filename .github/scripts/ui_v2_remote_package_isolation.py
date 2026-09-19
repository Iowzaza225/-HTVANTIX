from pathlib import Path
import sys

root = Path(sys.argv[1])

def read(rel):
    return (root / rel).read_text()

def write(rel, s):
    (root / rel).write_text(s)

# Keep every server catalog item bound to its own local package UUID.
# Older builds could bind multiple remote files to the same UUID, which made
# activating one row appear to activate every row.

rel = "ThreeOneOSFive/views/PatchProjectsView.swift"
s = read(rel)

old_loop = "            for remote in remoteItems where serverCatalog.needsDownload(remote, localItems: store.items) {"
new_loop = """            for remote in remoteItems where serverCatalog.needsDownload(remote, localItems: store.items)
                || serverCatalog.hasSharedLocalBinding(forRemoteID: remote.id) {"""
if new_loop not in s:
    if old_loop not in s:
        raise RuntimeError("remote download loop not found")
    s = s.replace(old_loop, new_loop, 1)

old_import = """                    let packageID = try await store.importRemotePackageSilently(
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

new_import = """                    let sharedBinding = previousLocalID.map {
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

                    // Migration from old builds: only remove the old package after
                    // no other remote catalog entry still points at that UUID.
                    if let previousLocalID,
                       previousLocalID != packageID,
                       !serverCatalog.isLocalPackageIDMapped(previousLocalID) {
                        try removeServerManagedPackage(localID: previousLocalID)
                    }"""

if "forcedPackageID: desiredLocalID" not in s:
    if old_import not in s:
        raise RuntimeError("remote import block not found")
    s = s.replace(old_import, new_import, 1)

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
if "func hasSharedLocalBinding(forRemoteID id: String)" not in s:
    if anchor not in s:
        raise RuntimeError("server binding helper anchor not found")
    s = s.replace(anchor, anchor + helpers, 1)

write(rel, s)

# Allow the remote importer to assign a stable local UUID per catalog item.
rel = "ThreeOneOSFive/helpers/PatchProjectStore.swift"
s = read(rel)

old_sig = """        expectedSHA256: String? = nil,
        origin: PatchPackageOrigin? = nil
    ) async throws -> UUID {"""
new_sig = """        expectedSHA256: String? = nil,
        origin: PatchPackageOrigin? = nil,
        forcedPackageID: UUID? = nil
    ) async throws -> UUID {"""
if "forcedPackageID: UUID? = nil" not in s:
    if old_sig not in s:
        raise RuntimeError("importRemotePackageSilently signature not found")
    s = s.replace(old_sig, new_sig, 1)

old_decode = """        let data = try PatchProjectLibrary.readPackage(at: temporaryURL)
        let summary = try PatchPackageCodec.inspect(data)
        if summary.isPasswordProtected {
            throw PatchPackageError.invalidPasswordOrCorruptedPackage
        }

        let existingURL = items.first(where: { $0.id == summary.packageID })?.packageURL
            ?? PatchProjectLibrary.load().first(where: { $0.id == summary.packageID })?.packageURL
"""

new_decode = """        var data = try PatchProjectLibrary.readPackage(at: temporaryURL)
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
"""
if "if let forcedPackageID, forcedPackageID != summary.packageID" not in s:
    if old_decode not in s:
        raise RuntimeError("remote decode/import block not found")
    s = s.replace(old_decode, new_decode, 1)

write(rel, s)

# Server-managed alternatives may target the same game file, but they still need
# separate library entries. Apply-time validation remains unchanged.
rel = "ThreeOneOSFive/helpers/PatchProjectLibrary.swift"
s = read(rel)

old_overlap = """        if let occupiedPath = overlappingTargetPath(
            in: decoded.project,
            excludingPackageID: summary.packageID,
            fileManager: fileManager
        ) {
            if decoded.project.isPrivate, !authorCopy {
                throw PatchPackageError.privateOperationFailed
            }
            throw PatchPackageError.targetOccupied(occupiedPath)
        }"""

new_overlap = """        let isServerManaged = origin?.repositoryName == "HTVINTEX Server"
        if !isServerManaged, let occupiedPath = overlappingTargetPath(
            in: decoded.project,
            excludingPackageID: summary.packageID,
            fileManager: fileManager
        ) {
            if decoded.project.isPrivate, !authorCopy {
                throw PatchPackageError.privateOperationFailed
            }
            throw PatchPackageError.targetOccupied(occupiedPath)
        }"""

if 'let isServerManaged = origin?.repositoryName == "HTVINTEX Server"' not in s:
    if old_overlap not in s:
        raise RuntimeError("overlap validation block not found")
    s = s.replace(old_overlap, new_overlap, 1)

write(rel, s)

print("UI V2 remote package isolation applied")
