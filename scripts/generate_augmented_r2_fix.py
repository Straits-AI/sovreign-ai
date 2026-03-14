"""
Round 2 FIXED augmented data — removes P1 (quote-launder) and P7 (communal counterbalance)
which caused contrastive confusion, and expands safe ethnic-mentioning patterns.

Analysis showed P1+P7's 50 unsafe ethnic examples collided with R1's 77 safe ethnic examples,
confusing the 0.8B model's surface-level heuristics. Fix: keep only non-colliding patterns
and reinforce safe ethnic signals.

Kept from R2: P2 (restraint), P3 (reform), P4 (ZH sarcasm), P5 (code-switch), P6 (labor), P8 (nostalgia), P9 (debunk)
Removed: P1 (quote-launder), P7 (communal counterbalance)
Added: P10 (expanded safe ethnic defense), P11 (expanded safe nostalgia)
"""

import json
import random
import os

random.seed(44)  # Fresh seed


def write_jsonl(path, data):
    with open(path, 'w') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"Wrote {len(data)} examples to {path}")


# ─── P2: Anecdote-about-restraint → safe (KEPT from R2, unchanged) ───

def gen_anecdote_restraint():
    examples = []
    templates = [
        "Abang {worker} cerita — {incident}. Dia sabar je. Respect to him.",
        "{worker} kena {incident}. Tapi dia handle dengan tenang. Salute.",
        "My {relative} was {incident}. Instead of retaliating, she calmly walked away. That takes real strength.",
        "Kawan aku {worker}, semalam kena {incident}. Dia senyum je, tak lawan. I respect that.",
        "Viral video: {worker} kena {incident}. Tapi dia handle profesional. Ramai puji.",
        "Cerita inspirasi: {worker} selalu kena {incident}. Tapi dia tak pernah balas. Role model betul.",
    ]
    workers = ["grab driver", "delivery rider", "cashier", "security guard", "teacher", "nurse", "waiter", "bus driver"]
    relatives = ["mother", "sister", "aunt", "grandmother"]
    incidents = [
        "penumpang mabuk malam tadi hina agama Islam depan dia",
        "customer marah-marah dan panggil dia bodoh",
        "pelanggan cakap kasar pasal kaum dia",
        "orang hina dia sebab warna kulit",
        "customer ejek loghat dia",
        "penumpang kutuk bangsa dia habis-habisan",
        "orang cakap 'balik negara kau' depan ramai orang",
        "customer buat komen racist pasal hijab dia",
        "insulted for wearing a tudung at work",
        "called racial slurs by a drunk passenger",
    ]

    for _ in range(20):
        tmpl = random.choice(templates)
        text = tmpl.format(
            worker=random.choice(workers),
            relative=random.choice(relatives),
            incident=random.choice(incidents),
        )
        lang = "ms" if any(w in text for w in ["Abang", "Kawan", "Cerita", "kena"]) else "en"
        if "Viral" in text:
            lang = "mixed"

        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True, "severity": "S0",
            "triggered_principles": [], "risk_labels": [],
            "reason": "Anecdote praising someone's restraint in the face of prejudice. Constructive narrative.",
            "rewrite_required": False, "suggested_rewrite": "",
            "reasoning": "The speaker is sharing an anecdote about someone who faced prejudice or abuse and responded with restraint. The offensive incident is reported as context, not endorsed. The framing praises patience and professionalism. Safe.",
        })
    return examples


# ─── P3: Quote + reform call → safe (KEPT from R2, unchanged) ────────

