"""Japanese verb conjugation, with furigana, plus the matching English.

    from conjugate import Verb, FORMS
    v = Verb("食べる", "たべる", "v1", "vt", "to eat")
    v.conj("nai")      -> ("食[た]べない", "たべない")    furigana text, kana
    v.english("nai")   -> "Does not eat"

Classes are JMdict's: v1 (る-verb), v5u/v5k/v5g/v5s/v5t/v5n/v5b/v5m/v5r
(う-verb, by ending), v5k-s (行く), v5r-i (ある), v5u-s (問う), v5aru
(いらっしゃる), vk (来る), vs-i (する and 勉強する), vs-s (愛する).

FORMS is the list of drilled forms, in study order, with their JLPT level,
the indication shown on the card and the English template. Add or remove a form there; everything else follows.
"""
import re
from dataclasses import dataclass

KANJI = re.compile(r"[一-鿿々〆ヶ]")

# --- kana rows -------------------------------------------------------------

ROWS = {  # dictionary ending -> (a, i, e, o) sounds
    "う": "わいえお", "く": "かきけこ", "ぐ": "がぎげご", "す": "さしせそ",
    "つ": "たちてと", "ぬ": "なにねの", "ぶ": "ばびべぼ", "む": "まみめも",
    "る": "らりれろ",
}
TE = {"う": "って", "つ": "って", "る": "って", "ぬ": "んで", "ぶ": "んで",
      "む": "んで", "く": "いて", "ぐ": "いで", "す": "して"}


@dataclass(frozen=True)
class Form:
    key: str          # internal name
    level: int        # JLPT level the form belongs to (5, 4, 3)
    mod: str          # indication shown on the card: "(polite, negative)"
    english: str      # template, see Verb.english
    kind: str = ""    # "keigo": only for verbs in KEIGO


FORMS = [
    # N5: polite (ます) forms
    Form("masu", 5, "polite", "{Vs}"),
    Form("masen", 5, "polite, negative", "{not}"),
    Form("mashita", 5, "polite, past", "{Vd}"),
    Form("masendeshita", 5, "polite, past negative", "{dnot}"),
    Form("mashou", 5, "polite, let's", "Let's {V}"),
    # N5: plain forms
    Form("nai", 5, "negative", "{not}"),
    Form("ta", 5, "past", "{Vd}"),
    Form("nakatta", 5, "past negative", "{dnot}"),
    # N5: て-form and what is built on it
    Form("te", 5, "て-form", "{V} and..."),
    Form("teiru", 5, "ongoing (ている)", "{prog}"),
    Form("tekudasai", 5, "request", "Please {V}"),
    Form("naidekudasai", 5, "negative request", "Please don't {V}"),
    Form("tai", 5, "want to", "Want to {V}"),
    # N4
    Form("pot", 4, "potential", "Can {V}"),
    Form("potnai", 4, "potential, negative", "Cannot {V}"),
    Form("vol", 4, "volitional", "Let's {V} (casual)"),
    Form("ba", 4, "ば-conditional", "If (one) {Vs_l}"),
    Form("tara", 4, "たら-conditional", "If/when (one) {Vs_l}"),
    Form("nakereba", 4, "must", "Must {V}"),
    Form("tari", 4, "たり (listing)", "Do things like {Vg_l}"),
    Form("nagara", 4, "while (ながら)", "While {Vg_l}"),
    Form("imp", 4, "command", "{V}!"),
    Form("proh", 4, "prohibition", "Don't {V}!"),
    Form("passive", 4, "passive", "{passive}"),
    Form("caus", 4, "causative", "Make/let (someone) {V}"),
    Form("honor", 4, "honorific", "{Vs} (honorific)", "keigo"),
    Form("humble", 4, "humble", "(I) {V} (humble)", "keigo"),
    # N3
    Form("causpass", 3, "causative-passive", "Is made to {V}"),
    Form("zuni", 3, "without (ずに)", "Without {Vg_l}"),
]
FORM = {f.key: f for f in FORMS}

