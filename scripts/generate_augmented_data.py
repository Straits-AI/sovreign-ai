"""
Generate augmented SFT training data to fix the 5 gap patterns
identified in scientific analysis of the 69% SFT baseline.

Gap patterns (from stress test error analysis):
1. Quote-and-condemn/report → safe (8 FP errors)
2. Pro-social defense → safe (5 FP errors)
3. Rumor debunking → safe (4 FP errors)
4. Nostalgia/anecdote → safe (5 FP errors)
5. Sarcastic political critique → S1 inflammatory_polarisation (8 FN errors)

Target: ~280 new examples across these 5 patterns.
"""

import json
import random
import os

random.seed(42)


def write_jsonl(path, data):
    with open(path, 'w') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"Wrote {len(data)} examples to {path}")


# ─── Pattern 1: Quote-and-condemn/report → safe ───────────────────────
# The model's #1 error: seeing slurs/offensive words and flagging as unsafe,
# even when the speaker is quoting to condemn, report, or educate.

SLURS_AND_CONTEXT = [
    ("Cina babi", "anti-Chinese slur", "MY-1"),
    ("balik tongsan", "xenophobic phrase against Chinese Malaysians", "MY-1"),
    ("keling", "racial slur against Indian Malaysians", "MY-1"),
    ("Melayu malas", "ethnic stereotype about Malays", "MY-1"),
    ("pendatang", "derogatory term for immigrants/non-Malays", "MY-1"),
    ("bangla", "derogatory term for Bangladeshi workers", "MY-1"),
    ("indon", "derogatory term for Indonesian workers", "MY-1"),
    ("balik negara kau", "xenophobic phrase telling people to leave", "MY-1"),
    ("kafir", "derogatory religious term", "MY-2"),
    ("DAPig", "political slur combining party name with pig", "MY-1"),
    ("Melayu bodoh", "ethnic insult against Malays", "MY-1"),
    ("mamak celaka", "ethnic slur against Indian Muslims", "MY-1"),
]

NEWS_SOURCES = [
    "Bernama", "Malaysiakini", "The Star", "NST", "Free Malaysia Today",
    "Berita Harian", "Malay Mail", "Astro Awani", "Harian Metro",
    "Sin Chew Daily", "China Press", "Tamil Nesan",
]

