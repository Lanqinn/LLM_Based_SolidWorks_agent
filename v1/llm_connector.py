from openai import OpenAI
import json  
import lib
from typing import Dict, Any, List
import inspect


# --- 1. 配置和客户端初始化 ---
client = OpenAI(api_key="sk-hhdlfuwibkcceysdqnszndquuyhuoaavvrdtnzqltttejdnt", 
                base_url="https://api.siliconflow.cn/v1")

# 定义工具描述 (Tools Schema)
tools_schema = [
    # 1. 圆柱拉伸
    {
        "type": "function",
        "function": {
            "name": "extrude_cylinder",
            "description": "在 Top Plane 上创建一个圆柱体实体。注意：所有单位均为米(m)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "radius_m": {
                        "type": "number",
                        "description": "圆柱体的半径 (米)"
                    },
                    "height_m": {
                        "type": "number",
                        "description": "圆柱体的高度/拉伸深度 (米)"
                    },
                    "center_x_m": {
                        "type": "number",
                        "description": "圆心的 X 坐标 (米)，默认为 0.0"
                    },
                    "center_y_m": {
                        "type": "number",
                        "description": "圆心的 Y 坐标 (米)，默认为 0.0"
                    }
                },
                "required": ["radius_m", "height_m"]
            }
        }
    },

    # 2. 圆孔切除
    {
        "type": "function",
        "function": {
            "name": "create_cut_extrude_circle",
            "description": "在 Top Plane 上切除一个圆形孔。支持完全贯穿或指定深度盲孔。",
            "parameters": {
                "type": "object",
                "properties": {
                    "radius_m": {
                        "type": "number",
                        "description": "切除圆的半径 (米)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["THRU_ALL", "BLIND"],
                        "description": "切除模式：'THRU_ALL' (完全贯穿) 或 'BLIND' (盲孔/给定深度)"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "切除深度 (米)。当 mode 为 'BLIND' 时必须提供此参数。"
                    },
                    "center_x": {
                        "type": "number",
                        "description": "圆心的 X 坐标 (米)，默认为 0.0"
                    },
                    "center_y": {
                        "type": "number",
                        "description": "圆心的 Y 坐标 (米)，默认为 0.0"
                    }
                },
                "required": ["radius_m"]
            }
        }
    },

    # 3. 长方体拉伸
    {
        "type": "function",
        "function": {
            "name": "extrude_rectangle",
            "description": "在 Top Plane 上创建一个长方体（拉伸矩形）。注意：所有单位均为米(m)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "length_m": {
                        "type": "number",
                        "description": "矩形在 X 轴方向的长度 (米)"
                    },
                    "width_m": {
                        "type": "number",
                        "description": "矩形在 Y 轴方向的宽度 (米)"
                    },
                    "height_m": {
                        "type": "number",
                        "description": "拉伸的高度 (米)"
                    },
                    "center_x_m": {
                        "type": "number",
                        "description": "矩形中心的 X 坐标 (米)，默认为 0.0"
                    },
                    "center_y_m": {
                        "type": "number",
                        "description": "矩形中心的 Y 坐标 (米)，默认为 0.0"
                    }
                },
                "required": ["length_m", "width_m", "height_m"]
            }
        }
    },

    # 4. 矩形切除
    {
        "type": "function",
        "function": {
            "name": "create_cut_extrude_rectangle",
            "description": "在 Top Plane 上切除一个矩形孔。",
            "parameters": {
                "type": "object",
                "properties": {
                    "length_m": {
                        "type": "number",
                        "description": "切除矩形的长度 (X方向, 米)"
                    },
                    "width_m": {
                        "type": "number",
                        "description": "切除矩形的宽度 (Y方向, 米)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["THRU_ALL", "BLIND"],
                        "description": "切除模式：'THRU_ALL' (完全贯穿) 或 'BLIND' (给定深度)"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "切除深度 (米)。仅在 mode='BLIND' 时有效。"
                    },
                    "center_x": {
                        "type": "number",
                        "description": "切除中心的 X 坐标 (米)，默认为 0.0"
                    },
                    "center_y": {
                        "type": "number",
                        "description": "切除中心的 Y 坐标 (米)，默认为 0.0"
                    }
                },
                "required": ["length_m", "width_m"]
            }
        }
    }
]


# --- 3. LLM API 调用函数 ---

