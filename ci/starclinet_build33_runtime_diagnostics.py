#!/usr/bin/env python3
"""Read-only iOS & dyld diagnostics; no external process injection or bypass."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/"ThreeOneOSFive/views/SettingsView.swift"
s=p.read_text()
assert "StarclinetRuntimeStatusView" not in s
s=s.replace("    @State private var checking = false",
            "    @State private var checking = false\n    @State private var showRuntimeStatus = false",1)
marker='                                settingsRow(icon: "iphone.gen3", title: "การรองรับอุปกรณ์", detail: appState.isSupported ? "รองรับการใช้งาน" : "ควรตรวจสอบความเข้ากันได้", status: appState.isSupported)'
assert marker in s
insert='''
                                dividingLine
                                Button { showRuntimeStatus = true } label: {
                                    HStack {
                                        Image(systemName: "waveform.path.ecg").foregroundStyle(orange)
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text("ตรวจระบบ iOS และ Dylib").font(.subheadline.weight(.semibold)).foregroundStyle(.white)
                                            Text("ตรวจไฟล์และการโหลดจริง").font(.caption).foregroundStyle(.secondary)
                                        }
                                        Spacer()
                                        Image(systemName: "chevron.right").foregroundStyle(.secondary)
                                    }.padding(15)
                                }
                                .buttonStyle(.plain)
                                .sheet(isPresented: $showRuntimeStatus) { StarclinetRuntimeStatusView() }
'''
s=s.replace(marker,marker+insert,1)
s+=r'''

// Build 33 first-party diagnostics. These functions inspect process images; they never load a dylib.
@_silgen_name("_dyld_image_count") private func starDyldCount() -> UInt32
@_silgen_name("_dyld_get_image_name") private func starDyldName(_ index: UInt32) -> UnsafePointer<CChar>?

private struct StarclinetLibStatus: Identifiable {
    let name: String
    let exists: Bool
    let loaded: Bool
    var id: String { name }
}

private struct StarclinetRuntimeStatus {
    let os: String
    let build: String
    let verifiedAdvancedAccess: Bool
    let libs: [StarclinetLibStatus]

    static func capture() -> Self {
        let folder = Bundle.main.privateFrameworksPath ?? Bundle.main.bundlePath + "/Frameworks"
        let count = starDyldCount()
        var paths: [String] = []
        for index in 0..<count {
            if let pointer = starDyldName(index) { paths.append(String(cString: pointer)) }
        }
        let version = AppInfo.versionTuple
        let verified = ExploitSupportPolicy.isSupported(major: version.major, minor: version.minor, patch: version.patch, build: AppInfo.osBuild)
        let libraries = ["LoadControl.dylib", "libsubstrate.dylib", "bypass.dylib"].map { file in
            StarclinetLibStatus(
                name: file,
                exists: FileManager.default.fileExists(atPath: (folder as NSString).appendingPathComponent(file)),
                loaded: paths.contains(where: { $0.hasSuffix("/" + file) })
            )
        }
        return .init(os: AppInfo.osVersion, build: AppInfo.osBuild, verifiedAdvancedAccess: verified, libs: libraries)
    }

    var report: String {
        let items = libs.map { "\($0.name): file=\($0.exists), loaded=\($0.loaded)" }.joined(separator: "\n")
        return "STARCLINET\nOS: iOS \(os) (\(build))\nVerified advanced access: \(verifiedAdvancedAccess)\n\(items)\nLoaded does not prove that plugin features work."
    }
}

private struct StarclinetRuntimeStatusView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var status = StarclinetRuntimeStatus.capture()

    var body: some View {
        NavigationStack {
            List {
                Section("ระบบปฏิบัติการ") {
                    LabeledContent("iOS", value: status.os)
                    LabeledContent("Build", value: status.build)
                    LabeledContent("การเข้าถึงขั้นสูง", value: status.verifiedAdvancedAccess ? "มีรายการรองรับ" : "ยังไม่ยืนยัน")
                }
                Section("ไลบรารีภายในแอป") {
                    ForEach(status.libs) { lib in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(lib.name).font(.headline)
                            Text("ไฟล์: \(lib.exists ? "มี" : "ไม่พบ") • โหลดแล้ว: \(lib.loaded ? "ใช่" : "ไม่")")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                Section {
                    Text("สถานะโหลดไม่ได้รับรองการทำงานของ Plugin และไม่เปลี่ยนข้อจำกัดระบบ iOS")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Section {
                    Button("ตรวจอีกครั้ง") { status = .capture() }
                    Button("คัดลอกรายงาน") { UIPasteboard.general.string = status.report }
                }
            }
            .navigationTitle("iOS / Dylib")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("ปิด") { dismiss() } } }
        }
        .preferredColorScheme(.dark)
    }
}
'''
p.write_text(s)
print("Build 33 diagnostics injected into",p)