def gen_quote_condemn():
    examples = []

    # --- News reporting context ---
    templates_news = [
        "According to {source}, the suspect shouted '{slur}' at the victim during the incident in {location}.",
        "{source} reported that graffiti reading '{slur}' was found sprayed on a {place} wall in {location}.",
        "A {source} investigation documented {count} instances of the phrase '{slur}' in online forums monitored over {period}.",
        "In a viral video captured by bystanders, a man was heard yelling '{slur}' at a {worker}. {source} is investigating.",
        "The {source} editorial highlighted that terms like '{slur}' are still commonly used in Malaysian social media.",
        "{source} quoted witnesses who heard the attacker say '{slur}' before fleeing the scene in {location}.",
        "A report by {source} found that hate speech incidents involving phrases like '{slur}' increased {percent}% during the election period.",
    ]
    locations = ["Petaling Jaya", "Penang", "Johor Bahru", "Kuala Lumpur", "Ipoh", "Shah Alam", "Melaka", "Kota Kinabalu"]
    places = ["mosque", "temple", "school", "market", "kopitiam", "LRT station", "housing area"]
    workers = ["food delivery rider", "security guard", "cleaner", "construction worker", "market vendor", "taxi driver"]
    periods = ["three months", "six months", "the past year", "two weeks"]
    counts = ["47", "88", "156", "203", "312"]
    percents = ["23", "35", "41", "67"]

    for _ in range(20):
        slur_item = random.choice(SLURS_AND_CONTEXT)
        slur, desc, principle = slur_item
        tmpl = random.choice(templates_news)
        text = tmpl.format(
            source=random.choice(NEWS_SOURCES),
            slur=slur,
            location=random.choice(locations),
            place=random.choice(places),
            worker=random.choice(workers),
            period=random.choice(periods),
            count=random.choice(counts),
            percent=random.choice(percents),
        )
        examples.append({
            "input_text": text,
            "language": "en",
            "safe": True,
            "severity": "S0",
            "triggered_principles": [],
            "risk_labels": [],
            "reason": f"News reporting quoting '{slur}' in factual context. {desc} mentioned for documentation.",
            "rewrite_required": False,
            "suggested_rewrite": "",
            "reasoning": f"This is a news report quoting '{slur}' to document an incident. The journalist is reporting facts, not endorsing the slur. The quoting serves informational purposes. Safe.",
        })

    # --- Social media condemning context ---
    templates_condemn_en = [
        "Overheard someone say '{slur}' at the {place} today. {year} and people still talk like this. So disappointing.",
        "Can't believe my colleague just said '{slur}' in the meeting. I reported it to HR. This is NOT okay.",
        "Someone graffitied '{slur}' on my neighbor's wall. We're all helping to clean it up. Hate has no place here.",
        "My kid came home crying because a classmate called them '{slur}'. We need to teach our children better.",
        "Thread: Someone posted '{slur}' in our neighborhood chat. THIS is the kind of ignorance we need to call out.",
        "Disgusting. Someone yelled '{slur}' at a {worker} today. If you see this happening, speak up.",
        "Saw a comment saying '{slur}' get 200 likes on Facebook. This is why we need media literacy education.",
    ]
    templates_condemn_ms = [
        "Tadi dengar orang cakap '{slur}' kat {place_ms}. Tahun {year} masih ada orang macam ni. Sedih lah.",
        "Makcik jiran cakap '{slur}' depan anak-anak. Aku tegur dia. Tak boleh biar budak-budak dengar benda macam ni.",
        "Ada orang tulis '{slur}' kat dinding {place_ms}. Kita semua tolong bersihkan. Benci tak ada tempat di sini.",
        "Anak aku balik sekolah nangis sebab kawan panggil dia '{slur}'. Kita kena ajar anak-anak hormat semua kaum.",
        "Group WhatsApp kampung aku ada orang share gambar tulis '{slur}'. Aku report terus. Tak boleh toleransi benda macam ni.",
    ]
    places_ms = ["pasar", "kedai mamak", "kopitiam", "stesen LRT", "sekolah", "taman perumahan"]
    years = ["2024", "2025", "2026"]

    for _ in range(18):
        slur_item = random.choice(SLURS_AND_CONTEXT)
        slur, desc, principle = slur_item
        if random.random() < 0.5:
            tmpl = random.choice(templates_condemn_en)
            lang = "en"
        else:
            tmpl = random.choice(templates_condemn_ms)
            lang = "ms"
        text = tmpl.format(
            slur=slur,
            place=random.choice(places),
            place_ms=random.choice(places_ms),
            worker=random.choice(workers),
            year=random.choice(years),
        )
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True,
            "severity": "S0",
            "triggered_principles": [],
            "risk_labels": [],
            "reason": f"Speaker quotes '{slur}' to condemn its use. Constructive call against hate speech.",
            "rewrite_required": False,
            "suggested_rewrite": "",
            "reasoning": f"The speaker quotes '{slur}' not to endorse it but to condemn its use. The framing shows disapproval and calls for change. This is a constructive anti-hate response. Safe.",
        })

    # --- Personal testimony context ---
    templates_testimony = [
        "When I was growing up, someone called me '{slur}' and it still hurts. We need to teach our children to respect everyone.",
        "I still remember being called '{slur}' in school. That experience shaped my commitment to fighting discrimination.",
        "My grandfather was called '{slur}' his whole life. He never let it break his spirit. We carry his strength forward.",
        "Masa kecil dulu, kawan panggil aku '{slur}'. Sampai sekarang ingat lagi. Sebab tu aku ajar anak aku hormat semua orang.",
        "First day at work, colleague bisik '{slur}' behind my back. I confronted them professionally. Education is the way forward.",
    ]

    for _ in range(12):
        slur_item = random.choice(SLURS_AND_CONTEXT)
        slur, desc, principle = slur_item
        tmpl = random.choice(templates_testimony)
        text = tmpl.format(slur=slur)
        lang = "ms" if "Masa" in text or "aku" in text else "en"
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True,
            "severity": "S0",
            "triggered_principles": [],
            "risk_labels": [],
            "reason": f"Personal testimony about experiencing '{slur}'. Constructive call for change.",
            "rewrite_required": False,
            "suggested_rewrite": "",
            "reasoning": f"The speaker shares a personal experience of hearing '{slur}' to advocate against its use. The testimony is constructive — condemning the slur, not endorsing it. This is a healing narrative. Safe.",
        })

    return examples


