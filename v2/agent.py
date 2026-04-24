import json
import os
import win32com.client as win32
import pythoncom
from openai import OpenAI
import lib # 导入 SolidWorks 库
import llm_connector # 导入 LLM 连接器和调度器
from typing import Dict, Any, List


LLM_MODEL_NAME = "zai-org/GLM-4.6"  #   Qwen/Qwen3-235B-A22B  deepseek-ai/DeepSeek-V3  deepseek-ai/DeepSeek-V3.2  zai-org/GLM-4.6最好，能实现画五角星   moonshotai/Kimi-K2-Thinking    
template_path = rf"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
ARG_NOTHING = win32.VARIANT(pythoncom.VT_DISPATCH, None)


# 系统 Prompt
# agent.py

SW_PLANNER_SYSTEM_PROMPT = """
**[系统角色：SolidWorks 资深建模工程师]**
你是一个精通 SolidWorks API 的智能体。你的目标是解析用户的模糊需求，将其转化为精确的**多步**建模指令，然后执行。

**[核心思维准则 - 必须遵守]**
1.  **完整性检查 (Critical)：用户的一句话通常包含多个步骤（例如“建桌子并打孔”）。你必须**一次性生成所有步骤**的工具调用，绝不能做完第一步就停下。
2.  **启动顺序**：在创建模型中的第一个实体（通常是底座）之前，**禁止**调用 `select_face`。第一个 `extrude_...` 函数会自动在 Top Plane 上生成。
3.  **坐标自动计算：** 用户通常只说“距离边缘多少”。你必须在脑中计算绝对坐标：
    - 例如：中心在原点的 1m 桌子，边缘坐标是 x=0.5 和 x=-0.5。
    - 如果“距离边缘 0.1m”，则孔的中心坐标是 0.4 或 -0.4。
4.  **如果一个任务，能通过在一个面上画草图然后再调用其他工具实现，就尽可能减少选面工具的使用，保持简洁，减少选面带来的错误。
    画的草图，拉伸、切除等操作之前，必须保证草图是闭合曲线
5.  **如果没说具体的数值参数，你就根据你的经验确定数值。
6.  **选面：如果需要选其他的面，你都要自己计算、判断出合适的面。
7.  **模糊数值决策：** 如果用户提供一个范围（例如 "0.04~0.08m"）或者没有明确给出数值，请根据你的经验给出，不要犹豫。

**[原子化草图工作流]**
如果要绘制复杂图形（如 L 型、三角形或不规则形状）：
1. 调用 `start_sketch`。
2. 连续调用 `sketch_line` ,你必须确保：
   - 线条首尾相连：Step N 的 (x2, y2) 必须等于 Step N+1 的 (x1, y1)。
   - 最后一步：Step Last 的 (x2, y2) 必须等于 Step 1 的 (x1, y1) 以实现闭合。
**[工具使用策略]**
- 所有的单位必须转换为 **米 (m)**。

**[旋转特征专项规则]**
    轴先行：建立任何回转体（花瓶、传感器外壳等）前，必须先调用 sketch_centerline 画出旋转轴。
    零点吸附：样条曲线 sketch_spline 的起始点和结束点，必须精确落在中心线上（例如中心线在 X=0，那么曲线端点的 X 也必须是 0）。
    单侧原则：所有轮廓线必须位于中心线的一侧（通常为 X 轴正半轴）。

**[圆角建模强制规范]**
1. 步骤必须为：拉伸实体 -> `select_face(direction="TOP", mark=1)` -> `apply_fillet(radius_m=...)`。
2. 注意：在调用 `apply_fillet` 之前的那个 `select_face` 必须包含参数 `mark=1`。

最后，根据需求选择材质。

一次性把后续所有操作都发出来！
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
    model_name = "五角星"
    save_path = rf"C:\Users\Free\Desktop\SW宏\v2\{model_name}335.SLDPRT"
    # 示例用户输入 (您可以替换为任何其
    user_command = f"建立一个{model_name},外观红色"
    
    print("\n" + "="*50)
    print(f"用户指令: {user_command}")
    print("="*50)
    
    # 执行 Agent 主流程
    run_sw_agent(user_command)
    
    print("\n--- 流程结束 ---")
