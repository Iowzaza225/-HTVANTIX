from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / "ThreeOneOSFive" / "views" / "PatchProjectsView.swift"
s = path.read_text()

# Keep download failures visible instead of leaving a permanent spinner.
state_anchor = "    @State private var needsRefilingProjectIDs: Set<UUID> = []\n"
state_line = "    @State private var serverDownloadFailures: [String: String] = [:]\n"
if state_line not in s:
    if state_anchor not in s:
        raise RuntimeError("state anchor not found")
    s = s.replace(state_anchor, state_anchor + state_line, 1)

# Each explicit catalog refresh is a fresh retry cycle.
load_anchor = "            let remoteItems = try await serverCatalog.load()\n"
load_extra = "            serverDownloadFailures = [:]\n"
if load_extra not in s:
    if load_anchor not in s:
        raise RuntimeError("catalog load anchor not found")
    s = s.replace(load_anchor, load_anchor + load_extra, 1)

# Clear any previous failure as soon as one package imports successfully.
bind_anchor = """                    serverCatalog.bind(
                        remoteID: remote.id,
                        to: packageID,
                        fingerprint: remote.fingerprint
                    )
"""
bind_with_clear = bind_anchor + "                    serverDownloadFailures[remote.id] = nil\n"
if bind_with_clear not in s:
    if bind_anchor not in s:
        raise RuntimeError("bind anchor not found")
    s = s.replace(bind_anchor, bind_with_clear, 1)

# Record the real failure reason per remote package.
old_catch = """                } catch {
                    warnings.append("\(remote.name): \(error.localizedDescription)")
                }
"""
new_catch = """                } catch {
                    let message = error.localizedDescription
                    serverDownloadFailures[remote.id] = message
                    warnings.append("\(remote.name): \(message)")
                }
"""
if new_catch not in s:
    if old_catch not in s:
        raise RuntimeError("download catch block not found")
    s = s.replace(old_catch, new_catch, 1)

start = s.find("    @ViewBuilder\n    private func serverPendingRow")
end = s.find("\n    @ViewBuilder\n    private func serverPatchRow", start)
if start < 0 or end < 0:
    raise RuntimeError("serverPendingRow block not found")

new_pending = r'''    @ViewBuilder
    private func serverPendingRow(_ remote: PatchServerCatalog.RemoteItem) -> some View {
        let failure = serverDownloadFailures[remote.id]

        HStack(spacing: 12) {
            AppRowIcon(
                systemName: failure == nil ? "arrow.down.circle.fill" : "exclamationmark.triangle.fill",
                tint: failure == nil ? AppTheme.accent : .orange,
                frameSize: 42
            )

            VStack(alignment: .leading, spacing: 4) {
                Text(remote.name)
                    .font(.headline.weight(.bold))
                    .foregroundStyle(.white)
                    .lineLimit(1)

                Text("\(serverCatalog.gameTitle(remote.game)) • \(serverCatalog.categoryTitle(remote.category))")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                if let failure {
                    Text("โหลดไฟล์ไม่สำเร็จ")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(.orange)

                    Text(failure)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                } else {
                    Text("กำลังเตรียมไฟล์…")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(AppTheme.accent)
                }
            }

            Spacer(minLength: 8)

            if failure != nil {
                Button {
                    Task { await refreshServerCatalog() }
                } label: {
                    Text("ลองใหม่")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(AppTheme.accent)
                        .padding(.horizontal, 12)
                        .frame(height: 34)
                        .background(
                            Capsule()
                                .fill(AppTheme.accent.opacity(0.12))
                        )
                        .overlay(
                            Capsule()
                                .stroke(AppTheme.accent.opacity(0.35), lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
                .disabled(serverCatalog.isLoading)
            } else {
                ProgressView()
                    .controlSize(.small)
            }
        }
        .htvCard(padding: 14, accent: failure == nil ? AppTheme.accent : .orange)
        .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
        .listRowBackground(Color.clear)
        .listRowSeparator(.hidden)
    }
'''

s = s[:start] + new_pending + s[end:]
path.write_text(s)
print("UI V2 download-state diagnostics/retry patch applied")
