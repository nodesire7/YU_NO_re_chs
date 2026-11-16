#!/usr/bin/env python3
"""Fill in the lines that were still Japanese in the final text set.

Covers the monologue block in zz.scx (Takuya's room, not present in the official Chinese
release) and a handful of stragglers. Control tags ([auto-forward], [linebreak], [%p], …)
are preserved verbatim.

Usage: python patch_jp_lines.py [--text work/text_final]
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AF = "[auto-forward][linebreak]】"
ZZ = {
    400: "是啊，就到床上睡吧。",
    401: "我可是困得很啊……。",
    404: "（怎么也睡不着啊……。）",
    406: "（可恶……这种时候还真不少啊。）",
    407: "（明明很困，各种念头却在脑子里转个不停。）",
    408: "（困却睡不着，就是这种状态……。）",
    409: "（现在正是这样啊……。）",
    411: "喂。",
    412: "那种事要真能做到，我就去当艺人了。",
    413: "在我面前，她总是装得很开朗……。",
    414: "温柔、慈爱、体贴的女性……大概就是理想中的母亲形象吧。",
    415: "虽然只有半年左右，可也给她添了不少麻烦……。",
    416: "还曾一起去校长那里道歉……。",
    417: "反过来，她还从那些离谱的老师手里护着我……。",
    418: "从来没骂过我……[auto-forward][auto-forward]不，有一次，就一次。",
    419: "那回啊……是我打完一场荒唐的架回来的时候。好像是帮了结城那家伙的时候吧。",
    420: "严厉又悲伤……她就是带着那种眼神对我说的。",
    421: "「这种事，不要再做第二次了……」",
    422: "……被那种眼神看着说，怎么可能不听啊。",
    424: "老爸出事故下落不明的时候……还有被认定死亡的时候……。",
    425: "她始终没有失态……至少在我面前。",
    426: "是啊……在我面前，她连哭都没哭过。",
    427: "在我面前……是这样。",
    429: "我明白……我必须振作起来。",
    430: "我心里是明白的……。",
    432: "我必须振作起来才行啊……。",
    433: "〔【[auto-forward][linebreak]】〕那个强势的家伙吗……。",
    434: "本以为那家伙怎么都死不了……结果说走就走了。",
    435: "听说在历史学领域，他和龙藏寺先生一起还挺有名气的……。",
    436: "几乎不着家，钱倒是每月打进银行，偶尔回来一次也是喝得烂醉倒头就睡……。",
    437: "而且这回还擅自死掉了……笨蛋。",
    439: "要我说，就是个游手好闲的废物老爸。",
    440: "真是的，万一那家伙回来了，我可不会饶他……。",
    441: "得揍他一顿。真期待他回来啊。",
    443: "再混蛋，名义上也是父亲。",
    444: "而且，亚由美她……。",
    446: "那混蛋只要偶尔回来一趟，亚由美就高兴得不得了……。",
    447: "那种闪闪发亮的表情……我从没见过的笑容……。",
    449: "就算是那种家伙，也有过人之处吧……。",
    450: "亚由美她，果然还是对老爸……？",
    452: "哈哈哈……真是蠢问题，这不是明摆着吗。",
    453: "要不是那样，那到底算什么呢？",
    455: "老爸走了，我们今后会怎样呢……。",
    456: "今后啊……。",
    457: "今后吗……今后？",
    459: "以前我一直以为，这样的生活会一直持续下去。",
    460: "我的日常……亚由美的日常……老爸……朋友……。",
    461: "没想到只缺了一块拼图，整个画面就变得这么不一样。",
    462: "表面上看没变的日常……我和亚由美的生活……。",
    463: "可是，那家伙再也不会回来了。",
    464: "回不去了……回不去的生活吗……。",
    466: "亚由美今后会怎么办呢。",
    467: "她可才二十多岁啊……总不可能当一辈子寡妇吧。",
    468: "想着那家伙一个人活下去……真是傻得可以的想象。",
    469: "再说，那种事也不流行啊。",
    470: "亚由美有权利去抓住属于她自己的幸福。",
    471: "也就是说，迟早会……。",
    473: "啊可恶，为什么这么烦躁。",
    474: "这不是我的问题，是她的问题。",
    475: "要说现在的我能做什么……我能做什么？",
    476: "……也就像往常那样过日子吧。",
    477: "犯点傻，让她稍微担心一下……日复一日。我能做的只有这些吗。",
    478: "老爸不在了留下的空缺吗……。",
    480: "……啊！算了，不想了！",
    481: "这就是所谓的钻牛角尖吧。光想也没用。",
    482: "「肯做就能成」，这是老爸的口头禅。是啊，肯做就能成吧。",
    483: "总之睡一觉明天就会来，我们的日常又会重新开始。",
    484: "肯做就能成……。",
    485: "呼……有点困了。",
    486: "明天开始还要补课……虽然很蠢，但也不想再让亚由美担心了。",
    487: "睡吧？",
    488: "该想的都想了……剩下就是睡觉。",
    489: "亚由美每周会来打扫一两次，多亏她房间才整整齐齐的。",
    491: "先说清楚，我可不是不擅长收拾或者打扫什么的。",
    492: "物质和能量会从有序变为无序，这可是有自然法则的。",
    493: "这就叫热力学第二定律，熵定律。",
    494: "也就是说，我那间无序的房间，其实是符合自然法则、在诠释宇宙真理啊。",
    495: "……我这是在跟谁说啊。",
    496: "也就是说，亚由美每周一两次，都在试图违抗宇宙的法则。",
    497: "这么一说，反倒被她回了句「我可是遵守这个家的法则的」……。",
    498: "今天上午打扫过了吧……。",
    499: "哼……哼哼……。",
    500: "好像能闻到亚由美的香水味……。",
    501: "看着床就困起来了……。",
    502: "差不多……。",
    503: "就是普通的铁管床啊……。",
    504: "就是那什么的时候会嘎吱嘎吱响，这点扣分……。",
    505: "当然，「那什么」指的是睡相不好的时候。",
    506: "看着就困……所以不看。",
    507: "还不想睡……所以还是别看了。",
    508: "左边的凸窗，简直快成杂物间了……。",
    509: "从右边的窗户，其实可以爬下去……。",
    510: "不过这么做亚由美会生气……说太危险了别这样。",
    511: "男人啊……[auto-forward][auto-forward]算了。会变得像老爸那样的。",
    512: "窗户啊……打开会进虫子，所以不开。",
    513: "据书上说，这画好像是叫莫奈的人画的。",
    514: "当然是赝品。不过室内装饰嘛，看着像那么回事就行。",
    515: "画着莫名其妙看不明白的风景……。",
    516: "下次可燃垃圾日把它扔了吧。",
    517: "也不太想看电视……就在这儿待着吧。",
}

OTHER = {
    ("_system.scx.txt", 214): " 【介护】[名](サ变) 照顾病人、伤者等人。‥‥OK？",
    ("z_saverestarttext.scx.txt", 38): " 【介护】[名](サ变) 照顾病人、伤者等人。‥‥OK？[%p]",
    ("yns_25_02i.scx.txt", 9): "[name]绘里子[line]嗯？波多乃同学的学生手册……？[%p]",
    ("yns_c27.scx.txt", 68): "[name]结城[line]嘶——……",
    ("yns_c27.scx.txt", 70): "[name]结城[line]嘶——……哈啊啊啊啊……。",
    ("yns_d_a12_03.scx.txt", 122): "[name]拓也[line]开、开玩笑的吧……？到底发生了什么。[%p]",
    ("yns_d_b12_03.scx.txt", 134): "[name]拓也[line]开、开玩笑的吧……？到底发生了什么。[%p]",
    ("yns_d_a16_02.scx.txt", 235):
        "而现在，我大概正处在最接近那个答案的位置上。身体在颤抖。感觉就像是得到了那个的时候……那个我受他托付帮他保管的装置。[%e]",
    ("yns_d_c16_02.scx.txt", 235):
        "而现在，我大概正处在最接近那个答案的位置上。身体在颤抖。感觉就像是得到了那个的时候……那个我受他托付帮他保管的装置。[%e]",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=os.path.join(ROOT, "work", "text_final"))
    args = ap.parse_args()

    changed = 0
    # zz.scx monologue: keep the [auto-forward][linebreak]】 prefix
    path = os.path.join(args.text, "zz.scx.txt")
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    for idx, body in ZZ.items():
        new = AF + body
        if idx < len(lines):
            lines[idx] = new
            changed += 1
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    for (name, idx), new in OTHER.items():
        p = os.path.join(args.text, name)
        if not os.path.exists(p):
            print("missing", p, file=sys.stderr)
            continue
        ls = open(p, encoding="utf-8", errors="replace").read().split("\n")
        if idx < len(ls):
            ls[idx] = new
            open(p, "w", encoding="utf-8", newline="\n").write("\n".join(ls))
            changed += 1
    # unify character-name spellings that the machine translation mixed up
    global_repl = {"亜由美": "亚由美", "尤诺": "优诺"}
    for name in os.listdir(args.text):
        if not name.endswith(".txt"):
            continue
        p2 = os.path.join(args.text, name)
        s = open(p2, encoding="utf-8", errors="replace").read()
        s2 = s
        for a, b in global_repl.items():
            s2 = s2.replace(a, b)
        if s2 != s:
            open(p2, "w", encoding="utf-8", newline="\n").write(s2)
            changed += 1

    print("patched %d lines" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
