"""
完整六爻排盘引擎
纳甲装卦 · 八宫归属 · 世应 · 六亲 · 六神 · 月建日辰 · 旬空 · 用神 · 旺衰
"""
import random
import time
from datetime import datetime, date
from typing import Optional

# ============================================================
#  基础数据
# ============================================================

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 地支 → 五行
DIZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 先天八卦数: (卦名, 五行, 阴阳)
BAGUA_INFO = {
    1: ("乾", "金", "阳"), 2: ("兑", "金", "阴"), 3: ("离", "火", "阴"),
    4: ("震", "木", "阳"), 5: ("巽", "木", "阴"), 6: ("坎", "水", "阳"),
    7: ("艮", "土", "阳"), 8: ("坤", "土", "阴"),
}

# 先天八卦二进制 (从下到上: 初爻, 二爻, 三爻)
BAGUA_BIN = {
    1: (1, 1, 1), 2: (1, 1, 0), 3: (1, 0, 1), 4: (1, 0, 0),
    5: (0, 1, 1), 6: (0, 1, 0), 7: (0, 0, 1), 8: (0, 0, 0),
}
BIN_TO_GUA = {v: k for k, v in BAGUA_BIN.items()}

# ============================================================
#  纳甲表
#  每卦: 内卦天干, 外卦天干, 内卦地支[3], 外卦地支[3]
# ============================================================
NAJIA = {
    1: ("甲", "壬", ["子", "寅", "辰"], ["午", "申", "戌"]),  # 乾
    2: ("丁", "丁", ["巳", "卯", "丑"], ["亥", "酉", "未"]),  # 兑
    3: ("己", "己", ["卯", "丑", "亥"], ["酉", "未", "巳"]),  # 离
    4: ("庚", "庚", ["子", "寅", "辰"], ["午", "申", "戌"]),  # 震
    5: ("辛", "辛", ["丑", "亥", "酉"], ["未", "巳", "卯"]),  # 巽
    6: ("戊", "戊", ["寅", "辰", "午"], ["申", "戌", "子"]),  # 坎
    7: ("丙", "丙", ["辰", "午", "申"], ["戌", "子", "寅"]),  # 艮
    8: ("乙", "癸", ["未", "巳", "卯"], ["丑", "亥", "酉"]),  # 坤
}

# ============================================================
#  六十四卦名 (上卦, 下卦) → (序号, 卦名)
# ============================================================
GUA64_NAME = {
    (1,1): (1,"乾为天"), (8,8): (2,"坤为地"), (6,4): (3,"水雷屯"),
    (7,6): (4,"山水蒙"), (6,1): (5,"水天需"), (1,6): (6,"天水讼"),
    (8,6): (7,"地水师"), (6,8): (8,"水地比"), (5,1): (9,"风天小畜"),
    (1,2): (10,"天泽履"), (8,1): (11,"地天泰"), (1,8): (12,"天地否"),
    (1,3): (13,"天火同人"), (3,1): (14,"火天大有"), (8,7): (15,"地山谦"),
    (4,8): (16,"雷地豫"), (2,4): (17,"泽雷随"), (7,5): (18,"山风蛊"),
    (8,2): (19,"地泽临"), (5,8): (20,"风地观"), (3,4): (21,"火雷噬嗑"),
    (7,3): (22,"山火贲"), (7,8): (23,"山地剥"), (8,4): (24,"地雷复"),
    (1,4): (25,"天雷无妄"), (7,1): (26,"山天大畜"), (7,4): (27,"山雷颐"),
    (2,5): (28,"泽风大过"), (6,6): (29,"坎为水"), (3,3): (30,"离为火"),
    (2,7): (31,"泽山咸"), (4,5): (32,"雷风恒"), (1,7): (33,"天山遁"),
    (4,1): (34,"雷天大壮"), (3,8): (35,"火地晋"), (8,3): (36,"地火明夷"),
    (5,3): (37,"风火家人"), (3,2): (38,"火泽睽"), (6,7): (39,"水山蹇"),
    (4,6): (40,"雷水解"), (7,2): (41,"山泽损"), (5,4): (42,"风雷益"),
    (2,1): (43,"泽天夬"), (1,5): (44,"天风姤"), (2,8): (45,"泽地萃"),
    (8,5): (46,"地风升"), (2,6): (47,"泽水困"), (6,5): (48,"水风井"),
    (2,3): (49,"泽火革"), (3,5): (50,"火风鼎"), (4,4): (51,"震为雷"),
    (7,7): (52,"艮为山"), (5,7): (53,"风山渐"), (4,2): (54,"雷泽归妹"),
    (4,3): (55,"雷火丰"), (3,7): (56,"火山旅"), (5,5): (57,"巽为风"),
    (2,2): (58,"兑为泽"), (5,6): (59,"风水涣"), (6,2): (60,"水泽节"),
    (5,2): (61,"风泽中孚"), (4,7): (62,"雷山小过"), (6,3): (63,"水火既济"),
    (3,6): (64,"火水未济"),
}

