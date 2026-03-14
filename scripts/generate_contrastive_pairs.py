"""Generate contrastive pairs for chain-of-thought fine-tuning.

Each pair: same topic, minimal edit, different verdict (safe vs unsafe).
Teaches the model to attend to context signals, not just keywords.

Uses template-based generation with variation to create large numbers of
high-quality contrastive pairs without API calls.

Usage:
    # Preview seed templates:
    python scripts/generate_contrastive_pairs.py --dry-run

    # Generate all pairs:
    python scripts/generate_contrastive_pairs.py --output data/cot/contrastive_pairs.jsonl
"""
import argparse
import json
import random
from pathlib import Path

random.seed(42)


def ex(input_text, language, safe, severity, principles, labels, reason,
       rewrite_required, suggested_rewrite, reasoning, edge_case_type, pair_id):
    """Create a single dataset example with reasoning."""
    return {
        "input_text": input_text,
        "language": language,
        "safe": safe,
        "severity": severity,
        "triggered_principles": principles,
        "risk_labels": labels,
        "reason": reason,
        "rewrite_required": rewrite_required,
        "suggested_rewrite": suggested_rewrite,
        "reasoning": reasoning,
        "edge_case_type": edge_case_type,
        "contrastive_pair_id": pair_id,
    }


# ═══════════════════════════════════════════════════════════════
# QUOTED OFFENSIVE PAIRS
# Safe: reporting/condemning context
# Unsafe: endorsing/amplifying context
# ═══════════════════════════════════════════════════════════════

