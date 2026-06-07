"""
占卜核心逻辑: 梅花易数 & 六爻
"""
import random
import time
from datetime import datetime
from typing import Optional
from .hexagram_data import (
    BAGUA, BAGUA_BINARY, BINARY_TO_BAGUA,
    HEXAGRAM_64, DIZHI, DIZHI_HOURS,
    get_hexagram_symbol, get_wuxing_relation,
)


class DivinationResult:
    """占卜结果数据类"""
    def __init__(self):
        self.method: str = ""          # 占卜方法
        self.question: str = ""        # 所问之事
        self.upper_gua: int = 0        # 上卦先天数
        self.lower_gua: int = 0        # 下卦先天数
        self.dong_yao: int = 0         # 动爻 (1-6, 从下往上)
        self.ben_gua: str = ""         # 本卦名
        self.ben_gua_ci: str = ""      # 本卦卦辞
        self.bian_gua: str = ""        # 变卦名
        self.bian_gua_ci: str = ""     # 变卦卦辞
        self.hu_gua: str = ""          # 互卦名
        self.hu_gua_ci: str = ""       # 互卦卦辞
        self.ti_gua: str = ""          # 体卦 (不动的)
        self.yong_gua: str = ""        # 用卦 (有动爻的)
        self.ti_wx: str = ""           # 体卦五行
        self.yong_wx: str = ""         # 用卦五行
        self.ti_yong: str = ""         # 体用关系
        self.time_info: str = ""       # 起卦时间
        self.extra_info: str = ""      # 额外信息 (报数等)
        self.symbol: str = ""          # 卦象符号
        self.liuyao_detail: str = ""   # 六爻详细信息

    def format_text(self) -> str:
        """格式化为文本输出"""
        lines = []
        lines.append(f"🔮 【{self.method}】")
        if self.question:
            lines.append(f"📜 所问：{self.question}")
        if self.time_info:
            lines.append(f"⏰ {self.time_info}")
        if self.extra_info:
            lines.append(f"📝 {self.extra_info}")
        lines.append("")
        lines.append(f"━━━ 本卦：{self.ben_gua} ━━━")
        lines.append(f"卦辞：{self.ben_gua_ci}")
        if self.dong_yao > 0:
            lines.append(f"动爻：第{self.dong_yao}爻")
        lines.append("")
        if self.bian_gua:
            lines.append(f"━━━ 变卦：{self.bian_gua} ━━━")
            lines.append(f"卦辞：{self.bian_gua_ci}")
            lines.append("")
        if self.hu_gua:
            lines.append(f"━━━ 互卦：{self.hu_gua} ━━━")
            lines.append(f"卦辞：{self.hu_gua_ci}")
            lines.append("")
        if self.ti_yong:
            lines.append(f"🔄 体卦：{self.ti_gua}({self.ti_wx}) | 用卦：{self.yong_gua}({self.yong_wx})")
            lines.append(f"📊 体用关系：{self.ti_yong}")
        if self.liuyao_detail:
            lines.append("")
            lines.append(self.liuyao_detail)
        return "\n".join(lines)


def _num_to_gua(num: int) -> int:
    """将数字映射到先天八卦数 (1-8), 取余后映射"""
    r = num % 8
    return r if r != 0 else 8


def _get_bian_gua(upper: int, lower: int, dong_yao: int) -> tuple:
    """根据动爻求变卦"""
    upper_bin = list(BAGUA_BINARY[upper])
    lower_bin = list(BAGUA_BINARY[lower])
    all_lines = list(lower_bin) + list(upper_bin)  # 从下到上 6 爻

    # 动爻变 (索引 dong_yao-1)
    idx = dong_yao - 1
    all_lines[idx] = 1 - all_lines[idx]

    new_lower = tuple(all_lines[0:3])
    new_upper = tuple(all_lines[3:6])

    new_lower_num = BINARY_TO_BAGUA.get(new_lower, 1)
    new_upper_num = BINARY_TO_BAGUA.get(new_upper, 1)
    return new_upper_num, new_lower_num


def _get_hu_gua(upper: int, lower: int) -> tuple:
    """求互卦: 2,3,4爻为下卦, 3,4,5爻为上卦"""
    upper_bin = list(BAGUA_BINARY[upper])
    lower_bin = list(BAGUA_BINARY[lower])
    all_lines = list(lower_bin) + list(upper_bin)  # 6 爻从下到上

    hu_lower = tuple(all_lines[1:4])  # 2,3,4爻
    hu_upper = tuple(all_lines[2:5])  # 3,4,5爻

    hu_lower_num = BINARY_TO_BAGUA.get(hu_lower, 1)
    hu_upper_num = BINARY_TO_BAGUA.get(hu_upper, 1)
    return hu_upper_num, hu_lower_num