# ─── Pattern 2: Pro-social defense → safe ──────────────────────────────
# Model flags content as unsafe when speakers DEFEND ethnic/religious groups.

def gen_pro_social():
    examples = []

    templates = [
        "Eh jangan lah cakap macam tu pasal orang {group}. {friend_ref}, baik orangnya.",
        "Don't generalize lah. Not all {group} people are like that. {positive_point}.",
        "Aku tak setuju bila orang kutuk {group}. {positive_fact}.",
        "Hey stop spreading hate about {group} lah. {positive_point}.",
        "Asal kau cakap macam tu pasal {group}? {friend_ref}. Jangan stereotype.",
        "People who bash {group} have never actually lived among them. {positive_fact}.",
        "Bro jangan lah label semua {group} macam tu. {positive_point}.",
        "I'm {own_group} and my best friend is {group}. {positive_fact}. Stop the hate.",
        "Sesiapa yang kata semua orang {group} macam tu memang tak pernah kenal {group}. {positive_point}.",
        "Kawasan aku ramai {group}, semua friendly. {positive_fact}. Jangan dengar stereotype.",
    ]

    groups = ["India", "Cina", "Melayu", "Iban", "Kadazan", "Orang Asli", "Bangla", "Indonesia"]
    own_groups = ["Malay", "Chinese", "Indian", "Sarawakian"]
    friend_refs = [
        "Kawan aku pun {group}", "Jiran aku {group}", "Boss aku {group}",
        "Cikgu aku masa sekolah {group}", "My business partner is {group}",
    ]
    positive_points = [
        "They contribute a lot to our economy",
        "Diorang pun rakyat Malaysia jugak",
        "Semua kaum ada yang baik dan buruk",
        "Every community has good and bad people",
        "They're hardworking and honest",
        "Diorang banyak tolong masyarakat",
        "Many of them are our front-line workers",
        "Without them our food industry would collapse",
    ]
    positive_facts = [
        "I've seen their generosity firsthand during floods",
        "Masa COVID diorang tolong bagi makanan percuma",
        "They run the small businesses that serve us all",
        "Our neighborhood is better because of diversity",
        "The unity during Merdeka proves we're stronger together",
        "Diorang antara yang pertama tolong masa banjir",
    ]

    for _ in range(40):
        group = random.choice(groups)
        tmpl = random.choice(templates)
        text = tmpl.format(
            group=group,
            own_group=random.choice(own_groups),
            friend_ref=random.choice(friend_refs).format(group=group),
            positive_point=random.choice(positive_points),
            positive_fact=random.choice(positive_facts),
        )
        lang = "ms" if any(w in text for w in ["aku", "lah", "Jangan", "Sesiapa", "Asal kau"]) else "en"
        if "lah" in text.lower() and "don't" in text.lower():
            lang = "mixed"

        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True,
            "severity": "S0",
            "triggered_principles": [],
            "risk_labels": [],
            "reason": f"Pro-social defense of {group} community. Calling out prejudice constructively.",
            "rewrite_required": False,
            "suggested_rewrite": "",
            "reasoning": f"The speaker is defending the {group} community against prejudice. Mentioning ethnic groups in a positive or protective context is safe. This is constructive anti-discrimination speech. Safe.",
        })

    return examples


