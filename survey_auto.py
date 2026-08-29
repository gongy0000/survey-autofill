# -*- coding: utf-8 -*-
"""
survey_auto.py
==============
เปิดแบบสอบถาม REDCap แล้ว "ติ๊กคำตอบเชิงปฏิเสธ (ไม่ใช่ / ไม่มี / ไม่เคย ...) ไว้ก่อน"
ให้ทุกคำถามที่เป็นปุ่มติ๊ก (radio button) ทั้งหน้า

มีข้อยกเว้นที่กำหนดคำตอบเองไว้แล้ว (ดูตัวแปร FORCE / EXCLUDE ด้านล่าง):
  - ข้อ 4   ที่อยู่อาศัย        -> "มีที่อยู่อาศัย"
  - ข้อ 5   กรรมสิทธิ์ที่อยู่    -> "เป็นของตนเอง หรือ ของคนในครอบครัว"
  - ข้อ 7   โทรศัพท์มือถือ      -> "มี โทรศัพท์แบบสมาร์ทโฟน ใช้ ไลน์ ได้"
  - Part2 ข้อ 2  มีหนี้สินหรือไม่ -> "ไม่ทราบ ไม่ตอบ"
  - ข้อ 17  พยายามฆ่าตัวตาย     -> ไม่ติ๊กอะไรเลย (ข้อก่อนหน้าตอบ 'ไม่มี' แล้ว ระบบข้ามให้เอง)

------------------------------------------------------------------
วิธีใช้ (สำหรับคนที่ทำไม่เป็น)
------------------------------------------------------------------
1. ลง Python  (https://www.python.org/downloads/  ตอนติดตั้งให้ติ๊ก "Add Python to PATH")
2. ลง Google Chrome
3. เปิดไฟล์นี้ใน VS Code  แล้วกดปุ่ม  Run  (สามเหลี่ยมมุมขวาบน)  หรือกด  F5
   -> ครั้งแรกสคริปต์จะติดตั้ง selenium ให้เองอัตโนมัติ (รอสักครู่)
4. Chrome จะเปิดหน้าแบบสอบถามขึ้นมาเอง แล้วติ๊กคำตอบให้ทั้งหน้า
5. ในหน้าต่าง TERMINAL ด้านล่างของ VS Code จะมีสรุป + รายชื่อข้อที่ต้องตอบเอง
6. กรอก/แก้ในเบราว์เซอร์ให้ครบ -> กดส่งในเว็บ
7. กลับมาที่ TERMINAL แล้วกด  Enter  เพื่อปิดเบราว์เซอร์
------------------------------------------------------------------
"""

import sys
import subprocess
import time
import json

# ---------------------------------------------------------------------------
# ตั้งค่า
# ---------------------------------------------------------------------------
URL = "https://rcp.pcm.ac.th/surveys/?s=P9Y87FDHWKHE49XX"

# True  = ไม่ทับข้อที่ถูกติ๊กไว้แล้ว (ปลอดภัยเวลารันซ้ำหลังแก้เอง)
# False = บังคับติ๊กทับทุกข้อเสมอ
SKIP_ALREADY_ANSWERED = True

# เวลารอโหลดหน้า (วินาที) เน็ตช้าเพิ่มเลขนี้ได้
PAGE_LOAD_WAIT = 4


# ---------------------------------------------------------------------------
# ติดตั้ง selenium อัตโนมัติถ้ายังไม่มี
# ---------------------------------------------------------------------------
def ensure_selenium():
    try:
        import selenium  # noqa: F401
        return
    except ImportError:
        pass
    print("ยังไม่มี selenium ... กำลังติดตั้งให้อัตโนมัติ (รอสักครู่)")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "selenium"]
        )
    except Exception as e:
        print("\n!! ติดตั้ง selenium อัตโนมัติไม่สำเร็จ:", e)
        print("   ให้เปิด Command Prompt แล้วพิมพ์:  pip install selenium")
        input("\nกด Enter เพื่อปิด...")
        sys.exit(1)