# Special respectful / humble verbs (尊敬語・謙譲語), as (spelling, reading).
# Verbs not listed get no keigo cards; お〜になる / お〜する is shown for a
# few common verbs where it is the normal form.
KEIGO = {
    "行く":   ("いらっしゃる", "いらっしゃる"), "来る": ("いらっしゃる", "いらっしゃる"),
    "いる":   ("いらっしゃる", "いらっしゃる"),
    "食べる": ("召[め]し 上[あ]がる", "めしあがる"), "飲む": ("召[め]し 上[あ]がる", "めしあがる"),
    "言う":   ("おっしゃる", "おっしゃる"), "する": ("なさる", "なさる"),
    "見る":   ("ご 覧[らん]になる", "ごらんになる"), "くれる": ("くださる", "くださる"),
    "寝る":   ("お 休[やす]みになる", "おやすみになる"), "着る": ("お 召[め]しになる", "おめしになる"),
    "知る":   ("ご 存[ぞん]じだ", "ごぞんじだ"),
}
HUMBLE = {
    "行く":   ("参[まい]る", "まいる"), "来る": ("参[まい]る", "まいる"), "いる": ("おる", "おる"),
    "食べる": ("いただく", "いただく"), "飲む": ("いただく", "いただく"), "もらう": ("いただく", "いただく"),
    "言う":   ("申[もう]す", "もうす"), "する": ("いたす", "いたす"),
    "見る":   ("拝見[はいけん]する", "はいけんする"), "あげる": ("差[さ]し 上[あ]げる", "さしあげる"),
    "会う":   ("お 目[め]にかかる", "おめにかかる"), "聞く": ("伺[うかが]う", "うかがう"),
    "訪ねる": ("伺[うかが]う", "うかがう"), "知る": ("存[ぞん]じる", "ぞんじる"),
}
# お〜になる (respectful) and お〜する (humble), regular keigo.
O_NI_NARU = ["待つ", "書く", "読む", "帰る", "使う", "話す", "持つ", "送る", "呼ぶ", "会う", "聞く", "届ける", "知らせる", "伝える", "教える", "手伝う", "調べる"]
for _v in O_NI_NARU:
    KEIGO.setdefault(_v, None)   # filled in by Verb (needs the ます stem)
    HUMBLE.setdefault(_v, None)
for _v in ("帰る", "読む"):      # お帰りする, お読みする: not used
    HUMBLE.pop(_v, None)

# Forms that make no sense for a verb (by spelling).
NO_FORMS = {
    "ある": {"pot", "potnai", "passive", "caus", "causpass", "imp", "proh", "vol", "mashou", "teiru", "tai", "tekudasai", "naidekudasai", "nakereba", "zuni", "tari", "nagara"},
    "死ぬ": {"mashou", "vol", "tekudasai", "imp"},
    "いる": {"teiru", "passive", "pot", "potnai"},
    "できる": {"pot", "potnai", "passive", "caus", "causpass", "imp", "proh", "vol", "mashou", "tekudasai", "naidekudasai", "tai", "nakereba"},
    "わかる": {"pot", "potnai", "passive", "imp", "proh", "vol", "mashou", "tekudasai", "tai", "causpass"},
    "要る": {"pot", "potnai", "passive", "caus", "causpass", "imp", "proh", "vol", "mashou", "tekudasai", "naidekudasai", "teiru", "tai"},
    "くれる": {"pot", "potnai", "passive", "caus", "causpass", "vol", "mashou", "tekudasai", "naidekudasai", "tai"},
}
# ている on a change-of-state verb is the resulting state, not an action in
# progress: 来ている "has come (is here)", 死んでいる "is dead".
TEIRU_STATE = set("""来る 行く 帰る 死ぬ 生まれる 結婚する 起きる 開く 閉まる 止まる 落ちる 壊れる 割れる
    消える つく 入る 出る 座る 立つ 太る 痩せる 疲れる 晴れる 曇る 乾く 濡れる 汚れる 済む 決まる
    始まる 終わる 着く 届く 集まる 並ぶ 混む 空く 慣れる 忘れる 治る 直る 違う 出かける 止む
    曲がる 折れる 冷える 冷める 溶ける 腐る 枯れる 凍る 決める 卒業する 入院する 退院する
    出発する 到着する 引っ越す 似合う 欠ける 外れる 破れる 倒れる""".split())