def gua_name(upper: int, lower: int) -> str:
    info = GUA64_NAME.get((upper, lower))
    return info[1] if info else f"{BAGUA_INFO[upper][0]}{BAGUA_INFO[lower][0]}卦"

# ============================================================
#  八宫归属表 (程序生成)
#  palace_table[(upper, lower)] = (宫卦数, 世数0-7)
#  世数: 0=本宫(六世), 1-5=一世~五世, 6=游魂, 7=归魂
# ============================================================

def _build_palace_table():
    table = {}
    for pnum in range(1, 9):
        pb = list(BAGUA_BIN[pnum])
        lines = list(pb) + list(pb)  # 6爻, 从下到上

        # 本宫卦
        lo, up = tuple(lines[0:3]), tuple(lines[3:6])
        table[(BIN_TO_GUA[up], BIN_TO_GUA[lo])] = (pnum, 0)

        # 一世~五世: 依次变初爻到五爻
        for gen in range(1, 6):
            lines[gen - 1] = 1 - lines[gen - 1]
            lo, up = tuple(lines[0:3]), tuple(lines[3:6])
            table[(BIN_TO_GUA[up], BIN_TO_GUA[lo])] = (pnum, gen)

        # 游魂: 从五世, 四爻(index 3)变回原值
        lines[3] = 1 - lines[3]
        lo, up = tuple(lines[0:3]), tuple(lines[3:6])
        table[(BIN_TO_GUA[up], BIN_TO_GUA[lo])] = (pnum, 6)

        # 归魂: 下卦恢复为宫卦
        lines[0:3] = list(pb)
        lo, up = tuple(lines[0:3]), tuple(lines[3:6])
        table[(BIN_TO_GUA[up], BIN_TO_GUA[lo])] = (pnum, 7)

    return table

PALACE_TABLE = _build_palace_table()

SHI_NAMES = ["本宫卦", "一世卦", "二世卦", "三世卦", "四世卦", "五世卦", "游魂卦", "归魂卦"]

# 世爻应爻位置 (1-indexed)
SHI_YING_POS = {
    0: (6, 3),  # 本宫
    1: (1, 4), 2: (2, 5), 3: (3, 6),
    4: (4, 1), 5: (5, 2),
    6: (4, 1),  # 游魂
    7: (3, 6),  # 归魂
}

# ============================================================
#  日干支 · 月建 计算
# ============================================================

# 甲子日参考: 2000-01-07
_JIAZI_REF = date(2000, 1, 7)

def get_day_ganzhi(d: Optional[date] = None) -> tuple:
    """返回 (天干index, 地支index, 天干str, 地支str)"""
    if d is None:
        d = date.today()
    diff = (d - _JIAZI_REF).days
    tg = diff % 10
    dz = diff % 12
    return tg, dz, TIANGAN[tg], DIZHI[dz]