def generate_quoted_offensive() -> list[dict]:
    """Generate quoted offensive contrastive pairs."""
    pairs = []
    pair_id = 0

    # Pattern 1: News reporting vs endorsement
    slurs = [
        ("Balik negara kau", "racial expulsion phrase"),
        ("pendatang haram", "illegal immigrant slur"),
        ("Cina babi", "racial slur against Chinese Malaysians"),
        ("keling", "racial slur against Indian Malaysians"),
        ("Melayu malas", "ethnic stereotype about Malays"),
        ("bangla", "derogatory term for Bangladeshi workers"),
        ("indon", "derogatory term for Indonesian workers"),
        ("kafir", "derogatory term used against non-Muslims"),
        ("sesat", "term labeling another faith as deviant"),
        ("DAPig", "political slur combining party name with insult"),
    ]

    # News contexts
    news_sources = ["The Star", "Berita Harian", "Malaysiakini", "Free Malaysia Today", "Sinar Harian"]
    news_templates_safe = [
        "{source} reported that a man was arrested after shouting '{slur}' at a {victim} in {place}. Police are investigating under Section 504.",
        "According to {source}, a viral video shows a person using the term '{slur}' in a heated argument at {place}. The incident has been condemned by local leaders.",
        "{source} — A complaint was filed after someone repeatedly called a colleague '{slur}' at the workplace. HR is investigating the incident.",
        "In its report on hate speech trends, {source} documented increased use of terms like '{slur}' on social media during the election period.",
        "A {source} investigation found that the phrase '{slur}' was used {count} times in community WhatsApp groups monitored over the past month.",
    ]
    endorsement_templates_unsafe = [
        "Betul la, '{slur}!' Memang patut cakap macam tu. Dah lama kita tahan. Share kalau setuju.",
        "Finally someone brave enough to say '{slur}' out loud. Ramai yang setuju tapi takut nak cakap. This is the truth.",
        "'{slur}' — that's just calling it what it is. Don't be so sensitive. Zaman dulu semua orang cakap macam tu, tak ada masalah.",
        "My uncle also always says '{slur}' and he's right. Memang fakta pun. People need to hear the truth.",
        "Someone posted '{slur}' in the group and everyone agreed. It's not racist, it's reality. Wake up Malaysia.",
    ]
    victims = ["food stall operator", "taxi driver", "neighbor", "security guard", "delivery rider", "shopkeeper"]
    places = ["a hawker center", "a parking lot", "Pasar Seni", "Bangsar", "Petaling Jaya", "a shopping mall"]

    for slur_text, slur_desc in slurs:
        for _ in range(3):  # 3 variations per slur
            source = random.choice(news_sources)
            victim = random.choice(victims)
            place = random.choice(places)
            count = random.randint(50, 500)

            safe_template = random.choice(news_templates_safe)
            safe_text = safe_template.format(
                source=source, slur=slur_text, victim=victim, place=place, count=count
            )
            unsafe_template = random.choice(endorsement_templates_unsafe)
            unsafe_text = unsafe_template.format(slur=slur_text)

            pid = f"QO-{pair_id:04d}"
            pairs.append(ex(
                safe_text, random.choice(["en", "mixed"]), True, "S0", [], [],
                f"News reporting quoting '{slur_text}' in factual context. {slur_desc} mentioned for documentation.",
                False, "",
                f"This is a news report quoting '{slur_text}' to document an incident. The {source} journalist is reporting facts, not endorsing the slur. The quoting serves informational purposes within a journalistic context.",
                "quoted_offensive", f"{pid}-safe",
            ))
            pairs.append(ex(
                unsafe_text, random.choice(["ms", "mixed"]), False, "S2",
                ["MY-1", "MY-4"], ["communal_hostility"],
                f"Endorses and amplifies the slur '{slur_text}' with call to share. Communal hostility.",
                True, "Bahasa yang menghina kaum lain tidak boleh diterima. Kita perlu menghormati semua rakyat Malaysia.",
                f"The speaker endorses the racial slur '{slur_text}' by agreeing with it and calling for amplification. This is not reporting — the speaker validates and normalizes the slur. This constitutes communal hostility.",
                "quoted_offensive", f"{pid}-unsafe",
            ))
            pair_id += 1

    # Pattern 2: Court/legal testimony vs agreement
    legal_contexts = [
        ("Dalam perbicaraan, saksi menyatakan tertuduh berkata '{slur}' kepada mangsa. Hakim merekodkan keterangan ini.",
         "Memang betul apa tertuduh cakap — '{slur}.' Ramai yang setuju tapi tak berani cakap."),
        ("Laporan polis mencatatkan suspek menggunakan perkataan '{slur}' sebanyak tiga kali semasa kejadian.",
         "'{slur}' — orang dah mula berani cakap benda betul. Tahniah! Lama dah kita simpan."),
        ("Tribunal Hak Asasi Manusia merekodkan penggunaan ungkapan '{slur}' sebagai bukti diskriminasi.",
         "Kalau tribunal pun record '{slur}', maknanya memang betul la kan? Even official bodies agree."),
    ]

    for slur_text, slur_desc in slurs[:7]:
        safe_template, unsafe_template = random.choice(legal_contexts)
        safe_text = safe_template.format(slur=slur_text)
        unsafe_text = unsafe_template.format(slur=slur_text)

        pid = f"QO-{pair_id:04d}"
        pairs.append(ex(
            safe_text, "ms", True, "S0", [], [],
            f"Legal/court context quoting '{slur_text}' as evidence. Factual documentation.",
            False, "",
            f"This is a legal/court record quoting '{slur_text}' as documented evidence. The speaker is providing testimony or recording facts, not expressing personal views. The judicial context frames this as factual documentation.",
            "quoted_offensive", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, random.choice(["ms", "mixed"]), False, "S2",
            ["MY-1", "MY-4"], ["communal_hostility"],
            f"Endorses the slur '{slur_text}' by misusing official context to validate it.",
            True, "Bahasa diskriminasi tetap salah walaupun dilaporkan dalam konteks rasmi.",
            f"The speaker misappropriates a legal/official context to validate the slur '{slur_text}'. 'Memang betul' signals endorsement, not reporting. This turns documentation into validation of communal hostility.",
            "quoted_offensive", f"{pid}-unsafe",
        ))
        pair_id += 1

    # Pattern 3: Personal testimony vs nostalgia for slurs
    testimony_pairs = [
        ("When I was growing up, someone called me '{slur}' and it still hurts. We need to teach our children to respect everyone.",
         "Dulu boleh panggil '{slur}', sekarang semua nak sensitif. Zaman dulu lagi bagus, orang tau tempat masing-masing."),
        ("I heard someone use '{slur}' at the market yesterday and was shocked. I thought we were past this as a society.",
         "Orang guna '{slur}' kat pasar semalam. At least ada orang yang masih berani cakap. Respect."),
        ("My colleague told me she was called '{slur}' at work. This is unacceptable in modern Malaysia. HR needs to act.",
         "Colleague kena panggil '{slur}' — and honestly? That's just how people talk la. Don't be so soft."),
    ]

    for slur_text, slur_desc in slurs[:8]:
        safe_template, unsafe_template = random.choice(testimony_pairs)
        safe_text = safe_template.format(slur=slur_text)
        unsafe_text = unsafe_template.format(slur=slur_text)

        pid = f"QO-{pair_id:04d}"
        pairs.append(ex(
            safe_text, random.choice(["en", "mixed"]), True, "S0", [], [],
            f"Personal testimony about experiencing '{slur_text}'. Constructive call for change.",
            False, "",
            f"The speaker shares a personal experience of hearing '{slur_text}' to advocate against its use. The testimony is constructive — condemning the slur, not endorsing it. This is a healing narrative.",
            "quoted_offensive", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, random.choice(["ms", "mixed", "en"]), False, "S2",
            ["MY-1", "MY-4"], ["communal_hostility"],
            f"Normalizes or endorses the slur '{slur_text}'. Dismisses harm as oversensitivity.",
            True, "Bahasa yang menghina sentiasa salah. Masyarakat moden perlu menghormati semua.",
            f"The speaker endorses or normalizes the slur '{slur_text}' by framing objections to it as oversensitivity. This dismisses the real harm caused by discriminatory language and perpetuates communal hostility.",
            "quoted_offensive", f"{pid}-unsafe",
        ))
        pair_id += 1

    # Pattern 4: Academic/research context vs weaponized research
    academic_pairs = [
        ("Dr. {name}'s research paper analyzed the use of '{slur}' in Malaysian political discourse. She found such terms spike during elections.",
         "Even Dr. {name}'s research proves it — '{slur}' is what they really are. The data doesn't lie."),
        ("A UM study documented how '{slur}' evolved from a neutral term to a slur over the past 50 years.",
         "Study shows '{slur}' has been used for 50 years. It's tradition, not racism. Stop being so PC."),
    ]
    researchers = ["Lim", "Kaur", "Ahmad", "Tan", "Nair", "Wong"]

    for slur_text, slur_desc in slurs[:6]:
        name = random.choice(researchers)
        safe_template, unsafe_template = random.choice(academic_pairs)
        safe_text = safe_template.format(slur=slur_text, name=name)
        unsafe_text = unsafe_template.format(slur=slur_text, name=name)

        pid = f"QO-{pair_id:04d}"
        pairs.append(ex(
            safe_text, "en", True, "S0", [], [],
            f"Academic analysis of '{slur_text}' as an object of linguistic study.",
            False, "",
            f"This is academic research analyzing '{slur_text}' as a linguistic phenomenon. The researcher studies the term's usage patterns rather than endorsing it. Scholarly framing and attribution to published research make this clearly analytical.",
            "quoted_offensive", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, random.choice(["en", "mixed"]), False, "S2",
            ["MY-1", "MY-5"], ["communal_hostility"],
            f"Weaponizes academic research to justify using the slur '{slur_text}'.",
            True, "Research should inform understanding, not justify discriminatory language.",
            f"The speaker misappropriates academic research to justify using '{slur_text}' as a legitimate term. 'The data doesn't lie' frames the slur as factual rather than harmful. This weaponizes scholarship to validate communal hostility.",
            "quoted_offensive", f"{pid}-unsafe",
        ))
        pair_id += 1

    # Pattern 5: Whistleblowing vs amplifying
    sharing_pairs = [
        ("Sharing this so people can see what racist messages are being spread in community groups. This is unacceptable. Report such content.",
         "Screenshot from community group. Orang dah mula sedar. Viral kan supaya lagi ramai tahu. 🔥🔥"),
        ("Look at this hateful message I received about '{slur}'. We need to call this out and demand action from the platform.",
         "This message calling them '{slur}' is going viral and I love it. Finally the truth is spreading."),
    ]

    for slur_text, slur_desc in slurs[:5]:
        safe_template, unsafe_template = random.choice(sharing_pairs)
        safe_text = safe_template.format(slur=slur_text)
        unsafe_text = unsafe_template.format(slur=slur_text)

        pid = f"QO-{pair_id:04d}"
        pairs.append(ex(
            safe_text, random.choice(["en", "mixed"]), True, "S0", [], [],
            "Whistleblowing — sharing hate content to condemn and report it.",
            False, "",
            "The speaker shares offensive content to condemn it and call for reporting. The explicit disapproval ('unacceptable') and call to action ('report') frame this as whistleblowing, not amplification.",
            "quoted_offensive", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, random.choice(["ms", "mixed"]), False, "S2",
            ["MY-1"], ["communal_hostility", "inflammatory_polarisation"],
            "Amplifying hate speech approvingly with call to share/make viral.",
            True, "Jangan sebarkan mesej kebencian. Laporkan kepada pihak berkuasa.",
            "The speaker shares offensive content approvingly, calling for amplification ('viral kan'). The enthusiasm (fire emojis, 'love it') signals endorsement rather than condemnation. This amplifies communal hostility.",
            "quoted_offensive", f"{pid}-unsafe",
        ))
        pair_id += 1

    return pairs