TEIRU_EN = {"知る": "Knows", "持つ": "Has, is holding", "住む": "Lives (somewhere)",
            "覚える": "Remembers", "似る": "Resembles", "分かる": "Understands", "わかる": "Understands",
            "結婚する": "Is married", "死ぬ": "Is dead", "疲れる": "Is tired", "太る": "Is fat",
            "痩せる": "Is thin", "違う": "Is different", "混む": "Is crowded", "空く": "Is empty"}

# Verbs whose gloss is "to be ..." (be born, be surprised...) or that happen
# by themselves: no commands, requests, potential, will.
NO_WILL_VERBS = set("""降る 曇る 晴れる 咲く 光る 鳴る 沸く 起こる 壊れる 割れる 消える 見える 聞こえる
    似る 困る 疲れる 混む 空く 止む 濡れる 乾く 汚れる 落ちる 流れる 揺れる 腐る 溶ける 冷える
    冷める 燃える 焼ける 生える 枯れる 散る 凍る 輝く 治る 直る 決まる 始まる 届く 足りる 余る
    違う 間に合う 込む 太る 痩せる 慣れる 錆びる 茂る 漏れる 崩れる 倒れる 破れる 外れる 欠ける
    溜まる たまる 増える 減る""".split())
NO_WILL = {"pot", "potnai", "imp", "proh", "vol", "mashou", "tekudasai", "naidekudasai", "tai", "caus", "causpass", "passive"}


def furigana(spell, reading):
    """'思い出す', 'おもいだす' -> '思[おも]い 出[だ]す' (Anki syntax)."""
    if not KANJI.search(spell):
        return spell
    # Kanji runs become groups, kana must match literally.
    parts = re.findall(r"[一-鿿々〆ヶ]+|[^一-鿿々〆ヶ]+", spell)
    pattern = "".join("(.+?)" if KANJI.match(p) else re.escape(p) for p in parts)
    m = re.fullmatch(pattern, reading)
    if not m:
        return f"{spell}[{reading}]"
    out, g = "", iter(m.groups())
    for p in parts:
        if KANJI.match(p):
            out += (" " if out else "") + f"{p}[{next(g)}]"
        else:
            out += p
    return out


