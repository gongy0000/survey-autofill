/* ============================================================
   survey_tick_no.js  —  ติ๊กคำตอบให้ทั้งหน้าแบบสอบถาม
   ============================================================

   ไฟล์นี้ไม่ต้องลง Python / Selenium
   ใช้วิธี "วางโค้ดใน Console ของเบราว์เซอร์"

   ---------- วิธีใช้ ----------
   1. เปิดหน้าแบบสอบถามใน Chrome / Edge:
      https://rcp.pcm.ac.th/surveys/?s=P9Y87FDHWKHE49XX
   2. กด  F12  -> คลิกแท็บ  "Console"
   3. ถ้ามีเตือนสีเหลือง ให้พิมพ์  allow pasting  แล้วกด Enter
   4. เลือกข้อความในไฟล์นี้ "ทั้งหมด" (ตั้งแต่บรรทัด (() => {  จนจบไฟล์)
      -> Copy -> วางใน Console -> กด Enter
   5. โปรแกรมจะติ๊กให้ทั้งหน้า แล้วขึ้นสรุป
   6. กรอกช่องที่ต้องพิมพ์เอง + ข้อที่ข้าม -> ตรวจทาน -> กดส่งในเว็บ

   ---------- ข้อยกเว้นที่กำหนดคำตอบไว้แล้ว ----------
   - ข้อ 4   ที่อยู่อาศัย        -> "มีที่อยู่อาศัย"
   - ข้อ 5   กรรมสิทธิ์ที่อยู่    -> "เป็นของตนเอง หรือ ของคนในครอบครัว"
   - ข้อ 7   โทรศัพท์มือถือ      -> "มี โทรศัพท์แบบสมาร์ทโฟน ใช้ ไลน์ ได้"
   - Part2 ข้อ 2 มีหนี้สินหรือไม่ -> "ไม่ทราบ ไม่ตอบ"
   - ข้อ 17  พยายามฆ่าตัวตาย     -> ไม่ติ๊กอะไรเลย (ข้อ 16 ตอบ 'ไม่มี' แล้ว ระบบข้ามให้)
   ============================================================ */

(() => {
  const SKIP_ALREADY_ANSWERED = true;   // true = ไม่ทับข้อที่ตอบไว้แล้ว

  // ====== ข้อยกเว้น: กำหนดคำตอบเอง (แทนค่า 'ไม่ใช่' อัตโนมัติ) ======
  const FORCE = {
    "home___radio":       "มีที่อยู่อาศัย",                     // ข้อ 4  ที่อยู่อาศัย
    "home_owner___radio": "เป็นของตนเอง หรือ ของคนในครอบครัว",   // ข้อ 5  กรรมสิทธิ์ที่อยู่
    "mphone___radio":     "มี โทรศัพท์แบบสมาร์ทโฟน ใช้ ไลน์ ได้", // ข้อ 7  โทรศัพท์มือถือ
    "debt___radio":       "ไม่ทราบ ไม่ตอบ"                       // Part2 ข้อ 2  มีหนี้สินหรือไม่
  };
  // ====== ข้อที่ "ไม่ต้องติ๊กอะไรเลย" ======
  const EXCLUDE = [
    "sui1_2___radio"   // ข้อ 17 พยายามฆ่าตัวตาย
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

  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const isNeg = (t) => {
    t = norm(t);
    if (!t) return false;
    if (NEG_EXCLUDE.some((x) => t.startsWith(x))) return false;
    return NEG_INCLUDE.some((x) => t.startsWith(x));
  };

  const labelOf = (inp) => {
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

  const groups = {};
  document.querySelectorAll('input[type=radio]').forEach((r) => {
    (groups[r.name] = groups[r.name] || []).push(r);
  });

  let picked = 0, forced = 0;
  const pickedList = [];
  const skipped = [];
  const excluded = [];

  for (const name in groups) {
    const inputs = groups[name];

    if (EXCLUDE.indexOf(name) !== -1) { excluded.push(name); continue; }
    if (SKIP_ALREADY_ANSWERED && inputs.some((i) => i.checked)) continue;

    let target = null;
    let isForced = false;

    if (FORCE[name]) {
      const want = norm(FORCE[name]);
      target = inputs.find((i) => norm(labelOf(i)) === want)
            || inputs.find((i) => norm(labelOf(i)).startsWith(want))
            || null;
      if (target) isForced = true;
    }

    if (!target) {
      for (const inp of inputs) {
        if (isNeg(labelOf(inp))) { target = inp; break; }
      }
    }

    if (!target) {
      skipped.push(name + "  ->  " + inputs.map((i) => norm(labelOf(i))).join(" / "));
      continue;
    }

    target.scrollIntoView({ block: "center" });
    target.click(); // .click() จะไปกระตุ้น onclick ของ REDCap ให้บันทึกค่าจริง
    target.dispatchEvent(new Event("change", { bubbles: true }));
    picked++;
    if (isForced) forced++;
    pickedList.push((isForced ? "[กำหนดเอง] " : "") + name + "  ->  " + norm(labelOf(target)));
  }

  console.log("%c==== สรุปผลการติ๊ก ====", "font-weight:bold;font-size:14px");
  console.log("คำถามแบบติ๊กทั้งหมด :", Object.keys(groups).length, "ข้อ");
  console.log("ติ๊กให้แล้ว          :", picked, "ข้อ  (กำหนดเอง " + forced + " ข้อ)");
  console.log("เว้นว่างตามที่สั่ง    :", excluded.length, "ข้อ ->", excluded);
  console.log("ข้าม (ต้องตอบเอง)   :", skipped.length, "ข้อ");
  console.log("");
  console.log("--- ข้อที่ติ๊กให้ ---");
  pickedList.forEach((s) => console.log("  " + s));
  console.log("");
  console.log("--- ข้อที่ข้าม ต้องไปเลือกเอง ---");
  skipped.forEach((s, i) => console.log((i + 1) + ". " + s));
  console.log("");
  console.log("--- ช่องที่ต้องพิมพ์เอง (โปรแกรมไม่ยุ่ง) ---");
  console.log("รหัสอาสาสมัคร 6 หลัก, วันที่กรอกฟอร์ม, อายุ/วันเกิด, รายได้,");
  console.log("เวลานอน-ตื่น, คะแนนสุขภาพ 0-100, ช่อง 'อื่นๆ ระบุ...'");

  alert(
    "ติ๊กให้แล้ว " + picked + " ข้อ (กำหนดเอง " + forced + " ข้อ)\n" +
    "เว้นว่างตามสั่ง " + excluded.length + " ข้อ\n" +
    "ข้ามให้ตอบเอง " + skipped.length + " ข้อ\n\n" +
    "เปิด Console (F12) ดูรายละเอียด แล้วตรวจทาน + กรอกช่องพิมพ์ + กดส่ง"
  );
})();