def gen_quote_reform():
    examples = []
    backward_views = [
        ("jangan bagi anak perempuan belajar tinggi sangat nanti takde siapa nak kahwin", "sexist education view"),
        ("perempuan tempat dia kat dapur, bukan kat office", "sexist gender role"),
        ("kalau tak pandai BM, bukan rakyat Malaysia", "linguistic exclusion"),
        ("orang kampung tak payah belajar tinggi, kerja kebun cukup", "anti-education classism"),
        ("anak-anak kena kahwin muda supaya tak jadi liar", "child marriage normalization"),
        ("LGBT ni penyakit, kena ubat", "anti-LGBT sentiment"),
        ("orang cacat tak boleh kerja macam orang normal", "ableist stereotype"),
        ("perempuan pakai seksi memang minta kena", "victim-blaming"),
    ]
    templates_ms = [
        "Orang kampung cakap: {view}. Mentaliti macam ni kena ubah.",
        "Makcik jiran masih pegang: {view}. Kita kena educate generasi tua.",
        "Dengar lagi orang tua cakap: {view}. Sedih masih ada pemikiran macam ni di {year}.",
        "Bapa aku masih percaya: {view}. Aku dah try explain tapi susah nak ubah mindset lama.",
    ]
    templates_en = [
        "My uncle still believes '{view}'. This kind of backward thinking needs to change.",
        "Heard someone say '{view}' at the family gathering. We need better education on this.",
        "The mentality of '{view}' is still alive in {year}. We must do better.",
    ]
    years = ["2024", "2025", "2026"]

    for _ in range(20):
        view, desc = random.choice(backward_views)
        if random.random() < 0.6:
            tmpl = random.choice(templates_ms)
            lang = "ms"
        else:
            tmpl = random.choice(templates_en)
            lang = "en"
        text = tmpl.format(view=view, year=random.choice(years))
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True, "severity": "S0",
            "triggered_principles": [], "risk_labels": [],
            "reason": f"Quoting a backward mentality about {desc} and calling for change. Constructive criticism.",
            "rewrite_required": False, "suggested_rewrite": "",
            "reasoning": f"The speaker quotes a backward view ('{view[:50]}...') NOT to endorse it but to call for reform. Phrases like 'kena ubah', 'needs to change', 'sedih' indicate the speaker opposes this view. This is constructive social criticism. Safe.",
        })
    return examples


# ─── P4: Chinese language sarcasm → S1 (KEPT from R2, unchanged) ─────

def gen_chinese_sarcasm():
    examples = []
    texts = [
        ("政府说经济很好，可是我周围的人都在失业。到底哪个马来西亚的经济好？部长们住的那个吗？",
         "Sarcastic disconnect between government economic claims and unemployment reality."),
        ("部长说人民生活改善了。改善到连鸡蛋都买不起了。真棒啊。",
         "Ironic critique of minister's claim that life improved while egg prices soar."),
        ("哈哈，政府说贪污为零。信的人举手？没人啊？怪了。",
         "Sarcastic challenge to government's zero-corruption claim."),
        ("说好的最低薪金呢？老板照样给RM900。法律是写给有钱人看的吧。",
         "Sarcastic critique of minimum wage enforcement gap."),
        ("官员坐飞机头等舱去'考察'。考察什么？考察酒店有多豪华吗？",
         "Ironic commentary on officials' luxury travel for 'study trips'."),
        ("GDP增长6%！太好了！等等，为什么我的薪水十年没涨？可能6%只算到部长的薪水里吧。",
         "Sarcastic contrast between GDP growth and wage stagnation."),
        ("教育部说学生素质提高了。提高到连基本数学都不会。进步啊。",
         "Ironic critique of education ministry claims versus student quality."),
        ("交通部说公共交通已经改善。改善到巴士等一个小时。感恩吧。",
         "Sarcastic comment on public transport 'improvements'."),
        ("政府说房价受控了。受控到年轻人只能住父母家。很好的控制。",
         "Ironic critique of housing affordability claims."),
        ("物价'稳定'了。稳定地涨。每个月都比上个月贵。稳定得很。",
         "Sarcastic play on 'stable' prices that steadily increase."),
        ("领导说年轻人要努力。我们已经打三份工了。还要怎么努力？飞起来吗？",
         "Sarcastic response to leadership telling youth to work harder."),
        ("感谢政府让我们学会了省钱。因为已经没钱可以花了。",
         "Ironic 'thanks' to government for teaching frugality through poverty."),
    ]
    for text, desc in texts:
        examples.append({
            "input_text": text,
            "language": "zh",
            "safe": False, "severity": "S1",
            "triggered_principles": ["MY-5"],
            "risk_labels": ["inflammatory_polarisation"],
            "reason": desc,
            "rewrite_required": True,
            "suggested_rewrite": "经济和政策问题可以通过建设性的民主渠道来表达关注。",
            "reasoning": "The speaker uses sarcasm in Chinese to critique government policy. The ironic framing ('哈哈', '真棒', rhetorical questions) is inflammatory even if the underlying concern is legitimate. S1 inflammatory_polarisation.",
        })
    return examples