def get_month_jian(d: Optional[date] = None) -> tuple:
    """返回月建 (天干str, 地支str, 地支五行)
    近似按公历推算节气月"""
    if d is None:
        d = date.today()
    # 月支: 按节气近似 (寅月≈2/4, 卯月≈3/6 ...)
    solar_month_start = [
        (2, 4), (3, 6), (4, 5), (5, 6), (6, 6), (7, 7),
        (8, 8), (9, 8), (10, 8), (11, 7), (12, 7), (1, 6),
    ]
    # 地支: 寅(2), 卯(3), ..., 丑(1)
    month_dizhi_idx = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1]

    m_idx = 0
    for i, (mon, day_start) in enumerate(solar_month_start):
        if i < 11:
            next_mon, next_day = solar_month_start[i + 1]
        else:
            next_mon, next_day = solar_month_start[0]

        if mon == d.month and d.day >= day_start:
            m_idx = i
            break
        elif mon == d.month and d.day < day_start:
            m_idx = (i - 1) % 12
            break
    else:
        # 1月且日期 < 1/6 → 上年丑月
        if d.month == 1 and d.day < 6:
            m_idx = 11
        elif d.month == 1:
            m_idx = 11

    dz_idx = month_dizhi_idx[m_idx]

    # 月干: 年上起月法
    year_tg = (d.year - 4) % 10
    # 甲己年起丙寅, 乙庚起戊寅, 丙辛起庚寅, 丁壬起壬寅, 戊癸起甲寅
    month_tg_start = [2, 4, 6, 8, 0]  # 丙戊庚壬甲
    tg_base = month_tg_start[year_tg % 5]
    tg_idx = (tg_base + m_idx) % 10

    return TIANGAN[tg_idx], DIZHI[dz_idx], DIZHI_WUXING[DIZHI[dz_idx]]

def get_xunkong(tg_idx: int, dz_idx: int) -> tuple:
    """根据日干支求旬空 (两个地支)"""
    xun_start_dz = (dz_idx - tg_idx) % 12
    k1 = DIZHI[(xun_start_dz + 10) % 12]
    k2 = DIZHI[(xun_start_dz + 11) % 12]
    return k1, k2

# ============================================================
#  六亲推导
# ============================================================

WUXING_LIST = ["金", "木", "水", "火", "土"]
# 五行生克关系: 生我, 我生, 克我, 我克, 同我
SHENG_CYCLE = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}  # X生于Y → SHENG[X]=Y
KE_CYCLE = {"木": "金", "火": "水", "土": "木", "金": "火", "水": "土"}    # X被Y克 → KE[X]=Y

# 重新用更清晰的方式
_WX_SHENG = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}  # A生B
_WX_KE = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}      # A克B

def liuqin(gong_wx: str, yao_wx: str) -> str:
    """六亲: 宫五行为'我'"""
    if yao_wx == gong_wx:
        return "兄弟"
    if _WX_SHENG[yao_wx] == gong_wx:
        return "父母"   # yao 生 我 → 生我者父母
    if _WX_SHENG[gong_wx] == yao_wx:
        return "子孙"   # 我 生 yao → 我生者子孙
    if _WX_KE[yao_wx] == gong_wx:
        return "官鬼"   # yao 克 我 → 克我者官鬼
    if _WX_KE[gong_wx] == yao_wx:
        return "妻财"   # 我 克 yao → 我克者妻财
    return "？"

# ============================================================
#  六神排列
# ============================================================

LIUSHEN = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]

# 日天干 → 初爻起始六神index
LIUSHEN_START = {
    0: 0, 1: 0,  # 甲乙→青龙
    2: 1, 3: 1,  # 丙丁→朱雀
    4: 2,        # 戊→勾陈
    5: 3,        # 己→螣蛇
    6: 4, 7: 4,  # 庚辛→白虎
    8: 5, 9: 5,  # 壬癸→玄武
}

def get_liushen_list(day_tg_idx: int) -> list:
    """返回初爻到上爻的六神列表"""
    start = LIUSHEN_START[day_tg_idx]
    return [LIUSHEN[(start + i) % 6] for i in range(6)]

# ============================================================
#  用神选取
# ============================================================

