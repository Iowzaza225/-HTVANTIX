from pathlib import Path
import sys

root = Path(sys.argv[1])
p = root / "ThreeOneOSFive/views/PatchProjectsView.swift"
s = p.read_text()

old = """            for remote in remoteItems where serverCatalog.needsDownload(remote, localItems: store.items)
                || serverCatalog.hasSharedLocalBinding(forRemoteID: remote.id) {
                do {
                    let previousLocalID = serverCatalog.localPackageID(forRemoteID: remote.id)
                    let origin = PatchPackageOrigin(
                        repositoryName: "HTVINTEX Server",
                        repositoryURL: serverCatalog.baseURL,
                        packageIdentifier: remote.id
                    )
                    // Preserve this row's existing unique local id. Old builds
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
                    }
                } catch {
                    warnings.append("\\(remote.name): \\(error.localizedDescription)")
                }
            }"""

new = """            // Process every missing/changed server row independently. A failure in
            // one row must never leave the other rows sharing its loading state.
            for remote in remoteItems {
                let mustDownload = serverCatalog.needsDownload(remote, localItems: store.items)
                    || serverCatalog.hasSharedLocalBinding(forRemoteID: remote.id)
                guard mustDownload else { continue }

                let previousLocalID = serverCatalog.localPackageID(forRemoteID: remote.id)
                let previousWasShared = previousLocalID.map {
                    serverCatalog.isLocalPackageIDShared($0)
                } ?? false
                let desiredLocalID = (previousLocalID != nil && !previousWasShared)
                    ? previousLocalID!
                    : UUID()
                let origin = PatchPackageOrigin(
                    repositoryName: "HTVINTEX Server",
                    repositoryURL: serverCatalog.baseURL,
                    packageIdentifier: remote.id
                )

                var lastError: Error?
                var installedID: UUID?
                for attempt in 1...3 {
                    do {
                        installedID = try await store.importRemotePackageSilently(
                            from: serverCatalog.downloadURL(for: remote),
                            headers: serverCatalog.requestHeaders,
                            expectedSHA256: remote.sha256,
                            origin: origin,
                            forcedPackageID: desiredLocalID
                        )
                        lastError = nil
                        break
                    } catch {
                        lastError = error
                        if attempt < 3 {
                            try? await Task.sleep(nanoseconds: 350_000_000)
                        }
                    }
                }

                if let packageID = installedID {
                    serverCatalog.bind(
                        remoteID: remote.id,
                        to: packageID,
                        fingerprint: remote.fingerprint
                    )
                    store.reload()

                    if let previousLocalID,
                       previousLocalID != packageID,
                       !serverCatalog.isLocalPackageIDMapped(previousLocalID) {
                        try? removeServerManagedPackage(localID: previousLocalID)
                    }
                } else if let lastError {
                    warnings.append("\\(remote.name): \\(lastError.localizedDescription)")
                }
            }"""

if old not in s:
    raise RuntimeError("expected remote import loop not found")
s = s.replace(old, new, 1)
p.write_text(s)
print("Applied robust independent server-row download/import fix")
