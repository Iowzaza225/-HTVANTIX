from pathlib import Path
import sys

root = Path(sys.argv[1])

def read(rel):
    return (root / rel).read_text()

def write(rel, s):
    (root / rel).write_text(s)

# Keep each server catalog entry bound by the package UUID that actually comes
# from the server package. Do NOT decode/re-encode a downloaded .3105 just to
# invent another UUID on-device.
#
# We still re-download an old shared binding once, because older builds could
# point more than one remote catalog id at the same local package id.

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

new_import = """                    let packageID = try await store.importRemotePackageSilently(
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

# Replace either the stable block or the previous forced-ID block.
if "forcedPackageID: desiredLocalID" in s:
    forced_start = s.index("                    let sharedBinding = previousLocalID.map {")
    forced_end_marker = """                    if let previousLocalID,
                       previousLocalID != packageID,
                       !serverCatalog.isLocalPackageIDMapped(previousLocalID) {
                        try removeServerManagedPackage(localID: previousLocalID)
                    }"""
    forced_end = s.index(forced_end_marker, forced_start) + len(forced_end_marker)
    s = s[:forced_start] + new_import + s[forced_end:]
elif "Trust the package UUID delivered by the website." not in s:
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

    func isLocalPackageIDMapped(_ id: UUID) -> Bool {
        remoteToLocal.values.contains(id.uuidString)
    }
"""
if "func hasSharedLocalBinding(forRemoteID id: String)" not in s:
    if anchor not in s:
        raise RuntimeError("server binding helper anchor not found")
    s = s.replace(anchor, anchor + helpers, 1)
else:
    # Remove the old helper that existed only for forced on-device UUIDs.
    shared_helper = """    func isLocalPackageIDShared(_ id: UUID) -> Bool {
        let raw = id.uuidString
        return remoteToLocal.values.filter { $0 == raw }.count > 1
    }

"""
    s = s.replace(shared_helper, "", 1)

write(rel, s)

# Server-managed alternatives may legitimately target the same game file.
# Keep the import-time overlap exception; apply/restore logic remains unchanged.
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

print("UI V2 remote package binding now trusts website package IDs")