def _fill_result(result: DivinationResult):
    """填充本卦、变卦、互卦、体用等信息"""
    u, l = result.upper_gua, result.lower_gua

    # 本卦
    hex_info = HEXAGRAM_64.get((u, l))
    if hex_info:
        result.ben_gua = hex_info[1]
        result.ben_gua_ci = hex_info[2]
    else:
        result.ben_gua = f"{BAGUA[u][0]}上{BAGUA[l][0]}下"
        result.ben_gua_ci = "卦辞未录"

    # 卦象符号
    result.symbol = get_hexagram_symbol(u, l)

    # 变卦
    if result.dong_yao > 0:
        bu, bl = _get_bian_gua(u, l, result.dong_yao)
        bian_info = HEXAGRAM_64.get((bu, bl))
        if bian_info:
            result.bian_gua = bian_info[1]
            result.bian_gua_ci = bian_info[2]
        else:
            result.bian_gua = f"{BAGUA[bu][0]}上{BAGUA[bl][0]}下"
            result.bian_gua_ci = "卦辞未录"

    # 互卦
    hu, hl = _get_hu_gua(u, l)
    hu_info = HEXAGRAM_64.get((hu, hl))
    if hu_info:
        result.hu_gua = hu_info[1]
        result.hu_gua_ci = hu_info[2]
    else:
        result.hu_gua = f"{BAGUA[hu][0]}上{BAGUA[hl][0]}下"
        result.hu_gua_ci = "卦辞未录"

    # 体用关系 (动爻在上卦则上卦为用、下卦为体, 反之)
    if result.dong_yao > 0:
        if result.dong_yao <= 3:
            # 动爻在下卦 -> 下卦为用, 上卦为体
            result.ti_gua = BAGUA[u][0]
            result.yong_gua = BAGUA[l][0]
            result.ti_wx = BAGUA[u][2]
            result.yong_wx = BAGUA[l][2]
        else:
            # 动爻在上卦 -> 上卦为用, 下卦为体
            result.ti_gua = BAGUA[l][0]
            result.yong_gua = BAGUA[u][0]
            result.ti_wx = BAGUA[l][2]
            result.yong_wx = BAGUA[u][2]
        result.ti_yong = get_wuxing_relation(result.ti_wx, result.yong_wx)


# ========== 梅花易数 ==========

def meihua_by_time(question: str = "") -> DivinationResult:
    """时间起卦 (梅花易数)"""
    now = datetime.now()
    year_gz = (now.year - 3) % 12  # 简化地支年序
    month = now.month
    day = now.day
    hour_idx = DIZHI_HOURS.get(now.hour, 0)

    upper_num = _num_to_gua(year_gz + month + day)
    lower_num = _num_to_gua(year_gz + month + day + hour_idx + 1)
    dong_yao = (year_gz + month + day + hour_idx + 1) % 6
    dong_yao = dong_yao if dong_yao != 0 else 6

    result = DivinationResult()
    result.method = "梅花易数·时间起卦"
    result.question = question
    result.upper_gua = upper_num
    result.lower_gua = lower_num
    result.dong_yao = dong_yao
    result.time_info = f"起卦时间：{now.strftime('%Y年%m月%d日 %H:%M')} ({DIZHI[hour_idx]}时)"
    _fill_result(result)
    return result


def meihua_by_numbers(num1: int, num2: int, question: str = "") -> DivinationResult:
    """报数起卦 (梅花易数): 两个数分别取上卦和下卦"""
    upper_num = _num_to_gua(num1)
    lower_num = _num_to_gua(num2)
    dong_yao = (num1 + num2) % 6
    dong_yao = dong_yao if dong_yao != 0 else 6

    result = DivinationResult()
    result.method = "梅花易数·报数起卦"
    result.question = question
    result.upper_gua = upper_num
    result.lower_gua = lower_num
    result.dong_yao = dong_yao
    result.extra_info = f"报数：{num1}, {num2}"
    now = datetime.now()
    result.time_info = f"起卦时间：{now.strftime('%Y年%m月%d日 %H:%M')}"
    _fill_result(result)
    return result