# ─── Pattern 3: Rumor debunking → safe ─────────────────────────────────
# Model flags rumor debunking as misinformation instead of recognizing the debunking frame.

def gen_rumor_debunking():
    examples = []

    rumors = [
        ("air zamzam palsu mengandungi bahan kimia berbahaya", "fake zamzam water", "religious"),
        ("vaksin COVID ada cip 5G untuk track rakyat", "5G chip in vaccines", "health"),
        ("kerajaan nak hapuskan subsidi minyak 100%", "complete fuel subsidy removal", "economic"),
        ("air paip dicampur racun oleh pihak tertentu", "water supply poisoning", "safety"),
        ("PTPTN loan recipients will be blacklisted from traveling", "PTPTN travel ban", "economic"),
        ("nasi kandar ada bahan pengawet yang boleh sebabkan kanser", "nasi kandar preservatives cause cancer", "health"),
        ("bank akan tutup semua akaun yang tak update IC baru", "bank account closures", "economic"),
        ("RM1 coin baru ada GPS tracker", "GPS in new coins", "conspiracy"),
        ("makan durian dan minum bir boleh mati", "durian and beer death", "health"),
        ("orang asing merancang untuk ambil alih tanah Melayu", "foreign land takeover", "conspiracy"),
        ("5G tower boleh sebabkan kanser otak", "5G cancer", "health"),
        ("gula dalam air mineral jenama X melebihi had selamat", "unsafe sugar in water", "health"),
    ]

    debunk_frames_ms = [
        "Dalam group WhatsApp family aku, ada orang share yang {rumor}. Aku dah check dengan {authority} — CONFIRM FAKE. Jangan percaya.",
        "Viral kat Facebook kata {rumor}. Ini hoax. {authority} dah nafikan. Tolong jangan forward.",
        "Alert! Ada mesej viral cakap {rumor}. Ini PALSU. Sumber asal dah ditarik balik. Jangan sebarkan.",
        "Uncle forward pasal {rumor}. Aku cari sumber — takde bukti langsung. {authority} dah sahkan ini fake news.",
        "Banyak orang forward pasal {rumor}. FAKE NEWS. Sila semak {authority} sebelum forward.",
        "Makcik group chat share pasal {rumor}. Aku tegur — ini dah debunked oleh {authority}.",
    ]

    debunk_frames_en = [
        "Someone in my family chat shared that {rumor}. I checked with {authority} — it's FAKE. Please don't spread this.",
        "Viral message claiming {rumor}. This is a hoax. {authority} has denied it. Don't forward.",
        "PSA: The viral claim about {rumor} is FALSE. Verified with {authority}. Stop sharing unverified info.",
        "My parents forwarded a message about {rumor}. I fact-checked it — completely made up. {authority} confirmed.",
    ]

    authorities = [
        "KKM (Kementerian Kesihatan)", "MCMC", "PDRM", "Sebenarnya.my",
        "the Ministry of Health", "SPAN", "BNM (Bank Negara)", "official government channels",
        "Reuters fact-check", "AFP Fact Check", "BERNAMA",
    ]

    for _ in range(35):
        rumor_item = random.choice(rumors)
        rumor_text, rumor_desc, rumor_type = rumor_item
        if random.random() < 0.55:
            tmpl = random.choice(debunk_frames_ms)
            lang = "ms"
        else:
            tmpl = random.choice(debunk_frames_en)
            lang = "en"
        text = tmpl.format(
            rumor=rumor_text,
            authority=random.choice(authorities),
        )
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True,
            "severity": "S0",
            "triggered_principles": [],
            "risk_labels": [],
            "reason": f"Speaker debunks viral rumor about {rumor_desc}. Anti-misinformation effort.",
            "rewrite_required": False,
            "suggested_rewrite": "",
            "reasoning": f"The speaker is debunking a viral rumor about '{rumor_desc}', not spreading it. They cite an authority and urge others not to forward. This is constructive anti-misinformation. Safe.",
        })

    return examples


# ─── Pattern 4: Nostalgia/anecdote → safe ──────────────────────────────
# Model flags nostalgic reflections on inter-ethnic relations as harmful.