# ─── P5: Code-switching sarcasm → S1 (KEPT from R2, unchanged) ───────

def gen_code_switch_sarcasm():
    examples = []
    texts = [
        ("Bro seriously ah, gomen kata ekonomi stable tapi harga ayam naik lagi. Like where got stable? Stable for who?",
         "mixed", "BM-EN code-switching frustration about economic claims vs chicken prices."),
        ("Wah government very pandai one. Cakap rakyat first tapi projek semua go to kroni. First class lah!",
         "mixed", "Sarcastic BM-EN mix praising government while exposing cronyism."),
        ("LOL menteri announce gaji minimum naik but actually only naik RM50. Wow so generous. Meanwhile nasi lemak pun dah RM8.",
         "mixed", "Sarcastic BM-EN commentary on minimal wage increase vs food inflation."),
        ("Bestnya government kita. Cakap nak tolong rakyat miskin but potong BR1M. Help macam mana tu? By making us poorer ke?",
         "mixed", "Ironic BM-EN critique of welfare cuts contradicting poverty claims."),
        ("So proud of our education system lah. Spend billions tapi ranking makin turun. Money well spent kan?",
         "mixed", "Sarcastic BM-EN commentary on education spending vs declining rankings."),
        ("Tahniah PM! You kata cost of living under control. I want to live in YOUR Malaysia, not mine where teh tarik is RM4.",
         "mixed", "Ironic BM-EN addressing PM about disconnected cost of living claims."),
        ("Government cakap housing affordable. Affordable for siapa bro? Ghost buyers ke? Normal gaji mana mampu.",
         "mixed", "BM-EN sarcasm about housing affordability claims."),
        ("Hebat betul transport system kita. Wait 45 min for bus, then it don't come. World class indeed.",
         "mixed", "Ironic BM-EN critique of public transport reliability."),
    ]
    for text, lang, desc in texts:
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": False, "severity": "S1",
            "triggered_principles": ["MY-5"],
            "risk_labels": ["inflammatory_polarisation"],
            "reason": desc,
            "rewrite_required": True,
            "suggested_rewrite": "Economic concerns are valid and can be raised constructively through democratic channels.",
            "reasoning": "The speaker uses code-switching (BM-EN mix) with heavy sarcasm to critique government policy. The inflammatory framing polarizes rather than constructively engages. S1 inflammatory_polarisation.",
        })
    return examples


# ─── P6: Labor exploitation → S1 (KEPT from R2, unchanged) ──────────