class Verb:
    def __init__(self, spell, reading, cls, trans="", english="", level=5):
        self.spell, self.reading, self.cls = spell, reading, cls
        self.trans, self.gloss, self.level = trans, english, level
        self.word = furigana(spell, reading)

    # --- Japanese ----------------------------------------------------------

    def _split(self, n):
        """Furigana text and kana of the verb minus its last n kana."""
        assert self.word.endswith(self.reading[-n:]) or not KANJI.search(self.word), (self.word, n)
        return self.word[:-n], self.reading[:-n]

    def _godan(self, end):
        return ROWS[end]

    def bases(self):
        """-> dict of stems, each (furigana, kana): a, i, e, o, te, ta, plus the class."""
        c, r = self.cls, self.reading
        if c in ("vs-i",):
            stem_w, stem_r = self._split(2)
            j = lambda k: (stem_w + k, stem_r + k)
            return {"type": "suru", "a": j("し"), "i": j("し"), "te": j("して"), "ta": j("した"),
                    "dict": j("する"), "pot": j("できる"), "passive": j("される"), "caus": j("させる"),
                    "causpass": j("させられる"), "vol": j("しよう"), "ba": j("すれば"), "imp": j("しろ"),
                    "zu": j("せず")}
        if c == "vk":
            # 来る: the kanji's reading changes, so the furigana is rebuilt.
            k = "来" if "来" in self.spell else ""
            pre_w, pre_r = (self.word[:-len("来[く]る")], r[:-2]) if k else (self.word[:-2], r[:-2])
            f = lambda yomi, tail: ((pre_w + (f"{(' ' if pre_w else '')}来[{yomi}]" if k else yomi) + tail), pre_r + yomi + tail)
            return {"type": "kuru", "a": f("こ", ""), "i": f("き", ""), "te": f("き", "て"), "ta": f("き", "た"),
                    "dict": f("く", "る"), "pot": f("こ", "られる"), "passive": f("こ", "られる"),
                    "caus": f("こ", "させる"), "causpass": f("こ", "させられる"), "vol": f("こ", "よう"),
                    "ba": f("く", "れば"), "imp": f("こ", "い"), "zu": f("こ", "ず")}
        if c == "vs-s":   # 愛する conjugates like 愛す (godan す)
            w, rr = self._split(2)
            return Verb._godan_bases(w + "す", rr + "す")
        if c == "v1":
            w, rr = self._split(1)
            j = lambda k: (w + k, rr + k)
            return {"type": "ichidan", "a": j(""), "i": j(""), "te": j("て"), "ta": j("た"), "dict": j("る"),
                    "pot": j("られる"), "passive": j("られる"), "caus": j("させる"),
                    "causpass": j("させられる"), "vol": j("よう"), "ba": j("れば"),
                    "imp": j("ろ") if self.spell != "くれる" else j(""), "zu": j("ず")}
        b = Verb._godan_bases(self.word, r)
        if c == "v5k-s":   # 行く: 行って, 行った
            w, rr = self._split(1)
            b["te"], b["ta"] = (w + "って", rr + "って"), (w + "った", rr + "った")
        if c == "v5u-s":   # 問う: 問うて, 問うた
            b["te"], b["ta"] = (self.word + "て", r + "て"), (self.word + "た", r + "た")
        if c == "v5aru":   # いらっしゃる: いらっしゃいます
            w, rr = self._split(1)
            b["i"] = (w + "い", rr + "い")
        return b

    @staticmethod
    def _godan_bases(word, reading):
        end = reading[-1]
        a, i, e, o = ROWS[end]
        w, r = word[:-1], reading[:-1]
        j = lambda k: (w + k, r + k)
        te = TE[end]
        b = {"type": "godan", "a": j(a), "i": j(i), "e": j(e), "o": j(o), "te": j(te),
             "ta": j(te[:-1] + ("だ" if te.endswith("で") else "た")), "dict": (word, reading),
             "pot": j(e + "る"), "passive": j(a + "れる"), "caus": j(a + "せる"),
             # Short causative-passive (書かされる) except for す-verbs (話させられる).
             "causpass": j(a + ("せられる" if end == "す" else "される")),
             "vol": j(o + "う"), "ba": j(e + "ば"), "imp": j(e), "zu": j(a + "ず")}
        return b

    def conj(self, key):
        """-> (furigana text, kana) of the form, or None if the verb doesn't have it."""
        if key not in self.forms():
            return None
        b = self.bases()
        cat = lambda base, tail: (base[0] + tail, base[1] + tail)
        neg = b["a"]
        if self.cls == "v5r-i":                        # ある -> ない
            neg = ("", "")
        dict_ = b["dict"]
        if key == "masu": return cat(b["i"], "ます")
        if key == "masen": return cat(b["i"], "ません")
        if key == "mashita": return cat(b["i"], "ました")
        if key == "masendeshita": return cat(b["i"], "ませんでした")
        if key == "mashou": return cat(b["i"], "ましょう")
        if key == "nai": return cat(neg, "ない")
        if key == "ta": return b["ta"]
        if key == "nakatta": return cat(neg, "なかった")
        if key == "te": return b["te"]
        if key == "teiru": return cat(b["te"], "いる")
        if key == "tekudasai": return cat(b["te"], "ください")
        if key == "naidekudasai": return cat(neg, "ないでください")
        if key == "tai": return cat(b["i"], "たい")
        if key == "pot": return b["pot"]
        if key == "potnai": return (b["pot"][0][:-1] + "ない", b["pot"][1][:-1] + "ない")
        if key == "vol": return b["vol"]
        if key == "ba": return b["ba"]
        if key == "tara": return cat(b["ta"], "ら")
        if key == "nakereba": return cat(neg, "なければならない")
        if key == "tari": return cat(b["ta"], "り")
        if key == "nagara": return cat(b["i"], "ながら")
        if key == "imp": return b["imp"]
        if key == "proh": return cat(dict_, "な")
        if key == "passive": return b["passive"]
        if key == "caus": return b["caus"]
        if key == "causpass": return b["causpass"]
        if key == "zuni": return cat(b["zu"], "に") if b["type"] != "suru" else cat((b["dict"][0][:-2], b["dict"][1][:-2]), "せずに")
        if key == "honor": return self._keigo(KEIGO, "お{}になる")
        if key == "humble": return self._keigo(HUMBLE, "お{}する")
        raise KeyError(key)

    def _keigo(self, table, pattern):
        got = table[self.spell]
        if got:
            return got
        i_w, i_r = self.bases()["i"]
        w = pattern.format(i_w)
        return (re.sub(r"^お(?=[一-鿿])", "お ", w), pattern.format(i_r))

    def forms(self):
        """Keys of the forms this verb gets."""
        skip = set(NO_FORMS.get(self.spell, ()))
        if (self.gloss.startswith("to be ") and self.spell not in NO_FORMS) or self.spell in NO_WILL_VERBS:
            skip |= NO_WILL
        if "vt" not in self.trans.split(","):
            skip.add("passive")   # 雨に降られる exists, but "is rained" isn't a translation
        out = []
        for f in FORMS:
            if f.key in skip:
                continue
            if f.kind == "keigo" and self.spell not in (KEIGO if f.key == "honor" else HUMBLE):
                continue
            out.append(f.key)
        return out

    # --- English -----------------------------------------------------------

    def english(self, key):
        head, rest = split_gloss(self.gloss)
        be = head == "be"
        sfx = (" " + rest) if rest else ""
        V = head + sfx
        vals = {
            "V": V,
            "Vs": ("is" if be else s_form(head)) + sfx,
            "Vd": ("was" if be else past(head)) + sfx,
            "not": ("is not" if be else "does not " + head) + sfx,
            "dnot": ("was not" if be else "did not " + head) + sfx,
            "prog": ("is being" if be else "is " + ing(head)) + sfx,
            "passive": "is " + participle(head) + sfx,
        }
        vals["Vs_l"], vals["Vg_l"] = vals["Vs"], ing(head) + sfx
        if key == "teiru":
            if self.spell in TEIRU_EN:
                return TEIRU_EN[self.spell]
            if self.spell in TEIRU_STATE:
                return f"Has {participle(head)}{sfx} (state)" if not be else f"Has been {rest}"
        text = FORM[key].english.format(**vals)
        return text[0].upper() + text[1:]


