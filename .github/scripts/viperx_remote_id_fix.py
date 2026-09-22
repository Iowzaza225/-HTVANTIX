from pathlib import Path
import sys

root = Path(sys.argv[1])
p = root / "ThreeOneOSFive/views/PatchProjectsView.swift"
s = p.read_text(encoding="utf-8")

repls = [
("""    struct RemoteItem: Identifiable, Hashable {
        let id: String
        let name: String""",
"""    struct RemoteItem: Identifiable, Hashable {
        let id: String
        let serverID: String
        let name: String"""),
("""            .appendingPathComponent("api/v4/packages")
            .appendingPathComponent(item.id)
            .appendingPathComponent("download")""",
"""            .appendingPathComponent("api/v4/packages")
            .appendingPathComponent(item.serverID)
            .appendingPathComponent("download")"""),
("""        return rawItems.compactMap { object in
            let enabled = (object["enabled"] as? Bool) ?? (object["active"] as? Bool) ?? true
            guard enabled else { return nil }
            guard let id = stringValue(object["id"] ?? object["packageId"] ?? object["_id"]),
                  !id.isEmpty else { return nil }

            return RemoteItem(
                id: id,
                name: stringValue(object["name"] ?? object["title"]) ?? "Patch",
                description: stringValue(object["description"]) ?? "",
                version: stringValue(object["version"]) ?? "1.0",
                game: stringValue(object["game"]),
                category: stringValue(object["category"]) ?? "other",
                fileName: stringValue(object["fileName"] ?? object["filename"]) ?? "\(id).3105",
                sizeBytes: intValue(object["sizeBytes"]),
                sha256: stringValue(object["sha256"])
            )
        }""",
"""        // Preserve the server id for the download endpoint, while each
        // catalog row gets a unique client identity for local binding.
        var seen: [String: Int] = [:]
        return rawItems.compactMap { object in
            let enabled = (object["enabled"] as? Bool) ?? (object["active"] as? Bool) ?? true
            guard enabled else { return nil }
            guard let serverID = stringValue(object["id"] ?? object["packageId"] ?? object["_id"]),
                  !serverID.isEmpty else { return nil }

            let fileName = stringValue(object["fileName"] ?? object["filename"]) ?? "\(serverID).3105"
            let occurrence = seen[serverID, default: 0]
            seen[serverID] = occurrence + 1
            let clientID = occurrence == 0 ? serverID : "\(serverID)#\(occurrence):\(fileName)"

            return RemoteItem(
                id: clientID,
                serverID: serverID,
                name: stringValue(object["name"] ?? object["title"]) ?? "Patch",
                description: stringValue(object["description"]) ?? "",
                version: stringValue(object["version"]) ?? "1.0",
                game: stringValue(object["game"]),
                category: stringValue(object["category"]) ?? "other",
                fileName: fileName,
                sizeBytes: intValue(object["sizeBytes"]),
                sha256: stringValue(object["sha256"])
            )
        }""")
]

for old,new in repls:
    if old not in s:
        raise SystemExit("Expected source block not found; refusing partial patch")
    s=s.replace(old,new,1)

p.write_text(s,encoding="utf-8")
print("Applied VIPERX remote ID isolation fix:", p)
