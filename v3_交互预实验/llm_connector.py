from openai import OpenAI
import json  
import lib
from typing import Dict, Any, List, Union  # 👈 确保这里加上了 Union
import inspect
import ast  # 🌟 必须导入此模块
import re  # 必须导入正则表达式模块


# --- 1. 配置和客户端初始化 ---
client = OpenAI(api_key="sk-hhdlfuwibkcceysdqnszndquuyhuoaavvrdtnzqltttejdnt", 
                base_url="https://api.siliconflow.cn/v1")

# ---大模型参数-----
LLM_MODEL_NAME = "zai-org/GLM-4.6"  #   Qwen/Qwen3-235B-A22B  deepseek-ai/DeepSeek-V3  deepseek-ai/DeepSeek-V3.2  zai-org/GLM-4.6能实现画五角星   moonshotai/Kimi-K2-Thinking    
# 系统 Prompt
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

一次性把后续所有操作都发出来！
"""

# 定义工具描述 (Tools Schema)
# llm_connector.py

tools_schema = [
    # --- 1. 选面工具 ---
    {
        "type": "function",
        "function": {
            "name": "select_face",
            "description": "空间几何选面工具。用于在多实体环境中精确定位。逻辑：当多个实体具有相同朝向的面时，通过 position_filter [x, y, z] 指定目标面中心的大致空间位置，系统将选中距离该点最近的面。选中后，后续建模将以此面的中心作为坐标原点 (0,0)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["TOP", "BOTTOM", "LEFT", "RIGHT", "FRONT", "BACK"],
                        "description": "目标面的法线朝向。"
                    },
                    "position_filter": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "可选。目标面中心点的参考坐标 [x, y, z]。用于区分不同实体上方向相同的面。"
                    },
                    "index": {
                        "type": "integer",
                        "description": "可选。若不提供位置过滤，则按该轴向坐标排序选择（0为最外侧）。"
                    }
                },
                "required": ["direction"]
            }
        }
    },

    # --- 2. 圆柱拉伸 ---
    {
        "type": "function",
        "function": {
            "name": "extrude_cylinder",
            "description": "创建圆柱体。逻辑：如果在调用此工具前已经选中了一个面，将在该面上生成；否则默认在 Top Plane 生成。",
            "parameters": {
                "type": "object",
                "properties": {
                    "radius_m": {
                        "type": "number",
                        "description": "圆柱体的半径 (米)"
                    },
                    "height_m": {
                        "type": "number",
                        "description": "圆柱体的高度 (米)"
                    },
                    "center_x_m": {
                        "type": "number",
                        "description": "相对于绘图面的局部 X 坐标 (米)，默认为 0.0"
                    },
                    "center_y_m": {
                        "type": "number",
                        "description": "相对于绘图面的局部 Y 坐标 (米)，默认为 0.0"
                    }
                },
                "required": ["radius_m", "height_m"]
            }
        }
    },

    # --- 3. 圆孔切除 ---
    {
        "type": "function",
        "function": {
            "name": "create_cut_extrude_circle",
            "description": "切除圆形孔。逻辑：如果在调用此工具前已经选中了一个面，将在该面上打孔；否则默认在 Top Plane 打孔。",
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
                        "description": "模式：'THRU_ALL' (贯穿) 或 'BLIND' (盲孔)"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "切除深度 (米)。当 mode 为 'BLIND' 时必须提供。"
                    },
                    "center_x": {
                        "type": "number",
                        "description": "相对于绘图面的局部 X 坐标 (米)"
                    },
                    "center_y": {
                        "type": "number",
                        "description": "相对于绘图面的局部 Y 坐标 (米)"
                    },
                    "flip_direction": {
                        "type": "boolean",
                        "description": "是否翻转切除方向。True=反向切除，False=正向切除。如果切除变成了切空气（没切到实体），通常需要改变这个值。"
                    }
                },
                "required": ["radius_m"]
            }
        }
    },

    # --- 4. 长方体拉伸 ---
    {
            "type": "function",
            "function": {
                "name": "extrude_rectangle",
                "description": "通用长方体拉伸工具。建模逻辑：1. height_m 是拉伸方向的长度（如立柱的高度）。2. 若之前调用过 select_face，则 center_x/y 是相对于该面中心的局部坐标；若未选面，则是在 Top Plane 上的世界坐标。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "length_m": {"type": "number", "description": "草图中的宽度 (X)"},
                        "width_m": {"type": "number", "description": "草图中的深度 (Y)"},
                        "height_m": {"type": "number", "description": "拉伸出来的长度 (Z/高度)"},
                        "center_x_m": {"type": "number", "description": "草图中心 X 偏移"},
                        "center_y_m": {"type": "number", "description": "草图中心 Y 偏移"}
                    },
                    "required": ["length_m", "width_m", "height_m"]
                }
            }
    },


    # --- 5. 矩形切除 ---
    {
        "type": "function",
        "function": {
            "name": "create_cut_extrude_rectangle",
            "description": "切除矩形孔。逻辑：如果在调用此工具前已经选中了一个面，将在该面上切除；否则默认在 Top Plane 切除。",
            "parameters": {
                "type": "object",
                "properties": {
                    "length_m": {
                        "type": "number",
                        "description": "切除矩形 X 方向长度 (米)"
                    },
                    "width_m": {
                        "type": "number",
                        "description": "切除矩形 Y 方向宽度 (米)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["THRU_ALL", "BLIND"],
                        "description": "模式：'THRU_ALL' (贯穿) 或 'BLIND' (盲孔)"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "切除深度 (米)。当 mode 为 'BLIND' 时必须提供。"
                    },
                    "center_x": {
                        "type": "number",
                        "description": "相对于绘图面的局部 X 坐标 (米)"
                    },
                    "center_y": {
                        "type": "number",
                        "description": "相对于绘图面的局部 Y 坐标 (米)"
                    },
                    "flip_direction": {
                        "type": "boolean",
                        "description": "是否翻转切除方向。True=反向切除，False=正向切除。通常在平面上向下挖孔需要根据法线判断。"
                    }
                },
                "required": ["length_m", "width_m"]
            }
        }
    },

    # --- 6. 撤销 ---
    {
        "type": "function",
        "function": {
            "name": "undo_last_step",
            "description": "撤销上一步操作。用途：1. 如果选错了面，调用此工具取消选择。2. 如果上一步建模建错了（比如位置不对），调用此工具可以删除刚刚生成的实体。无参数。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    # --- 7. 拉伸正多边形 ---
    {
        "type": "function",
        "function": {
            "name": "extrude_polygon",
            "description": "在指定平面上创建并拉伸正多边形实体（如六边形、五边形等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {
                        "type": "integer",
                        "description": "多边形的边数（例如 6 代表六边形，3 代表等边三角形）。"
                    },
                    "radius_m": {
                        "type": "number",
                        "description": "外接圆半径（米）。"
                    },
                    "height_m": {
                        "type": "number",
                        "description": "拉伸高度（米）。"
                    },
                    "center_x_m": {
                        "type": "number",
                        "description": "中心点 X 坐标，默认为 0.0。"
                    },
                    "center_y_m": {
                        "type": "number",
                        "description": "中心点 Y 坐标，默认为 0.0。"
                    }
                },
                "required": ["sides", "radius_m", "height_m"]
            }
        }
    },
    # --- 8. 切除正多边形 ---
    {
        "type": "function",
        "function": {
            "name": "create_cut_extrude_polygon",
            "description": "在指定平面上通过正多边形草图进行拉伸切除（挖孔）。具备自动方向纠错功能。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {
                        "type": "integer",
                        "description": "多边形的边数。"
                    },
                    "radius_m": {
                        "type": "number",
                        "description": "多边形外接圆半径（米）。"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["THRU_ALL", "BLIND"],
                        "description": "切除模式：'THRU_ALL' (完全贯穿) 或 'BLIND' (指定深度)。"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "切除深度（米），仅在 BLIND 模式下有效。"
                    },
                    "center_x": {
                        "type": "number",
                        "description": "中心 X 坐标。"
                    },
                    "center_y": {
                        "type": "number",
                        "description": "中心 Y 坐标。"
                    },
                    "flip_direction": {
                        "type": "boolean",
                        "description": "是否翻转切除方向。默认为 False。"
                    }
                },
                "required": ["sides", "radius_m"]
            }
        }
    },
    # --- 9. 矩形旋转生成 ---
    {
        "type": "function",
        "function": {
            "name": "revolve_rectangle_feature",
            "description": "通过旋转截面生成实体。适用于圆环、瓶子或轴类零件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "width_m": {"type": "number", "description": "旋转截面的宽度"},
                    "height_m": {"type": "number", "description": "旋转截面的高度"},
                    "offset_m": {"type": "number", "description": "截面距离中心轴的距离。0代表实心，大于0代表中间有孔的环状物。"},
                    "angle_deg": {"type": "number", "description": "旋转角度，默认360"}
                },
                "required": ["width_m", "height_m", "offset_m"]
            }
        }
    },
    # --- 10. 新建草图 ---
    {
        "type": "function",
        "function": {
            "name": "start_sketch",
            "description": "在当前选定面上开始一个新草图会话。这是绘制复杂图形的第一步。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # --- 11. 在当前草图中画线 ---
    {
        "type": "function",
        "function": {
            "name": "sketch_line",
            "description": "在当前草图中画线。注意：要形成闭合图形，下一条线的起点必须是上一条线的终点。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "number"}, "y1": {"type": "number"},
                    "x2": {"type": "number"}, "y2": {"type": "number"}
                },
                "required": ["x1", "y1", "x2", "y2"]
            }
        }
    },
    # --- 12. 当前草图按指定高度拉伸 ---
    {
        "type": "function",
        "function": {
            "name": "extrude",
            "description": "把当前草图按指定高度拉伸。",
            "parameters": {
                "type": "object",
                "properties": {
                    "height_m": {"type": "number", "description": "拉伸高度"}
                },
                "required": ["height_m"]
            }
        }
    },
    # --- 10. 绘制样条曲线 (Spline) ---
    {
        "type": "function",
        "function": {
            "name": "sketch_spline",
            "description": "在当前草图中绘制平滑的样条曲线。适用于创建花瓶、酒杯等具有有机弧线的轮廓。注意：为了形成闭合实体，曲线的终点应能与其他线条连接回中心轴。",
            "parameters": {
                "type": "object",
                "properties": {
                    "points": {
                        "type": "array",
                        "description": "坐标点列表，格式为 [[x1, y1], [x2, y2], ...]。系统会自动在这些点之间生成平滑曲线。",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    }
                },
                "required": ["points"]
            }
        }
    },

    # --- 11. 通用旋转特征 (Revolve)生成实心回转体或薄壁壳体 ---
    {
        "type": "function",
        "function": {
            "name": "revolve_sketch",
            "description": "通用旋转建模工具。可以生成实心回转体或薄壁壳体。逻辑：如果不需要厚度（实心体），不传 thickness_m；如果需要生成空心外壳，请指定 thickness_m。",
            "parameters": {
                "type": "object",
                "properties": {
                    "angle_deg": {"type": "number", "description": "旋转角度，默认 360"},
                    "thickness_m": {
                        "type": "number", 
                        "description": "必选参数。如果提供，将生成该厚度的薄壁实体（米）。若不提供，则生成实心体。"
                    }
                },
                "required": ["angle_deg", "thickness_m"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "sketch_centerline",
            "description": "在当前草图中绘制中心线（构造线）。核心用途：1. 作为旋转特征（revolve_sketch）的旋转轴；2. 作为镜像或对齐的参考线。注意：旋转体建模时，必须先画中心线，再画截面轮廓。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "number", "description": "起点 X 坐标 (米)"},
                    "y1": {"type": "number", "description": "起点 Y 坐标 (米)"},
                    "x2": {"type": "number", "description": "终点 X 坐标 (米)"},
                    "y2": {"type": "number", "description": "终点 Y 坐标 (米)"}
                    },
                "required": ["x1", "y1", "x2", "y2"]
            }
        }
    },
   
]





###   创建一个 SWAgentBrain 类来管理对话历史。
class SWAgentBrain:
    def __init__(self, system_prompt, model_name):
        self.model_name = model_name
        # 初始化历史记录，放入系统提示词
        self.history = [{"role": "system", "content": system_prompt}]

    def get_plan(self, user_input: str):
        """对齐主程序接口，返回解析后的步骤列表"""
        return self.chat(user_input)

    def chat(self, user_input: str):
        """
        接收用户输入，发送给 LLM，并更新历史记录
        """
        # 1. 将用户输入加入历史
        self.history.append({"role": "user", "content": user_input})
        
        try:
            print("--- 🤖 思考中... ---")
            response = client.chat.completions.create(
                model=self.model_name,
                messages=self.history,  # 关键：发送完整的历史记录
                tools=tools_schema,       
                tool_choice="auto", 
                temperature=0.0
            )
            
            message = response.choices[0].message
            
            # 2. 将 LLM 的回复 (可能是文本，可能是工具调用) 加入历史
            # 注意：OpenAI 格式要求必须把 message 对象存回去，否则下一轮会报错
            self.history.append(message)

            # --- 解析逻辑 (保持你原有的解析逻辑，略微适配 message 对象) ---
            if message.tool_calls:
                print(f"⚡ 规划了 {len(message.tool_calls)} 个操作。")
                steps = []
                for tool_call in message.tool_calls:
                    # (这里复用你之前的解析代码)
                    func_name = tool_call.function.name
                    raw_args = tool_call.function.arguments
                    try:
                        arguments = json.loads(raw_args)
                    except:
                        try:
                            arguments = ast.literal_eval(raw_args)
                        except:
                            continue
                    steps.append({"function": func_name, "parameters": arguments})
                
                # 返回结构化步骤
                return steps
            
            elif message.content:
                # 如果 LLM 只是说话（比如“好的，已修改完成”），没有调用工具
                print(f"🤖 Agent: {message.content}")
                return [] # 空步骤
                
        except Exception as e:
            print(f"❌ API 请求失败: {e}")
            return []

    def add_execution_result(self, result_content: str):
        """
        关键：将 SolidWorks 的执行结果（成功/失败）告诉 LLM
        这样 LLM 才知道它的操作是否生效，或者是否需要修正参数
        """
        # 在 OpenAI 格式中，通常用 tool 角色或者 user 角色反馈结果
        # 这里简化处理，作为 system 或 user 反馈均可，目的是让 LLM 看到结果
        self.history.append({
            "role": "user", 
            "content": f"[系统反馈] 上一步操作结果: {result_content}"
        })

# ... (FUNCTION_MAP 和 dispatch_instructions 保持不变，但 dispatch 需要返回结果字符串) ...

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
        
        # 1. openAI的标准，优先检查 Tool Calls
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

            # ======= 新增：Kimi 标签格式兼容逻辑 (保持原有逻辑向下兼容) =======
            if "<|tool_calls_section_begin|>" in content:
                # 使用 \| 来转义正则中的竖线
                tag_pattern = r"<\|tool_call_begin\|>functions\.(.*?):.*?<\|tool_call_argument_begin\|>(.*?)<\|tool_call_end\|>"
                matches = re.findall(tag_pattern, content, re.DOTALL)
                
                if matches:
                    steps = []
                    for func_name, args_raw in matches:
                        try:
                            # 清洗可能的空白字符并解析
                            steps.append({
                                "function": func_name.strip(),
                                "parameters": json.loads(args_raw.strip())
                            })
                        except:
                            continue
                    if steps:
                        print(f"✅ 修正解析：成功提取 {len(steps)} 个 Kimi 建模步骤。")
                        return json.dumps({"steps": steps})

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
    "start_sketch": lib.start_sketch,

    # --- 基础拉伸与切除 ---
    "extrude": lib.extrude,   # 通用拉伸功能
    "extrude_cylinder": lib.extrude_cylinder,
    "create_cut_extrude_circle": lib.create_cut_extrude_circle,
    "extrude_rectangle": lib.extrude_rectangle,
    "create_cut_extrude_rectangle": lib.create_cut_extrude_rectangle,
    "extrude_polygon": lib.extrude_polygon,
    "create_cut_extrude_polygon": lib.create_cut_extrude_polygon,
    
    # --- 底层草图工具 ---
    "sketch_line": lib.sketch_line,
    "sketch_spline": lib.sketch_spline,

    
    # --- 旋转轴线 ---
    "sketch_centerline": lib.sketch_centerline,
    # --- 旋转执行器 ---
    "revolve_rectangle_feature": lib.revolve_rectangle_feature,
    "revolve_sketch": lib.revolve_sketch,

    # --- 辅助与撤销 ---
    "select_face": lib.select_face, 
    "undo_last_step": lib.undo_last_step,
}

def dispatch_instructions(swModel: Any, llm_output: Union[str, List[dict]]) -> str:
    """
    完善后的调度器：
    1. 自动处理 JSON 字符串或解析后的列表。
    2. 汇总每一步的详细执行日志，用于闭环反馈。
    """
    execution_logs = []
    instructions = []

    # --- 🛡️ 兼容性检查：确保输入是可迭代的步骤列表 ---
    if isinstance(llm_output, str):
        try:
            data = json.loads(llm_output)
            instructions = data.get("steps", []) if isinstance(data, dict) else data
        except json.JSONDecodeError:
            return "❌ 调度错误：无法解析 LLM 返回的 JSON 字符串。"
    elif isinstance(llm_output, list):
        instructions = llm_output
    else:
        return "⚠️ 调度错误：无效的指令格式。"

    if not instructions:
        return "⚠️ 系统提示：未生成任何有效的建模指令。"

    print(f"\n--- 🧠 Agent 开始执行指令 (共 {len(instructions)} 步) ---")

    for i, instruction in enumerate(instructions):
        func_name = instruction.get("function") or instruction.get("name")
        params = instruction.get("parameters", {})
        
        if func_name in FUNCTION_MAP:
            target_func = FUNCTION_MAP[func_name]
            
            # --- 🛡️ 参数清洗与类型安全处理 ---
            sig = inspect.signature(target_func)
            valid_args = [name for name in sig.parameters.keys() if name != 'swModel']
            
            cleaned_params = {}
            for k, v in params.items():
                if k in valid_args:
                    # 关键：将数值强制转换为 float，避免 SW API 报错
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        cleaned_params[k] = float(v)
                    else:
                        cleaned_params[k] = v

            # --- 🚀 执行并收集日志 ---
            try:
                print(f"👉 步骤 {i+1}: 执行 {func_name}...")
                # 执行函数
                success = target_func(swModel, **cleaned_params)
                
                status_icon = "✅" if success else "❌"
                log_entry = f"{status_icon} 步骤 {i+1} [{func_name}]: {'成功' if success else '失败 (SW内部错误)'}"
                execution_logs.append(log_entry)
                
                # 如果某一步失败，停止后续操作，防止模型逻辑错乱
                if not success:
                    execution_logs.append("🛑 由于上步失败，后续建模已中止。")
                    break 
            except Exception as e:
                err_msg = f"💥 步骤 {i+1} [{func_name}] 运行时异常: {str(e)}"
                execution_logs.append(err_msg)
                break
        else:
            execution_logs.append(f"❓ 步骤 {i+1}: 无法识别工具 '{func_name}'")

    # 返回所有日志，这将作为大模型下一轮对话的参考
    return "\n".join(execution_logs)