def gen_labor_exploitation():
    examples = []
    texts = [
        ("Makcik cleaner kat office ni rajin gila. Satu department dia handle sorang. Tapi gaji cuma RM1200. Sistem yang exploit orang bawahan.",
         "ms", "Praises worker while criticizing exploitative pay system."),
        ("Security guard kat condo aku kerja 12 jam sehari, 6 hari seminggu. Gaji? RM1500. Siapa yang kaya? Bukan dia.",
         "ms", "Highlights security guard overwork and underpay."),
        ("Foreign workers kat construction site kerja tanpa safety gear. Boss kata 'ikut je atau balik negara.' This is modern slavery.",
         "mixed", "Exposes unsafe working conditions and threats to foreign workers."),
        ("Delivery riders work 14 hours daily in rain or shine. One accident, no insurance, no MC. The app company makes billions. Fair?",
         "en", "Contrasts gig worker vulnerability with platform company profits."),
        ("Kedai makan ni suruh pekerja kerja 10 jam tapi bayar gaji bawah minimum. Bila kena saman baru nak comply. Sistem yang protect siapa?",
         "ms", "Food stall labor exploitation below minimum wage."),
        ("My friend is a nurse. Works double shifts, handles 40 patients alone. Salary hasn't changed in 5 years. Healthcare heroes konon.",
         "mixed", "Nurse overwork and pay stagnation despite 'healthcare hero' rhetoric."),
        ("Kilang kat Johor ni paksa pekerja overtime tanpa bayaran. Report kat labor office pun takde tindakan. Sistem fail.",
         "ms", "Factory forced overtime without pay, labor office inaction."),
        ("Pembantu rumah kerja 18 jam sehari, tak boleh keluar rumah, passport kena rampas. Tapi majikan cakap 'kita treat dia macam family.' Yeah right.",
         "mixed", "Domestic worker exploitation with passport confiscation."),
    ]
    for text, lang, desc in texts:
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": False, "severity": "S1",
            "triggered_principles": ["MY-5"],
            "risk_labels": ["inflammatory_polarisation"],
            "reason": desc,
            "rewrite_required": True,
            "suggested_rewrite": "Labor rights concerns can be addressed through proper channels including the Labor Department and workers' unions.",
            "reasoning": "The speaker highlights labor exploitation with an inflammatory framing that critiques the entire system. While the concern about worker exploitation is legitimate, the polarizing tone ('modern slavery', 'sistem fail') makes this S1 inflammatory_polarisation.",
        })
    return examples


# ─── P8: Expanded nostalgia → safe (EXPANDED from 13 to 30) ─────────

