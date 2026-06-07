"""
AstrBot 占卜插件 - 梅花易数 & 六爻 (完整排盘版)
三路触发：
  1. /占卜 /算卦 /梅花 /六爻 — 斜杠命令 (或自定义唤醒前缀)
  2. "帮我算一卦" 等关键词 — regex 匹配
  3. 唤醒词 + 自然语言 — LLM Tool (核心！)
"""
import re
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .divination_core import (
    meihua_by_time,
    meihua_by_numbers,
    meihua_random,
    DivinationResult,
)
from .liuyao_engine import liuyao_paipan, LiuYaoPaiPan

# 梅花易数解读提示
MEIHUA_INTERPRET_PROMPT = """你现在是一位精通周易占卜的角色，同时保持自己原本的人设和说话风格来解卦。
请根据卦象信息为求卦者解读。要求：
1. 简要说明卦象基本含义
2. 结合本卦、变卦、互卦和体用关系综合分析
3. 给出对所问之事的具体建议
4. 保持你自己的人设风格和语气
5. 解读 200-400 字
6. 结尾提醒这是娱乐性质的占卜"""

# 六爻解读提示 (含完整排盘术语指引)
LIUYAO_INTERPRET_PROMPT = """你现在是一位精通六爻断卦的角色，同时保持自己原本的人设和说话风格来断卦。
你收到的是一份完整的六爻排盘，包含纳甲、六亲、六神、世应、月建日辰、旬空、用神等信息。
请按以下要点断卦：
1. 先看用神旺衰：用神在月建中旺相还是休囚？日辰生扶还是克泄？是否旬空？是否发动？
2. 再看世爻：世爻代表求卦者自身，旺则有利，衰则不利
3. 分析动爻：动爻是事情的变化因素，注意动爻与用神、世爻的生克关系
4. 六神辅助判断：青龙主吉庆、朱雀主口舌文书、勾陈主田土迟滞、螣蛇主虚惊怪异、白虎主凶丧血光、玄武主暗昧盗贼
5. 变卦参考：动爻变出的爻对用神是回头生还是回头克
6. 综合给出对所问之事的具体判断和建议
7. 保持你自己的人设风格，语气自然
8. 解读 300-500 字
9. 结尾提醒这是娱乐性质的占卜"""


