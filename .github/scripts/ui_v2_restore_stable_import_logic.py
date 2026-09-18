from pathlib import Path
import sys

root = Path(sys.argv[1])

def read(rel):
    return (root / rel).read_text()

def write(rel, s):
    (root / rel).write_text(s)

# 1) Restore the pre-UI remote-package import API: do NOT decode/re-encode
# downloaded .3105 packages just to force a new package UUID.
rel = "ThreeOneOSFive/helpers/PatchProjectStore.swift"
s = read(rel)
s = s.replace(
"""        expectedSHA256: String? = nil,
        origin: PatchPackageOrigin? = nil,
        forcedPackageID: UUID? = nil
""",
"""        expectedSHA256: String? = nil,
        origin: PatchPackageOrigin? = nil
""",
1
)
forced = """        if let forcedPackageID, forcedPackageID != summary.packageID {
            let decoded = try PatchPackageCodec.decode(data, password: nil)
            var project = decoded.project
            project.id = forcedPackageID
            project.updatedAt = Date()
            let encoded = try PatchPackageCodec.encodeNew(project: project, password: nil)
            data = encoded.data
            summary = try PatchPackageCodec.inspect(data)
        }

"""
s = s.replace(forced, "", 1)
s = s.replace(
"        var data = try PatchProjectLibrary.readPackage(at: temporaryURL)\n        var summary = try PatchPackageCodec.inspect(data)\n",
"        let data = try PatchProjectLibrary.readPackage(at: temporaryURL)\n        let summary = try PatchPackageCodec.inspect(data)\n",
1
)
write(rel, s)

# 2) Restore the original overlap validation used by the known-good build.
rel = "ThreeOneOSFive/helpers/PatchProjectLibrary.swift"
s = read(rel)
s = s.replace(
"""        let isServerManaged = origin?.repositoryName == "HTVINTEX Server"
        if !isServerManaged, let occupiedPath = overlappingTargetPath(
""",
"""        if let occupiedPath = overlappingTargetPath(
""",
1
)
write(rel, s)

# 3) Restore ONLY the remote catalog download/import/binding routine from the
# pre-UI stable source. Leave all UI V2 rendering/layout code intact.
rel = "ThreeOneOSFive/views/PatchProjectsView.swift"
s = read(rel)
start = s.index("    private func refreshServerCatalog() async {")
end = s.index("\n    @MainActor\n    private func removeServerManagedPackage", start)

stable_refresh = r'''    private func refreshServerCatalog() async {
        do {
            // Server metadata/download endpoints use a short-lived client session.
            // Renew it before every explicit catalog sync so Installed keeps working
            // even after the app has been open longer than the session TTL.
            await licenseManager.bootstrap(forceSessionRefresh: true)
            guard licenseManager.isAuthorized else {
                throw PatchServerError.sessionRequired
            }

            let remoteItems = try await serverCatalog.load()
            var warnings: [String] = []
            let activeRemoteIDs = Set(remoteItems.map(\.id))

            // If an admin disables/removes a server package, restore any active
            // patch first and remove its cached local copy. This prevents a
            // server-hidden package from remaining active on the device.
            for stale in serverCatalog.staleBindings(activeRemoteIDs: activeRemoteIDs) {
                do {
                    try removeServerManagedPackage(localID: stale.localID)
                    serverCatalog.unbind(remoteID: stale.remoteID)
                } catch {
                    warnings.append("ล้างไฟล์เก่าไม่สำเร็จ: \(error.localizedDescription)")
                }
            }

            for remote in remoteItems where serverCatalog.needsDownload(remote, localItems: store.items) {
                do {
                    let previousLocalID = serverCatalog.localPackageID(forRemoteID: remote.id)
                    let origin = PatchPackageOrigin(
                        repositoryName: "HTVINTEX Server",
                        repositoryURL: serverCatalog.baseURL,
                        packageIdentifier: remote.id
                    )
                    let packageID = try await store.importRemotePackageSilently(
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
                    )
                } catch {
                    warnings.append("\(remote.name): \(error.localizedDescription)")
                }
            }

            store.reload()
            serverCatalog.finishSync(warning: warnings.first)
            syncActiveStates()
        } catch {
            serverCatalog.fail(error)
        }
    }
'''
s = s[:start] + stable_refresh + s[end:]
write(rel, s)

print("Restored pre-UI stable remote package import/binding logic; UI V2 preserved")