# ---------------------------------------------------------------------------
# สคริปต์ JavaScript ที่ยิงเข้าไปในหน้าเว็บเพื่อค้นหาและติ๊กคำตอบ
#   arguments[0] = SKIP_ALREADY_ANSWERED
# ---------------------------------------------------------------------------
JS_TICK_NEGATIVE = r"""
const SKIP_ANSWERED = arguments[0];

// ====== ข้อยกเว้น: กำหนดคำตอบเอง (แทนค่า 'ไม่ใช่' อัตโนมัติ) ======
// key = ชื่อฟิลด์ (name ของ radio) , value = ข้อความตัวเลือกที่ต้องการเลือก
const FORCE = {
    "home___radio":       "มีที่อยู่อาศัย",                          // ข้อ 4  ที่อยู่อาศัย
    "home_owner___radio": "เป็นของตนเอง หรือ ของคนในครอบครัว",        // ข้อ 5  กรรมสิทธิ์ที่อยู่
    "mphone___radio":     "มี โทรศัพท์แบบสมาร์ทโฟน ใช้ ไลน์ ได้",      // ข้อ 7  โทรศัพท์มือถือ
    "debt___radio":       "ไม่ทราบ ไม่ตอบ"                            // Part2 ข้อ 2  มีหนี้สินหรือไม่
};
// ====== ข้อที่ "ไม่ต้องติ๊กอะไรเลย" ======
const EXCLUDE = [
    "sui1_2___radio"   // ข้อ 17 พยายามฆ่าตัวตาย (ข้อ 16 ตอบ 'ไม่มี' แล้ว ระบบจะข้ามให้)
];

// คำขึ้นต้นที่ถือว่าเป็น "คำตอบเชิงปฏิเสธ / ค่าปลอดภัย"
const NEG_INCLUDE = [
    "ไม่ใช่", "ไม่มี", "ไม่เคย", "ไม่เป็น",
    "ไม่ได้ทำ", "ไม่ได้เลี้ยง", "ไม่ได้ดื่ม", "ไม่ได้ออก",
    "ไม่สูบ"
];
// คำที่ห้ามเลือก แม้จะขึ้นต้นด้วย "ไม่" (กันเลือกผิด)
const NEG_EXCLUDE = [
    "ไม่ทราบ", "ไม่ประสงค์", "ไม่ตอบ",
    "ไม่มีที่อยู่",   // "ไม่มีที่อยู่อาศัย คนไร้บ้าน" = คำตอบจริง ไม่ใช่ค่าปลอดภัย
    "ไม่มีอาการ"
];

const norm = s => (s || "").replace(/\s+/g, " ").trim();
const isNeg = t => {
    t = norm(t);
    if (!t) return false;
    if (NEG_EXCLUDE.some(x => t.startsWith(x))) return false;
    return NEG_INCLUDE.some(x => t.startsWith(x));
};

// ดึงข้อความ label ของ radio หนึ่งปุ่ม
const labelOf = inp => {
    let lab = inp.getAttribute("label");             // แบบตาราง matrix
    if (lab) return lab;
    const albl = inp.getAttribute("aria-labelledby"); // แบบเลือกข้อเดียว
    if (albl) {
        const ids = albl.trim().split(/\s+/);
        const el = document.getElementById(ids[ids.length - 1]);
        if (el) return el.innerText;
    }
    const l = inp.parentElement && inp.parentElement.querySelector("label");
    if (l) return l.innerText;
    const td = inp.closest("td");
    if (td) return td.innerText;
    return "";
};

// จัดกลุ่ม radio ตาม name (1 name = 1 คำถาม)
const groups = {};
Array.from(document.querySelectorAll('input[type=radio]')).forEach(r => {
    (groups[r.name] = groups[r.name] || []).push(r);
});

let picked = 0, forced = 0;
const pickedList = [];
const skipped = [];
const excluded = [];

for (const name in groups) {
    const inputs = groups[name];

    if (EXCLUDE.indexOf(name) !== -1) { excluded.push(name); continue; }
    if (SKIP_ANSWERED && inputs.some(i => i.checked)) continue;

    let target = null;
    let isForced = false;

    if (FORCE[name]) {
        const want = norm(FORCE[name]);
        target = inputs.find(i => norm(labelOf(i)) === want)
              || inputs.find(i => norm(labelOf(i)).startsWith(want))
              || null;
        if (target) isForced = true;
    }

    if (!target) {
        for (const inp of inputs) {
            if (isNeg(labelOf(inp))) { target = inp; break; }
        }
    }

    if (!target) {
        skipped.push(name + "  ->  " + inputs.map(i => norm(labelOf(i))).join(" / "));
        continue;
    }

    target.scrollIntoView({ block: "center" });
    target.click();  // .click() จะไปกระตุ้น onclick ของ REDCap ให้บันทึกค่าจริง
    target.dispatchEvent(new Event("change", { bubbles: true }));
    picked++;
    if (isForced) forced++;
    pickedList.push((isForced ? "[กำหนดเอง] " : "") + name + "  ->  " + norm(labelOf(target)));
}

return JSON.stringify({
    totalGroups: Object.keys(groups).length,
    picked: picked,
    forced: forced,
    excluded: excluded,
    skippedCount: skipped.length,
    skipped: skipped,
    pickedList: pickedList
});
"""