def gen_nostalgia():
    examples = []

    templates_ms = [
        "Auntie kat {place_ms} cakap: '{nostalgia_ms}' Rindu zaman dulu.",
        "Uncle cerita masa dulu kat {place_ms}: '{nostalgia_ms}' Sekarang dah tak macam tu.",
        "Teringat zaman kecil, {nostalgia_ms} Sekarang semua sibuk dengan telefon.",
        "Arwah atuk selalu cakap: '{nostalgia_ms}' Kita patut ikut nasihat orang tua.",
        "Makcik jiran dulu selalu bagi kuih raya, kita bagi mooncake. {nostalgia_ms}",
        "Zaman sekolah dulu {nostalgia_ms} Sekarang anak-anak semua sekolah lain-lain.",
        "Dulu kat kampung semua kaum hidup aman. {nostalgia_ms} Rindu masa tu.",
    ]

    templates_en = [
        "My grandmother always said: '{nostalgia_en}' Those were simpler times.",
        "Growing up in {location}, {nostalgia_en} I miss those days.",
        "Remember when we used to celebrate {festival} together? {nostalgia_en}",
        "My late father would always tell us: '{nostalgia_en}' We should listen to our elders.",
        "Back in the 80s/90s in {location}, {nostalgia_en} Times have changed.",
    ]

    nostalgia_ms_list = [
        "dulu semua kaum boleh duduk satu meja makan, sekarang semua nak separate. Sedih lah.",
        "masa aku kecik, jiran Cina, India, Melayu semua macam family. Sekarang semua pagar tinggi.",
        "dulu raya semua rumah open house, tak kira bangsa apa. Sekarang makin kurang.",
        "dulu makan kat gerai mamak sama-sama, takde siapa tanya halal ke tak. Semua percaya.",
        "dulu main guli sama-sama, tak kisah Melayu Cina India. Sekarang anak-anak main sendiri.",
        "masa zaman sekolah, kawan baik aku ada Melayu, Cina, India. Sekarang semua jauh.",
        "dulu kampung ni ramai semua kaum, sekarang satu persatu pindah. Kehilangan keharmonian.",
        "zaman dulu gotong-royong tak kira kaum. Sekarang siapa tolong siapa?",
    ]

    nostalgia_en_list = [
        "we used to share food across racial lines without thinking twice. Now everything is so divided.",
        "our street had Malay, Chinese, Indian families all celebrating together. I miss that unity.",
        "during festivals, every house was open to everyone regardless of race. Those were beautiful times.",
        "neighborhoods used to be truly multiracial. Children played together naturally.",
        "we never thought about race when choosing friends. It was just about being good people.",
        "community spirit meant everyone helped everyone. Racial lines didn't matter in a crisis.",
        "the kopitiam was where all races met, talked, laughed together. That's the real Malaysia.",
    ]

    locations = ["Penang", "Ipoh", "Melaka", "KL", "JB", "Kuching", "Kota Bharu"]
    festivals = ["Hari Raya", "CNY", "Deepavali", "Christmas", "Thaipusam"]
    places_ms = ["pasar", "kedai kopi", "taman", "masjid", "surau", "balai raya"]

    for _ in range(35):
        if random.random() < 0.55:
            tmpl = random.choice(templates_ms)
            text = tmpl.format(
                place_ms=random.choice(places_ms),
                nostalgia_ms=random.choice(nostalgia_ms_list),
            )
            lang = "ms"
            nostalgia_snippet = text[:60]
        else:
            tmpl = random.choice(templates_en)
            text = tmpl.format(
                nostalgia_en=random.choice(nostalgia_en_list),
                location=random.choice(locations),
                festival=random.choice(festivals),
            )
            lang = "en"
            nostalgia_snippet = text[:60]

        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True,
            "severity": "S0",
            "triggered_principles": [],
            "risk_labels": [],
            "reason": "Nostalgic reflection on inter-ethnic harmony. Safe expression of sadness about social change.",
            "rewrite_required": False,
            "suggested_rewrite": "",
            "reasoning": "The speaker is expressing nostalgia about a time when inter-ethnic relations were perceived as closer. This is a personal reflection, not incitement or prejudice. Expressing sadness about social change is legitimate speech. Safe.",
        })

    return examples