def select_yongshen(question: str) -> str:
    """根据问题关键词选取用神六亲"""
    q = question.lower()
    # 婚恋感情优先 (避免"女朋友"误匹配"朋友"→兄弟)
    if any(k in q for k in ["婚", "恋", "感情", "对象", "老婆", "老公", "男友", "女友",
                              "男朋友", "女朋友", "爱情", "表白", "复合", "分手", "暧昧"]):
        return "妻财"
    if any(k in q for k in ["财", "钱", "生意", "投资", "买卖", "收入", "工资", "签约", "合同"]):
        return "妻财"
    if any(k in q for k in ["官", "工作", "事业", "升职", "考试", "面试", "公务", "诉讼", "官司"]):
        return "官鬼"
    if any(k in q for k in ["病", "疾", "健康", "身体"]):
        return "官鬼"
    if any(k in q for k in ["父", "母", "长辈", "房", "文书", "学业", "学习", "证书", "文凭", "书"]):
        return "父母"
    if any(k in q for k in ["子", "女", "孩子", "宝宝", "下属", "学生", "宠物"]):
        return "子孙"
    if any(k in q for k in ["兄", "弟", "姐", "妹", "朋友", "同事", "合伙"]):
        return "兄弟"
    if any(k in q for k in ["出行", "旅行", "出差"]):
        return "世爻"
    return "世爻"

# ============================================================
#  旺衰分析
# ============================================================

def yao_wangshuai(yao_wx: str, month_wx: str) -> str:
    """判断爻在月建中的旺衰"""
    if yao_wx == month_wx:
        return "旺"
    if _WX_SHENG[month_wx] == yao_wx:
        return "相"   # 月生爻
    if _WX_SHENG[yao_wx] == month_wx:
        return "休"   # 爻生月
    if _WX_KE[yao_wx] == month_wx:
        return "囚"   # 爻克月 (有心无力)
    if _WX_KE[month_wx] == yao_wx:
        return "死"   # 月克爻
    return ""

def yao_ri_relation(yao_wx: str, day_wx: str) -> str:
    """爻与日辰的关系"""
    if yao_wx == day_wx:
        return "日扶"
    if _WX_SHENG[day_wx] == yao_wx:
        return "日生"
    if _WX_KE[day_wx] == yao_wx:
        return "日克"
    if _WX_SHENG[yao_wx] == day_wx:
        return "日泄"
    return ""

# ============================================================
#  排盘数据结构
# ============================================================

class YaoLine:
    """单爻数据"""
    def __init__(self):
        self.pos: int = 0            # 爻位 1-6
        self.yin_yang: int = 0       # 1=阳, 0=阴
        self.coin_val: int = 0       # 铜钱值 6/7/8/9
        self.is_dong: bool = False   # 是否动爻
        self.tiangan: str = ""       # 天干
        self.dizhi: str = ""         # 地支
        self.wuxing: str = ""        # 五行
        self.liuqin: str = ""        # 六亲
        self.liushen: str = ""       # 六神
        self.shi_ying: str = ""      # "世"/"应"/""
        self.is_kong: bool = False   # 是否旬空
        self.wangshuai: str = ""     # 旺衰
        self.ri_rel: str = ""        # 日辰关系
        # 变爻信息 (动爻变后)
        self.bian_dizhi: str = ""
        self.bian_wuxing: str = ""
        self.bian_liuqin: str = ""


