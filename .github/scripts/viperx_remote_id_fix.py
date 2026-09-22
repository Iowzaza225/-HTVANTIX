from pathlib import Path
import sys

root = Path(sys.argv[1])
p = root / "ThreeOneOSFive/views/PatchProjectsView.swift"
s = p.read_text(encoding="utf-8")

old_struct = """    struct RemoteItem: Identifiable, Hashable {
        let id: String
        let name: String"""
new_struct = """    struct RemoteItem: Identifiable, Hashable {
        // id is the unique client-side row/binding key.
        // serverID is the original server package id used only for download.
        let id: String
        let serverID: String
        let name: String"""

old_url = """.appendingPathComponent("api/v4/packages")
            .appendingPathComponent(item.id)
            .appendingPathComponent("download")"""
new_url = """.appendingPathComponent("api/v4/packages")
            .appendingPathComponent(item.serverID)
            .appendingPathComponent("download")"""

old_parse = """        return rawItems.compactMap { object in
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
                fileName: stringValue(object["fileName"] ?? object["filename"]) ?? "\\(id).3105",
                sizeBytes: intValue(object["sizeBytes"]),
                sha256: stringValue(object["sha256"])
            )
        }"""

new_parse = """        var seen: [String: Int] = [:]
        return rawItems.compactMap { object in
            let enabled = (object["enabled"] as? Bool) ?? (object["active"] as? Bool) ?? true
            guard enabled else { return nil }
            guard let serverID = stringValue(object["id"] ?? object["packageId"] ?? object["_id"]),
                  !serverID.isEmpty else { return nil }

            let name = stringValue(object["name"] ?? object["title"]) ?? "Patch"
            let fileName = stringValue(object["fileName"] ?? object["filename"]) ?? "\\(serverID).3105"
            let occurrence = seen[serverID, default: 0]
            seen[serverID] = occurrence + 1
            // Keep the first key backward-compatible. Duplicate server IDs get
            // a deterministic independent key so they cannot share local state.
            let clientID = occurrence == 0
                ? serverID
                : "\\(serverID)#\\(occurrence)|\\(fileName)|\\(name)"

            return RemoteItem(
                id: clientID,
                serverID: serverID,
                name: name,
                description: stringValue(object["description"]) ?? "",
                version: stringValue(object["version"]) ?? "1.0",
                game: stringValue(object["game"]),
                category: stringValue(object["category"]) ?? "other",
                fileName: fileName,
                sizeBytes: intValue(object["sizeBytes"]),
                sha256: stringValue(object["sha256"])
            )
        }"""

for label, old, new in [
    ("RemoteItem", old_struct, new_struct),
    ("downloadURL", old_url, new_url),
    ("parseCatalog", old_parse, new_parse),
]:
    if old not in s:
        raise SystemExit(f"Expected {label} source block not found; refusing partial patch")
    s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("Applied VIPERX remote ID isolation fix:", p)