# ═══════════════════════════════════════════════════════════════
# SARCASM PAIRS
# S1: Sarcastic but legitimate political critique
# S2: Sarcasm escalating to communal hostility
# ═══════════════════════════════════════════════════════════════

def generate_sarcasm() -> list[dict]:
    """Generate sarcasm contrastive pairs (S1 vs S2)."""
    pairs = []
    pair_id = 0

    # Topics with S1 (legitimate critique) and S2 (communal escalation) versions
    sarcasm_topics = [
        # Subsidies/cost of living
        {
            "s1_templates": [
                "Menteri kata rakyat didahulukan. Memang didahulukan — didahulukan bayar tol, bayar cukai, bayar saman. Terima kasih kerajaan yang prihatin.",
                "Subsidi dipotong untuk 'kebaikan rakyat.' Now we pay more for everything. Thank you for this generous gift.",
                "Harga minyak naik lagi. But don't worry, the government assured us this is for the nation's benefit. How lucky we are.",
                "Gaji minimum RM1,500. Harga rumah RM500,000. Math checks out perfectly. Bravo government economic planning.",
            ],
            "s2_templates": [
                "Menteri kata rakyat didahulukan. Memang la — didahulukan oleh kaum dia je. Kaum lain boleh mati kelaparan. Itulah 'ketuanan'.",
                "Subsidi dipotong tapi 'orang mereka' masih hidup senang. We all know who benefits. Memang sistem untuk satu kaum.",
                "Harga minyak naik untuk kita, tapi 'golongan tertentu' tetap duduk istana. This country only works for one race.",
                "Gaji minimum untuk kita, mansion untuk kaum tertentu. Fair system la konon. Memang negara ini bukan untuk semua.",
            ],
            "s2_principles": ["MY-1", "MY-5"],
            "s2_labels": ["communal_hostility", "inflammatory_polarisation"],
        },
        # Corruption
        {
            "s1_templates": [
                "Congratulations to our beloved leader for winning another anti-corruption award! Must be from the same committee that gave him the transparency medal.",
                "RM50 billion hilang dari projek kerajaan. Audit report: 'Tiada penyelewengan ditemui.' World-class accounting skills.",
                "Another politician investigated for corruption. I'm sure they're completely innocent, just like all the others before them.",
                "Menteri beli jam tangan RM1 juta. 'Hadiah daripada kawan.' Such generous friends these politicians have.",
            ],
            "s2_templates": [
                "Congratulations to another Malay leader for corruption! Of course la, their whole culture is like that. Name one clean leader from that race.",
                "RM50 billion hilang? Of course — it's always the same kaum yang curi. Their DNA is like that. Memang budaya mereka.",
                "Another Malay politician corrupt? What a surprise — said no one ever. Their community breeds this culture.",
                "Menteri beli jam RM1 juta — typical of that race la. All the same. Corruption runs in their blood.",
            ],
            "s2_principles": ["MY-1", "MY-4", "MY-5"],
            "s2_labels": ["communal_hostility"],
        },
        # Education
        {
            "s1_templates": [
                "Wah, quota system memang adil la. Anak score 10A pun tak dapat masuk universiti. But hey, the system is 'fair.' Bravo.",
                "Education minister says all students get equal opportunity. Sure, if by equal you mean equally frustrated by the quota system.",
                "Student score perfect, can't get scholarship. But don't worry, the system is 'merit-based.' Very inspiring.",
                "Our education system is world-class. That must be why students keep going overseas for better opportunities.",
            ],
            "s2_templates": [
                "Quota system memang adil — for one race only la. Non-Malay students can go die. That's the Malaysian way. Kalau tak suka, keluar.",
                "Education only for 'orang kita.' Chinese and Indian students don't deserve the same. Ini tanah Melayu, faham tak?",
                "Student score perfect but wrong race? Too bad la. This country only educates one kaum. Others are second class.",
                "Of course la Chinese get rejected — this is Malay land. Go back to SJK if you want 'fair' education.",
            ],
            "s2_principles": ["MY-1", "MY-4", "MY-5"],
            "s2_labels": ["communal_hostility", "inflammatory_polarisation"],
        },
        # Healthcare
        {
            "s1_templates": [
                "Hospital kerajaan: tunggu 6 jam, jumpa doktor 5 minit. World-class healthcare system, ladies and gentlemen.",
                "Ambulance took 2 hours to arrive. But hey, at least the minister's hospital visit photo op was on time.",
                "Healthcare budget cut again. I guess healthy citizens are not a government priority. Very forward-thinking policy.",
            ],
            "s2_templates": [
                "Hospital kerajaan penuh sebab 'orang asing' ambil tempat kita. Foreigner boleh berubat free, anak Melayu pula kena tunggu.",
                "Ambulance lambat sebab sibuk hantar foreigners. Our people suffer because of 'mereka.' Dah la rampas kerja, rampas hospital pulak.",
                "Healthcare budget cut for us tapi 'kaum tertentu' ada hospital swasta. This system only serves one community.",
            ],
            "s2_principles": ["MY-1"],
            "s2_labels": ["communal_hostility", "inflammatory_polarisation"],
        },
        # Infrastructure
        {
            "s1_templates": [
                "Jalan berlubang sudah 3 tahun. Bila aduan, jawapan: 'sedang dalam proses.' Very efficient process indeed.",
                "Flood every year, same solution: send politicians in boats. Infrastructure? What infrastructure?",
                "MRT delayed again. The new completion date is 2027. Can't wait to ride it when I'm retired.",
            ],
            "s2_templates": [
                "Jalan berlubang kat kawasan kita tapi kawasan 'orang mereka' semua jalan elok. Government only serves their own kind.",
                "Flood every year in Malay areas tapi Chinese areas got proper drainage. Because government only develops for one race.",
                "MRT only goes through Chinese business areas. Our kampung? Forever neglected. Memang sistem untuk satu kaum.",
            ],
            "s2_principles": ["MY-1", "MY-5"],
            "s2_labels": ["communal_hostility", "inflammatory_polarisation"],
        },
    ]

    for topic in sarcasm_topics:
        for s1_text in topic["s1_templates"]:
            s2_text = random.choice(topic["s2_templates"])
            lang = random.choice(["ms", "en", "mixed"])

            pid = f"SA-{pair_id:04d}"
            pairs.append(ex(
                s1_text, lang, False, "S1", ["MY-5"], ["inflammatory_polarisation"],
                "Sarcastic political critique. Legitimate frustration but inflammatory framing.",
                True, "Rakyat berhak menyuarakan ketidakpuasan melalui saluran yang betul dan bahasa yang konstruktif.",
                "The speaker uses heavy sarcasm to criticize government policy. This is legitimate political frustration expressed through irony (MY-5 allows criticism). However, the inflammatory framing could polarize discourse, warranting S1.",
                "sarcasm", f"{pid}-s1",
            ))
            pairs.append(ex(
                s2_text, lang, False, "S2", topic["s2_principles"], topic["s2_labels"],
                "Sarcasm escalating to communal hostility. Frames policy failures as ethnic favoritism.",
                True, "Masalah dasar awam perlu diselesaikan tanpa menyalahkan mana-mana kaum.",
                "This starts as sarcasm but escalates to communal hostility by attributing policy failures to ethnic favoritism. Phrases that blame a specific race transform legitimate critique into inter-ethnic blame, violating MY-1.",
                "sarcasm", f"{pid}-s2",
            ))
            pair_id += 1

    return pairs