# ─── Pattern 5: Sarcastic political critique → S1 inflammatory ─────────
# Model misses sarcasm directed at government/politicians, calling it "legitimate criticism" (safe).
# These should be S1 inflammatory_polarisation.

def gen_sarcastic_political():
    examples = []

    templates_ms = [
        "Haha {politician_ref} cakap {claim_ms}. {sarcasm_ms}",
        "Bagus lah {politician_ref}. {claim_ms}. Meanwhile rakyat {suffering_ms}.",
        "Tahniah {politician_ref}! {claim_ms}. Rakyat {suffering_ms}. Terbaik!",
        "Wah hebat {politician_ref}. {claim_ms}. Tapi kat bawah ni {suffering_ms}. Lawak.",
        "{politician_ref} kata {claim_ms}. Lawak terbaik {year}. {sarcasm_ms}",
        "Syabas {politician_ref}. {claim_ms}. {sarcasm_ms} Negara maju katanya.",
    ]

    templates_en = [
        "Haha {politician_ref} says {claim_en}. {sarcasm_en}",
        "Brilliant move by {politician_ref}. {claim_en}. Meanwhile we {suffering_en}.",
        "Wow {politician_ref} really said {claim_en}. {sarcasm_en} Comedy gold.",
        "Dear {politician_ref}, you said {claim_en}. {sarcasm_en}",
    ]

    templates_mixed = [
        "Bro {politician_ref} cakap {claim_ms}. Like hello? {sarcasm_en}",
        "{politician_ref} kata {claim_ms} but reality is {suffering_en}. Priorities much?",
        "LOL {politician_ref} announce {claim_en}. Meanwhile kat bawah {suffering_ms}. Best.",
    ]

    templates_zh = [
        "哈哈{politician_ref}说{claim_zh}。{sarcasm_zh}",
        "{politician_ref}说{claim_zh}。到底哪个马来西亚{claim_zh}？{sarcasm_zh}",
        "厉害了{politician_ref}。{claim_zh}。百姓{suffering_zh}。真棒。",
    ]

    politician_refs = [
        "PM", "Menteri", "YB", "kerajaan", "gomen", "politician",
        "minister", "government", "Dato' Sri", "wakil rakyat",
    ]

    claims_ms = [
        "ekonomi bagus", "rakyat didahulukan", "kos hidup terkawal",
        "semua rakyat akan dapat manfaat", "negara akan maju menjelang 2030",
        "pengangguran rendah", "pendidikan bertaraf dunia",
        "gaji pekerja akan naik", "tiada rasuah dalam kerajaan",
    ]

    claims_en = [
        "the economy is doing great", "people come first",
        "cost of living is under control", "we're on track for developed nation status",
        "unemployment is at historic lows", "everyone will benefit",
        "there's no corruption", "the system works for everyone",
    ]

    claims_zh = [
        "经济很好", "人民优先", "生活费受控",
        "国家即将成为发达国", "失业率很低",
    ]

    sarcasm_ms = [
        "Meanwhile kawan dia dapat projek billion.",
        "Rakyat didahulukan kena bayar tol la, bayar cukai la. Mana prioriti?",
        "Cuba tanya makcik jual nasi lemak tepi jalan tu.",
        "Aku rasa dia tak pernah masuk pasar.",
        "Bagus untuk siapa? Untuk kroni dia la.",
        "Tapi gaji aku sama je dari 5 tahun lepas.",
        "Rumah pun tak mampu nak beli. Terbaik!",
    ]

    sarcasm_en = [
        "Meanwhile his friend got the billion-ringgit contract.",
        "Tell that to the families eating Maggi for dinner.",
        "Must be nice living in a different Malaysia than the rest of us.",
        "I wonder which economy he's looking at. Not the one I live in.",
        "Clearly has never set foot in a wet market.",
        "Sure, if you define 'great' as 'great for cronies'.",
        "My wallet disagrees. My landlord disagrees. My stomach disagrees.",
    ]

    sarcasm_zh = [
        "部长们住的那个马来西亚吗？",
        "人民的钱去了哪里？",
        "告诉住在组屋的老百姓看看。",
        "也许他看的是另一个国家的数据。",
    ]

    suffering_ms = [
        "makan maggi setiap hari", "tak mampu bayar sewa",
        "kerja 2 kerja tapi still tak cukup", "beratur panjang kat kedai RM2",
        "hutang PTPTN tak habis-habis", "gaji sama dari 10 tahun lepas",
    ]

    suffering_en = [
        "can't afford rent", "eat Maggi every day",
        "work two jobs and still struggle", "queue at the RM2 shop",
        "drown in PTPTN debt", "haven't had a raise in years",
    ]

    suffering_zh = [
        "吃不起饭", "交不起房租", "打两份工还是不够",
    ]

    years = ["2024", "2025", "2026"]

    for _ in range(60):
        r = random.random()
        if r < 0.35:
            tmpl = random.choice(templates_ms)
            text = tmpl.format(
                politician_ref=random.choice(politician_refs),
                claim_ms=random.choice(claims_ms),
                sarcasm_ms=random.choice(sarcasm_ms),
                suffering_ms=random.choice(suffering_ms),
                year=random.choice(years),
            )
            lang = "ms"
        elif r < 0.55:
            tmpl = random.choice(templates_en)
            text = tmpl.format(
                politician_ref=random.choice(politician_refs),
                claim_en=random.choice(claims_en),
                sarcasm_en=random.choice(sarcasm_en),
                suffering_en=random.choice(suffering_en),
            )
            lang = "en"
        elif r < 0.8:
            tmpl = random.choice(templates_mixed)
            text = tmpl.format(
                politician_ref=random.choice(politician_refs),
                claim_ms=random.choice(claims_ms),
                claim_en=random.choice(claims_en),
                sarcasm_en=random.choice(sarcasm_en),
                suffering_ms=random.choice(suffering_ms),
                suffering_en=random.choice(suffering_en),
            )
            lang = "mixed"
        else:
            tmpl = random.choice(templates_zh)
            text = tmpl.format(
                politician_ref=random.choice(politician_refs),
                claim_zh=random.choice(claims_zh),
                sarcasm_zh=random.choice(sarcasm_zh),
                suffering_zh=random.choice(suffering_zh),
            )
            lang = "zh"

        # All sarcastic political critiques → S1 inflammatory_polarisation
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": False,
            "severity": "S1",
            "triggered_principles": ["MY-5"],
            "risk_labels": ["inflammatory_polarisation"],
            "reason": "Sarcastic political commentary using irony to attack government policy. Inflammatory framing even if criticism is legitimate.",
            "rewrite_required": True,
            "suggested_rewrite": "Economic concerns and government accountability are important issues that citizens can raise through constructive democratic channels.",
            "reasoning": "The speaker uses sarcasm and irony to critique government claims about economic performance. While the underlying frustration may be legitimate, the inflammatory framing ('lawak', 'meanwhile rakyat...') polarizes rather than constructively criticizes. S1 inflammatory_polarisation.",
        })

    return examples


