import json
import os
import win32com.client as win32
import pythoncom
from openai import OpenAI
import lib # 导入 SolidWorks 库
import llm_connector # 导入 LLM 连接器和调度器
from typing import Dict, Any, List
from llm_connector import SWAgentBrain # 假设你按建议将 LLM 逻辑封装进了类




ARG_NOTHING = win32.VARIANT(pythoncom.VT_DISPATCH, None)


# 将 LLM 输出的函数名映射到实际的 Python 函数对象
def start_interactive_SW_agent():
    # 1. 初始化设置
    
    template_path = rf"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
    
    print("========================================")
    print("   🚀 SolidWorks 交互式智能建模 Agent   ")
    print("========================================")
    
    # 2. 连接 SolidWorks
    sw_app = lib.get_solidworks_app()
    # 询问用户是新建还是连接
    mode = input("输入 'n' 新建零件，输入 'c' 连接当前活动零件: ").lower()
    
    if mode == 'n':
        swModel = lib.create_new_part_document(sw_app, template_path)
    else:
        swModel = sw_app.ActiveDoc
        if not swModel:
            print("⚠️ 未检测到活动文档，正在为您新建...")
            swModel = lib.create_new_part_document(sw_app, template_path)

    if not swModel:
        print("❌ 无法启动 SolidWorks 会话，程序退出。")
        return
        
    # 3. 初始化智能体大脑 (传入系统提示词)
    brain = llm_connector.SWAgentBrain(
        system_prompt=llm_connector.SW_PLANNER_SYSTEM_PROMPT,
        model_name=llm_connector.LLM_MODEL_NAME
    )

    print("\n✅ 系统就绪！您可以开始下达指令了。")
    print("提示：输入 'exit' 退出，输入 'undo' 尝试撤销。")

    # 4. 进入交互循环
    while True:
        try:
            user_command = input("\n👤 用户指令: ").strip()
            
            if not user_command:
                continue
            if user_command.lower() in ['exit', 'quit', '退出']:
                print("👋 建模结束，再见！")
                break

            # --- A. 大脑规划 ---
            # 获取 LLM 的 JSON 规划字符串
            plan_json = brain.get_plan(user_command)
            
            # --- B. 物理执行 ---
            # 调用你完善的调度器，获取执行日志字符串
            execution_feedback = llm_connector.dispatch_instructions(swModel, plan_json)
            
            # --- C. 结果反馈 ---
            print(f"\n⚙️ 执行记录:\n{execution_feedback}")
            
            # 关键：将反馈喂回给大脑记忆
            brain.add_execution_result(execution_feedback)
            
            # 自动刷新视图，让效果立即可见
            swModel.ViewZoomtofit2()

        except KeyboardInterrupt:
            print("\n🛑 用户强制中断")
            break
        except Exception as e:
            print(f"❌ 运行过程中发生错误: {e}")

if __name__ == "__main__":
    start_interactive_SW_agent()