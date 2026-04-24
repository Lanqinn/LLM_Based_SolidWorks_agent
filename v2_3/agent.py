import json
import os
import win32com.client as win32
import pythoncom
from openai import OpenAI
import lib # 导入 SolidWorks 库
import llm_connector # 导入 LLM 连接器和调度器
from typing import Dict, Any, List


LLM_MODEL_NAME = "zai-org/GLM-4.6"  #    Pro/zai-org/GLM-4.7  zai-org/GLM-4.6   Qwen/Qwen3-235B-A22B  deepseek-ai/DeepSeek-V3  deepseek-ai/DeepSeek-V3.2  zai-org/GLM-4.6最好，能实现画五角星   moonshotai/Kimi-K2-Thinking    
template_path = rf"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
ARG_NOTHING = win32.VARIANT(pythoncom.VT_DISPATCH, None)


# 系统 Prompt
# agent.py

SW_PLANNER_SYSTEM_PROMPT = """
**[系统角色：SolidWorks 资深建模工程师]**
你是一个精通 SolidWorks API 的智能体。你的目标是解析用户的模糊需求，将其转化为精确的**多步**建模指令，然后执行。

**[核心思维准则 - 必须遵守]**
1.  完整性检查 (Critical)：用户的一句话通常包含多个步骤（例如“建桌子并打孔”）。你必须**一次性生成所有步骤**的工具调用，绝不能做完第一步就停下。
2.  启动顺序**：在创建模型中的第一个实体（通常是底座）之前，**禁止**调用 `select_face`。第一个 `extrude_...` 函数会自动在 Top Plane 上生成。
3.  坐标自动计算：用户通常只说“距离边缘多少”。你必须在脑中计算绝对坐标：
    - 例如：中心在原点的 1m 桌子，边缘坐标是 x=0.5 和 x=-0.5。
    - 如果“距离边缘 0.1m”，则孔的中心坐标是 0.4 或 -0.4。
4.  如果一个任务，能通过在一个面上画草图然后再调用其他工具实现，就尽可能减少选面工具的使用，保持简洁，减少选面带来的错误。
    画的草图，拉伸、切除等操作之前，必须保证草图是闭合曲线
7.  模糊数值决策：** 如果用户提供一个范围（例如 "0.04~0.08m"）或者没有明确给出数值，请根据你的经验给出，不要犹豫。

**[坐标系与空间定义 - 绝对准则]**
当前 SolidWorks 环境采用 **Y-Up** (Y轴向上) 的标准机械设计习惯。你必须严格遵守以下映射：
1.  **“顶面” (Top / Up)**：
    - 几何意义：Y 轴正方向 (+Y)。
    - **工具调用映射**：当用户说“顶面”或“上面”时，你必须调用 `select_face(direction="TOP")`。
2.  **“前面” (Front)**：
    - 几何意义：Z 轴正方向 (+Z)。
    - **工具调用映射**：当用户说“前面”时，你必须调用 `select_face(direction="FRONT")`。
3.  **“右面” (Right)**：
    - 几何意义：X 轴正方向 (+X)。
    - **工具调用映射**：调用 `select_face(direction="RIGHT")`。

**[决策逻辑更新]**
用户说：“在顶面画圆” -> 你思考：“顶面是+Y，对应代码 TOP” -> 你输出：`select_face("TOP")`。

**[原子化草图工作流]**
如果要绘制复杂图形（如 L 型、三角形或不规则形状）：
1. 调用 `start_sketch`。
2. 连续调用 `sketch_line` ,你必须确保：
   - 线条首尾相连：Step N 的 (x2, y2) 必须等于 Step N+1 的 (x1, y1)。
   - 最后一步：Step Last 的 (x2, y2) 必须等于 Step 1 的 (x1, y1) 以实现闭合。

**[工具使用策略]
- 所有的单位必须转换为 *米 (m)*。

**[旋转特征专项规则]**
    轴先行：建立任何回转体（圆锥、花瓶等）前，必须先调用 sketch_centerline 画出旋转轴。
    零点吸附：样条曲线 sketch_spline 的起始点和结束点，必须精确落在中心线上（例如中心线在 X=0，那么曲线端点的 X 也必须是 0）。
    单侧原则：所有轮廓线必须位于中心线的一侧（通常为 X 轴正半轴）。

**[视觉验收与闭环]
你现在拥有视觉能力。**在完成所有建模步骤后（即在最后一步），你必须执行以下“视觉验收”流程：**
1.  拍照：调用 `capture_viewport_screenshot`，保存路径建议与零件文件同名（后缀改为 .jpg）。
2.  分析：紧接着调用 `analyze_modeling_result`，传入用户的原始需求和刚才的截图路径。
3.  目的：这相当于你的“眼睛”和“大脑”，用于确认你建立的模型是否正确。

最后，根据需求选择材质。

一定要一次性把后续所有操作都发出来！
"""



# 将 LLM 输出的函数名映射到实际的 Python 函数对象
def run_sw_agent(user_input: str, save_path):
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
    model_name = "圆锥"
    base_dir = rf"C:\Users\Free\Desktop\SW宏\v2_3"  # 根据你的实际路径修改
    # 零件路径 (.SLDPRT)
    save_path = f"{base_dir}\\{model_name}2.SLDPRT"
    # 截图路径 (.jpg) - Agent 应该能推断出这个路径，或者你可以显式告诉它
    screenshot_path = f"{base_dir}\\vision\\{model_name}2.jpg"

    # 2. 构造测试指令
    # 关键点：我们在指令里稍微暗示一下“帮我检查”，看看它能不能自动调用两个新工具
    user_command = f"""
    请建立一个圆锥，旋转生成，最后涂上红宝石材质并截图。保存到 '{screenshot_path}'，并调用视觉模型帮我检查一下做得对不对。
    """ 
    print("\n" + "="*50)
    print(f"用户指令: {user_command}")
    print("="*50)
    
    # 执行 Agent 主流程
    run_sw_agent(user_command, save_path=save_path)
    
    print("\n--- 流程结束 ---")