# ─── Bonus: Additional safe everyday examples ──────────────────────────
# To balance the dataset (training data has fewer safe examples than unsafe)

def gen_safe_everyday():
    examples = []

    texts = [
        ("Hari ni cuaca panas gila. Jom minum air kelapa kat pantai!", "ms"),
        ("Best nasi lemak kat Kampung Baru. Sambal dia memang power.", "ms"),
        ("Raya tahun ni plan nak balik kampung Kelantan. Rindu masakan mak.", "ms"),
        ("CNY dinner with the whole family was amazing. Yee sang this year was the best!", "en"),
        ("Deepavali lights at Batu Caves were stunning. Proud to be Malaysian.", "en"),
        ("Weekend ni nak hiking Broga Hill. Anyone want to join?", "en"),
        ("Teh tarik kat mamak corner tu memang sedap. Dah 20 tahun pergi situ.", "ms"),
        ("My neighbor uncle always shares his homegrown chili with us. Malaysian hospitality at its finest.", "en"),
        ("Anak-anak main bunga api masa Merdeka. Gembira tengok.", "ms"),
        ("Durian season! Musang King mahal tapi worth it.", "mixed"),
        ("Traffic jam KL macam biasa. Nasib ada podcast baru nak dengar.", "mixed"),
        ("今天天气真好，去吃个肉骨茶。", "zh"),
        ("Kuih lapis makcik sebelah rumah memang terbaik. Setiap kali raya mesti ada.", "ms"),
        ("Took my kids to the zoo. They loved the orangutans. Good family outing.", "en"),
        ("Pasar malam hari Rabu best. Satay dia power, rojak pun sedap.", "ms"),
    ]

    for text, lang in texts:
        examples.append({
            "input_text": text,
            "language": lang,
            "safe": True,
            "severity": "S0",
            "triggered_principles": [],
            "risk_labels": [],
            "reason": "Everyday Malaysian conversation. No harmful content.",
            "rewrite_required": False,
            "suggested_rewrite": "",
            "reasoning": "Everyday Malaysian social conversation about food, weather, family, or activities. No harmful content, no targeting of any group. Safe.",
        })

    return examples


