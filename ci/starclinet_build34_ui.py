#!/usr/bin/env python3
"""STARCLINET Build34: first-party pairing UI, native status, no unverified exploit claims."""
from pathlib import Path
import sys
root=Path(sys.argv[1]); p=root/"ThreeOneOSFive/views/SettingsView.swift"; s=p.read_text()
anchor='    @State private var checking = false'
if s.count(anchor)!=1: raise SystemExit("Settings state anchor changed")
s=s.replace(anchor,anchor+'''
    @State private var showPairing = false
    @State private var showCompatibility = false''',1)
old='settingsRow(icon: "iphone.gen3", title: "การรองรับอุปกรณ์", detail: appState.isSupported ? "รองรับการใช้งาน" : "ควรตรวจสอบความเข้ากันได้", status: appState.isSupported)'
if s.count(old)!=1: raise SystemExit("Settings system row changed")
new='''settingsRow(icon: "iphone.gen3", title: "การเข้าถึงขั้นสูง", detail: appState.isSupported ? "รองรับตามรายการเดิม" : "ยังไม่ยืนยัน — ตรวจเป็นขั้นตอน", status: appState.isSupported)
                                dividingLine
                                Button { showPairing = true } label: {
                                    HStack(spacing: 13) {
                                        Image(systemName: "network.badge.shield.half.filled")
                                            .font(.system(size: 19)).foregroundStyle(orange)
                                            .frame(width: 38, height: 38)
                                            .background(orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text("AirLift • Pairing / RSD").foregroundStyle(.white)
                                                .font(.subheadline.weight(.semibold))
                                            Text("จับคู่และตรวจสอบการเชื่อมต่อจริง")
                                                .font(.caption).foregroundStyle(.secondary)
                                        }
                                        Spacer()
                                        Image(systemName: "chevron.right").foregroundStyle(.secondary)
                                    }.padding(14)
                                }
                                .buttonStyle(.plain)
                                .sheet(isPresented: $showPairing) { RuizenPairingView() }
                                dividingLine
                                Button { showCompatibility = true } label: {
                                    HStack(spacing: 13) {
                                        Image(systemName: "stethoscope").foregroundStyle(orange)
                                            .frame(width: 38, height: 38)
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text("รายงานความพร้อม iOS").foregroundStyle(.white)
                                                .font(.subheadline.weight(.semibold))
                                            Text("แยกสถานะระบบกับสิทธิ์ไฟล์")
                                                .font(.caption).foregroundStyle(.secondary)
                                        }
                                        Spacer()
                                        Image(systemName: "chevron.right").foregroundStyle(.secondary)
                                    }.padding(14)
                                }
                                .buttonStyle(.plain)
                                .sheet(isPresented: $showCompatibility) { StarclinetBuild34CompatibilityView() }'''
s=s.replace(old,new,1)
s+='''
// Build34: The version gate for privileged legacy routines remains unchanged.
// Pairing and RSD checks do not grant access to third-party app sandboxes.
private struct StarclinetBuild34CompatibilityView: View {
    @Environment(\\.dismiss) private var dismiss
    @State private var report = ""

    var body: some View {
        NavigationStack {
            List {
                Section("อุปกรณ์") {
                    LabeledContent("iOS", value: AppInfo.osVersion)
                    LabeledContent("Build", value: AppInfo.osBuild)
                    LabeledContent("รุ่นแอป", value: "1.1.11 (34)")
                }
                Section("การเชื่อมต่อ") {
                    Text("เข้าที่ AirLift • Pairing / RSD เพื่อตรวจสอบการจับคู่ Tunnel และ RSD ทีละขั้น")
                    Text("การเชื่อมต่อสำเร็จไม่เท่ากับสิทธิ์อ่านเขียนไฟล์ของแอปหรือเกมอื่น")
                        .foregroundStyle(.secondary)
                }
                Section("ความพร้อมที่ตรวจสอบได้") {
                    Text("ระบบเดิมสำหรับการเข้าถึงขั้นสูงจะเปิดเฉพาะรุ่นที่ได้รับการยืนยัน ไม่เปิดให้ iOS 27.0.1 โดยอัตโนมัติ")
                        .foregroundStyle(.secondary)
                }
                Button("คัดลอกรายงานอุปกรณ์") {
                    UIPasteboard.general.string = "STARCLINET 34 | iOS \\(AppInfo.osVersion) (\\(AppInfo.osBuild)); Pairing/RSD require in-app verification; advanced access not implied"
                }
            }
            .navigationTitle("ตรวจความพร้อม")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("ปิด") { dismiss() } } }
        }.preferredColorScheme(.dark)
    }
}
'''
p.write_text(s)
print("Build34 safe AirLift navigation installed")
