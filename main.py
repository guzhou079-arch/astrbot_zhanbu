"""
AstrBot 占卜插件 - 梅花易数 & 六爻
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
    liuyao,
    DivinationResult,
)

DIVINATION_SYSTEM_PROMPT = """你现在是一位精通周易占卜的角色，同时你需要保持自己原本的人设和说话风格来进行解卦。

请根据以下卦象信息，为求卦者进行详细解读。解读要求：
1. 先简要说明卦象的基本含义
2. 结合本卦、变卦、互卦和体用关系进行综合分析
3. 给出对所问之事的具体建议
4. 用你自己的人设风格和语气来表达，保持你平时说话的感觉，不要变成另一个人
5. 可以适当加入一些轻松的元素，但占卜解读的内容要认真对待
6. 解读内容适中，不要太短也不要太长，大约 200-400 字

注意：这是娱乐性质的占卜，请在结尾适当提醒这一点。"""


@register(
    "astrbot_plugin_divination",
    "guzhou079-arch",
    "周易占卜插件 - 梅花易数 & 六爻，支持时间/报数/心念起卦和铜钱摇卦，LLM 人设解读",
    "1.1.0",
    "https://github.com/guzhou079-arch/astrbot_plugin_divination",
)
class DivinationPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("占卜插件已加载 🔮")

    # ==========================================
    #  LLM Tool 注册 (唤醒词触发的核心)
    #  用户说「流光 帮我占一卦」→ LLM 自动调用
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
        yield event.plain_result(result.format_text())

    @filter.llm_tool(name="liuyao_divination")
    async def tool_liuyao(self, event: AstrMessageEvent, question: str) -> MessageEventResult:
        '''六爻铜钱摇卦占卜。当用户明确要求用六爻、铜钱、摇卦方式占卜时调用此工具。

        Args:
            question(string): 用户想要占卜的问题，如果用户没有明确说明则填"综合运势"
        '''
        result = liuyao(question)
        yield event.plain_result(result.format_text())

    @filter.llm_tool(name="time_divination")
    async def tool_time_gua(self, event: AstrMessageEvent, question: str) -> MessageEventResult:
        '''按当前时间起卦（梅花易数时间起卦法）。当用户要求按时间、时辰起卦时调用。

        Args:
            question(string): 用户想要占卜的问题，如果用户没有明确说明则填"综合运势"
        '''
        result = meihua_by_time(question)
        yield event.plain_result(result.format_text())

    # ==========================================
    #  辅助方法：调用 LLM 解读卦象
    # ==========================================

    async def _interpret(self, event: AstrMessageEvent, result: DivinationResult) -> str:
        """调用 LLM 解读卦象，使用 bot 当前人设"""
        try:
            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo=umo)
            if not provider_id:
                return "（暂时无法连接到 AI 进行解读，请查看上方卦象自行参悟~）"

            prompt = f"""请解读以下卦象：

{result.format_text()}

{'求卦者想问的是：' + result.question if result.question else '求卦者未说明具体问题，请根据卦象给出通用解读。'}

请用你自己的风格来解读这个卦象。"""

            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
                system_prompt=DIVINATION_SYSTEM_PROMPT,
            )
            return llm_resp.completion_text
        except Exception as e:
            logger.error(f"LLM 解读卦象失败: {e}")
            return "（AI 解读暂时不可用，请根据卦辞自行参悟~）"

    # ==========================================
    #  斜杠命令 (/ 前缀或自定义唤醒前缀)
    # ==========================================

    @filter.command("占卜", alias={"算卦", "卜卦", "起卦"})
    async def cmd_divination(self, event: AstrMessageEvent):
        '''占卜 [问题] - 心念起卦，随机占卜'''
        question = event.message_str.strip()
        result = meihua_random(question)
        gua_text = result.format_text()
        yield event.plain_result(gua_text)
        interpretation = await self._interpret(event, result)
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
        gua_text = result.format_text()
        yield event.plain_result(gua_text)
        interpretation = await self._interpret(event, result)
        yield event.plain_result(f"\n🌟 解卦：\n{interpretation}")

    @filter.command("六爻", alias={"摇卦", "铜钱"})
    async def cmd_liuyao(self, event: AstrMessageEvent):
        '''六爻 [问题] - 铜钱摇卦法占卜'''
        question = event.message_str.strip()
        result = liuyao(question)
        gua_text = result.format_text()
        yield event.plain_result(gua_text)
        interpretation = await self._interpret(event, result)
        yield event.plain_result(f"\n🌟 解卦：\n{interpretation}")

    # ==========================================
    #  关键词 regex 触发 (不需要任何前缀)
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
        gua_text = result.format_text()
        yield event.plain_result(gua_text)
        interpretation = await self._interpret(event, result)
        yield event.plain_result(f"\n🌟 解卦：\n{interpretation}")

    @filter.command("卦象帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        '''显示占卜插件使用帮助'''
        help_text = (
            "🔮 占卜插件使用指南\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 /占卜 [问题] — 心念随机起卦\n"
            "📌 /算卦 [问题] — 同上\n"
            "📌 /梅花 [问题] — 按当前时间起卦\n"
            "📌 /梅花 数字1 数字2 [问题] — 报数起卦\n"
            "📌 /六爻 [问题] — 铜钱摇卦法\n"
            "📌 /卦象帮助 — 显示本帮助\n"
            "━━━━━━━━━━━━━━━\n"
            "💡 也可以直接对我说「帮我算一卦」「来占卜一下」\n"
            "💡 或者用唤醒词叫我，比如「流光 帮我算算今天运势」\n"
            "💡 [问题] 可填可不填，填了会针对性解读\n"
            "🎭 解读会以我的风格为你呈现~"
        )
        yield event.plain_result(help_text)

    async def terminate(self):
        logger.info("占卜插件已卸载")