def auto_fill_survey():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_experimental_option("detach", True)  # กัน Chrome ปิดเองตอนสคริปต์จบ

    print("กำลังเปิด Chrome ...")
    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as e:
        print("\n!! เปิด Chrome ไม่สำเร็จ:", e)
        print("   ตรวจสอบว่าได้ติดตั้ง Google Chrome แล้ว และ selenium เป็นเวอร์ชันใหม่")
        input("\nกด Enter เพื่อปิด...")
        return

    print(f"กำลังเปิดหน้าเว็บ: {URL}")
    driver.get(URL)
    time.sleep(PAGE_LOAD_WAIT)

    print("กำลังค้นหาและติ๊กคำตอบ ...")
    result = json.loads(driver.execute_script(JS_TICK_NEGATIVE, SKIP_ALREADY_ANSWERED))

    print("\n" + "=" * 60)
    print(f"  พบคำถามแบบติ๊กทั้งหมด : {result['totalGroups']} ข้อ")
    print(f"  ติ๊กให้แล้ว            : {result['picked']} ข้อ "
          f"(ในนั้นเป็นข้อกำหนดเอง {result['forced']} ข้อ)")
    print(f"  เว้นว่างตามที่สั่ง      : {len(result['excluded'])} ข้อ -> {result['excluded']}")
    print(f"  ข้าม (ไม่มีตัวเลือกปฏิเสธ / ตอบไว้แล้ว) : {result['skippedCount']} ข้อ")
    print("=" * 60)

    if result["skipped"]:
        print("\n*** ข้อที่โปรแกรมข้าม -> คุณต้องไปเลือกเอง ***")
        for i, s in enumerate(result["skipped"], 1):
            print(f"  {i:2d}. {s}")

    print("\nช่องที่ต้องพิมพ์เอง (โปรแกรมไม่ยุ่ง) เช่น:")
    print("  - รหัสอาสาสมัคร 6 หลัก / วันที่กรอกแบบฟอร์ม")
    print("  - อายุ / วันเดือนปีเกิด / รายได้ / เวลานอน-ตื่น / คะแนนสุขภาพ 0-100")
    print("  - ช่อง 'อื่นๆ ระบุ...' ต่าง ๆ")

    print("\n" + "-" * 60)
    print("ตอนนี้เบราว์เซอร์เปิดค้างไว้ให้แล้ว")
    print("1) ตรวจ/แก้คำตอบให้ครบ   2) กดส่งในเว็บ")
    input("เสร็จแล้วกลับมากด Enter ที่นี่เพื่อปิดเบราว์เซอร์...")

    try:
        driver.quit()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        ensure_selenium()
        auto_fill_survey()
    except Exception:
        import traceback
        print("\n!! เกิดข้อผิดพลาด:")
        traceback.print_exc()
        input("\nกด Enter เพื่อปิด...")