def meihua_random(question: str = "") -> DivinationResult:
    """随机起卦 (心念起卦, 用随机数模拟)"""
    # 用当前时间戳的微秒级作为随机种子的一部分
    random.seed(time.time_ns())
    num1 = random.randint(1, 100)
    num2 = random.randint(1, 100)

    result = meihua_by_numbers(num1, num2, question)
    result.method = "梅花易数·心念起卦"
    result.extra_info = f"天机数：{num1}, {num2}"
    return result


# ========== 六爻占卜 ==========

def _toss_three_coins() -> int:
    """掷三枚铜钱, 返回 6/7/8/9
    正面(字)=3, 背面(花)=2
    三正=9(老阳), 三背=6(老阴), 两正一背=8(少阴), 一正两背=7(少阳)
    """
    coins = [random.choice([2, 3]) for _ in range(3)]
    return sum(coins)


def liuyao(question: str = "") -> DivinationResult:
    """六爻占卜 (铜钱摇卦法)"""
    random.seed(time.time_ns())
    yaos = []
    detail_lines = ["🪙 六爻摇卦过程："]

    yao_names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
    yao_types = {6: "老阴 ⚋×", 7: "少阳 ⚊", 8: "少阴 ⚋", 9: "老阳 ⚊○"}

    for i in range(6):
        val = _toss_three_coins()
        yaos.append(val)
        detail_lines.append(f"  {yao_names[i]}：{yao_types[val]} ({val})")

    # 本卦: 7,9 为阳, 6,8 为阴
    ben_lines = [1 if y in (7, 9) else 0 for y in yaos]
    lower_bin = tuple(ben_lines[0:3])
    upper_bin = tuple(ben_lines[3:6])
    upper_num = BINARY_TO_BAGUA.get(upper_bin, 1)
    lower_num = BINARY_TO_BAGUA.get(lower_bin, 1)

    # 找动爻 (6 和 9 为动爻)
    dong_yaos = [i + 1 for i, y in enumerate(yaos) if y in (6, 9)]

    # 变卦: 动爻变
    bian_lines = ben_lines.copy()
    for dy in dong_yaos:
        bian_lines[dy - 1] = 1 - bian_lines[dy - 1]

    result = DivinationResult()
    result.method = "六爻·铜钱摇卦"
    result.question = question
    result.upper_gua = upper_num
    result.lower_gua = lower_num

    # 六爻的动爻处理: 多个动爻时取主要动爻
    if len(dong_yaos) == 0:
        result.dong_yao = 0
        detail_lines.append("\n📌 无动爻，以本卦卦辞断。")
    elif len(dong_yaos) == 1:
        result.dong_yao = dong_yaos[0]
        detail_lines.append(f"\n📌 动爻：第{dong_yaos[0]}爻")
    else:
        result.dong_yao = dong_yaos[0]  # 取第一个动爻做体用分析
        detail_lines.append(f"\n📌 动爻：{', '.join([f'第{d}爻' for d in dong_yaos])}")

    # 变卦信息
    if dong_yaos:
        bian_lower = tuple(bian_lines[0:3])
        bian_upper = tuple(bian_lines[3:6])
        bian_upper_num = BINARY_TO_BAGUA.get(bian_upper, 1)
        bian_lower_num = BINARY_TO_BAGUA.get(bian_lower, 1)
        bian_info = HEXAGRAM_64.get((bian_upper_num, bian_lower_num))
        if bian_info:
            result.bian_gua = bian_info[1]
            result.bian_gua_ci = bian_info[2]
        else:
            result.bian_gua = "未知卦"
            result.bian_gua_ci = ""

    result.liuyao_detail = "\n".join(detail_lines)

    now = datetime.now()
    result.time_info = f"起卦时间：{now.strftime('%Y年%m月%d日 %H:%M')}"

    _fill_result(result)

    # 六爻的变卦由自己计算, 覆盖 _fill_result 中的变卦
    if dong_yaos:
        bian_lower = tuple(bian_lines[0:3])
        bian_upper = tuple(bian_lines[3:6])
        bian_upper_num = BINARY_TO_BAGUA.get(bian_upper, 1)
        bian_lower_num = BINARY_TO_BAGUA.get(bian_lower, 1)
        bian_info = HEXAGRAM_64.get((bian_upper_num, bian_lower_num))
        if bian_info:
            result.bian_gua = bian_info[1]
            result.bian_gua_ci = bian_info[2]

    return result