@register(
    "astrbot_zhanbu",
    "guzhou079-arch",
    "周易占卜插件 - 梅花易数 & 六爻完整排盘，LLM 人设解读",
    "2.0.0",
    "https://github.com/guzhou079-arch/astrbot_zhanbu",
)
class DivinationPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("占卜插件已加载 🔮 v2.0 (完整六爻排盘)")

    # ==========================================
    #  LLM Tool 注册 (唤醒词触发的核心)
    # ==========================================

    @filter.llm_tool(name="meihua_divination")
    async def tool_meihua(self, event: AstrMessageEvent, question: str, number1: int = 0, number2: int = 0) -> MessageEventResult:
        '''梅花易数占卜起卦。当用户想要占卜、算卦、算命、测运势、问吉凶时调用此工具。

        Args:
            question(string): 用户想要占卜的问题，如果用户没有明确说明则填"综合运势"
            number1(number): 用户提供的第一个数字，如果没有提供则填0
            number2(number): 用户提供的第二个数字，如果没有提供则填0
        '''
        if number1 > 0 and number2 > 0:
            result = meihua_by_numbers(number1, number2, question)
        else:
            result = meihua_random(question)
        interpretation = await self._interpret_meihua(event, result)
        combined = result.format_text() + f"\n\n🌟 解卦：\n{interpretation}"
        yield event.plain_result(combined)

    @filter.llm_tool(name="liuyao_divination")
    async def tool_liuyao(self, event: AstrMessageEvent, question: str) -> MessageEventResult:
        '''六爻铜钱摇卦占卜（完整排盘）。当用户明确要求用六爻、铜钱、摇卦方式占卜时调用。

        Args:
            question(string): 用户想要占卜的问题，如果用户没有明确说明则填"综合运势"
        '''
        pan = liuyao_paipan(question)
        interpretation = await self._interpret_liuyao(event, pan)
        combined = pan.format_text() + f"\n\n🌟 断卦：\n{interpretation}"
        yield event.plain_result(combined)

    @filter.llm_tool(name="time_divination")
    async def tool_time_gua(self, event: AstrMessageEvent, question: str) -> MessageEventResult:
        '''按当前时间起卦（梅花易数时间起卦法）。当用户要求按时间、时辰起卦时调用。

        Args:
            question(string): 用户想要占卜的问题，如果用户没有明确说明则填"综合运势"
        '''
        result = meihua_by_time(question)
        interpretation = await self._interpret_meihua(event, result)
        combined = result.format_text() + f"\n\n🌟 解卦：\n{interpretation}"
        yield event.plain_result(combined)

    # ==========================================
    #  辅助: 调用 LLM 解读
    # ==========================================

    async def _interpret_meihua(self, event: AstrMessageEvent, result: DivinationResult) -> str:
        """梅花易数 LLM 解读"""
        try:
            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo=umo)
            if not provider_id:
                return "（暂时无法连接到 AI 进行解读，请查看上方卦象自行参悟~）"
            prompt = f"请解读以下卦象：\n\n{result.format_text()}\n\n{'所问：' + result.question if result.question else '未说明问题，给出通用解读。'}\n\n请用你自己的风格解读。"
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id, prompt=prompt, system_prompt=MEIHUA_INTERPRET_PROMPT)
            return llm_resp.completion_text
        except Exception as e:
            logger.error(f"LLM 解读失败: {e}")
            return "（AI 解读暂时不可用，请根据卦辞自行参悟~）"

    async def _interpret_liuyao(self, event: AstrMessageEvent, pan: LiuYaoPaiPan) -> str:
        """六爻 LLM 解读"""
        try:
            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo=umo)
            if not provider_id:
                return "（暂时无法连接到 AI 进行解读，请查看上方排盘自行断卦~）"
            prompt = f"请根据以下完整六爻排盘进行断卦：\n\n{pan.format_text()}\n\n{'所问：' + pan.question if pan.question else '未说明问题，给出通用断卦。'}\n\n请重点分析用神旺衰、世爻状态、动爻影响，用你自己的风格断卦。"
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id, prompt=prompt, system_prompt=LIUYAO_INTERPRET_PROMPT)
            return llm_resp.completion_text
        except Exception as e:
            logger.error(f"LLM 断卦失败: {e}")
            return "（AI 断卦暂时不可用，请根据排盘自行断卦~）"

    # ==========================================
    #  斜杠命令
    # ==========================================

    @filter.command("占卜", alias={"算卦", "卜卦", "起卦"})
    async def cmd_divination(self, event: AstrMessageEvent):
        '''占卜 [问题] - 心念起卦'''
        question = event.message_str.strip()
        result = meihua_random(question)
        yield event.plain_result(result.format_text())
        interpretation = await self._interpret_meihua(event, result)
        yield event.plain_result(f"\n🌟 解卦：\n{interpretation}")

    @filter.command("梅花")
    async def cmd_meihua(self, event: AstrMessageEvent):
        '''梅花 [数字1 数字2] [问题] - 梅花易数起卦'''
        text = event.message_str.strip()
        num_match = re.match(r'(\d+)\s+(\d+)\s*(.*)', text)
        if num_match:
            n1, n2 = int(num_match.group(1)), int(num_match.group(2))
            question = num_match.group(3).strip()
            result = meihua_by_numbers(n1, n2, question)
        else:
            result = meihua_by_time(text)
        yield event.plain_result(result.format_text())
        interpretation = await self._interpret_meihua(event, result)
        yield event.plain_result(f"\n🌟 解卦：\n{interpretation}")

    @filter.command("六爻", alias={"摇卦", "铜钱"})
    async def cmd_liuyao(self, event: AstrMessageEvent):
        '''六爻 [问题] - 铜钱摇卦法（完整排盘）'''
        question = event.message_str.strip()
        pan = liuyao_paipan(question)
        yield event.plain_result(pan.format_text())
        interpretation = await self._interpret_liuyao(event, pan)
        yield event.plain_result(f"\n🌟 断卦：\n{interpretation}")

    # ==========================================
    #  关键词 regex 触发
    # ==========================================

    @filter.regex(r"(帮我|给我|来|求|我要|想).{0,4}(算一?卦|占卜|占一?卦|起一?卦|测一?卦)")
    async def keyword_divination(self, event: AstrMessageEvent):
        '''自然语言关键词触发占卜'''
        text = event.message_str.strip()
        question = re.sub(
            r"(帮我|给我|来|求|我要|想).{0,4}(算一?卦|占卜|占一?卦|起一?卦|测一?卦)",
            "", text
        ).strip()
        question = re.sub(r"^[，,。.！!？?\s]+|[，,。.！!？?\s]+$", "", question)
        result = meihua_random(question)
        yield event.plain_result(result.format_text())
        interpretation = await self._interpret_meihua(event, result)
        yield event.plain_result(f"\n🌟 解卦：\n{interpretation}")

    @filter.command("卦象帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        '''显示占卜插件使用帮助'''
        help_text = (
            "🔮 占卜插件使用指南\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 /占卜 [问题] — 心念随机起卦（梅花易数）\n"
            "📌 /算卦 [问题] — 同上\n"
            "📌 /梅花 [问题] — 按当前时间起卦\n"
            "📌 /梅花 数字1 数字2 [问题] — 报数起卦\n"
            "📌 /六爻 [问题] — 铜钱摇卦（完整排盘）\n"
            "📌 /卦象帮助 — 显示本帮助\n"
            "━━━━━━━━━━━━━━━\n"
            "💡 也可以直接对我说「帮我算一卦」「来占卜一下」\n"
            "💡 或者用唤醒词叫我，比如「流光 帮我算算今天运势」\n"
            "💡 六爻排盘含纳甲·六亲·六神·世应·用神·旺衰\n"
            "🎭 解读会以我的风格为你呈现~"
        )
        yield event.plain_result(help_text)

    async def terminate(self):
        logger.info("占卜插件已卸载")