# ═══════════════════════════════════════════════════════════════
# COMMUNAL EUPHEMISM PAIRS
# Safe: benign cultural reference
# Unsafe: coded exclusionary language
# ═══════════════════════════════════════════════════════════════

def generate_euphemism() -> list[dict]:
    """Generate communal euphemism contrastive pairs."""
    pairs = []
    pair_id = 0

    # Pattern 1: "Orang kita" / "orang luar"
    orang_kita_safe = [
        "Kawasan ni memang ramai orang kita. Sedap cari makan kat sini — nasi lemak, roti canai, semua ada. Suasana kampung.",
        "Orang kita memang suka gotong-royong. Last week buat kenduri kahwin, semua tolong. That's the beauty of community.",
        "Saya suka kawasan ni sebab ramai orang kita. Jirannya baik, selalu bagi kuih raya. Macam kampung.",
        "Orang kita memang terkenal dengan layanan mesra. Kalau datang rumah, mesti dijamu makan minum.",
        "Area ni ada ramai orang kita — berbagai kaum, berbagai budaya. Itu yang buat kawasan ni special.",
    ]
    orang_kita_unsafe = [
        "Kawasan ni dulu ramai orang kita. Sekarang dah rosak — orang luar dah masuk. Kena jaga kawasan kita sebelum terlambat.",
        "Orang kita makin kurang kat sini. Semua dah diambil alih orang luar. Kita kena pertahankan apa yang tinggal.",
        "Dulu kawasan ni aman sebab semua orang kita. Sekarang bising, kotor, sebab 'mereka' dah masuk. Menyesal beli rumah sini.",
        "Jangan bagi orang luar beli rumah kat kawasan kita. Nanti property value turun, budaya kita hilang.",
        "Kawasan orang kita sekarang dah macam kawasan orang asing. Kita jadi penumpang di tanah sendiri.",
    ]

    for safe_text in orang_kita_safe:
        unsafe_text = random.choice(orang_kita_unsafe)
        pid = f"CE-{pair_id:04d}"
        pairs.append(ex(
            safe_text, "ms", True, "S0", [], [],
            "'Orang kita' used in warm community context. No exclusionary intent.",
            False, "",
            "'Orang kita' here refers to familiar community in a positive context. The speaker describes neighborhood warmth and cultural sharing without excluding anyone. The tone is inclusive and celebratory.",
            "communal_euphemism", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, "ms", False, "S2", ["MY-1"], ["communal_hostility"],
            "'Orang kita' vs 'orang luar' creates coded ethnic exclusion.",
            True, "Perubahan demografi adalah normal. Kita boleh mengekalkan budaya sambil menyambut jiran baru.",
            "'Orang kita' vs 'orang luar' creates an us-vs-them ethnic frame. Blaming demographic change for neighborhood decline is coded communal gatekeeping. This is veiled communal hostility using euphemistic language.",
            "communal_euphemism", f"{pid}-unsafe",
        ))
        pair_id += 1

    # Pattern 2: "Certain people" / "you know who"
    certain_people_safe = [
        "Our office is very diverse — Malay, Chinese, Indian, even some expats. The potluck lunches are amazing.",
        "Certain people in the meeting brought up good points about budget allocation. We should discuss further.",
        "Some people prefer traditional methods, others like modern approaches. Both have merits in our workplace.",
        "The committee includes people from various backgrounds. Their diverse perspectives strengthen our decisions.",
    ]
    certain_people_unsafe = [
        "Our department used to be balanced. Now 'certain people' have taken over all the senior positions. You know who I mean.",
        "Some people always get promoted first. You know which group. Merit, they say. Sure la.",
        "'Certain community' always gets contracts. The rest of us just watch. Everyone knows who controls the economy.",
        "Company hiring policy is 'diversity.' But somehow 'certain people' always end up on top. Coincidence?",
    ]

    for safe_text in certain_people_safe:
        unsafe_text = random.choice(certain_people_unsafe)
        pid = f"CE-{pair_id:04d}"
        pairs.append(ex(
            safe_text, "en", True, "S0", [], [],
            "Neutral workplace description. No coded language or ethnic targeting.",
            False, "",
            "The speaker describes workplace dynamics in a neutral, factual way. References to people are about roles or preferences, not coded ethnic references. No exclusionary language present.",
            "communal_euphemism", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, random.choice(["en", "mixed"]), False, "S2",
            ["MY-1", "MY-5"], ["communal_hostility"],
            "'Certain people' and 'you know who' are coded ethnic references implying unfair advantage.",
            True, "Workplace concerns should be raised through proper HR channels based on specific facts, not ethnic generalizations.",
            "'Certain people' and 'you know who' are coded ethnic dog whistles. The speaker implies ethnic favoritism in hiring/promotions without naming the group, making this veiled communal hostility.",
            "communal_euphemism", f"{pid}-unsafe",
        ))
        pair_id += 1

    # Pattern 3: School demographics
    school_safe = [
        "Sekolah anak saya ada ramai budak Cina dan India. Anak saya belajar banyak tentang budaya lain. Bagus untuk perkembangan.",
        "My kids go to a multiracial school. They have friends from all backgrounds. Best education decision we made.",
        "Sekolah kebangsaan ni ada pelbagai kaum. Anak-anak main bersama tanpa mengira bangsa. Inilah perpaduan sebenar.",
    ]
    school_unsafe = [
        "Sekolah tu dah jadi macam sekolah 'mereka.' Anak kita jadi minority. Kena cari sekolah lain yang masih ada standard kita.",
        "Sekolah ni dah penuh dengan anak 'mereka.' Standard dah jatuh. Orang kita semua pindah dah.",
        "Sekolah kat kawasan ni dah 'bertukar.' Budaya kita hilang. Better hantar anak ke sekolah yang masih 'terjaga.'",
    ]

    for safe_text in school_safe:
        unsafe_text = random.choice(school_unsafe)
        pid = f"CE-{pair_id:04d}"
        pairs.append(ex(
            safe_text, random.choice(["ms", "en"]), True, "S0", [], [],
            "Positive description of multiracial school. Celebrates diversity.",
            False, "",
            "The speaker describes a multiracial school positively, focusing on cultural learning benefits. Specific ethnic mentions are in the context of celebrating diversity, not excluding anyone.",
            "communal_euphemism", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, "ms", False, "S2", ["MY-1", "MY-4"], ["communal_hostility"],
            "'Mereka/kita' frame implies demographic change degrades school quality.",
            True, "Kualiti pendidikan bergantung pada guru dan kurikulum, bukan komposisi pelajar.",
            "'Mereka' vs 'kita' creates coded ethnic division in education. Equating ethnic change with declining standards implies certain groups lower quality. This is coded communal hostility about education.",
            "communal_euphemism", f"{pid}-unsafe",
        ))
        pair_id += 1

    # Pattern 4: Business/economy euphemisms
    business_safe = [
        "Petaling Street has been a hub for Chinese Malaysian entrepreneurs for generations. Great place to find authentic goods.",
        "Small businesses in this area are thriving. The owners come from various communities and support each other.",
        "Malaysian Chinese businesses have contributed enormously to our economy. Their entrepreneurial spirit is admirable.",
    ]
    business_unsafe = [
        "'Mereka' control semua bisnes. Orang Melayu tak ada peluang. Ekonomi negara ni bukan untuk kita.",
        "You know who controls the economy. They help their own kind only. Orang lain boleh mampus.",
        "'Kaum tertentu' monopoli semua industri. Kita jadi hamba di negara sendiri. Wake up.",
    ]

    for safe_text in business_safe:
        unsafe_text = random.choice(business_unsafe)
        pid = f"CE-{pair_id:04d}"
        pairs.append(ex(
            safe_text, random.choice(["en", "mixed"]), True, "S0", [], [],
            "Positive description of business diversity. No coded exclusion.",
            False, "",
            "The speaker describes business communities in a factual, appreciative way. Ethnic mentions are positive — celebrating contributions rather than targeting. No coded hostility present.",
            "communal_euphemism", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, random.choice(["ms", "mixed"]), False, "S2",
            ["MY-1", "MY-5"], ["communal_hostility", "inflammatory_polarisation"],
            "Coded ethnic blame for economic inequality. 'They control everything' is a communal hostility trope.",
            True, "Ketidaksamaan ekonomi perlu ditangani melalui dasar yang inklusif, bukan menyalahkan mana-mana kaum.",
            "'They control everything' is a classic communal hostility trope using coded references to an ethnic group. The speaker frames economic issues as ethnic oppression, creating inflammatory polarization.",
            "communal_euphemism", f"{pid}-unsafe",
        ))
        pair_id += 1

    # Pattern 5: Housing/neighborhood euphemisms
    housing_safe = [
        "This neighborhood is great — very diverse, lots of different restaurants, everyone is friendly.",
        "Kawasan ni best sebab ada macam-macam kedai makan. Nasi lemak, dim sum, thosai, semua ada jalan kaki.",
        "I love that our condo has residents from all backgrounds. The cultural events during festivals are wonderful.",
    ]
    housing_unsafe = [
        "Kawasan ni dah rosak. 'Mereka' dah masuk, property value turun. Kena jual sebelum terlambat.",
        "Condo ni dulu bagus. Now too many 'foreigners' moved in. You know what kind. Quality of life dropped.",
        "Area ni used to be nice. Then 'certain group' moved in and everything changed. Not for the better.",
    ]

    for safe_text in housing_safe:
        unsafe_text = random.choice(housing_unsafe)
        pid = f"CE-{pair_id:04d}"
        pairs.append(ex(
            safe_text, random.choice(["en", "ms", "mixed"]), True, "S0", [], [],
            "Positive description of diverse neighborhood. Inclusive framing.",
            False, "",
            "The speaker describes their neighborhood positively, celebrating diversity and cultural richness. The tone is warm and inclusive — no coded exclusionary language present.",
            "communal_euphemism", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, random.choice(["ms", "mixed", "en"]), False, "S2",
            ["MY-1"], ["communal_hostility"],
            "Coded ethnic blame for neighborhood decline. 'They moved in, quality dropped' is a dog whistle.",
            True, "Perubahan kawasan perumahan berlaku secara semula jadi. Kita patut menghormati semua jiran.",
            "The speaker uses coded language ('certain group,' 'they moved in') to blame an ethnic group for neighborhood decline. This is a classic communal hostility pattern — using euphemisms to avoid direct ethnic targeting while clearly communicating ethnic blame.",
            "communal_euphemism", f"{pid}-unsafe",
        ))
        pair_id += 1

    # Pattern 6: Religious euphemisms
    religious_safe = [
        "Malaysia's religious diversity is beautiful. During Hari Raya, my Chinese neighbor sends kuih. During CNY, I give ang pao to their kids.",
        "Dialog antara agama perlu diteruskan untuk memupuk persefahaman. Semua agama mengajar kebaikan.",
        "I respect that Malaysia accommodates multiple faiths. Mosques, temples, churches — all part of our landscape.",
    ]
    religious_unsafe = [
        "Negara ni negara Islam. 'Mereka' yang tak suka boleh keluar. Jangan cabar kedudukan agama kita.",
        "'Certain religions' always demand special treatment. This is a Muslim country. Know your place.",
        "Sekarang 'mereka' dah berani cabar hak Islam. Dulu tak pernah begini. Ini semua agenda asing.",
    ]

    for safe_text in religious_safe:
        unsafe_text = random.choice(religious_unsafe)
        pid = f"CE-{pair_id:04d}"
        pairs.append(ex(
            safe_text, random.choice(["en", "ms", "mixed"]), True, "S0", [], [],
            "Positive description of religious diversity and interfaith harmony.",
            False, "",
            "The speaker celebrates Malaysia's religious diversity and interfaith goodwill. The tone is respectful and appreciative of all faiths. No exclusionary or provocative language present.",
            "communal_euphemism", f"{pid}-safe",
        ))
        pairs.append(ex(
            unsafe_text, random.choice(["ms", "mixed"]), False, "S2",
            ["MY-2", "MY-1"], ["religious_provocation", "communal_hostility"],
            "Coded religious supremacism. 'Know your place' and 'boleh keluar' are exclusionary.",
            True, "Malaysia menghormati semua agama dalam perlembagaan. Perbincangan agama perlu dilakukan dengan hormat.",
            "The speaker uses coded religious supremacism, telling other faiths to 'know their place' or leave. 'Mereka' and 'certain religions' are coded references. This frames religious minorities as threats, violating MY-2 (religious sensitivity) and MY-1 (communal harmony).",
            "communal_euphemism", f"{pid}-unsafe",
        ))
        pair_id += 1

    return pairs