# --- English inflection (only what the glosses need) -----------------------

IRREGULAR = {  # base: (past, participle)
    "be": ("was", "been"), "become": ("became", "become"), "begin": ("began", "begun"),
    "bear": ("bore", "borne"), "bet": ("bet", "bet"), "bind": ("bound", "bound"),
    "bite": ("bit", "bitten"), "blow": ("blew", "blown"), "break": ("broke", "broken"),
    "build": ("built", "built"), "burn": ("burned", "burned"), "buy": ("bought", "bought"),
    "catch": ("caught", "caught"), "choose": ("chose", "chosen"), "come": ("came", "come"),
    "cut": ("cut", "cut"), "do": ("did", "done"), "draw": ("drew", "drawn"),
    "drink": ("drank", "drunk"), "eat": ("ate", "eaten"), "fall": ("fell", "fallen"),
    "feel": ("felt", "felt"), "fight": ("fought", "fought"), "find": ("found", "found"),
    "fly": ("flew", "flown"), "forget": ("forgot", "forgotten"), "freeze": ("froze", "frozen"),
    "get": ("got", "gotten"), "give": ("gave", "given"), "go": ("went", "gone"),
    "grow": ("grew", "grown"), "hang": ("hung", "hung"), "have": ("had", "had"),
    "hear": ("heard", "heard"), "hide": ("hid", "hidden"), "hit": ("hit", "hit"),
    "hold": ("held", "held"), "keep": ("kept", "kept"), "know": ("knew", "known"),
    "lay": ("laid", "laid"), "lead": ("led", "led"), "leave": ("left", "left"),
    "lend": ("lent", "lent"), "let": ("let", "let"), "lie": ("lay", "lain"),
    "lose": ("lost", "lost"), "make": ("made", "made"), "mean": ("meant", "meant"),
    "meet": ("met", "met"), "overtake": ("overtook", "overtaken"), "pay": ("paid", "paid"),
    "put": ("put", "put"), "read": ("read", "read"), "ride": ("rode", "ridden"),
    "ring": ("rang", "rung"), "rise": ("rose", "risen"), "run": ("ran", "run"),
    "say": ("said", "said"), "see": ("saw", "seen"), "seek": ("sought", "sought"),
    "sell": ("sold", "sold"), "send": ("sent", "sent"), "set": ("set", "set"),
    "shake": ("shook", "shaken"), "shine": ("shone", "shone"), "shoot": ("shot", "shot"),
    "show": ("showed", "shown"), "shut": ("shut", "shut"), "sing": ("sang", "sung"),
    "sink": ("sank", "sunk"), "sit": ("sat", "sat"), "sleep": ("slept", "slept"),
    "slide": ("slid", "slid"), "sow": ("sowed", "sown"), "speak": ("spoke", "spoken"),
    "spend": ("spent", "spent"), "split": ("split", "split"), "spread": ("spread", "spread"),
    "stand": ("stood", "stood"), "steal": ("stole", "stolen"), "stick": ("stuck", "stuck"),
    "sting": ("stung", "stung"), "strike": ("struck", "struck"), "swim": ("swam", "swum"),
    "take": ("took", "taken"), "teach": ("taught", "taught"), "tear": ("tore", "torn"),
    "tell": ("told", "told"), "think": ("thought", "thought"), "throw": ("threw", "thrown"),
    "thrust": ("thrust", "thrust"), "understand": ("understood", "understood"),
    "wake": ("woke", "woken"), "wear": ("wore", "worn"), "weave": ("wove", "woven"),
    "win": ("won", "won"), "wind": ("wound", "wound"), "write": ("wrote", "written"),
    "awaken": ("awakened", "awakened"), "forbid": ("forbade", "forbidden"),
}
# Verbs ending in a stressed consonant-vowel-consonant: stop -> stopped.
DOUBLE = {"stop", "drop", "skip", "step", "plan", "ship", "rob", "rub", "hug", "nod", "wet",
          "permit", "omit", "occur", "prefer", "refer", "regret", "admit", "control", "plot",
          "knit", "chat", "pat", "tap", "trap", "wrap", "beg", "dip", "grab", "slip", "stir",
          "jog", "hop", "mop", "pop", "rot", "sob", "ban", "bat", "fit", "dot", "chop", "pin",
          "swim", "run", "sit", "win", "get", "cut", "hit", "put",
          "set", "let", "begin", "forget", "bet", "shut", "split", "spin", "thin", "sin", "tip"}