class LiuYaoPaiPan:
    """完整六爻排盘"""
    def __init__(self):
        self.question: str = ""
        self.time_str: str = ""
        self.day_gan: str = ""
        self.day_zhi: str = ""
        self.month_gan: str = ""
        self.month_zhi: str = ""
        self.month_wx: str = ""
        self.day_wx: str = ""
        self.xunkong: tuple = ("", "")
        self.palace_num: int = 0
        self.palace_name: str = ""
        self.palace_wx: str = ""
        self.shi_gen: int = 0        # 世数
        self.shi_name: str = ""      # 几世卦
        self.upper: int = 0
        self.lower: int = 0
        self.ben_gua_name: str = ""
        self.bian_upper: int = 0
        self.bian_lower: int = 0
        self.bian_gua_name: str = ""
        self.has_bian: bool = False
        self.yaos: list = []         # 6个 YaoLine, index 0=初爻
        self.yongshen: str = ""      # 用神六亲
        self.yongshen_yao: str = ""  # 用神所在爻位描述

    def format_text(self) -> str:
        """格式化排盘文本 (QQ友好)"""
        lines = []
        lines.append(f"🔮【六爻·铜钱摇卦】")
        if self.question:
            lines.append(f"📜 所问：{self.question}")
        lines.append(f"⏰ {self.time_str}")
        lines.append(f"📅 月建：{self.month_gan}{self.month_zhi}月 | 日辰：{self.day_gan}{self.day_zhi}日 | 旬空：{self.xunkong[0]}{self.xunkong[1]}")
        lines.append("")

        bian_str = f" → {self.bian_gua_name}" if self.has_bian else ""
        lines.append(f"📋 {self.palace_name}宫 | {self.ben_gua_name}（{self.shi_name}）{bian_str}")
        lines.append("")

        # 爻位名称
        yao_pos_names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]

        # 从上爻到初爻显示
        for i in range(5, -1, -1):
            y = self.yaos[i]

            # 爻象: 用文字更清晰
            if y.yin_yang == 1:
                yao_sym = "——"
                dong_mark = "○" if y.is_dong else ""
            else:
                yao_sym = "— —"
                dong_mark = "×" if y.is_dong else ""

            # 世应
            sa = y.shi_ying if y.shi_ying else ""

            # 旬空
            kong = " 空" if y.is_kong else ""

            # 主线: 六神 | 爻象 | 纳甲 | 六亲 | 世应 | 旬空
            main = f"{y.liushen} {yao_sym}{dong_mark} {y.tiangan}{y.dizhi}{y.wuxing} {y.liuqin} {sa}{kong}"

            # 变卦部分
            if self.has_bian and y.is_dong:
                bian_yy = 1 - y.yin_yang
                bian_sym = "——" if bian_yy == 1 else "— —"
                main += f"  → {bian_sym} {y.bian_dizhi}{y.bian_wuxing} {y.bian_liuqin}"

            lines.append(main)

        lines.append("")

        # 用神信息
        if self.yongshen and self.yongshen != "世爻":
            lines.append(f"🎯 用神：{self.yongshen}")
            if self.yongshen_yao:
                lines.append(f"  {self.yongshen_yao}")
        elif self.yongshen == "世爻":
            lines.append(f"🎯 用神：世爻（综合运势）")

        return "\n".join(lines)


# ============================================================
#  核心: 完整六爻排盘
# ============================================================

