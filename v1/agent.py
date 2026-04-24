import json
import os
import win32com.client as win32
import pythoncom
from openai import OpenAI
import lib # 导入 SolidWorks 库
import llm_connector # 导入 LLM 连接器和调度器
from typing import Dict, Any, List


LLM_MODEL_NAME =  "deepseek-ai/DeepSeek-V3"  #   "deepseek-ai/DeepSeek-R1"
template_path = rf"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
ARG_NOTHING = win32.VARIANT(pythoncom.VT_DISPATCH, None)


# 系统 Prompt
# agent.py

SW_PLANNER_SYSTEM_PROMPT = """
**[系统角色：SolidWorks 资深建模工程师]**
你是一个精通 SolidWorks API 的智能体。你的目标是解析用户的模糊需求，将其转化为精确的**多步**建模指令。

**[核心思维准则 - 必须遵守]**
1.  **完整性检查 (Critical)：** 用户的一句话通常包含多个步骤（例如“建桌子并打孔”）。你必须**一次性生成所有步骤**的工具调用，绝不能做完第一步就停下。
2.  **模糊数值决策：** 如果用户提供一个范围（例如 "0.04~0.08m"），请**自动取中间值或合理值**（例如 0.06m），不要犹豫。
3.  **坐标自动计算：** 用户通常只说“距离边缘多少”。你必须在脑中计算绝对坐标：
    - 例如：中心在原点的 1m 桌子，边缘坐标是 x=0.5 和 x=-0.5。
    - 如果“距离边缘 0.1m”，则孔的中心坐标是 0.4 或 -0.4。
4.  **多孔处理：** 如果用户说“四个角”，你必须**连续调用4次**切除函数，分别对应四个象限的坐标（(+,+), (+,-), (-,+), (-,-)）。
5.  **如果没说具体的数值参数，你就根据你的经验确定数值。

**[工具使用策略]**
- 所有的单位必须转换为 **米 (m)**。
- 先做减材（Cut），必先有增材（Extrude）。

不要等待执行结果！我已经预知第一步会成功！请立刻、马上、一次性把后续所有操作都发出来！即使是打孔操作，也假设桌子已经存在，直接计算坐标并发起调用！
"""


# 将 LLM 输出的函数名映射到实际的 Python 函数对象
def run_sw_agent(user_input: str):
    """主 Agent 运行函数，包含初始化、规划和执行。"""
    
    print("--- ⚙️ SolidWorks Agent 启动 ---")
    
    # 1. 初始化 SolidWorks 环境
    sw_app = lib.get_solidworks_app()
    swModel = lib.create_new_part_document(sw_app, template_path)

    if swModel is None:
        return
        
    # 2. LLM 规划
    print("\n--- 🤖 正在调用 LLM 规划建模步骤... ---")
    
    # 调用 llm_connector 中的 API 函数获取 JSON 规划
    llm_output_json = llm_connector.get_llm_planner_output(
        user_input, 
        SW_PLANNER_SYSTEM_PROMPT,
        model_name=LLM_MODEL_NAME
    )
    
    # 3. 调度与执行
    # 调用 llm_connector 中的调度器函数
    success = llm_connector.dispatch_instructions(swModel, llm_output_json)

    # 4. 清理与保存
    if success:
        swModel.ViewZoomtofit2()
        lib.save_document(swModel, save_path)
    else:
        print("建模失败，未保存文件。")


if __name__ == "__main__":
    save_path = rf"C:\Users\Free\Desktop\SW宏\v1\梯子.SLDPRT"
    # 示例用户输入 (您可以替换为任何其他指令)
    user_command = "建立一个梯子，立柱间距 0.4 米，高度 2 米，有 5 根横梁。"
    
    print("\n" + "="*50)
    print(f"用户指令: {user_command}")
    print("="*50)
    
    # 执行 Agent 主流程
    run_sw_agent(user_command)
    
    print("\n--- 流程结束 ---")