def split_gloss(gloss):
    """'to put on (e.g., glasses)' -> ('put', 'on'). Keeps notes like '(animate)'."""
    g = re.sub(r"^to\s+", "", gloss.strip())
    g = re.sub(r"\s*\((e\.g\.|i\.e\.|usu\.|esp\.)[^)]*\)", "", g)
    g = re.sub(r"\s*;.*$", "", g).strip(" ,;")
    head, _, rest = g.partition(" ")
    return head, rest


def s_form(v):
    if v == "have": return "has"
    if v == "be": return "is"
    if re.search(r"(s|sh|ch|x|z|o)$", v): return v + "es"
    if re.search(r"[^aeiou]y$", v): return v[:-1] + "ies"
    return v + "s"


def _double(v):
    return v in DOUBLE


def past(v):
    if v in IRREGULAR: return IRREGULAR[v][0]
    if "-" in v:  # stir-fry
        a, b = v.rsplit("-", 1)
        return a + "-" + past(b)
    if v.endswith("e"): return v + "d"
    if re.search(r"[^aeiou]y$", v): return v[:-1] + "ied"
    if _double(v): return v + v[-1] + "ed"
    return v + "ed"


def participle(v):
    if v in IRREGULAR: return IRREGULAR[v][1]
    return past(v)


def ing(v):
    if v == "be": return "being"
    if "-" in v:
        a, b = v.rsplit("-", 1)
        return a + "-" + ing(b)
    if v.endswith("ie"): return v[:-2] + "ying"
    if v.endswith("e") and v not in ("see", "flee", "agree", "free") and not v.endswith("ee"): return v[:-1] + "ing"
    if _double(v): return v + v[-1] + "ing"
    return v + "ing"