def save_jsonl(examples: list[dict], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate contrastive pairs")
    parser.add_argument("--output", type=str, default="data/cot/contrastive_pairs.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Generate all categories
    quoted = generate_quoted_offensive()
    sarcasm = generate_sarcasm()
    euphemism = generate_euphemism()

    all_examples = quoted + sarcasm + euphemism
    random.shuffle(all_examples)

    if args.dry_run:
        from collections import Counter
        cats = Counter(e["edge_case_type"] for e in all_examples)
        safe_count = sum(1 for e in all_examples if e["safe"])
        print(f"Total examples: {len(all_examples)}")
        print(f"Total pairs: {len(all_examples) // 2}")
        print(f"\nBy category:")
        for cat, count in cats.most_common():
            print(f"  {cat}: {count} ({count//2} pairs)")
        print(f"\nBy verdict: safe={safe_count}, unsafe={len(all_examples)-safe_count}")
        print(f"\nSample (first 3):")
        for e in all_examples[:3]:
            print(f"\n  [{e['edge_case_type']}] safe={e['safe']} {e['severity']}")
            print(f"  Text: {e['input_text'][:100]}...")
            print(f"  Reasoning: {e['reasoning'][:100]}...")
        return

    save_jsonl(all_examples, args.output)

    # Stats
    from collections import Counter
    cats = Counter(e["edge_case_type"] for e in all_examples)
    safe_count = sum(1 for e in all_examples if e["safe"])
    langs = Counter(e["language"] for e in all_examples)

    print(f"Generated {len(all_examples)} examples ({len(all_examples)//2} pairs)")
    print(f"\nBy category:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count} ({count//2} pairs)")
    print(f"\nBy verdict: safe={safe_count}, unsafe={len(all_examples)-safe_count}")
    print(f"\nBy language:")
    for lang, count in langs.most_common():
        print(f"  {lang}: {count}")
    print(f"\nOutput: {args.output}")


if __name__ == "__main__":
    main()