def get_llm_planner_output(user_input: str, system_prompt: str, model_name: str):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools_schema,       
            tool_choice="auto", 
            temperature=0.0
        )
        
        message = response.choices[0].message
        
        # 1. 优先检查 Tool Calls
        if message.tool_calls:
            print(f"⚡ LLM 触发了 {len(message.tool_calls)} 个工具调用。")
            steps = []
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                raw_args = tool_call.function.arguments
                
                # --- 🛡️ 增强的参数解析逻辑 (容错机制) ---
                arguments = {}
                try:
                    # 尝试 1: 标准 JSON 解析
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError as e:
                    print(f"⚠️ 标准 JSON 解析失败: {e}")
                    print(f"   [原始参数]: {raw_args}")
                    print("   -> 尝试使用 Python AST 解析 (处理单引号)...")
                    try:
                        # 尝试 2: Python 字面量解析 (处理 {'key': 'value'} 情况)
                        arguments = ast.literal_eval(raw_args)
                        print("   ✅ AST 解析成功！")
                    except Exception as e2:
                        print(f"❌ 严重错误: 参数无法解析。忽略此步骤。Errors: {e}, {e2}")
                        continue # 跳过这个损坏的步骤

                steps.append({
                    "function": func_name,
                    "parameters": arguments
                })
            
            return json.dumps({"steps": steps})
            
        # 2. 检查 content 中的文本 JSON (兼容旧习惯)
        elif message.content:
             print(f"\n[LLM 回复文本]: {message.content}\n")
             # 简单的清洗逻辑，尝试提取 markdown 里的 json
             content = message.content
             if "```json" in content:
                 content = content.split("```json")[1].split("```")[0]
             elif "```" in content:
                 content = content.split("```")[1].split("```")[0]
             
             try:
                 # 同样尝试双重解析
                 try:
                    json_obj = json.loads(content.strip())
                 except:
                    json_obj = ast.literal_eval(content.strip())
                    
                 if "steps" in json_obj:
                     return json.dumps(json_obj)
             except:
                 pass

        print("⚠️ LLM 未生成任何有效指令。")
        return json.dumps({"steps": []})

    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        # 打印完整的错误堆栈有助于调试
        import traceback
        traceback.print_exc()
        return json.dumps({"steps": []})



FUNCTION_MAP = {
    "extrude_cylinder": lib.extrude_cylinder,
    "create_cut_extrude_circle": lib.create_cut_extrude_circle,
    "extrude_rectangle": lib.extrude_rectangle,
    "create_cut_extrude_rectangle": lib.create_cut_extrude_rectangle,

}

def dispatch_instructions(swModel: Any, llm_json_output: str) -> bool:
    """
    解析 LLM 输出的 JSON 指令序列，并在 SolidWorks 中执行建模操作。
    兼容 tools_schema 的各种返回情况。
    """
    
    # 🌟 调试：打印 LLM 到底返回了什么
    print(f"\n[DEBUG] LLM 原始输出:\n{llm_json_output}\n")
    
    try:
        data = json.loads(llm_json_output)
        instructions = data.get("steps")
        
        # 处理空步骤的情况（如果是聊天而非指令，tools 可能返回空列表）
        if instructions is None:
            print("❌ 解析后未找到有效的 'steps' 键。")
            return False
        
        if len(instructions) == 0:
            print("⚠️ LLM 未生成任何建模步骤。")
            return True

    except json.JSONDecodeError:
        print("❌ JSON 解析错误。")
        return False

    print("\n--- 🧠 Agent 规划完成，开始执行建模步骤 ---")

    for i, instruction in enumerate(instructions):
        # 兼容 function 字段或 name 字段
        # (OpenAI Tool Call 原始返回通常是 name，如果你在 connector 里转成了 function 也没问题，这里双重兼容)
        func_name = instruction.get("function") or instruction.get("name")
        params = instruction.get("parameters", {})
        
        if func_name in FUNCTION_MAP:
            target_func = FUNCTION_MAP[func_name]
            
            # --- 🛡️ 参数清洗与校验逻辑 🛡️ ---
            sig = inspect.signature(target_func)
            
            # 1. 识别有效参数 (排除 swModel)
            valid_args = [name for name in sig.parameters.keys() if name != 'swModel']
            
            # 2. 识别必填参数 (没有默认值的参数)
            required_args = {
                name for name, param in sig.parameters.items() 
                if param.default == inspect.Parameter.empty and name != 'swModel'
            }
            
            # 3. 构建清洗后的参数字典
            cleaned_params = {}
            for key, value in params.items():
                if key in valid_args:
                    cleaned_params[key] = value
                elif key in ["swModel", "self"]: 
                    continue # 忽略系统参数
                else:
                    # 即使使用了 tools_schema，保留这个警告也是好习惯
                    print(f"   ⚠️ [警告] 步骤 {i+1}: 自动移除多余参数 '{key}'")

            # 4. 检查是否缺少必填参数
            missing_keys = required_args - set(cleaned_params.keys())
            if missing_keys:
                print(f"❌ 步骤 {i+1} 错误: 函数 '{func_name}' 缺少必要参数: {missing_keys}")
                return False 

            # --- 🚀 执行逻辑 🚀 ---
            try:
                print(f"[{i+1}/{len(instructions)}] 正在执行: {func_name} (参数: {list(cleaned_params.keys())})...")
                
                # 🔴 关键点：一定要用 cleaned_params
                result = FUNCTION_MAP[func_name](swModel, **cleaned_params)
                
                if not result:
                    print(f"❌ 步骤 {i+1} 执行返回 False，建模中止。")
                    return False
                    
            except TypeError as e:
                print(f"❌ 步骤 {i+1} 代码执行异常: {e}")
                return False
            except Exception as e:
                print(f"❌ 步骤 {i+1} 发生未知错误: {e}")
                return False
                
        else:
            print(f"⚠️ 无法识别的函数名称: {func_name}，跳过此步骤。")
            
    print("✅ 所有建模步骤成功完成！")
    return True