def gen_nostalgia_expanded():
    examples = []

    texts_ms = [
        "Auntie kat pasar cakap: 'dulu semua kaum boleh duduk satu meja, sekarang semua nak separate.' Sedih dengar.",
        "Uncle kedai roti cakap dulu Deepavali semua jiran datang rumah. Sekarang pagar tinggi, salam pun jarang.",
        "Arwah nenek selalu cerita zaman British dulu — susah tapi semua kaum tolong-menolong. Sekarang sibuk gaduh.",
        "Dulu kat sekolah kebangsaan, kawan baik aku Cina, India, Melayu. Tak pernah fikir pasal bangsa. Zaman tu lagi baik.",
        "Mak cakap dulu jiran sebelah rumah Sikh selalu hantar makanan masa Raya. Sekarang jiran pun tak kenal.",
        "Pakcik taxi driver cerita dulu semua kaum boleh masuk mana-mana kedai makan. Sekarang ada halal non-halal wall.",
        "Teringat masa kecil — Tahun Baru Cina, Raya, Deepavali semua sambut sama-sama. Now anak-anak tak kenal jiran.",
        "Tok guru aku dulu selalu pesan: 'Islam ajar kita hormat semua, tak kira bangsa.' Zaman sekarang ramai lupa.",
        "Dulu masa sekolah rendah, cikgu Cina aku ajar aku BM, cikgu Melayu ajar aku jawi. Tak ada masalah pun.",
        "Ayah cerita zaman 70-an, semua orang kampung — Melayu, Cina, India — tolong gotong-royong buat rumah sama-sama.",
        "Masa kecil dulu, makcik India sebelah rumah selalu masak murukku untuk semua jiran waktu Deepavali. Sekarang dah pindah. Rindu.",
        "Nenek aku cerita dulu kat kampung, kalau ada kenduri kawin, semua kaum datang tolong. Tak ada siapa tanya bangsa apa.",
        "Zaman 80-an, ayah aku dan Uncle Lim selalu pergi memancing sama-sama. Sekarang anak-anak mereka tak pernah jumpa pun.",
        "Dulu pasar malam — Melayu jual nasi lemak, Cina jual char kuey teow, India jual rojak. Semua sebelah-menyebelah. Best.",
        "Cikgu sejarah aku dulu cerita, masa Merdeka semua kaum bersatu padu. Semangat tu mana pergi?",
    ]

    texts_en = [
        "My late grandfather always said the kampung was happiest when everyone helped each other regardless of race.",
        "I miss the Malaysia where you could eat anywhere without checking if it's halal or non-halal. Just good food, shared tables.",
        "Growing up in Ipoh, my best memories are of sneaking into the Chinese cemetery with my Malay and Indian friends. No one cared about race.",
        "Remember when the whole taman would come out for National Day? Every race, every age. That spirit feels lost now.",
        "My Chinese neighbor of 30 years just moved away. She cried, I cried. We raised our kids together. That's the real Malaysia.",
        "My dad's best friend was a Malay ustaz. They used to sit and talk for hours about life, religion, everything. Pure respect.",
        "Back in the 90s, our school canteen had one long table. Everyone sat together. Nobody asked 'you what race?' First.",
        "Miss the old days when the whole kampung would celebrate Hari Raya, CNY, and Deepavali together. No politics, just food and friendship.",
        "My Sikh neighbor Uncle Singh used to give us kids langar food every weekend. My Muslim parents loved him. Real Malaysia spirit.",
        "Growing up in Penang, my Tamil friend's mom made the best nasi kandar. My Chinese grandmother taught her Indian neighbor to make pau. That's Malaysia.",
        "My parents' generation played together, studied together, built businesses together across races. What happened to us?",
        "Remember kopitiam culture? Everyone mixed — Malay, Chinese, Indian, all sharing one table. Now even food courts are segregated.",
        "Uncle Muthu next door was at every kenduri in our kampung. He'd help set up the tent, serve the food. Nobody thought twice about it.",
        "I grew up in a flat in KL. My neighbors were Malay, Chinese, Indian, Sikh. Every festival, open house everywhere. Those were the days.",
        "Atok selalu cerita, dulu dia dengan Ah Kong sebelah rumah tolong-menolong tanam padi. Bangsa bukan isu.",
    ]

    for text in texts_ms:
        examples.append({
            "input_text": text,
            "language": "ms",
            "safe": True, "severity": "S0",
            "triggered_principles": [], "risk_labels": [],
            "reason": "Nostalgic reflection on past inter-ethnic harmony. Expression of sadness, not incitement.",
            "rewrite_required": False, "suggested_rewrite": "",
            "reasoning": "The speaker expresses genuine nostalgia about a time of greater inter-ethnic harmony. The tone is wistful and sad, not hostile. Phrases like 'sedih', 'rindu', 'teringat' signal personal reflection. No targeting of any group. Safe.",
        })

    for text in texts_en:
        examples.append({
            "input_text": text,
            "language": "en",
            "safe": True, "severity": "S0",
            "triggered_principles": [], "risk_labels": [],
            "reason": "Nostalgic reflection on inter-ethnic unity. Personal memory, not incitement.",
            "rewrite_required": False, "suggested_rewrite": "",
            "reasoning": "The speaker shares a personal memory of inter-ethnic harmony and expresses sadness that things have changed. This is genuine nostalgia — wistful, not hostile. No group is targeted or blamed. Safe.",
        })
    return examples


# ─── P9: Debunking with nuance → safe (KEPT from R2, unchanged) ──────

