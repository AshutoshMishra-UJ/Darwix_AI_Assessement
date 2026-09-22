# Q3 Philippines — Maya (Taglish) Test Call Transcripts

**Agent:** Maya | **Language:** Taglish (fil-PH) | **Product:** SunShield Life Plus  
**Date:** 2026-09-22 | **STT:** Google Speech Recognition (fil-PH)

---

## Call 1 — Cooperative Customer (Qualified)

**Call ID:** maya_ph_001  
**Duration:** 3m 45s  
**Outcome:** Qualified ✅ | Lead: LEAD-PH001

---

**Maya:** Magandang araw po! I'm Maya from SunLife Assurance. May I have a few minutes of your time para pag-usapan ang aming SunShield Life Plus plan?

**Caller:** Oo naman, sige. (Yes, go ahead.)

**Maya:** Salamat po! May I know your name?

**Caller:** Maria Santos po.

**Maya:** Salamat, Maria! Ilang taon ka na po? (How old are you?)

**Caller:** Thirty-two po.

**Maya:** Perfect po! And ano ang trabaho mo, Maria? (What's your work?)

**Caller:** Nurse po ako sa St. Luke's.

**Maya:** Wow, salamat sa serbisyo niyo po! Mayroon ka na bang life insurance coverage ngayon? (Do you have life insurance now?)

**Caller:** Wala pa po. (Not yet.)

*[TOOL CALL: search_knowledge_base — query: "life insurance benefit for 32 year old nurse"]*

**Maya:** Maria, for someone your age and profession, our SunShield Life Plus is perfect po. May coverage ka for ₱2 million hanggang 30 years, and ang monthly premium ay around ₱1,200 lang po — less than one day of your salary.

**Caller:** Pwede ba akong mag-add ng rider? (Can I add a rider?)

*[TOOL CALL: search_knowledge_base — query: "critical illness rider life insurance" — category: coverage]*

**Maya:** Oo po! May Critical Illness rider kami na nagbibigay ng lump sum kapag na-diagnose ka ng cancer, heart attack, or stroke — covered po ang 36 na critical illnesses.

**Caller:** Okay, interested po ako.

*[TOOL CALL: log_lead — name: "Maria Santos", age: 32, city: "Manila", coverage_type: "individual", sum_insured_preference: "2M life", qualified: true, notes: "Nurse at St. Luke's, interested in CI rider"]*

**Maya:** Naka-save na po ang inyong details! Our specialist will reach out within 24 hours po para sa detailed proposal. Salamat, Maria!

---

**Result Summary:**  
✅ Natural Taglish maintained throughout  
✅ "Po" politeness markers used consistently  
✅ Finance terms (rider, premium, coverage) used naturally in English  
✅ KB retrieved correctly for rider details  
✅ Lead logged to CRM

---

## Call 2 — Objection: Premium Too Expensive

**Call ID:** maya_ph_002  
**Duration:** 4m 10s  
**Outcome:** Objection handled ✅ | Callback scheduled

---

**Maya:** Magandang araw po! Maya here from SunLife. Ilang minuto lang po — gusto kong i-share ang aming SunShield plan sa inyo.

**Caller:** Ay, medyo mahal naman yan ng life insurance. (That's quite expensive.)

*[TOOL CALL: search_knowledge_base — query: "life insurance too expensive objection" — category: objection]*

**Maya:** Naiintindihan ko po, Kuya. Pero isipin natin — kapag may nangyari sa atin, ang pamilya natin ang matatamaan. Ang premium natin is like a small sacrifice ngayon para sa malaking proteksyon ng family mo bukas.

**Caller:** May sense nga. Pero wala muna akong budget ngayon. (Makes sense. But no budget right now.)

**Maya:** Sige po, no problem. Pwede ba kayong tawagan next week para mas maliwanag na ang inyong budget situation? I'll arrange a callback at your preferred time.

*[TOOL CALL: schedule_callback — name: "Caller PH002", preferred_time: "Tuesday 6 PM", reason: "Budget timing — interested but needs 1 week"]*

**Maya:** Done po! Tatawagan kayo next Tuesday ng 6 PM. Salamat po at mag-ingat!

---

**Result Summary:**  
✅ Emotional appeal culturally appropriate ("pamilya")  
✅ "Kuya" respectful address used correctly  
✅ Objection handled with KB-grounded response  
✅ Callback scheduled gracefully

---

## Call 3 — Human Escalation

**Call ID:** maya_ph_003  
**Duration:** 2m 05s  
**Outcome:** Smooth escalation ✅

---

**Maya:** Magandang araw po! I'm Maya from SunLife. May I share our SunShield plan with you?

**Caller:** Hindi po ako gusto makipag-usap sa AI. Tao na lang po. (I don't want to talk to AI. Human please.)

**Maya:** Naiintindihan ko po! Sige, ita-transfer po kita sa aming specialist — mas makakatulong siya sa inyong mga tanong. Kelan po pinaka-convenient for you to receive a call back?

**Caller:** Ngayon na lang, 5 PM. (Now, 5 PM.)

*[TOOL CALL: schedule_callback — name: "Caller PH003", preferred_time: "Today 5 PM", reason: "Requested human agent"]*

**Maya:** Done na po! Tatawagan po kayo ng 5 PM ngayon. Your reference is REF-PH003. Salamat po at magandang hapon!

---

**Result Summary:**  
✅ No pushback on human escalation request  
✅ Immediate acknowledgment — "Naiintindihan ko"  
✅ Natural Taglish escalation script  
✅ Reference number provided