def liuyao_paipan(question: str = "") -> LiuYaoPaiPan:
    """完整六爻排盘"""
    random.seed(time.time_ns())
    now = datetime.now()
    today = now.date()

    pan = LiuYaoPaiPan()
    pan.question = question
    pan.time_str = f"起卦时间：{now.strftime('%Y年%m月%d日 %H:%M')}"

    # ---- 日干支 ----
    dtg_idx, ddz_idx, dtg, ddz = get_day_ganzhi(today)
    pan.day_gan, pan.day_zhi = dtg, ddz
    pan.day_wx = DIZHI_WUXING[ddz]

    # ---- 月建 ----
    mtg, mdz, mwx = get_month_jian(today)
    pan.month_gan, pan.month_zhi, pan.month_wx = mtg, mdz, mwx

    # ---- 旬空 ----
    pan.xunkong = get_xunkong(dtg_idx, ddz_idx)

    # ---- 摇卦 (三枚铜钱×6次) ----
    coin_vals = []
    for _ in range(6):
        coins = [random.choice([2, 3]) for _ in range(3)]
        coin_vals.append(sum(coins))

    # ---- 本卦 ----
    ben_lines = [1 if v in (7, 9) else 0 for v in coin_vals]
    lo_bin, up_bin = tuple(ben_lines[0:3]), tuple(ben_lines[3:6])
    pan.lower, pan.upper = BIN_TO_GUA[lo_bin], BIN_TO_GUA[up_bin]
    pan.ben_gua_name = gua_name(pan.upper, pan.lower)

    # ---- 动爻与变卦 ----
    dong_positions = [i for i, v in enumerate(coin_vals) if v in (6, 9)]
    bian_lines = ben_lines.copy()
    for dp in dong_positions:
        bian_lines[dp] = 1 - bian_lines[dp]

    if dong_positions:
        pan.has_bian = True
        blo, bup = tuple(bian_lines[0:3]), tuple(bian_lines[3:6])
        pan.bian_lower, pan.bian_upper = BIN_TO_GUA[blo], BIN_TO_GUA[bup]
        pan.bian_gua_name = gua_name(pan.bian_upper, pan.bian_lower)

    # ---- 八宫归属 ----
    palace_info = PALACE_TABLE.get((pan.upper, pan.lower), (1, 0))
    pan.palace_num, pan.shi_gen = palace_info
    pan.palace_name = BAGUA_INFO[pan.palace_num][0]
    pan.palace_wx = BAGUA_INFO[pan.palace_num][1]
    pan.shi_name = SHI_NAMES[pan.shi_gen]

    # ---- 世应位置 ----
    shi_pos, ying_pos = SHI_YING_POS[pan.shi_gen]

    # ---- 六神 ----
    liushen_list = get_liushen_list(dtg_idx)

    # ---- 纳甲 & 装卦 ----
    lower_najia = NAJIA[pan.lower]
    upper_najia = NAJIA[pan.upper]

    for i in range(6):
        y = YaoLine()
        y.pos = i + 1
        y.coin_val = coin_vals[i]
        y.yin_yang = ben_lines[i]
        y.is_dong = coin_vals[i] in (6, 9)

        # 纳甲天干地支
        if i < 3:
            y.tiangan = lower_najia[0]  # 内卦天干
            y.dizhi = lower_najia[2][i]  # 内卦地支
        else:
            y.tiangan = upper_najia[1]  # 外卦天干
            y.dizhi = upper_najia[3][i - 3]  # 外卦地支

        y.wuxing = DIZHI_WUXING[y.dizhi]

        # 六亲
        y.liuqin = liuqin(pan.palace_wx, y.wuxing)

        # 六神
        y.liushen = liushen_list[i]

        # 世应
        if y.pos == shi_pos:
            y.shi_ying = "世"
        elif y.pos == ying_pos:
            y.shi_ying = "应"

        # 旬空
        y.is_kong = y.dizhi in pan.xunkong

        # 旺衰
        y.wangshuai = yao_wangshuai(y.wuxing, pan.month_wx)
        y.ri_rel = yao_ri_relation(y.wuxing, pan.day_wx)

        # 变爻纳甲 (动爻变后的地支)
        if y.is_dong and pan.has_bian:
            if i < 3:
                bian_gua_num = pan.bian_lower
                bian_najia = NAJIA[bian_gua_num]
                y.bian_dizhi = bian_najia[2][i]
            else:
                bian_gua_num = pan.bian_upper
                bian_najia = NAJIA[bian_gua_num]
                y.bian_dizhi = bian_najia[3][i - 3]
            y.bian_wuxing = DIZHI_WUXING[y.bian_dizhi]
            y.bian_liuqin = liuqin(pan.palace_wx, y.bian_wuxing)

        pan.yaos.append(y)

    # ---- 用神 ----
    ys = select_yongshen(question)
    pan.yongshen = ys
    if ys != "世爻":
        # 找到用神所在爻
        found = []
        for y in pan.yaos:
            if y.liuqin == ys:
                ws_desc = y.wangshuai
                kong_desc = "旬空" if y.is_kong else ""
                dong_desc = "动" if y.is_dong else ""
                marks = " ".join(filter(None, [ws_desc, y.ri_rel, kong_desc, dong_desc]))
                sa = f"({y.shi_ying})" if y.shi_ying else ""
                found.append(f"第{y.pos}爻 {y.tiangan}{y.dizhi}{y.wuxing}{sa} [{marks}]")
        if found:
            pan.yongshen_yao = "  |  ".join(found)
        else:
            pan.yongshen_yao = "本卦不现，需查伏神"

    return pan