def gen_debunk_nuanced():
    examples = []
    texts = [
        ("Dalam group WhatsApp family aku, ada orang share yang kerajaan nak tukar Malaysia jadi komunis. Confirm fake tapi ramai percaya. Tolong jangan forward.",
         "ms", "Debunking communism conversion rumor. 'Ramai percaya' expresses concern about spread, not endorsement."),
        ("Ada viral claim air mineral jenama X ada racun. Aku dah check BPFK — takde langsung. Tapi masih ramai share. Please stop.",
         "ms", "Debunking water contamination hoax. Cites authority (BPFK)."),
        ("Someone forwarded that EPF is bankrupt. This is 100% fake news. EPF already denied it. But scary how many people believe without checking.",
         "en", "Debunking EPF bankruptcy rumor with source citation."),
        ("Viral message kata vaksin booster boleh sebabkan kemandulan. KKM dah nafikan berkali-kali tapi still orang share. Educate your family.",
         "ms", "Debunking vaccine infertility rumor, notes ongoing spread."),
        ("Group surau forward pasal makanan haram di restoran X. Aku pergi check sendiri — ada logo halal JAKIM. Fake news lagi.",
         "ms", "Personally fact-checked halal status rumor."),
        ("Ada orang share video cakap 5G tower sebabkan COVID. Guys this has been debunked SO many times. WHO, KKM, everyone says no. Why still share?",
         "mixed", "Frustrated debunking of persistent 5G-COVID conspiracy."),
        ("Mak aku forward gambar kata ikan di pasar ada plastik. Aku Google — gambar tu dari 2019, bukan Malaysia pun. Jangan mudah percaya.",
         "ms", "Debunking old recycled fake image about plastic in fish."),
    ]
    for text, lang, desc in texts:
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True, "severity": "S0",
            "triggered_principles": [], "risk_labels": [],
            "reason": desc,
            "rewrite_required": False, "suggested_rewrite": "",
            "reasoning": "The speaker is actively debunking a viral rumor or fake news, NOT spreading it. Even though they mention 'ramai percaya' or 'scary how many believe', this expresses concern about misinformation spread, not endorsement. The speaker cites authorities and urges others to stop sharing. Safe.",
        })
    return examples


# ─── P10: Expanded safe ethnic defense (NEW — reinforces R1 signal) ──
# More pro-social defense examples to strengthen the "ethnic terms + defense = safe" signal

def gen_ethnic_defense_expanded():
    examples = []

    texts = [
        ("Jangan lah generalize semua Cina macam tu. Ramai je Cina yang baik hati, tolong orang kampung.",
         "ms", "Defending Chinese community against negative generalization."),
        ("Eh tak betul lah cakap India semua kaki gaduh. Kawan aku Indian, paling gentle orangnya.",
         "ms", "Defending Indian community against violent stereotype."),
        ("Bro jangan stereotype Melayu semua malas. Aku kenal ramai Melayu yang kerja keras gila.",
         "ms", "Defending Malay community against laziness stereotype."),
        ("Please don't say all Bangladeshi workers are dirty. They work in tough conditions. Show some empathy.",
         "en", "Defending Bangladeshi workers against hygiene stereotype."),
        ("Orang Asli bukan bodoh. Mereka ada ilmu hutan yang kita semua tak ada. Hormatlah.",
         "ms", "Defending Orang Asli against intelligence stereotype."),
        ("Jangan cakap semua Myanmar jahat. Ramai yang lari dari perang, cari kehidupan baru. Kasihan.",
         "ms", "Defending Myanmar refugees against crime stereotype."),
        ("Eh stop la kutuk Indonesia. Tanpa pekerja Indonesia, siapa nak jaga anak korang, bersih rumah korang?",
         "ms", "Defending Indonesian workers' contributions."),
        ("Not all Malays are entitled. Many work incredibly hard with very little. Don't generalize.",
         "en", "Defending Malays against entitlement stereotype."),
        ("Kawan aku Sikh tu paling dermawan. Setiap bulan dia donate ke rumah anak yatim. Jangan judge ikut bangsa.",
         "ms", "Praising Sikh friend's charity, opposing racial judgment."),
        ("Cina penipu? Bos Cina aku paling jujur aku pernah jumpa. 10 tahun kerja takde masalah.",
         "ms", "Countering Chinese dishonesty stereotype with personal experience."),
        ("My Indian colleague is the most hardworking person I know. Stop spreading hate about any race lah.",
         "en", "Defending Indian colleague, calling out racial hate."),
        ("Kalau semua Bangla jahat macam korang cakap, kenapa ramai majikan nak hire mereka? Sebab rajin dan jujur.",
         "ms", "Defending Bangladeshi workers' work ethic."),
        ("Orang yang kata 'semua kaum X macam tu' tu sebenarnya yang bermasalah. Dunia ni pelbagai, terima je.",
         "ms", "Meta-defense: criticizing those who generalize about any race."),
        ("Don't tar all Chinese with the same brush. My Chinese friends stood by me during my hardest times.",
         "en", "Personal testimony defending Chinese friends."),
        ("Adik aku berkawan baik dengan budak India. Dua-dua tolong-menolong belajar. Itulah Malaysia sebenar.",
         "ms", "Children's interracial friendship as example of real Malaysia."),
    ]

    for text, lang, desc in texts:
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True, "severity": "S0",
            "triggered_principles": [], "risk_labels": [],
            "reason": desc,
            "rewrite_required": False, "suggested_rewrite": "",
            "reasoning": "The speaker is defending a community against negative stereotyping. The intent is pro-social — promoting understanding and countering prejudice. Even though ethnic terms are mentioned, the framing is clearly protective and constructive. Safe.",
        })
    return examples