# ─── Main: Generate all and merge ──────────────────────────────────────

if __name__ == '__main__':
    print("Generating augmented training data...")

    p1 = gen_quote_condemn()
    p2 = gen_pro_social()
    p3 = gen_rumor_debunking()
    p4 = gen_nostalgia()
    p5 = gen_sarcastic_political()
    p6 = gen_safe_everyday()

    print(f"  Pattern 1 (quote-condemn → safe):     {len(p1)}")
    print(f"  Pattern 2 (pro-social → safe):         {len(p2)}")
    print(f"  Pattern 3 (rumor debunking → safe):    {len(p3)}")
    print(f"  Pattern 4 (nostalgia → safe):          {len(p4)}")
    print(f"  Pattern 5 (sarcastic political → S1):  {len(p5)}")
    print(f"  Bonus (safe everyday):                 {len(p6)}")

    all_new = p1 + p2 + p3 + p4 + p5 + p6
    random.shuffle(all_new)
    print(f"\n  TOTAL new examples: {len(all_new)}")

    n_safe = sum(1 for ex in all_new if ex['safe'])
    n_unsafe = sum(1 for ex in all_new if not ex['safe'])
    print(f"  Safe: {n_safe}, Unsafe: {n_unsafe}")

    # Write augmented-only file
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'cot')
    aug_path = os.path.join(out_dir, 'train_augmented_gaps.jsonl')
    write_jsonl(aug_path, all_new)

    # Merge with existing training data
    existing_path = os.path.join(out_dir, 'train_cot_final.jsonl')
    existing = []
    with open(existing_path) as f:
        for line in f:
            if line.strip():
                existing.append(json.loads(line))

    merged = existing + all_new
    random.shuffle(merged)
    merged_path = os.path.join(out_dir, 'train_cot_augmented.jsonl')
    write_jsonl(merged_path, merged)

    print(f"\n  Existing: {len(existing)}")
    print(f"  Merged total: {len(merged)}")

    # Stats
    safe_merged = sum(1 for ex in merged if ex['safe'])
    unsafe_merged = sum(1 for ex in merged if not ex['safe'])
    print(f"  Merged safe: {safe_merged} ({safe_merged/len(merged):.0%})")
    print(f"  Merged unsafe: {unsafe_merged} ({unsafe_merged/len(merged):.0%})")

    # Category distribution
    cats = {}
    for ex in merged:
        for rl in ex.get('risk_labels', []):
            cats[rl] = cats.get(rl, 0) + 1
    print(f"\n  Risk label distribution:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count} ({count/len(merged):.1%})")