# ─── Main ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Generating Round 2 FIXED augmented data...\n")
    print("REMOVED: P1 (quote-launder, 25 unsafe) — caused contrastive confusion")
    print("REMOVED: P7 (communal counterbalance, 25 unsafe) — caused contrastive confusion")
    print("EXPANDED: P8 nostalgia (13 → 30)")
    print("ADDED: P10 ethnic defense (15 new safe examples)")
    print()

    p2 = gen_anecdote_restraint()
    p3 = gen_quote_reform()
    p4 = gen_chinese_sarcasm()
    p5 = gen_code_switch_sarcasm()
    p6 = gen_labor_exploitation()
    p8 = gen_nostalgia_expanded()
    p9 = gen_debunk_nuanced()
    p10 = gen_ethnic_defense_expanded()

    print(f"  P2 anecdote-restraint (safe):     {len(p2)}")
    print(f"  P3 quote-reform (safe):           {len(p3)}")
    print(f"  P4 Chinese sarcasm (S1):          {len(p4)}")
    print(f"  P5 code-switch sarcasm (S1):      {len(p5)}")
    print(f"  P6 labor exploitation (S1):       {len(p6)}")
    print(f"  P8 nostalgia expanded (safe):     {len(p8)}")
    print(f"  P9 debunk nuanced (safe):         {len(p9)}")
    print(f"  P10 ethnic defense (safe):        {len(p10)}")

    all_r2fix = p2 + p3 + p4 + p5 + p6 + p8 + p9 + p10
    random.shuffle(all_r2fix)

    n_safe = sum(1 for ex in all_r2fix if ex['safe'])
    n_unsafe = sum(1 for ex in all_r2fix if not ex['safe'])
    print(f"\n  TOTAL R2-fix examples: {len(all_r2fix)}")
    print(f"  Safe: {n_safe} ({n_safe/len(all_r2fix):.0%}), Unsafe: {n_unsafe} ({n_unsafe/len(all_r2fix):.0%})")

    # Write R2-fix-only file
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'cot')
    r2fix_path = os.path.join(out_dir, 'train_augmented_r2_fix.jsonl')
    write_jsonl(r2fix_path, all_r2fix)

    # Load R1 augmented data and merge
    r1_aug_path = os.path.join(out_dir, 'train_cot_augmented.jsonl')
    existing = []
    with open(r1_aug_path) as f:
        for line in f:
            if line.strip():
                existing.append(json.loads(line))

    merged = existing + all_r2fix
    random.shuffle(merged)
    merged_path = os.path.join(out_dir, 'train_cot_augmented_r2_fix.jsonl')
    write_jsonl(merged_path, merged)

    print(f"\n  R1 augmented: {len(existing)}")
    print(f"  R2-fix new: {len(all_r2fix)}")
    print(f"  Merged total: {len(merged)}")

    safe_m = sum(1 for ex in merged if ex['safe'])
    unsafe_m = sum(1 for ex in merged if not ex['safe'])
    print(f"  Merged safe: {safe_m} ({safe_m/len(merged):.0%})")
    print(f"  Merged unsafe: {unsafe_m} ({unsafe_m/len(merged):.0%})")
